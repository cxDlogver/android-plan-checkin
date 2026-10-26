#!/usr/bin/env python3
"""Read-only validation and Canvas rendering of a final state-transition graph."""
import argparse
import hashlib
import json
import math
import re
from pathlib import Path

SKILL_DIR=Path(__file__).resolve().parents[1]

def canonical(value):
    def norm(v):
        if isinstance(v,float) and math.isfinite(v) and v.is_integer(): return int(v)
        if isinstance(v,dict): return {k:norm(x) for k,x in v.items()}
        if isinstance(v,list): return [norm(x) for x in v]
        return v
    return json.dumps(norm(value),ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False)

def digest(value): return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()
def raw_hash(value): return hashlib.sha256(value).hexdigest()
def load_json(file):
    def reject(x): raise ValueError("Non-finite JSON value: "+x)
    return json.loads(Path(file).read_text(encoding="utf-8-sig"),parse_constant=reject)

def schema_errors(value,schema,at="$",root=None):
    root=root or schema
    if schema is True: return []
    if schema is False: return [at+": forbidden"]
    if "$ref" in schema:
        target=root
        for part in schema["$ref"][2:].split("/"): target=target[part]
        return schema_errors(value,target,at,root)
    errors=[]
    if "const" in schema and canonical(value)!=canonical(schema["const"]): errors.append(at+": const mismatch")
    if "enum" in schema and canonical(value) not in {canonical(x) for x in schema["enum"]}: errors.append(at+": enum mismatch")
    typ="null" if value is None else "boolean" if isinstance(value,bool) else "object" if isinstance(value,dict) else "array" if isinstance(value,list) else "string" if isinstance(value,str) else "number" if isinstance(value,(int,float)) else "unknown"
    allowed=schema.get("type")
    if allowed:
        allowed=allowed if isinstance(allowed,list) else [allowed]
        integer=typ=="number" and math.isfinite(value) and int(value)==value
        if typ not in allowed and not (integer and "integer" in allowed): return errors+[at+": unexpected type "+typ]
    if isinstance(value,str):
        if len(value.strip())<schema.get("minLength",0): errors.append(at+": empty string")
        if "pattern" in schema and not re.search(schema["pattern"],value): errors.append(at+": pattern mismatch")
    if typ=="number":
        if not math.isfinite(value): errors.append(at+": non-finite number")
        if "minimum" in schema and value<schema["minimum"]: errors.append(at+": minimum")
    if typ=="array":
        if len(value)<schema.get("minItems",0): errors.append(at+": minItems")
        if schema.get("uniqueItems") and len({canonical(x) for x in value})!=len(value): errors.append(at+": duplicate item")
        for i,x in enumerate(value): errors+=schema_errors(x,schema.get("items",{}),at+"["+str(i)+"]",root)
    if typ=="object":
        if len(value)<schema.get("minProperties",0): errors.append(at+": minProperties")
        for key in schema.get("required",[]):
            if key not in value: errors.append(at+"."+key+": required")
        for key,x in value.items():
            if key in schema.get("properties",{}): errors+=schema_errors(x,schema["properties"][key],at+"."+key,root)
            elif schema.get("additionalProperties") is False: errors.append(at+"."+key+": extra property")
            elif isinstance(schema.get("additionalProperties"),dict): errors+=schema_errors(x,schema["additionalProperties"],at+"."+key,root)
    if "anyOf" in schema and not any(not schema_errors(value,s,at,root) for s in schema["anyOf"]): errors.append(at+": no anyOf match")
    return errors

def resolve_file(model_path,raw,workspace):
    if re.match(r"^[a-z][a-z0-9+.-]*:",raw,re.I) or Path(raw).is_absolute() or raw.startswith(("//","\\\\")):
        raise ValueError("Reference must be project-relative: "+raw)
    result=(model_path.parent/raw).resolve()
    try: result.relative_to(workspace.resolve())
    except ValueError: raise ValueError("Reference escapes workspace: "+raw)
    if result.suffix.lower()==".pen": raise ValueError("Read encrypted pen content through its MCP tool")
    if not result.is_file(): raise ValueError("Missing source file: "+raw)
    return result

def all_ids(data):
    if isinstance(data,dict):
        ids={data["id"]} if isinstance(data.get("id"),str) else set()
        for v in data.values(): ids|=all_ids(v)
        return ids
    if isinstance(data,list): return set().union(*(all_ids(v) for v in data)) if data else set()
    return set()

def lookup(data,dotted):
    for key in dotted.split("."):
        if not isinstance(data,dict) or key not in data: return False,None
        data=data[key]
    return True,data

def pointer(data,locator):
    if locator=="$": return data
    if not locator.startswith("/"): raise ValueError("JSON source needs JSON Pointer or $ locator")
    for key in locator[1:].split("/"):
        key=key.replace("~1","/").replace("~0","~")
        data=data[int(key)] if isinstance(data,list) else data[key]
    return data

def conditions_overlap(a,b):
    for key in a["match"].keys()&b["match"].keys():
        if not {canonical(x) for x in a["match"][key]}&{canonical(x) for x in b["match"][key]}: return False
    return True

def action_key(edge):
    op=edge["operation"]
    return (edge["from"]," ".join(op["actor"].split()).casefold()," ".join(op["label"].split()).casefold(),canonical(op.get("input",{})))

def html_text(model):
    template=(SKILL_DIR/"assets"/"graph.template.html").read_text(encoding="utf-8")
    embedded=canonical(model).replace("<","\\u003c").replace("\u2028","\\u2028").replace("\u2029","\\u2029")
    return template.replace("__MODEL_SHA__",digest(model)).replace("__MODEL_JSON__",embedded)

def check_html(model,path):
    file=path.with_suffix(".html")
    if not file.is_file(): return ["HTML not generated"]
    text=file.read_text(encoding="utf-8")
    data=re.search(r'<script id="model" type="application/json">(.*?)</script>',text,re.S)
    marker=re.search(r'<meta name="model-sha256" content="([a-f0-9]{64})">',text)
    if not data or not marker: return ["HTML model or digest marker missing"]
    try: embedded=json.loads(data.group(1))
    except ValueError: return ["Invalid embedded JSON"]
    if canonical(embedded)!=canonical(model) or marker.group(1)!=digest(model): return ["HTML and graph JSON differ"]
    if "<canvas" not in text or "function selectState" not in text or "function selectEdge" not in text: return ["Canvas selection code missing"]
    return []

def evaluate(model,path,workspace,with_html=False):
    categories=("schema","source","facts","operation","branch","reachability","constraints","html")
    checks={name:[] for name in categories}
    checks["schema"]=schema_errors(model,load_json(SKILL_DIR/"assets"/"state-transitions.schema.json"))
    if checks["schema"]:
        return {"scope":"graph-structure-and-references","status":"failed","checks":[{"id":name,"status":"failed" if name=="schema" else "not-tested","findings":checks[name]} for name in categories]}
    def fail(name,msg): checks[name].append(msg)
    seen=set();cache={}
    def sources(refs,label):
        ui=[];identities=set()
        for s in refs:
            if canonical(s) in identities: fail("source",label+": duplicate source")
            identities.add(canonical(s))
            try:
                if s["kind"]=="document":
                    file=resolve_file(path,s["path"],workspace)
                    if file not in cache: cache[file]=file.read_bytes()
                    raw=cache[file]
                    if raw_hash(raw)!=s["sha256"]: fail("source",label+": document hash mismatch")
                    text=raw.decode("utf-8-sig").replace("\r\n","\n");loc=s["locator"]
                    lines=re.fullmatch(r"L(\d+)(?:-L?(\d+))?",loc)
                    if lines:
                        start,end=int(lines[1]),int(lines[2] or lines[1])
                        if start<1 or end<start or end>len(text.splitlines()): raise ValueError("Invalid source line locator: "+loc)
                        selected="\n".join(text.splitlines()[start-1:end])
                    elif file.suffix.lower()==".json":
                        selected=canonical(pointer(json.loads(text),loc))
                    else:
                        if loc!="$" and loc not in text: raise ValueError("Source heading not found: "+loc)
                        selected=text
                    if "quote" in s and s["quote"].replace("\r\n","\n") not in selected: fail("source",label+": quote does not match source locator")
                else:
                    structured=resolve_file(path,s["structurePath"],workspace);image=resolve_file(path,s["screenshotPath"],workspace)
                    for file in (structured,image):
                        if file not in cache: cache[file]=file.read_bytes()
                    if raw_hash(cache[structured])!=s["structureSha256"] or raw_hash(cache[image])!=s["screenshotSha256"]: fail("source",label+": UI or screenshot hash mismatch")
                    data=json.loads(cache[structured].decode("utf-8-sig"))
                    if data.get("id")!=s["documentId"]: fail("source",label+": wrong UI document")
                    if not set(s["nodeIds"]).issubset(all_ids(data.get("tree",data))): fail("source",label+": UI node missing")
                    ui.append(s)
            except (OSError,ValueError,KeyError,IndexError,TypeError) as exc: fail("source",label+": "+str(exc))
        return ui
    def check_assertion(a,label,visual=None,effect=False):
        op=a["op"];value=a["value"]
        if op=="in" and (not isinstance(value,list) or not value): fail("facts",label+": in needs nonempty values")
        if op=="exists" and not isinstance(value,bool): fail("facts",label+": exists needs boolean")
        if op=="count-eq" and (isinstance(value,bool) or not isinstance(value,int) or value<0): fail("facts",label+": count-eq needs nonnegative integer")
        if op=="eq-ref" and (not effect or not isinstance(value,str) or not re.match(r"^(before|input|outcome|after)\.",value)): fail("facts",label+": eq-ref requires an effects relation")
        if op=="matches-ui":
            wanted=("documentId","nodeIds","structureSha256")
            if effect or not isinstance(value,dict) or set(value)!=set(wanted) or not any(value=={k:s[k] for k in wanted} for s in visual or []): fail("facts",label+": matches-ui must match a direct state UI source")
    states={s["id"]:s for s in model["states"]}
    fact_statements=set()
    for collection in ("states","transitions","constraints"):
        for item in model[collection]:
            if item["id"] in seen: fail("schema","Duplicate entity ID: "+item["id"])
            seen.add(item["id"])
    for state in model["states"]:
        ui=sources(state["source"],state["id"])
        if not state["functionalFacts"] and not state["visualFacts"]: fail("facts",state["id"]+": empty state")
        if state["visualFacts"] and not ui: fail("facts",state["id"]+": visual state needs a direct UI and original screenshot source")
        assertions=set()
        for category in ("functionalFacts","visualFacts"):
            for f in state[category]:
                fact_statements.add(" ".join(f["statement"].split()))
                sig=canonical(f["assertion"])
                if sig in assertions: fail("facts",state["id"]+": duplicate fact assertion")
                assertions.add(sig)
                check_assertion(f["assertion"],state["id"],ui if category=="visualFacts" else None)
    groups={}
    for edge in model["transitions"]:
        sources(edge["source"],edge["id"])
        if edge["from"] not in states or edge["to"] not in states: fail("schema",edge["id"]+": endpoint missing")
        op=edge["operation"]
        if "input" in op and not op["input"]: fail("operation",edge["id"]+": omit empty operation input")
        if edge["from"]==edge["to"] and not edge.get("effects"): fail("operation",edge["id"]+": self-loop needs an observable effect")
        for effect in edge.get("effects",[]): check_assertion(effect["assertion"],edge["id"],effect=True)
        if "condition" in edge:
            c=edge["condition"]
            for field,values in c["match"].items():
                if not field.startswith("outcome.") or len(field)<=8: fail("branch",edge["id"]+": preconditions and inputs are not post-action branch conditions")
                found,value=lookup(c["sampleOutcome"],field)
                if not found or canonical(value) not in {canonical(x) for x in values}: fail("branch",edge["id"]+": sample outcome does not satisfy branch")
        groups.setdefault(action_key(edge),[]).append(edge)
    for edges in groups.values():
        conditional=[e for e in edges if "condition" in e]
        if len(edges)==1 and conditional: fail("branch",edges[0]["id"]+": condition has no alternative branch")
        if len(edges)>1:
            if len(conditional)!=len(edges): fail("branch","Same source/action/input needs mutually exclusive result branches: "+edges[0]["id"])
            else:
                for i,e in enumerate(edges):
                    for p in edges[:i]:
                        if conditions_overlap(p["condition"],e["condition"]): fail("branch","Overlapping result branches: "+p["id"]+" / "+e["id"])
                if len({canonical({"to":e["to"],"effects":e.get("effects",[])}) for e in edges})==1: fail("branch","Conditions do not change any target or observable effect: "+edges[0]["id"])
    if states:
        starts=[s["id"] for s in model["states"] if s["isInitial"]]
        if not starts: fail("reachability","Graph has no initial state")
        reachable=set(starts);queue=list(starts)
        for current in queue:
            for e in model["transitions"]:
                if e["from"]==current and e["to"] in states and e["to"] not in reachable: reachable.add(e["to"]);queue.append(e["to"])
        for missing in sorted(states.keys()-reachable): fail("reachability","Unreachable state: "+missing)
    statements=set()
    for rule in model["constraints"]:
        sources(rule["source"],rule["id"])
        normalized=" ".join(rule["statement"].split())
        if normalized in statements or normalized in fact_statements: fail("constraints",rule["id"]+": duplicates an existing rule or state fact")
        statements.add(normalized)
    if with_html: checks["html"]=check_html(model,path)
    output=[{"id":name,"status":"failed" if notes else "not-tested" if name=="html" and not with_html else "passed","findings":notes} for name,notes in checks.items()]
    return {"scope":"graph-structure-and-references","status":"failed" if any(checks.values()) else "passed","checks":output}

def execute(command,path,workspace):
    model=load_json(path)
    report=evaluate(model,path,workspace,with_html=command=="check")
    if command=="render" and report["status"]=="passed":
        path.with_suffix(".html").write_text(html_text(model),encoding="utf-8")
        report=evaluate(model,path,workspace,with_html=True)
    print(json.dumps(report,ensure_ascii=False,indent=2))
    return 0 if report["status"]=="passed" else 1

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command",choices=("validate","render","check"))
    parser.add_argument("model",type=Path)
    parser.add_argument("--workspace",required=True,type=Path)
    args=parser.parse_args()
    try: return execute(args.command,args.model.resolve(),args.workspace.resolve())
    except (OSError,ValueError,KeyError,TypeError,RecursionError) as exc:
        print(json.dumps({"status":"failed","error":str(exc)},ensure_ascii=False));return 1

if __name__=="__main__": raise SystemExit(main())
