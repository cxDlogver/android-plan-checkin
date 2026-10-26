#!/usr/bin/env python3
"""Independent exhaustive optimality tests for minimum-visit coverage with free restarts."""
from collections import deque
import unittest
from coverage_route import minimum_visit_plan

def graph(arcs,initial=(0,),size=None):
    size=size if size is not None else max((v for pair in arcs for v in pair),default=0)+1
    return {"states":[{"id":str(v),"isInitial":v in initial} for v in range(size)],
            "transitions":[{"id":"T"+str(i).zfill(3),"from":str(a),"to":str(b)} for i,(a,b) in enumerate(arcs)]}

def exhaustive_minimum(model):
    transitions=model["transitions"];n=len(transitions)
    if not n: return 0
    initial={s["id"] for s in model["states"] if s["isInitial"]};done=(1<<n)-1;queue=deque();seen=set()
    for i,t in enumerate(transitions):
        if t["from"] in initial: queue.append((1<<i,i,1));seen.add((1<<i,i))
    while queue:
        mask,last,cost=queue.popleft()
        if mask==done: return cost
        for j,t in enumerate(transitions):
            if transitions[last]["to"]==t["from"] or t["from"] in initial:
                key=(mask|(1<<j),j)
                if key not in seen: seen.add(key);queue.append((*key,cost+1))
    raise ValueError("No legal covering sequence")

class CoverageRouteTests(unittest.TestCase):
    def check(self,model):
        sequence,minimum=minimum_visit_plan(model);by_id={"R-"+t["id"]:t for t in model["transitions"]};initial={s["id"] for s in model["states"] if s["isInitial"]}
        self.assertEqual(set(sequence),set(by_id));self.assertEqual(len(sequence),minimum)
        if sequence: self.assertIn(by_id[sequence[0]]["from"],initial)
        for a,b in zip(sequence,sequence[1:]): self.assertTrue(by_id[a]["to"]==by_id[b]["from"] or by_id[b]["from"] in initial)
        self.assertEqual(minimum,exhaustive_minimum(model));return sequence,minimum
    def test_branch_requires_repeating_entry_requirement(self):
        sequence,cost=self.check(graph([(0,1),(1,2),(1,3)]));self.assertEqual(cost,4);self.assertEqual(sequence.count("R-T000"),2)
    def test_initial_requirements_can_be_reentered_after_dead_ends(self):
        _,cost=self.check(graph([(0,1),(0,2)]));self.assertEqual(cost,2)
    def test_disconnected_balanced_components_and_multiple_initial_states(self):
        _,cost=self.check(graph([(0,1),(1,0),(2,3),(3,2)],initial=(0,2)));self.assertEqual(cost,4)
    def test_open_end_does_not_require_return_to_start(self):
        _,cost=self.check(graph([(0,1),(1,2)]));self.assertEqual(cost,2)
    def test_self_loops_parallel_transitions_and_empty_graph(self):
        for model in [graph([(0,0)]),graph([(0,1),(0,1)]),graph([],size=1)]: self.check(model)
    def test_input_reordering_keeps_the_same_optimal_sequence(self):
        model=graph([(0,1),(1,0),(1,2),(0,2)]);first=minimum_visit_plan(model);model["states"].reverse();model["transitions"].reverse();self.assertEqual(minimum_visit_plan(model),first)
    def test_unreachable_required_component_is_rejected(self):
        with self.assertRaises(ValueError): minimum_visit_plan(graph([(0,0),(1,1)],size=2))
    def test_all_reachable_three_state_directed_graphs_against_bitmask_search(self):
        choices=[(a,b) for a in range(3) for b in range(3)];checked=0
        for mask in range(1,1<<len(choices)):
            arcs=[pair for i,pair in enumerate(choices) if mask&(1<<i)];reachable={0}
            while True:
                after=reachable|{b for a,b in arcs if a in reachable}
                if after==reachable: break
                reachable=after
            if reachable!={0,1,2}: continue
            self.check(graph(arcs,size=3));checked+=1
        self.assertGreater(checked,200)

if __name__=="__main__": unittest.main(verbosity=2)
