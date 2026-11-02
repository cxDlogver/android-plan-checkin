#!/usr/bin/env python3
"""Create, check and remove a separate requirement-analysis work record."""
import argparse
import json
import re
from pathlib import Path
from analyze import SKILL_DIR, action_key, all_ids, canonical, evaluate, load_json, pointer, raw_hash, resolve_file, schema_errors

from atomic import check_package

REVIEW_NAMES=("scope","facts","operations","inheritance","branches","coverage")

def initial_value(definition,schema):
    if "$ref" in definition:
        target=schema
        for part in definition["$ref"][2:].split("/"): target=target[part]
        return initial_value(target,schema)
    if "const" in definition: return definition["const"]
    if "default" in definition: return json.loads(json.dumps(definition["default"]))
    if definition.get("type")=="object":
        return {key:initial_value(definition["properties"][key],schema) for key in definition.get("required",[])}
    if definition.get("type")=="array": return []
    if "anyOf" in definition:
        if any(item.get("type")=="null" for item in definition["anyOf"]): return None
        return initial_value(definition["anyOf"][0],schema)
    if "enum" in definition: return definition["enum"][0]
    if definition.get("type")=="string": return ""
    raise ValueError("Schema cannot initialize this work field")

def work_file(graph): return graph.parent/".work"/"analysis-work.json"

def bounded(file,workspace):
    file=file.resolve()
    try: file.relative_to(workspace.resolve())
    except ValueError: raise ValueError("Work path escapes workspace")
    return file

def file_paths(source):
    return [source["path"]] if source["kind"]=="document" else [source["structurePath"],source["screenshotPath"]]

def validate_source(source,graph,workspace):
    if source["kind"]=="document":
        file=resolve_file(graph,source["path"],workspace);raw=file.read_bytes()
        if raw_hash(raw)!=source["sha256"]: raise ValueError("Document hash changed: "+source["path"])
        text=raw.decode("utf-8-sig").replace("\r\n","\n");loc=source["locator"]
        lines=re.fullmatch(r"L(\d+)(?:-L?(\d+))?",loc)
        if lines:
            first,last=int(lines[1]),int(lines[2] or lines[1])
            if first<1 or last<first or last>len(text.splitlines()): raise ValueError("Invalid line locator: "+loc)
            text="\n".join(text.splitlines()[first-1:last])
        elif file.suffix.lower()==".json": text=canonical(pointer(json.loads(text),loc))
        elif loc!="$" and loc not in text: raise ValueError("Heading not found: "+loc)
        if "quote" in source and source["quote"].replace("\r\n","\n") not in text: raise ValueError("Quote does not match source locator")
    else:
        structured=resolve_file(graph,source["structurePath"],workspace);image=resolve_file(graph,source["screenshotPath"],workspace)
        if raw_hash(structured.read_bytes())!=source["structureSha256"] or raw_hash(image.read_bytes())!=source["screenshotSha256"]: raise ValueError("UI source hash changed")
        data=load_json(structured)
        if data.get("id")!=source["documentId"] or not set(source["nodeIds"]).issubset(all_ids(data.get("tree",data))): raise ValueError("UI document or nodes differ")

def source_key(source):
    return canonical({k:v for k,v in source.items() if k not in ("quote","version")})

def check_modeling_evidence(work,model,source_check,registered,record):
    states={s["id"]:s for s in model["states"]}
    edges={e["id"]:e for e in model["transitions"]}
    constraints={c["id"] for c in model["constraints"]}
    initial={s["id"] for s in model["states"] if s["isInitial"]}
    connected={end for e in edges.values() for end in (e["from"],e["to"])}
    def check_source(source,label):
        source_check(source,label)
        if not set(file_paths(source)).issubset(registered):
            record("documents","failed",label+": source is not registered")
    seen=set()
    for entry in work["entries"]:
        ident=entry["stateId"];label="Entry "+ident
        check_source(entry["source"],label)
        if ident in seen: record("entry-evidence","failed",label+": duplicate entry evidence")
        seen.add(ident)
        if ident not in initial:
            record("entry-evidence","failed",label+": evidence must belong to an initial state")
            continue
        if source_key(entry["source"]) not in {source_key(s) for s in states[ident]["source"]}:
            record("entry-evidence","failed",label+": entry source must also be a direct state source")
        if ident not in connected and not entry.get("isolationReason","").strip():
            record("entry-evidence","blocked",label+": isolated state needs its independent acceptance basis")
        if ident in connected and "isolationReason" in entry:
            record("entry-evidence","failed",label+": isolationReason is only for states without edges")
    for ident in sorted(initial-seen):
        record("entry-evidence","blocked","Initial state lacks entry or preparation evidence: "+ident)
    modeled=set()
    for i,requirement in enumerate(work["requirements"]):
        if requirement["classification"]!="included": continue
        analysis=requirement["actionAnalysis"];label="Requirement "+str(i+1)
        if analysis["status"]=="pending": record("action-coverage","blocked",label+": action analysis pending")
        elif analysis["status"]=="failed": record("action-coverage","failed",label+": action analysis failed")
        elif not analysis["evidence"].strip(): record("action-coverage","failed",label+": action analysis needs source-grounded evidence, including when no action is found")
        targets={(t["collection"],t["id"]) for t in requirement["targets"]}
        local_keys=set()
        for j,action in enumerate(analysis["actions"]):
            item=label+" action "+str(j+1);disposition=action["disposition"]
            key=action_key(action)
            if key in local_keys: record("action-coverage","failed",item+": duplicate source/action/input assessment")
            local_keys.add(key)
            if action["from"] is not None and action["from"] not in states:
                record("action-coverage","failed",item+": unknown initial state "+action["from"])
            if not set(action["expectedTargets"]).issubset(states):
                record("action-coverage","failed",item+": expected result state is missing")
            if "resolutionSource" in action: check_source(action["resolutionSource"],item)
            if disposition=="open":
                record("action-coverage","blocked",item+": action or result is unresolved")
            if disposition=="modeled":
                if action["from"] is None or not action["transitionIds"] or not action["expectedTargets"]:
                    record("action-coverage","failed",item+": modeled action needs an initial state, expected results and transitions")
                actual_targets=set()
                for ident in action["transitionIds"]:
                    edge=edges.get(ident)
                    if edge is None:
                        record("action-coverage","failed",item+": missing transition "+ident)
                        continue
                    modeled.add(ident);actual_targets.add(edge["to"])
                    if action_key(edge)!=key:
                        record("action-coverage","failed",item+": transition does not match the assessed initial state/action/input: "+ident)
                    if ("transitions",ident) not in targets:
                        record("action-coverage","failed",item+": transition is not in this requirement's scope mapping: "+ident)
                    if source_key(requirement["source"]) not in {source_key(s) for s in edge["source"]}:
                        record("action-coverage","failed",item+": transition lacks this action's direct requirement source: "+ident)
                if actual_targets!=set(action["expectedTargets"]):
                    record("action-coverage","failed",item+": transitions do not cover the assessed result states")
            else:
                if action["transitionIds"]:
                    record("action-coverage","failed",item+": unresolved, excluded or rule-covered action cannot claim transitions")
                if disposition in ("excluded","constraint") and action["expectedTargets"]:
                    record("action-coverage","failed",item+": unmodeled action must not claim result states")
                if disposition in ("excluded","constraint") and any(action_key(e)==key for e in edges.values()):
                    record("action-coverage","failed",item+": disposition conflicts with an existing transition")
                if disposition=="excluded" and "resolutionSource" not in action:
                    record("action-coverage","failed",item+": exclusion needs a quoted scope source")
            rule_ids=action.get("constraintIds",[])
            if disposition=="constraint":
                if not rule_ids or not set(rule_ids).issubset(constraints):
                    record("action-coverage","failed",item+": name the existing global rule that covers this check")
                if any(("constraints",ident) not in targets for ident in rule_ids):
                    record("action-coverage","failed",item+": rule is not in this requirement's scope mapping")
            elif "constraintIds" in action:
                record("action-coverage","failed",item+": constraintIds is only for rule-covered checks")
    for ident in sorted(set(edges)-modeled):
        record("action-coverage","failed","Transition lacks a source-grounded action assessment: "+ident)

def check_work(work,graph,workspace,with_html=False):
    checks={k:{"id":k,"status":"passed","findings":[]} for k in ("work-schema","documents","scope-mapping","entry-evidence","action-coverage","clarifications","reviews","graph-version","graph")}
    def record(name,status,message):
        c=checks[name]
        if status=="failed" or c["status"]=="passed": c["status"]=status
        c["findings"].append(message)
    schema=load_json(SKILL_DIR/"assets"/"analysis-work.schema.json")
    errors=schema_errors(work,schema)
    if errors:
        record("work-schema","failed","; ".join(errors))
        for name in list(checks)[1:]: checks[name]["status"]="not-tested"
        return finish(checks)
    if not graph.is_file():
        record("graph","blocked","Graph is not yet available")
        for name in checks:
            if name not in ("work-schema","graph"): checks[name]["status"]="not-tested"
        return finish(checks)
    model=load_json(graph)
    graph_report=evaluate(model,graph,workspace,with_html=with_html)
    if graph_report["status"]!="passed":
        record("graph","failed",json.dumps(graph_report,ensure_ascii=False))
        if graph_report["checks"][0]["status"]=="failed":
            for name in checks:
                if name not in ("work-schema","graph"): checks[name]["status"]="not-tested"
            return finish(checks)
    collections={k:{e["id"] for e in model.get(k,[]) if isinstance(e,dict) and "id" in e} for k in ("states","transitions","constraints")}
    registered=set();cache=set()
    def source_check(source,label):
        signature=canonical(source)
        if signature in cache: return
        cache.add(signature)
        if any(".work" in Path(p).parts for p in file_paths(source)):
            record("documents","failed",label+": analysis evidence must reference original sources, not work records")
            return
        try: validate_source(source,graph,workspace)
        except (OSError,ValueError,TypeError,KeyError,IndexError) as exc: record("documents","failed",label+": "+str(exc))
    for document in work["documents"]:
        source_check(document["source"],"document")
        registered.update(file_paths(document["source"]))
    if not any(d["role"]=="prd" and d["source"]["kind"]=="document" for d in work["documents"]):
        record("documents","failed","Register the current PRD document")
    covered=set()
    for i,requirement in enumerate(work["requirements"]):
        source_check(requirement["source"],"requirement "+str(i+1))
        if not set(file_paths(requirement["source"])).issubset(registered): record("documents","failed","Requirement uses an unregistered source")
        if requirement["classification"]=="included" and not requirement["targets"]:
            record("scope-mapping","failed","Included requirement needs graph targets: "+str(i+1))
        if requirement["classification"]!="included" and requirement["targets"]:
            record("scope-mapping","failed","Excluded/context requirement must not create targets: "+str(i+1))
        for target in requirement["targets"]:
            if target["id"] not in collections[target["collection"]]: record("scope-mapping","failed","Missing graph target: "+target["id"])
            elif requirement["classification"]=="included": covered.add((target["collection"],target["id"]))
    for collection,ids in collections.items():
        for ident in sorted(ids):
            if (collection,ident) not in covered: record("scope-mapping","failed","Graph entity has no included requirement mapping: "+ident)
        for entity in model.get(collection,[]):
            for source in entity.get("source",[]):
                if any(".work" in Path(p).parts for p in file_paths(source)): record("documents","failed","Final graph references temporary work material")
                if not set(file_paths(source)).issubset(registered): record("documents","failed","Graph uses an unregistered source: "+entity.get("id","?"))
    check_modeling_evidence(work,model,source_check,registered,record)
    for i,q in enumerate(work["clarifications"]):
        if q["status"]=="open":
            record("clarifications","blocked","User answer required: "+q["question"])
            if q["answer"] is not None or q["resolution"] is not None: record("clarifications","failed","Open question carries a resolution")
        elif q["answer"] is None or not (q["resolution"] or "").strip():
            record("clarifications","failed","Resolved question needs a real answer, conversation reference and resolution")
        if "resolutionSource" in q:
            source_check(q["resolutionSource"],"clarification "+str(i+1))
            if not set(file_paths(q["resolutionSource"])).issubset(registered): record("documents","failed","Clarification resolution source is not registered")
    for name in REVIEW_NAMES:
        review=work["reviews"][name]
        if review["status"]=="pending": record("reviews","blocked","Review pending: "+name)
        elif review["status"]=="failed": record("reviews","failed","Review failed: "+name)
        elif not review["evidence"].strip(): record("reviews","failed","Review needs source-grounded evidence: "+name)
    if work["graphSha256"]!=raw_hash(graph.read_bytes()):
        record("graph-version","blocked","Graph hash is missing or changed since review")
    return finish(checks)

def finish(checks):
    statuses={c["status"] for c in checks.values()}
    return {"scope":"analysis-work-and-graph-consistency","status":"failed" if "failed" in statuses else "blocked" if "blocked" in statuses else "passed","checks":list(checks.values())}

def execute(command,graph,workspace):
    graph=bounded(graph,workspace);work_path=bounded(work_file(graph),workspace)
    if command=="init":
        work_path.parent.mkdir(parents=True,exist_ok=True)
        schema=load_json(SKILL_DIR/"assets"/"analysis-work.schema.json")
        draft=initial_value(schema,schema)
        with work_path.open("x",encoding="utf-8") as handle: handle.write(json.dumps(draft,ensure_ascii=False,indent=2)+"\n")
        print(json.dumps({"status":"created","work":str(work_path)},ensure_ascii=False));return 0
    work=load_json(work_path)
    report=check_work(work,graph,workspace,with_html=command=="finalize")
    if command=="finalize": report["scope"]="analysis-work-and-final-artifacts"
    if command=="finalize" and report["status"]!="passed": report["checks"].append({"id":"atomic-package","status":"not-tested","findings":["Complete state-model analysis before final artifact checks"]})
    if command=="finalize" and report["status"]=="passed":
        atomic_report=check_package(graph,workspace)
        report["checks"].append({"id":"atomic-package","status":atomic_report["status"],"findings":[] if atomic_report["status"]=="passed" else [atomic_report]})
        if atomic_report["status"]!="passed": report["status"]="failed"
    if command=="finalize" and report["status"]=="passed":
        if set(work_path.parent.iterdir())!={work_path}:
            report={"status":"failed","error":"Additional work files exist; review their ownership and clean them before finalizing"}
        else:
            work_path.unlink()
            work_path.parent.rmdir()
            report["cleanup"]="Removed this task's analysis-work.json and empty .work directory"
    print(json.dumps(report,ensure_ascii=False,indent=2))
    return 0 if report["status"]=="passed" else 2 if report["status"]=="blocked" else 1

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command",choices=("init","check","finalize"));parser.add_argument("graph",type=Path);parser.add_argument("--workspace",required=True,type=Path)
    args=parser.parse_args()
    try: return execute(args.command,args.graph.resolve(),args.workspace.resolve())
    except (OSError,ValueError,TypeError,KeyError,IndexError,RecursionError) as exc:
        print(json.dumps({"status":"failed","error":str(exc)},ensure_ascii=False));return 1

if __name__=="__main__": raise SystemExit(main())
