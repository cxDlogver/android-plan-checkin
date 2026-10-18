"""Finite-domain path feasibility; never evaluate guards as executable code."""
from collections import deque


def validate_context(model):
    spec=model.get("pathContext")
    if spec is None:return []
    errors=[]
    if not isinstance(spec,dict):return ["pathContext: expected object"]
    domains=spec.get("domains")
    if not isinstance(domains,dict) or not domains:return ["pathContext.domains: expected nonempty object"]
    values={}
    for name,row in domains.items():
        if not isinstance(name,str) or not name.strip() or not isinstance(row,dict):
            errors.append("pathContext domain must be a named object");continue
        vs=row.get("values");labels=row.get("labels")
        if not isinstance(vs,list) or not vs or any(not isinstance(x,str) or not x.strip() for x in vs) or len(set(vs))!=len(vs):
            errors.append("pathContext invalid finite domain: "+str(name));continue
        values[name]=set(vs)
        if not isinstance(labels,dict) or set(labels)!=set(vs) or any(not isinstance(x,str) or not x.strip() for x in labels.values()):errors.append("pathContext Chinese labels required: "+name)
        if not isinstance(row.get("description"),str) or not row["description"].strip():errors.append("pathContext description required: "+name)
    def assignments(obj,where):
        if not isinstance(obj,dict):errors.append(where+": expected object");return
        for name,vs in obj.items():
            if name not in values or not isinstance(vs,list) or not vs or any(not isinstance(x,str) or x not in values.get(name,set()) for x in vs):errors.append(where+": unknown variable/value "+str(name))
    roots=set(model.get("entryStateIds",[]));initial=spec.get("entryContexts")
    if not isinstance(initial,dict) or set(initial)!=roots:errors.append("pathContext entry contexts must cover exactly real starts")
    else:
        for key,row in initial.items():assignments(row,"pathContext.entryContexts."+key)
    rules=spec.get("transitionRules");transitions={t["id"]:t for t in model["transitions"]}
    if not isinstance(rules,dict) or set(rules)!=set(transitions):errors.append("pathContext rules must cover exactly current transitions")
    if isinstance(rules,dict):
        for tid,rule in rules.items():
            if not isinstance(rule,dict):errors.append("pathContext rule must be object: "+tid);continue
            if not isinstance(rule.get("reason"),str) or not rule["reason"].strip():errors.append("pathContext rule reason required: "+tid)
            refs=rule.get("sourceRefs")
            if not isinstance(refs,list) or not refs:errors.append("pathContext source references required: "+tid)
            else:
                for ref in refs:
                    if not isinstance(ref,dict) or ref.get("sourceId") not in transitions.get(tid,{}).get("sourceIds",[]) or not isinstance(ref.get("locator"),str) or not ref["locator"].strip():errors.append("pathContext source ref invalid: "+tid)
            cases=rule.get("cases")
            if not isinstance(cases,list) or not cases:errors.append("pathContext cases required: "+tid);continue
            for case in cases:
                if not isinstance(case,dict):errors.append("pathContext case must be object: "+tid);continue
                if set(case)-{"requires","set","setFrom","forget"}:errors.append("pathContext case contains unknown operations: "+tid)
                for field in ("requires","set"):assignments(case.get(field,{}),tid+"."+field)
                copies=case.get("setFrom",{})
                if not isinstance(copies,dict):errors.append("pathContext setFrom must be object: "+tid)
                else:
                    for dest,src in copies.items():
                        required=case.get("requires",{})
                        allowed=required.get(src,values.get(src,set())) if isinstance(required,dict) and isinstance(src,str) else []
                        if dest not in values or not isinstance(src,str) or src not in values or not isinstance(allowed,(list,set)) or not (set(allowed) & values.get(dest,set())):errors.append("pathContext copy domains invalid: "+tid)
                forgotten=case.get("forget",[])
                if not isinstance(forgotten,list) or any(x not in values for x in forgotten):errors.append("pathContext forget invalid: "+tid)
                if isinstance(copies,dict) and isinstance(forgotten,list) and isinstance(case.get("set",{}),dict):
                    targets=list(case.get("set",{}))+list(copies)+forgotten
                    if len(targets)!=len(set(targets)):errors.append("pathContext conflicting effects: "+tid)
    constraints=spec.get("stateConstraints",{})
    if not isinstance(constraints,dict) or not set(constraints)<=set(s["id"] for s in model["states"]):errors.append("invalid state constraints")
    else:
        state_sources={s["id"]:set(s.get("sourceIds",[])) for s in model["states"]}
        for sid,row in constraints.items():
            if not isinstance(row,dict):errors.append("state constraint must be object: "+sid);continue
            if set(row)-{"requires","reason","sourceRefs"}:errors.append("state constraint has unknown fields: "+sid)
            assignments(row.get("requires",{}),"stateConstraints."+sid)
            if not isinstance(row.get("reason"),str) or not row['reason'].strip():errors.append("state constraint lacks reason: "+sid)
            refs=row.get("sourceRefs")
            if not isinstance(refs,list) or not refs:errors.append("state constraint lacks sources: "+sid);continue
            for ref in refs:
                if not isinstance(ref,dict) or ref.get("sourceId") not in state_sources[sid] or not isinstance(ref.get("locator"),str) or not ref['locator'].strip():errors.append("invalid state constraint source: "+sid)
    return errors


def advance(spec, ctx, case):
    before={k:set(v) for k,v in ctx.items()}
    for k,v in case.get('requires',{}).items():
        before[k]&=set(v)
        if not before[k]:return []
    branches=[before]
    # Freeze copy sources before applying any effect; expand correlations explicitly.
    sources=sorted(set(case.get('setFrom',{}).values()))
    for src in sources:
        expanded=[]
        for b in branches:
            for v in sorted(b[src]):
                c={k:set(vs) for k,vs in b.items()};c[src]={v};expanded.append(c)
        branches=expanded
    out=[]
    for b in branches:
        c={k:set(v) for k,v in b.items()}
        for k in case.get('forget',[]):c[k]=set(spec['domains'][k]['values'])
        for k,v in case.get('set',{}).items():c[k]=set(v)
        for dest,src in case.get('setFrom',{}).items():c[dest]=b[src]&set(spec['domains'][dest]['values'])
        if all(c.values()):out.append(c)
    return out

def constrain_state(spec,node,context):
    if spec is None:return context
    out={k:set(v) for k,v in context.items()}
    for key,values in spec.get('stateConstraints',{}).get(node,{}).get('requires',{}).items():
        out[key]&=set(values)
        if not out[key]:return None
    return out


def paths_for_start(model,start,max_configurations=200000):
    """BFS over state + symbolic finite domains; empty intersection blocks an edge.

    A broader configuration reached no later dominates a narrower one. This does
    not enumerate arbitrary dates or invoke an LLM. Conditions outside the declared
    finite abstraction remain a semantic review obligation.
    """
    spec=model.get("pathContext");nodes=[s["id"] for s in model["states"]]
    adjacency={key:[] for key in nodes}
    for edge in model["transitions"]:adjacency[edge["from"]].append(edge)
    if start not in adjacency:return {key:None for key in nodes},{"complete":True,"configurations":0,"contextAware":bool(spec)}
    if spec:
        errors=validate_context(model)
        if errors:raise ValueError("; ".join(errors))
        initial={key:set(row["values"]) for key,row in spec["domains"].items()}
        for key,values in spec["entryContexts"][start].items():initial[key]&=set(values)
    else:initial={}
    initial=constrain_state(spec,start,initial)
    if initial is None:return {key:None for key in nodes},{"complete":True,"configurations":0,"contextAware":bool(spec)}
    structurally_reachable={start};todo=[start]
    for node in todo:
        for edge in adjacency[node]:
            if edge["to"] not in structurally_reachable:structurally_reachable.add(edge["to"]);todo.append(edge["to"])
    def signature(context):return tuple((key,tuple(sorted(values))) for key,values in sorted(context.items()))
    exact={(start,signature(initial))}
    routes={key:None for key in nodes};routes[start]=[]
    queue=deque([(start,initial,[])])
    seen={start:[(initial,0)]};count=1
    while queue:
        node,context,route=queue.popleft()
        for edge in adjacency[node]:
            cases=spec["transitionRules"][edge["id"]]["cases"] if spec else [{}]
            for case in cases:
                for updated in advance(spec,context,case) if spec else [context]:
                    updated=constrain_state(spec,edge["to"],updated)
                    if updated is None:continue
                    target=edge["to"];steps=route+[edge["id"]]
                    key=(target,signature(updated))
                    if key in exact:continue
                    exact.add(key)
                    previous=seen.setdefault(target,[])
                    if any(depth<=len(steps) and all(updated[key]<=old[key] for key in updated) for old,depth in previous):continue
                    previous.append((updated,len(steps)));count+=1
                    if count>max_configurations:raise ValueError("path context search incomplete: configuration limit reached; do not label remaining states unreachable")
                    if routes[target] is None:routes[target]=steps
                    queue.append((target,updated,steps))
        if all(routes[node] is not None for node in structurally_reachable):break
    return routes,{"complete":True,"configurations":count,"contextAware":bool(spec)}
