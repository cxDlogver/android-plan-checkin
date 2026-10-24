"""Independent concrete-state oracle and condition replay; no application imports."""
import copy
import hashlib
import heapq
import itertools
import json
import random
import sys
import time
from collections import Counter, deque
from pathlib import Path

HERE=Path(__file__).resolve().parent
RUN=HERE.parent.parent
SKILL=RUN.parents[1]/'.codex/skills/requirements-analysis'
sys.dont_write_bytecode=True
sys.path.insert(0,str(SKILL/'scripts'))
from feasibility import analyze, verify_witnesses, Solver
from requirement_graph import requirement_graph, verify_coverage
from path_context import validate_context
from path_context import paths_for_start


def fixture(pairs, roots=('A',), restart=True):
    names=sorted(set(roots)|{v for p in pairs for v in p})
    ts=[{'id':f'T{i:02d}','requirementId':f'R{i:02d}','from':a,'to':b,'event':f'操作{i}','guard':'true','sourceIds':['P']} for i,(a,b) in enumerate(pairs)]
    return {'entryStateIds':list(roots),'states':[{'id':n,'sourceIds':['P']} for n in names],
      'transitions':ts,'requirements':[],
      'requirementTraversal':{'restartPolicy':'documented_entries' if restart else 'none','authorization':'独立合成场景'},
      'pathContext':{'domains':{k:{'values':['0','1'],'labels':{'0':'零','1':'一'},'description':k} for k in ['x','y']},
        'entryContexts':{r:{'x':['0'],'y':['1']} for r in roots},'stateConstraints':{},
        'transitionRules':{t['id']:{'cases':[{}],'reason':'合成规则','sourceRefs':[{'sourceId':'P','locator':'合成来源'}]} for t in ts}}}


def concrete_graph(m):
    spec=m['pathContext'];keys=tuple(sorted(spec['domains']));domains={k:spec['domains'][k]['values'] for k in keys}
    def invariant(node,row):
        return all(row[k] in vs for k,vs in spec.get('stateConstraints',{}).get(node,{}).get('requires',{}).items())
    def concrete_effects(before,case):
        if any(before[k] not in allowed for k,allowed in case.get('requires',{}).items()):return []
        outputs=[]
        for k in keys:
            if k in case.get('setFrom',{}):values=[before[case['setFrom'][k]]]
            elif k in case.get('set',{}):values=case['set'][k]
            elif k in case.get('forget',[]):values=domains[k]
            else:values=[before[k]]
            outputs.append([v for v in values if v in domains[k]])
        return [dict(zip(keys,values)) for values in itertools.product(*outputs)]
    entries=[]
    for root in m['entryStateIds']:
        for values in itertools.product(*(domains[k] for k in keys)):
            row=dict(zip(keys,values))
            if invariant(root,row) and all(row[k] in vs for k,vs in spec['entryContexts'][root].items()):entries.append((root,values))
    adjacent={}
    for node in [s['id'] for s in m['states']]:
        for values in itertools.product(*(domains[k] for k in keys)):
            row=dict(zip(keys,values));edges=[]
            if invariant(node,row):
                for i,t in enumerate(m['transitions']):
                    if t['from']!=node:continue
                    for ci,c in enumerate(spec['transitionRules'][t['id']]['cases']):
                        for result in concrete_effects(row,c):
                            if invariant(t['to'],result):edges.append((i,(t['to'],tuple(result[k] for k in keys)),ci))
            adjacent[node,values]=edges
    return entries,adjacent


def oracle(m):
    entries,adjacent=concrete_graph(m);dist={e:0 for e in entries};queue=deque(entries);edge_dist={};case_dist={}
    while queue:
        current=queue.popleft();d=dist[current]
        for i,nxt,ci in adjacent[current]:
            edge_dist.setdefault(m['transitions'][i]['id'],d+1)
            case_dist.setdefault((m['transitions'][i]['id'],ci),d+1)
            if nxt not in dist:dist[nxt]=d+1;queue.append(nxt)
    return edge_dist,entries,adjacent,case_dist


def cover_oracle(m,entries,adjacent):
    target=(1<<len(m['transitions']))-1
    distances={(e,0):0 for e in entries};queue=[(0,e,0) for e in entries];heapq.heapify(queue)
    while queue:
        d,pos,mask=heapq.heappop(queue)
        if distances.get((pos,mask))!=d:continue
        if mask==target:return d
        choices=[(nxt,mask|(1<<i),1) for i,nxt,_ in adjacent[pos]]
        if m['requirementTraversal']['restartPolicy']=='documented_entries':choices.extend((e,mask,0) for e in entries)
        for nxt,updated,price in choices:
            key=nxt,updated
            if d+price<distances.get(key,float('inf')):distances[key]=d+price;heapq.heappush(queue,(d+price,nxt,updated))
    return None


def replay_boxes(m, entry, sequence, initial, choices):
    # Own forward interpreter of finite boxes; enumerate only copied source
    # values, preserving correlations without invoking the candidate executor.
    spec=m.get('pathContext');ts={t['id']:t for t in m['transitions']}
    def invariant(node,row):
        result={k:set(v) for k,v in row.items()}
        for k,values in spec.get('stateConstraints',{}).get(node,{}).get('requires',{}).items():result[k]&=set(values)
        return result if all(result.values()) else None
    if entry not in m['entryStateIds']:return False
    for k,d in spec['domains'].items():
        if not set(initial.get(k,[])) or not set(initial[k])<=set(spec['entryContexts'][entry].get(k,d['values'])):return False
    row=invariant(entry,initial)
    if row is None:return False
    boxes=[row];node=entry
    for tid,ci in zip(sequence,choices):
        edge=ts[tid]
        if edge['from']!=node:return False
        c=spec['transitionRules'][tid]['cases'][ci];out=[]
        for box in boxes:
            before={k:set(v) for k,v in box.items()}
            for k,values in c.get('requires',{}).items():before[k]&=set(values)
            if not all(before.values()):continue
            sources=sorted(set(c.get('setFrom',{}).values()))
            for values in itertools.product(*(before[k] for k in sources)):
                frozen={k:set(v) for k,v in before.items()}
                for k,v in zip(sources,values):frozen[k]={v}
                after={k:set(v) for k,v in frozen.items()}
                for k in c.get('forget',[]):after[k]=set(spec['domains'][k]['values'])
                for k,values in c.get('set',{}).items():after[k]=set(values)
                for dst,src in c.get('setFrom',{}).items():after[dst]=frozen[src]&set(spec['domains'][dst]['values'])
                after=invariant(edge['to'],after)
                if after is not None:out.append(after)
        unique={tuple((k,tuple(sorted(v))) for k,v in sorted(row.items())):row for row in out}
        boxes=list(unique.values());node=edge['to']
        if not boxes:return False
    return len(sequence)==len(choices) and bool(boxes)


def main():
    started=time.monotonic()
    hashes={p.relative_to(SKILL).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in SKILL.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    result={'scope':'New independent feasibility review; no prior PASS reused; no Android application reads',
            'readResourceHashes':hashes,'oracleGraphs':0,'oracleTransitionChecks':0,'coverageChecks':0,
            'stateShortestPathChecks':0,'oracleCaseChecks':0,
            'mismatches':[],'tamperChecks':[],'browserObserved':False}
    for seed in range(1200):
        rng=random.Random(seed+170318)
        states='ABC' if seed%2 else 'AB'
        pairs=[(rng.choice(states),rng.choice(states)) for _ in range(rng.randint(1,7))]
        roots=tuple(rng.sample(list(states),rng.randint(1,len(states))))
        m=fixture(pairs,roots,bool(seed%3))
        spec=m['pathContext']
        for root in roots:
            spec['entryContexts'][root]={k:rng.choice([['0'],['1'],['0','1']]) for k in ['x','y']}
        for state in states:
            if any(s['id']==state for s in m['states']) and rng.random()<.5:
                spec['stateConstraints'][state]={'requires':{rng.choice(['x','y']):[rng.choice(['0','1'])]},'reason':'合成状态事实','sourceRefs':[{'sourceId':'P','locator':'合成'}]}
        for t in m['transitions']:
            cases=[]
            for _ in range(rng.randint(1,3)):
                c={}
                if rng.random()<.8:c['requires']={rng.choice(['x','y']):[rng.choice(['0','1'])]}
                for k in ['x','y']:
                    op=rng.choice(['keep','set','copy','forget'])
                    if op=='set':c.setdefault('set',{})[k]=rng.choice([['0'],['1'],['0','1']])
                    if op=='copy':c.setdefault('setFrom',{})[k]=rng.choice(['x','y'])
                    if op=='forget':c.setdefault('forget',[]).append(k)
                cases.append(c)
            spec['transitionRules'][t['id']]['cases']=cases
        assert not validate_context(m)
        expected,entries,adjacent,case_expected=oracle(m)
        try:
            actual=analyze(m)
            for tid,w in actual['transitions'].items():
                assert (w['status']=='finite_domain_passed')==(tid in expected),(tid,w,expected)
                if tid in expected:
                    assert len(w['transitionIds'])==expected[tid],(tid,w,expected)
                    assert replay_boxes(m,w['entryStateId'],w['transitionIds'],w['initialContext'],w['ruleCases'])
                result['oracleTransitionChecks']+=1
            for tid,rows in actual['caseResults'].items():
                assert len(rows)==len(spec['transitionRules'][tid]['cases'])
                for ci,w in enumerate(rows):
                    assert (w['status']=='finite_domain_passed')==((tid,ci) in case_expected),(tid,ci,w,case_expected)
                    if (tid,ci) in case_expected:
                        assert w['ruleCases'][-1]==ci and len(w['transitionIds'])==case_expected[tid,ci]
                        assert replay_boxes(m,w['entryStateId'],w['transitionIds'],w['initialContext'],w['ruleCases'])
                    result['oracleCaseChecks']+=1
            if seed<300:
                graph=requirement_graph(m);p=graph['traversal'];opt=cover_oracle(m,entries,adjacent)
                for r in p['routes']:
                    c=r['contextCheck'];assert c['status']=='finite_domain_passed'
                    assert replay_boxes(m,r['entryStateId'],r['transitionIds'],c['initialContext'],c['ruleCases'])
                if not graph['reduction']['uncoveredRequirementIds']:
                    assert opt is not None and p['totalVisits']>=opt
                    if p['status']=='optimal':assert p['totalVisits']==opt
                    else:assert p.get('optimality')=='not_proven'
                result['coverageChecks']+=1
            if seed<100:
                for root in roots:
                    q=deque(e for e in entries if e[0]==root);seen={e:0 for e in q};state_depth={root:0} if q else {}
                    while q:
                        pos=q.popleft()
                        for _,nxt,_ in adjacent[pos]:
                            state_depth.setdefault(nxt[0],seen[pos]+1)
                            if nxt not in seen:seen[nxt]=seen[pos]+1;q.append(nxt)
                    paths,_=paths_for_start(m,root)
                    for state,route in paths.items():
                        assert (None if route is None else len(route))==state_depth.get(state),(root,state,route,state_depth)
                        result['stateShortestPathChecks']+=1
            result['oracleGraphs']+=1
        except Exception as e:result['mismatches'].append({'seed':seed,'error':repr(e),'model':m})

    # A validated list with duplicate values still represents the same finite set.
    duplicate=fixture([('A','B')]);duplicate['pathContext']['transitionRules']['T00']['cases']=[{'requires':{'x':['0','0']}}]
    result['duplicateAssignment']={'validationErrors':validate_context(duplicate),'oracle':oracle(duplicate)[0],
                                   'candidate':analyze(duplicate)['transitions']['T00']}
    # The verifier should reject a shortest/overall-success claim inconsistent with evidence.
    m=fixture([('A','B'),('B','A')]);report=copy.deepcopy(analyze(m))
    report['transitions']['T00']['status']='infeasible';report['status']='passed'
    result['tamperChecks'].append({'kind':'passSummaryWithInfeasibleWitness','errors':verify_witnesses(m,report)})
    report=copy.deepcopy(analyze(m));report['inputDigest']='stale'
    result['tamperChecks'].append({'kind':'staleInputDigest','errors':verify_witnesses(m,report)})
    report=copy.deepcopy(analyze(m));report['caseResults']['T00'][0]['status']='made_up'
    report['caseCounts']=dict(Counter(w['status'] for rows in report['caseResults'].values() for w in rows))
    result['tamperChecks'].append({'kind':'unknownCaseStatus','errors':verify_witnesses(m,report)})
    m_cases=fixture([('A','B')]);m_cases['pathContext']['transitionRules']['T00']['cases']=[{}, {'requires':{'x':['1']}}]
    case_report=analyze(m_cases)
    assert case_report['transitions']['T00']['status']=='finite_domain_passed'
    assert case_report['caseResults']['T00'][1]['status']=='infeasible' and case_report['status']=='failed'
    result['possibleEdgeImpossibleCase']={'edge':case_report['transitions']['T00']['status'],'cases':[x['status'] for x in case_report['caseResults']['T00']],'overall':case_report['status']}
    report=copy.deepcopy(case_report);report['caseResults']['T00'][1]=copy.deepcopy(report['caseResults']['T00'][0]);report['caseCounts']={'finite_domain_passed':2};report['status']='passed'
    result['tamperChecks'].append({'kind':'wrongTargetCase','errors':verify_witnesses(m_cases,report)})
    report=copy.deepcopy(case_report);report['caseResults']['T00'].pop();report['caseCounts']={'finite_domain_passed':1};report['status']='passed'
    result['tamperChecks'].append({'kind':'missingDeclaredCase','errors':verify_witnesses(m_cases,report)})
    limited=Solver(fixture([('A','B')])).witness('T00',limit=0,target_case=0)
    result['zeroSearchBudget']=limited
    assert limited['status']=='incomplete'
    m=fixture([('A','B'),('B','A'),('A','C')])
    m['pathContext']['transitionRules']['T01']['cases']=[{'set':{'x':['1']}}]
    m['pathContext']['transitionRules']['T02']['cases']=[{'requires':{'x':['0']}}]
    forged=requirement_graph(m);forged['traversal']['certificate']['globalMinimumProven']=True
    result['tamperChecks'].append({'kind':'heuristicCertificateClaimsGlobalMinimum','errors':verify_coverage(m,forged)})
    if '--algorithm-only' in sys.argv:
        result['currentModelReview']='deferred while author revises source semantics'
        result['elapsedSeconds']=round(time.monotonic()-started,3)
        (HERE/'independent-feasibility-evidence.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps({k:v if k not in {'readResourceHashes','mismatches'} else len(v) for k,v in result.items()},ensure_ascii=False,indent=2))
        return
    current_bytes=(RUN/'_process/analysis-model.json').read_bytes()
    current=json.loads(current_bytes.decode('utf-8'))
    validation=analyze(current)
    bad=[];bad_cases=[]
    for tid,w in validation['transitions'].items():
        if w['status']=='finite_domain_passed' and not replay_boxes(current,w['entryStateId'],w['transitionIds'],w['initialContext'],w['ruleCases']):bad.append(tid)
    for tid,rows in validation['caseResults'].items():
        for ci,w in enumerate(rows):
            if w['status']=='finite_domain_passed' and (w['ruleCases'][-1]!=ci or not replay_boxes(current,w['entryStateId'],w['transitionIds'],w['initialContext'],w['ruleCases'])):bad_cases.append([tid,ci])
    graph=requirement_graph(current);p=graph['traversal'];route_bad=[]
    for i,r in enumerate(p['routes']):
        c=r['contextCheck']
        if c['status']!='finite_domain_passed' or not replay_boxes(current,r['entryStateId'],r['transitionIds'],c['initialContext'],c['ruleCases']):route_bad.append(i)
    counts=Counter(rid for r in p['routes'] for rid in r['requirementIds'])
    uses=Counter((a,b) for r in p['routes'] for a,b in zip(r['requirementIds'],r['requirementIds'][1:]))
    projection_pass=({(e['from'],e['to']):e['usageCount'] for e in graph['edges']}==dict(uses)
                     and dict(counts)==p['visitCounts'] and sum(counts.values())==p['totalVisits']
                     and set(counts)=={r['id'] for r in current['requirements']})
    result['current']={'modelSha256':hashlib.sha256(current_bytes).hexdigest(),
                       'states':len(current['states']),'transitions':len(current['transitions']),
                       'witnessStatus':validation['status'],'witnessCounts':validation['counts'],'caseCounts':validation['caseCounts'],
                       'independentReplayFailures':bad,'caseReplayFailures':bad_cases,'coverageReplayFailures':route_bad,
                       'independentProjectionAndCountCheck':projection_pass,
                       'coverageStatus':p['status'],'totalVisits':p['totalVisits'],'repeatedVisits':p['repeatedVisits'],
                       'routes':len(p['routes']),'lowerBoundVisits':p.get('lowerBoundVisits'),
                       'optimality':p.get('optimality'),'uncovered':graph['reduction']['uncoveredRequirementIds']}
    result['candidateChangedDuringRun']=[p.relative_to(SKILL).as_posix() for p in SKILL.rglob('*') if p.is_file() and '__pycache__' not in p.parts and hashes.get(p.relative_to(SKILL).as_posix())!=hashlib.sha256(p.read_bytes()).hexdigest()]
    result['elapsedSeconds']=round(time.monotonic()-started,3)
    (HERE/'independent-feasibility-evidence.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v if k not in {'readResourceHashes','mismatches'} else len(v) for k,v in result.items()},ensure_ascii=False,indent=2))


if __name__=='__main__':main()
