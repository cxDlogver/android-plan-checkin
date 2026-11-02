#!/usr/bin/env python3
"""Derive one atomic requirement per transition and an exact minimum-visit coverage route."""
import argparse
import json
import os
from pathlib import Path
from analyze import SKILL_DIR, check_html, digest, evaluate as evaluate_states, html_text, load_json, resolve_file, schema_errors
from coverage_route import minimum_visit_plan

OUTPUT_NAME="atomic-requirements.json"
def output_path(graph): return graph.parent/OUTPUT_NAME

def derive(state_model,graph,path):
    transitions=sorted(state_model["transitions"],key=lambda e:e["id"])
    requirements=[{"id":"R-"+e["id"],"transitionId":e["id"]} for e in transitions]
    sequence,minimum=minimum_visit_plan(state_model)
    by_req={"R-"+t["id"]:t for t in transitions};initial={s["id"] for s in state_model["states"] if s["isInitial"]}
    edges=[];seen=set()
    for a,b in zip(sequence,sequence[1:]):
        if (a,b) in seen: continue
        seen.add((a,b));before=by_req[a];after=by_req[b]
        edge={"id":"L"+str(len(edges)+1).zfill(6),"from":a,"to":b}
        if before["to"]==after["from"]: edge.update(kind="handoff",viaStateId=before["to"])
        elif after["from"] in initial: edge["kind"]="restart"
        else: raise ValueError("Coverage route contains an illegal requirement entry")
        edges.append(edge)
    return {"schemaVersion":"1.0.0","title":state_model["title"]+" · 原子需求图","revision":state_model["revision"],
            "stateGraph":{"path":os.path.relpath(graph,path.parent).replace(os.sep,"/"),"sha256":digest(state_model)},
            "requirements":requirements,"edges":edges,
            "coverage":{"algorithm":"min-cost-circulation-with-free-restarts","optimality":"proven","sequence":sequence,
                        "visitCount":len(sequence),"minimumVisitCount":minimum,"additionalVisitCount":minimum-len(requirements)}}

def evaluate(model,path,workspace,with_html=False):
    checks={k:[] for k in ("schema","state-graph","one-to-one","coverage","selected-edges","optimality","html")}
    def result():
        return {"scope":"atomic-requirements-and-state-graph-consistency","status":"failed" if any(checks.values()) else "passed",
                "checks":[{"id":k,"status":"failed" if v else "not-tested" if k=="html" and not with_html else "passed","findings":v} for k,v in checks.items()]}
    checks["schema"]=schema_errors(model,load_json(SKILL_DIR/"assets"/"atomic-requirements.schema.json"))
    if checks["schema"]:
        report=result()
        for check in report["checks"][1:]: check["status"]="not-tested"
        return report
    try:
        graph=resolve_file(path,model["stateGraph"]["path"],workspace)
        if graph==path.resolve(): raise ValueError("Atomic graph cannot reference itself as its state graph")
        state_model=load_json(graph)
        upstream=evaluate_states(state_model,graph,workspace)
        if upstream["status"]!="passed": checks["state-graph"].append(upstream)
        elif model["stateGraph"]["sha256"]!=digest(state_model): checks["state-graph"].append("State graph digest changed; regenerate the atomic graph")
    except (OSError,ValueError,KeyError,TypeError) as exc: checks["state-graph"].append(str(exc))
    if checks["state-graph"]:
        report=result()
        for check in report["checks"][2:]: check["status"]="not-tested"
        return report
    expected=derive(state_model,graph,path)
    if model["title"]!=expected["title"] or model["revision"]!=state_model["revision"]: checks["one-to-one"].append("Title and revision must derive from the referenced state graph")
    if model["requirements"]!=expected["requirements"]: checks["one-to-one"].append("Requirements must map every transition exactly once, with deterministic IDs and order")
    requirement_map={r["id"]:r for r in model["requirements"]};transition_map={t["id"]:t for t in state_model["transitions"]}
    initial={s["id"] for s in state_model["states"] if s["isInitial"]};sequence=model["coverage"]["sequence"]
    if set(sequence)!=set(requirement_map): checks["coverage"].append("Coverage must visit every requirement and no unknown IDs")
    if sequence and sequence[0] in requirement_map:
        first=transition_map.get(requirement_map[sequence[0]]["transitionId"])
        if first and first["from"] not in initial: checks["coverage"].append("The first visit must be an initial requirement")
    for a,b in zip(sequence,sequence[1:]):
        if a not in requirement_map or b not in requirement_map: continue
        ta=transition_map.get(requirement_map[a]["transitionId"]);tb=transition_map.get(requirement_map[b]["transitionId"])
        if ta and tb and ta["to"]!=tb["from"] and tb["from"] not in initial: checks["coverage"].append("Illegal entry: "+a+" -> "+b)
    if model["coverage"]["visitCount"]!=len(sequence): checks["coverage"].append("visitCount must count all visits, including repeats")
    if model["coverage"]!=expected["coverage"]: checks["optimality"].append("Route and minimum cost must match the deterministic exact optimizer")
    if model["edges"]!=expected["edges"]: checks["selected-edges"].append("Keep only consecutive pairs used by the selected route, with correct handoff/restart semantics")
    if with_html: checks["html"]=check_html(model,path,state_model)
    return result()

def build(graph,workspace):
    state_model=load_json(graph);upstream=evaluate_states(state_model,graph,workspace)
    if upstream["status"]!="passed": return upstream
    path=output_path(graph)
    if path.resolve()==graph.resolve(): raise ValueError("State graph must have a different filename from atomic-requirements.json")
    model=derive(state_model,graph,path);report=evaluate(model,path,workspace)
    if report["status"]!="passed": return report
    html=html_text(model,state_model)
    path.write_text(json.dumps(model,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    path.with_suffix(".html").write_text(html,encoding="utf-8")
    return evaluate(model,path,workspace,with_html=True)

def check_package(graph,workspace):
    path=output_path(graph)
    if not path.is_file(): return {"scope":"atomic-requirements-and-state-graph-consistency","status":"failed","error":"Missing atomic-requirements.json"}
    try: return evaluate(load_json(path),path,workspace,with_html=True)
    except (OSError,ValueError,KeyError,TypeError) as exc: return {"scope":"atomic-requirements-and-state-graph-consistency","status":"failed","error":str(exc)}

def execute(command,path,workspace):
    path=path.resolve();workspace=workspace.resolve()
    try: path.relative_to(workspace)
    except ValueError: raise ValueError("Graph path escapes workspace")
    report=build(path,workspace) if command=="build" else evaluate(load_json(path),path,workspace,with_html=True)
    print(json.dumps(report,ensure_ascii=False,indent=2));return 0 if report["status"]=="passed" else 1

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command",choices=("build","check"));parser.add_argument("model",type=Path);parser.add_argument("--workspace",required=True,type=Path)
    args=parser.parse_args()
    try: return execute(args.command,args.model,args.workspace)
    except (OSError,ValueError,KeyError,TypeError,RecursionError) as exc:
        print(json.dumps({"status":"failed","error":str(exc)},ensure_ascii=False));return 1

if __name__=="__main__": raise SystemExit(main())
