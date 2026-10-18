"""Concrete-state BFS oracle, independent of symbolic preimages and replay."""
import copy
import itertools
import random
import unittest
from collections import Counter, deque
from feasibility import analyze, verify_witnesses, Solver
from requirement_graph import requirement_graph, verify_coverage
from path_context import advance


def fixture():
    return {'entryStateIds':['A'],'states':[{'id':s,'sourceIds':['P']} for s in 'ABC'],
      'requirements':[], 'requirementTraversal':{'restartPolicy':'documented_entries','authorization':'synthetic'},
      'transitions':[{'id':'T'+str(i),'requirementId':'R'+str(i),'from':a,'to':b,'event':'测试','guard':'true','sourceIds':['P']}
          for i,(a,b) in enumerate([('A','B'),('B','A'),('A','C'),('B','C'),('C','A')])],
      'pathContext':{'domains':{k:{'values':['0','1'],'labels':{'0':'零','1':'一'},'description':k} for k in ['x','y']},
          'entryContexts':{'A':{'x':['0'],'y':['0']}},'transitionRules':{},'stateConstraints':{}}}


def concrete_oracle(m):
    spec=m['pathContext'];keys=sorted(spec['domains']);domains=[spec['domains'][k]['values'] for k in keys]
    def allowed(node,value):
        return all(value[keys.index(k)] in vs for k,vs in spec.get('stateConstraints',{}).get(node,{}).get('requires',{}).items())
    queue=deque();seen=set();dist={};case_dist={}
    for root in m['entryStateIds']:
        for v in itertools.product(*domains):
            if all(v[keys.index(k)] in vs for k,vs in spec['entryContexts'][root].items()) and allowed(root,v):
                queue.append((root,v,0));seen.add((root,v))
    while queue:
        node,v,d=queue.popleft();old=dict(zip(keys,v))
        for t in m['transitions']:
            if t['from']!=node:continue
            for ci,c in enumerate(spec['transitionRules'][t['id']]['cases']):
                if not all(old[k] in values for k,values in c.get('requires',{}).items()):continue
                possibilities={k:[old[k]] for k in keys}
                for k,values in c.get('set',{}).items():possibilities[k]=values
                for k in c.get('forget',[]):possibilities[k]=spec['domains'][k]['values']
                for k,src in c.get('setFrom',{}).items():possibilities[k]=[old[src]]
                for out in itertools.product(*(possibilities[k] for k in keys)):
                    if not allowed(t['to'],out):continue
                    dist.setdefault(t['id'],d+1)
                    case_dist.setdefault((t['id'],ci),d+1)
                    key=(t['to'],out)
                    if key not in seen:seen.add(key);queue.append((t['to'],out,d+1))
    return dist,case_dist


class FeasibilityTests(unittest.TestCase):
    def test_random_symbolic_witnesses_match_concrete_exhaustion(self):
        for seed in range(120):
            rng=random.Random(seed);m=fixture();s=m['pathContext']
            if seed%3==0:m['entryStateIds'].append('C');s['entryContexts']['C']={'x':['1']}
            for t in m['transitions']:
                cases=[]
                for _ in range(rng.randint(1,2)):
                    c={}
                    if rng.random()<.8:c['requires']={rng.choice(['x','y']):[rng.choice(['0','1'])]}
                    for key in ['x','y']:
                        op=rng.choice(['keep','set','forget','copy'])
                        if op=='set':c.setdefault('set',{})[key]=[rng.choice(['0','1'])]
                        if op=='forget':c.setdefault('forget',[]).append(key)
                        if op=='copy':c.setdefault('setFrom',{})[key]=rng.choice(['x','y'])
                    cases.append(c)
                s['transitionRules'][t['id']]={'cases':cases,'reason':'合成','sourceRefs':[{'sourceId':'P','locator':'合成'}]}
            if seed%2==0:s['stateConstraints']['B']={'requires':{'x':['1']},'reason':'合成','sourceRefs':[{'sourceId':'P','locator':'合成'}]}
            expected,case_expected=concrete_oracle(m);actual=analyze(m)
            for tid,w in actual['transitions'].items():
                with self.subTest(seed=seed,tid=tid):
                    self.assertEqual(tid in expected,w['status']=='finite_domain_passed')
                    if tid in expected:self.assertEqual(expected[tid],len(w['transitionIds']))
            for tid,rows in actual['caseResults'].items():
                for ci,w in enumerate(rows):
                    with self.subTest(seed=seed,tid=tid,case=ci):
                        self.assertEqual((tid,ci) in case_expected,w['status']=='finite_domain_passed')
                        if (tid,ci) in case_expected:
                            self.assertEqual(ci,w['ruleCases'][-1])
                            self.assertEqual(case_expected[tid,ci],len(w['transitionIds']))
            self.assertEqual([],verify_witnesses(m,actual))

    def test_possible_edge_does_not_hide_impossible_declared_case(self):
        m=fixture()
        for t in m['transitions']:m['pathContext']['transitionRules'][t['id']]={'cases':[{}]}
        m['pathContext']['transitionRules']['T0']['cases'].append({'requires':{'x':['1']}})
        r=analyze(m)
        self.assertEqual('finite_domain_passed',r['transitions']['T0']['status'])
        self.assertEqual('infeasible',r['caseResults']['T0'][1]['status'])
        self.assertEqual('failed',r['status'])
        bad=copy.deepcopy(r);bad['caseResults']['T0'][1]=copy.deepcopy(bad['caseResults']['T0'][0])
        bad['caseCounts']=dict(Counter(w['status'] for rows in bad['caseResults'].values() for w in rows));bad['status']='passed'
        self.assertIn('T0: target case mismatch',verify_witnesses(m,bad))
        bad=copy.deepcopy(r);bad['caseResults']['T0'].pop()
        bad['caseCounts']=dict(Counter(w['status'] for rows in bad['caseResults'].values() for w in rows));bad['status']='passed'
        self.assertIn('T0: case count mismatch',verify_witnesses(m,bad))
        self.assertEqual('incomplete',Solver(m).witness('T0',limit=0,target_case=0)['status'])

    def test_case_status_must_match_declared_constraint_scope(self):
        m=fixture()
        for t in m['transitions']:m['pathContext']['transitionRules'][t['id']]={'cases':[{}]}
        for status in ('made_up','no_guard_constraints','structure_only'):
            r=copy.deepcopy(analyze(m));r['caseResults']['T0'][0]['status']=status
            r['caseCounts']=dict(Counter(w['status'] for rows in r['caseResults'].values() for w in rows))
            r['status']='incomplete' if status=='structure_only' else 'passed'
            self.assertIn('case witness status incompatible with model constraint scope',verify_witnesses(m,r))
        m.pop('pathContext')
        r=copy.deepcopy(analyze(m));r['caseResults']['T0'][0]['status']='finite_domain_passed'
        r['caseCounts']=dict(Counter(w['status'] for rows in r['caseResults'].values() for w in rows))
        self.assertIn('case witness status incompatible with model constraint scope',verify_witnesses(m,r))

    def test_edge_budget_can_exhaust_before_individual_case_budgets(self):
        m=fixture();m['transitions']=m['transitions'][:1]
        m['pathContext']['entryContexts']['A']['x']=['0','1']
        m['pathContext']['transitionRules']['T0']={'cases':[{'requires':{'x':['0']}},{'requires':{'x':['1']}}]}
        r=analyze(m,limit=1)
        self.assertEqual('incomplete',r['transitions']['T0']['status'])
        self.assertEqual(['finite_domain_passed']*2,[w['status'] for w in r['caseResults']['T0']])
        self.assertEqual('incomplete',r['status'])
        self.assertEqual([],verify_witnesses(m,r))

    def test_copy_uses_pre_effect_values_including_swap(self):
        spec=fixture()['pathContext']
        self.assertEqual([{'x':{'1'},'y':{'0'}}],advance(spec,{'x':{'0'},'y':{'1'}},{'setFrom':{'x':'y','y':'x'}}))
        self.assertEqual([{'x':{'1'},'y':{'0'}}],advance(spec,{'x':{'0'},'y':{'0'}},{'set':{'x':['1']},'setFrom':{'y':'x'}}))

    def test_state_reachable_does_not_prove_each_outgoing_edge(self):
        m=fixture();s=m['pathContext']
        for t in m['transitions']:s['transitionRules'][t['id']]={'cases':[{}]}
        s['transitionRules']['T3']['cases']=[{'requires':{'x':['1']}}]
        r=analyze(m)
        self.assertEqual('finite_domain_passed',r['transitions']['T0']['status'])
        self.assertEqual('infeasible',r['transitions']['T3']['status'])

    def test_search_limit_is_not_impossibility(self):
        m=fixture()
        for t in m['transitions']:m['pathContext']['transitionRules'][t['id']]={'cases':[{}]}
        self.assertTrue(any(x['status']=='incomplete' for x in analyze(m,limit=0)['transitions'].values()))

    def test_tampered_witness_is_rejected(self):
        m=fixture()
        for t in m['transitions']:m['pathContext']['transitionRules'][t['id']]={'cases':[{}]}
        r=copy.deepcopy(analyze(m));r['transitions']['T3']['transitionIds']=['T3'];r['transitions']['T3']['ruleCases']=[0]
        self.assertTrue(verify_witnesses(m,r))
        r=copy.deepcopy(analyze(m));r['inputDigest']='stale';self.assertTrue(verify_witnesses(m,r))
        r=copy.deepcopy(analyze(m));r['transitions']['T3']={'status':'infeasible'};self.assertTrue(verify_witnesses(m,r))

    def test_repeated_domain_value_does_not_change_predicate(self):
        m=fixture()
        for t in m['transitions']:m['pathContext']['transitionRules'][t['id']]={'cases':[{'requires':{'x':['0','0']}}]}
        w=analyze(m)['transitions']['T0'];self.assertEqual('finite_domain_passed',w['status']);self.assertEqual(1,len(w['transitionIds']))

    def test_conflicting_structure_replaced_by_valid_explicit_segments(self):
        m=fixture();m['transitions']=m['transitions'][:3]
        for t in m['transitions']:m['pathContext']['transitionRules'][t['id']]={'cases':[{'set':{'x':['1']}} if t['id']=='T1' else {'requires':{'x':['0']}}],'reason':'合成','sourceRefs':[{'sourceId':'P','locator':'合成'}]}
        g=requirement_graph(m);p=g['traversal']
        self.assertEqual('feasible',p['status']);self.assertEqual('not_proven',p['optimality'])
        self.assertEqual([],g['reduction']['uncoveredRequirementIds']);self.assertEqual([],verify_coverage(m,g))
        self.assertTrue(all(r['contextCheck']['status']=='finite_domain_passed' for r in p['routes']))
        self.assertEqual(2,len(p['routes']))
        bad=copy.deepcopy(g);bad['traversal']['optimality']='proven';self.assertTrue(verify_coverage(m,bad))
        bad=copy.deepcopy(g);bad['traversal']['certificate']['globalMinimumProven']=True;self.assertTrue(verify_coverage(m,bad))
        bad=copy.deepcopy(g);bad['edges']=[];self.assertTrue(verify_coverage(m,bad))

if __name__=='__main__':unittest.main(verbosity=2)
