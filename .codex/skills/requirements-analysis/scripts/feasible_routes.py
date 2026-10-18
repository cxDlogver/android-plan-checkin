"""Cover transitions using certified prefixes; never join incompatible contexts."""
from path_context import advance, constrain_state


def initial(model,entry):
    spec=model.get('pathContext')
    if not spec:return [{}]
    ctx={k:set(d['values']) for k,d in spec['domains'].items()}
    for k,v in spec['entryContexts'][entry].items():ctx[k]&=set(v)
    row=constrain_state(spec,entry,ctx)
    return [row] if row is not None else []


def follow(model,contexts,tids):
    spec=model.get('pathContext');ts={t['id']:t for t in model['transitions']}
    for tid in tids:
        unique={}
        for ctx in contexts:
            for case in spec['transitionRules'][tid]['cases'] if spec else [{}]:
                for row in advance(spec,ctx,case) if spec else [ctx]:
                    row=constrain_state(spec,ts[tid]['to'],row)
                    if row is not None:
                        key=tuple((k,tuple(sorted(v))) for k,v in sorted(row.items()))
                        unique[key]=row
        if len(unique)>200000:return None
        contexts=list(unique.values())
        if not contexts:return []
    return contexts


def cover(model,validation,restart):
    ts={t['id']:t for t in model['transitions']}
    witnesses={tid:w for tid,w in validation['transitions'].items()
               if w['status'] in ('finite_domain_passed','no_guard_constraints')}
    pending=set(witnesses);routes=[];current=None;contexts=[];state=None
    while pending:
        choices=[]
        for tid in sorted(pending):
            w=witnesses[tid];path=w['transitionIds']
            if current is None:
                candidates=[(path,initial(model,w['entryStateId']),w['entryStateId'])]
            else:
                candidates=[(path[i:],contexts,current['entryStateId']) for i,t in enumerate(path) if ts[t]['from']==state]
            for tail,before,entry in candidates:
                new=len(set(tail)&pending)
                choices.append((len(tail)/new,len(tail),tuple(tail),entry,before))
        chosen=None
        for candidate in sorted(choices,key=lambda x:x[:4]):
            after=follow(model,candidate[4],candidate[2])
            if after:
                chosen=(*candidate[:4],after);break
        if chosen is None:
            if current is None:break
            if not restart:break
            current=None;contexts=[];state=None
            continue
        _,_,tids,entry,after=chosen
        if current is None:
            current={'entryStateId':entry,'transitionIds':[]};routes.append(current)
        current['transitionIds'].extend(tids);contexts=after;state=ts[tids[-1]]['to'];pending-=set(tids)
    # Only redundant complete segments can be removed; keep each remaining prefix intact.
    counts={tid:sum(tid in r['transitionIds'] for r in routes) for tid in ts}
    kept=[]
    for route in sorted(enumerate(routes),key=lambda item:(-len(item[1]['transitionIds']),item[0])):
        index,r=route
        if all(counts[t]>1 for t in set(r['transitionIds'])):
            for t in set(r['transitionIds']):counts[t]-=1
        else:kept.append((index,r))
    return [r for _,r in sorted(kept)]
