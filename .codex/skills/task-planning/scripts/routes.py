"""Deterministic finite-domain search. Output is an abstraction witness, not a fixture."""
from collections import deque, Counter

def validate_context(model):
    spec=model.get('pathContext')
    if spec is None:return
    domains=spec.get('domains',{})
    if not domains:raise ValueError('empty finite domains')
    for k,d in domains.items():
        if not d.get('values') or len(set(d['values']))!=len(d['values']):raise ValueError('invalid finite values')
        if set(d.get('labels',{}))!=set(d['values']):raise ValueError('missing finite labels')
    def assignments(row):
        for k,vs in row.items():
            if k not in domains or not isinstance(vs,list) or not vs or not set(vs)<=set(domains[k]['values']):raise ValueError('unknown finite assignment')
    if set(spec.get('entryContexts',{}))!=set(model['entryStateIds']):raise ValueError('entry contexts mismatch')
    for row in spec['entryContexts'].values():assignments(row)
    rules=spec.get('transitionRules',{})
    if set(rules)!={t['id'] for t in model['transitions']}:raise ValueError('transition contexts mismatch')
    for rule in rules.values():
        if not rule.get('cases'):raise ValueError('empty transition cases')
        for c in rule['cases']:
            if set(c)-{'requires','set','setFrom','forget'}:raise ValueError('unknown finite operation')
            assignments(c.get('requires',{}));assignments(c.get('set',{}))
            if not set(c.get('forget',[]))<=set(domains):raise ValueError('unknown forgotten domain')
            for dest,src in c.get('setFrom',{}).items():
                if dest not in domains or src not in domains:raise ValueError('unknown copy domain')
            targets=list(c.get('set',{}))+list(c.get('setFrom',{}))+c.get('forget',[])
            if len(targets)!=len(set(targets)):raise ValueError('conflicting effects')

def signature(ctx):
    return tuple((k, tuple(sorted(v))) for k,v in sorted(ctx.items()))

def initial(model, entry):
    spec=model.get('pathContext')
    if not spec:return {}
    ctx={k:set(v['values']) for k,v in spec['domains'].items()}
    for k,v in spec['entryContexts'][entry].items():ctx[k]&=set(v)
    return ctx

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

def nearest(model, start, ctx, wanted, limit):
    """BFS goal is executing an edge; exact states plus safe breadth dominance."""
    spec=model.get('pathContext');adj={s['id']:[] for s in model['states']}
    for t in sorted(model['transitions'],key=lambda x:x['id']):adj[t['from']].append(t)
    q=deque([(start,ctx,[])]);seen={start:[ctx]};count=1
    while q:
        node,c,path=q.popleft()
        for t in adj[node]:
            cases=spec['transitionRules'][t['id']]['cases'] if spec else [{}]
            for ci,case in enumerate(cases):
                for after in advance(spec,c,case) if spec else [c]:
                    step={'transitionId':t['id'],'ruleCase':ci,'contextAfter':{k:sorted(v) for k,v in after.items()}}
                    candidate=path+[step]
                    if t['id'] in wanted:return candidate,after,{'complete':True,'configurations':count}
                    old=seen.setdefault(t['to'],[])
                    if any(all(after[k]<=prev[k] for k in after) for prev in old):continue
                    old.append(after);count+=1
                    if count>limit:return None,None,{'complete':False,'configurations':count}
                    q.append((t['to'],after,candidate))
    return None,None,{'complete':True,'configurations':count}

def replay(model, route):
    if route['entryStateId'] not in model['entryStateIds']:return ['invalid entry']
    state=route['entryStateId'];contexts=[initial(model,state)];ts={t['id']:t for t in model['transitions']};spec=model.get('pathContext')
    for i,step in enumerate(route['steps']):
        t=ts.get(step['transitionId'])
        if not t or t['from']!=state:return ['discontinuous step '+str(i+1)]
        cases=spec['transitionRules'][t['id']]['cases'] if spec else [{}]
        ci=step['ruleCase']
        if not isinstance(ci,int) or ci<0 or ci>=len(cases):return ['invalid rule case']
        candidates=[a for c in contexts for a in (advance(spec,c,cases[ci]) if spec else [c])]
        claimed={k:set(v) for k,v in step['contextAfter'].items()}
        contexts=[a for a in candidates if signature(a)==signature(claimed)]
        if not contexts:return ['context conflict at step '+str(i+1)]
        state=t['to']
    return []

def invariant_conflicts(model):
    """Sound product-domain over-approximation. A rejected edge is impossible in this abstraction."""
    spec=model.get('pathContext')
    if not spec:return {}
    reached={e:initial(model,e) for e in model['entryStateIds']}
    changed=True
    while changed:
        changed=False
        for t in model['transitions']:
            if t['from'] not in reached:continue
            for case in spec['transitionRules'][t['id']]['cases']:
                for out in advance(spec,reached[t['from']],case):
                    if t['to'] not in reached:reached[t['to']]=out;changed=True
                    else:
                        old=reached[t['to']]
                        for k,v in out.items():
                            if not v<=old[k]:old[k]|=v;changed=True
    conflicts={}
    for t in model['transitions']:
        ctx=reached.get(t['from'])
        if ctx is None:conflicts[t['id']]='起点在有限域不动点内不可达';continue
        cases=spec['transitionRules'][t['id']]['cases']
        if not any(advance(spec,ctx,c) for c in cases):
            reasons=[]
            for c in cases:
                for k,values in c.get('requires',{}).items():
                    if not ctx[k]&set(values):
                        labels=spec['domains'][k]['labels'];reasons.append('已有可能值：'+ '/'.join(labels[v] for v in sorted(ctx[k]))+'；本边要求：'+'/'.join(labels[v] for v in values))
            conflicts[t['id']]='；'.join(reasons) or '复制或守卫的有限域交集为空'
    return conflicts

def plan_routes(model, policy):
    validate_context(model)
    conflicts=invariant_conflicts(model)
    remaining={t['id'] for t in model['transitions']}-set(conflicts);ts={t['id']:t for t in model['transitions']}
    routes=[];searches=[];maxcfg=policy.get('maxConfigurations',20000);maxsteps=policy.get('maxSegmentSteps',80)
    while remaining:
        choices=[]
        for entry in model['entryStateIds']:
            path,ctx,info=nearest(model,entry,initial(model,entry),remaining,maxcfg);searches.append(info)
            if path:choices.append((len(path),entry,path,ctx))
        if not choices:break
        if routes and not policy.get('resetAllowed',False):break
        _,entry,path,ctx=min(choices,key=lambda x:(x[0],x[1]))
        route={'id':'route-'+str(len(routes)+1),'entryStateId':entry,'steps':[],
               'preparation':'独立测试数据准备后从真实入口进入；不得把重启等同于清库或改变业务事实。',
               'fixtureStatus':'needs_concretization','contextStatus':'finite_domain_passed' if model.get('pathContext') else 'not_modeled'}
        while path:
            route['steps'].extend(path)
            remaining-={s['transitionId'] for s in path};state=ts[path[-1]['transitionId']]['to']
            if not remaining or len(route['steps'])>=maxsteps:break
            path,ctx,info=nearest(model,state,ctx,remaining,maxcfg);searches.append(info)
        route['stopReason']='已覆盖全部项或无可行接续；分段上限只约束展示，不证明最优'
        routes.append(route)
    counts=Counter(s['transitionId'] for r in routes for s in r['steps'])
    uncovered=remaining|set(conflicts)
    return {'routes':routes,'uncoveredTransitionIds':sorted(uncovered),'complete':not uncovered,
            'uncoveredDetails':[{'transitionId':tid,'reason':conflicts.get(tid,'搜索未找到可执行前缀；不宣称业务上不可能'),'proof':'finite_domain_invariant_conflict' if tid in conflicts else 'not_proven'} for tid in sorted(uncovered)],
            'searchComplete':all(s['complete'] for s in searches),'optimality':'not_proven',
            'objective':'覆盖必要测试后减少重复操作；有限域贪心，不声称全局最优',
            'lowerBoundVisits':len(ts),'visits':sum(counts.values()),'repeatedVisits':sum(v-1 for v in counts.values()),
            'searchConfigurations':sum(s['configurations'] for s in searches)}
