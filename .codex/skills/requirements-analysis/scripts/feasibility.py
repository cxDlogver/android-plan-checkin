"""Shortest transition witnesses by exact symbolic preimages of finite-domain boxes.

This checks the declared abstraction, not arbitrary Chinese guards or real fixtures.
"""
from collections import deque, Counter
from functools import lru_cache
import hashlib
import json
import heapq
from path_context import advance, constrain_state


def model_key(model):
    fields={k:model.get(k) for k in ('entryStateIds','states','transitions','requirements','pathContext')}
    return json.dumps(fields,ensure_ascii=False,sort_keys=True,separators=(',',':'))


class Solver:
    def __init__(self, model):
        self.model=model;self.spec=model.get('pathContext') or {}
        self.names=tuple(sorted(self.spec.get('domains',{})))
        self.values=[self.spec['domains'][k]['values'] for k in self.names]
        self.index={k:i for i,k in enumerate(self.names)}
        self.full=tuple((1<<len(v))-1 for v in self.values)
        self.incoming={s['id']:[] for s in model['states']}
        self.transitions={t['id']:t for t in model['transitions']}
        self.invariants={sid:self.assign(row['requires']) for sid,row in self.spec.get('stateConstraints',{}).items()}
        self.entries={root:self.assign(self.spec.get('entryContexts',{}).get(root,{})) for root in model['entryStateIds']}
        self.rules={}
        outgoing={s['id']:[] for s in model['states']}
        for t in model['transitions']:outgoing[t['from']].append(t['to'])
        self.distance={root:0 for root in model['entryStateIds']};q=deque(self.distance)
        while q:
            node=q.popleft()
            for target in outgoing[node]:
                if target not in self.distance:self.distance[target]=self.distance[node]+1;q.append(target)
        for t in sorted(model['transitions'],key=lambda x:x['id']):
            self.incoming[t['to']].append(t)
            self.rules[t['id']]=self.spec.get('transitionRules',{}).get(t['id'],{'cases':[{}]})['cases']

    def assign(self, row):
        result=list(self.full)
        for key,vs in row.items():
            i=self.index[key];result[i]=sum(1<<self.values[i].index(v) for v in set(vs))
        return tuple(result)

    def meet(self, a, b):
        out=tuple(x&y for x,y in zip(a,b))
        return out if all(out) else None

    def preimage(self, edge, case, goal):
        post=self.meet(goal,self.invariants.get(edge['to'],self.full))
        if post is None:return None
        before=list(self.full)
        effects=set(case.get('set',{}))|set(case.get('forget',[]))|set(case.get('setFrom',{}))
        for i,k in enumerate(self.names):
            if k not in effects:before[i]&=post[i]
        for k,vs in case.get('set',{}).items():
            i=self.index[k]
            if not self.assign({k:vs})[i]&post[i]:return None
        for dest,src in case.get('setFrom',{}).items():
            di,si=self.index[dest],self.index[src]
            allowed={v for i,v in enumerate(self.values[di]) if post[di]&(1<<i)}
            before[si]&=sum(1<<i for i,v in enumerate(self.values[si]) if v in allowed)
        result=self.meet(tuple(before),self.assign(case.get('requires',{})))
        return self.meet(result,self.invariants.get(edge['from'],self.full)) if result is not None else None

    def witness(self, target_id, limit=200000, target_case=None):
        target=self.transitions[target_id];queue=[];seen={};count=0
        def offer(node,ctx,tids,cases):
            nonlocal count
            depth=len(tids);old=seen.setdefault(node,[])
            if any(d<=depth and all(a&b==a for a,b in zip(ctx,prior)) for prior,d in old):return
            old.append((ctx,depth));count+=1
            heapq.heappush(queue,(depth+self.distance.get(node,float('inf')),depth,count,node,ctx,tids,cases))
        for ci,case in enumerate(self.rules[target_id]):
            if target_case is not None and ci!=target_case:continue
            ctx=self.preimage(target,case,self.full)
            if ctx is not None:offer(target['from'],ctx,[target_id],[ci])
        while queue:
            if count>limit:return {'status':'incomplete','configurations':count,'reason':'search_limit'}
            _,_,_,node,ctx,tids,cases=heapq.heappop(queue)
            if node in self.entries:
                start=self.meet(ctx,self.entries[node])
                if start is not None:
                    return {'status':'finite_domain_passed' if self.names else 'no_guard_constraints' if all(t.get('guard','true')=='true' for t in self.model['transitions']) else 'structure_only',
                            'entryStateId':node,'transitionIds':tids,'ruleCases':cases,
                            'initialContext':{k:[v for j,v in enumerate(self.values[i]) if start[i]&(1<<j)] for i,k in enumerate(self.names)},
                            'shortest':True,'configurations':count}
            for edge in self.incoming[node]:
                for ci,case in enumerate(self.rules[edge['id']]):
                    pre=self.preimage(edge,case,ctx)
                    if pre is not None:offer(edge['from'],pre,[edge['id']]+tids,[ci]+cases)
        return {'status':'infeasible','configurations':count,'reason':'exhausted_finite_preimages'}


@lru_cache(maxsize=2)
def _analyze(key,limit):
    model=json.loads(key);solver=Solver(model)
    witnesses={t['id']:solver.witness(t['id'],limit) for t in model['transitions']}
    counts=Counter(w['status'] for w in witnesses.values())
    case_results={tid:[solver.witness(tid,limit,ci) for ci in range(len(solver.rules[tid]))] for tid in witnesses}
    case_counts=Counter(w['status'] for rows in case_results.values() for w in rows)
    return {'method':'symbolic_backward_astar','scope':'declared_finite_domains',
            'inputDigest':hashlib.sha256(key.encode()).hexdigest(),
            'status':'failed' if counts['infeasible'] or case_counts['infeasible'] else 'incomplete' if counts['incomplete'] or counts['structure_only'] or case_counts['incomplete'] or case_counts['structure_only'] else 'passed',
            'counts':dict(counts),'transitions':witnesses,'caseCounts':dict(case_counts),'caseResults':case_results}


def analyze(model,limit=200000):
    result=_analyze(model_key(model),limit)
    errors=verify_witnesses(model,result)
    if errors:raise ValueError('invalid transition witness: '+ '; '.join(errors))
    return result


def verify_witnesses(model,report):
    errors=[];spec=model.get('pathContext');ts={t['id']:t for t in model['transitions']}
    success_status=('finite_domain_passed' if (spec or {}).get('domains') else
                    'no_guard_constraints' if all(t.get('guard','true')=='true' for t in model['transitions']) else 'structure_only')
    allowed_statuses={success_status,'infeasible','incomplete'}
    if report.get('inputDigest')!=hashlib.sha256(model_key(model).encode()).hexdigest():errors.append('stale witness input digest')
    if report.get('method')!='symbolic_backward_astar' or report.get('scope')!='declared_finite_domains':errors.append('invalid witness method/scope')
    if set(report['transitions'])!=set(ts):return ['witness coverage differs from transition set']
    counts=Counter(w.get('status') for w in report['transitions'].values())
    if set(counts)-allowed_statuses:errors.append('witness status incompatible with model constraint scope')
    if report.get('counts')!=dict(counts):errors.append('witness counts differ from per-edge results')
    case_results=report.get('caseResults',{})
    if set(case_results)!=set(ts):return errors+['case witness coverage differs from transition set']
    case_counts=Counter(w.get('status') for rows in case_results.values() for w in rows)
    if set(case_counts)-allowed_statuses:errors.append('case witness status incompatible with model constraint scope')
    if report.get('caseCounts')!=dict(case_counts):errors.append('case witness counts differ')
    status='failed' if counts['infeasible'] or case_counts['infeasible'] else 'incomplete' if counts['incomplete'] or counts['structure_only'] or case_counts['incomplete'] or case_counts['structure_only'] else 'passed'
    if report.get('status')!=status:errors.append('witness overall status differs from per-edge results')
    checks=list(report['transitions'].items())
    for tid,rows in case_results.items():
        expected=spec['transitionRules'][tid]['cases'] if spec else [{}]
        if len(rows)!=len(expected):errors.append(tid+': case count mismatch');continue
        for ci,w in enumerate(rows):
            if w.get('ruleCases') and w['ruleCases'][-1]!=ci:errors.append(tid+': target case mismatch')
            checks.append((tid,w))
    for tid,w in checks:
        if w['status'] not in {'finite_domain_passed','no_guard_constraints','structure_only'}:continue
        if w['entryStateId'] not in model['entryStateIds'] or not w['transitionIds'] or w['transitionIds'][-1]!=tid:
            errors.append(tid+': invalid entry/target');continue
        node=w['entryStateId'];initial={k:set(v) for k,v in w['initialContext'].items()}
        if spec:
            if set(initial)!=set(spec['domains']) or any(not vs or not vs<=set(spec['entryContexts'][node].get(k,spec['domains'][k]['values'])) for k,vs in initial.items()):
                errors.append(tid+': invalid initial constraints');continue
        contexts=[constrain_state(spec,node,initial)]
        if contexts[0] is None:errors.append(tid+': initial invariant conflict');continue
        if len(w['ruleCases'])!=len(w['transitionIds']):errors.append(tid+': missing rule choices');continue
        for edge_id,ci in zip(w['transitionIds'],w['ruleCases']):
            edge=ts.get(edge_id)
            if edge is None or edge['from']!=node:errors.append(tid+': discontinuous witness');break
            cases=spec['transitionRules'][edge_id]['cases'] if spec else [{}]
            if not isinstance(ci,int) or not 0<=ci<len(cases):errors.append(tid+': invalid rule choice');break
            rows=[constrain_state(spec,edge['to'],row) for ctx in contexts for row in (advance(spec,ctx,cases[ci]) if spec else [ctx])]
            contexts=[r for r in rows if r is not None]
            if not contexts:errors.append(tid+': replay conflict');break
            node=edge['to']
    return errors
