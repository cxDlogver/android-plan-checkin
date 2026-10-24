"""Independent subset-search oracle for minimum continuous requirement visits."""
import copy
import itertools
import random
import unittest
from collections import deque
from requirement_graph import requirement_graph, verify_coverage, reachable, full_requirement_graph


def fixture(pairs, roots=('A',), restart=True):
    names = sorted(set(roots) | {x for pair in pairs for x in pair})
    transitions = [{'id': 'T%d' % i, 'requirementId': 'R%d' % i, 'from': a, 'to': b,
                    'event': '操作', 'guard': 'true'} for i, (a, b) in enumerate(pairs)]
    return {'entryStateIds': list(roots), 'states': [{'id': x} for x in names],
            'transitions': transitions,
            'requirements': [{'id':t['requirementId'],'transitionId':t['id'],'title':t['event']} for t in transitions],
            'requirementTraversal': {'restartPolicy': 'documented_entries' if restart else 'none',
                                     'authorization': 'synthetic user decision'}}


def oracle(model):
    # 0/1 shortest path over (current state, covered edges), independent of flow.
    known = reachable(model)
    edges = [t for t in model['transitions'] if t['from'] in known]
    target = (1 << len(edges)) - 1
    queue = deque((root, 0) for root in model['entryStateIds'])
    distances = {key: 0 for key in queue}
    while queue:
        current, covered = queue.popleft()
        cost = distances[current, covered]
        if covered == target:
            return cost
        choices = [(t['to'], covered | (1 << i), 1) for i, t in enumerate(edges) if t['from'] == current]
        if model['requirementTraversal']['restartPolicy'] == 'documented_entries':
            choices += [(root, covered, 0) for root in model['entryStateIds']]
        for node, mask, weight in choices:
            key = node, mask
            if cost + weight < distances.get(key, float('inf')):
                distances[key] = cost + weight
                (queue.appendleft if weight == 0 else queue.append)(key)
    return None


class CoverageTests(unittest.TestCase):
    def assert_optimal(self, model):
        before = copy.deepcopy(model)
        graph = requirement_graph(model)
        self.assertEqual([], verify_coverage(model, graph))
        expected = oracle(model)
        if expected is None:
            self.assertEqual('infeasible', graph['traversal']['status'])
        else:
            self.assertEqual(expected, graph['traversal']['totalVisits'])
        self.assertEqual(before, model)
        return graph

    def test_dead_end_branches_need_explicit_restarts(self):
        graph = self.assert_optimal(fixture([('A', 'B'), ('A', 'C')]))
        self.assertEqual(2, len(graph['traversal']['routes']))
        self.assertEqual([], graph['edges'])
        self.assertEqual('infeasible', self.assert_optimal(fixture([('A', 'B'), ('A', 'C')], restart=False))['traversal']['status'])

    def test_return_paths_are_retained_and_repetitions_counted(self):
        graph = self.assert_optimal(fixture([('A', 'B'), ('B', 'C'), ('C', 'B'), ('B', 'D')], restart=False))
        self.assertEqual(['R0', 'R1', 'R2', 'R3'], graph['traversal']['routes'][0]['requirementIds'])
        self.assertEqual(3, len(graph['edges']))

    def test_repeated_trunk_is_paid_after_every_restart(self):
        graph = self.assert_optimal(fixture([('A', 'B'), ('B', 'C'), ('B', 'D')]))
        self.assertEqual(4, graph['traversal']['totalVisits'])
        self.assertEqual(2, graph['traversal']['visitCounts']['R0'])

    def test_parallel_edges_self_loops_and_cycles(self):
        self.assert_optimal(fixture([('A', 'A'), ('A', 'B'), ('A', 'B'), ('B', 'A')]))

    def test_multiple_disconnected_entry_components(self):
        graph = self.assert_optimal(fixture([('A', 'A'), ('X', 'Y'), ('Y', 'X')], ('A', 'X')))
        self.assertEqual({'A', 'X'}, {r['entryStateId'] for r in graph['traversal']['routes']})

    def test_unreachable_nodes_remain_uncovered(self):
        graph = self.assert_optimal(fixture([('A', 'B'), ('X', 'X')]))
        self.assertEqual(['R1'], graph['reduction']['unreachableRequirementIds'])
        self.assertEqual(2, len(graph['nodes']))
        self.assertEqual('partial', graph['traversal']['status'])

    def test_no_entry_does_not_invent_one(self):
        graph = requirement_graph(fixture([('X', 'X')], ()))
        self.assertEqual('infeasible', graph['traversal']['status'])
        self.assertEqual(['R0'], graph['reduction']['uncoveredRequirementIds'])

    def test_stable_under_input_transition_reordering(self):
        model = fixture([('A', 'B'), ('B', 'A'), ('A', 'C'), ('C', 'B'), ('B', 'C')])
        expected = self.assert_optimal(model)['traversal']
        for seed in range(12):
            random.Random(seed).shuffle(model['transitions'])
            self.assertEqual(expected, requirement_graph(model)['traversal'])

    def test_tampered_routes_counts_edges_context_are_rejected(self):
        model = fixture([('A', 'B'), ('B', 'A'), ('B', 'C')])
        graph = self.assert_optimal(model)
        mutations = [lambda g: g['edges'].pop(), lambda g: g['traversal'].update(totalVisits=100),
                     lambda g: g['traversal']['routes'][0]['transitionIds'].reverse(),
                     lambda g: g['traversal']['routes'][0]['contextCheck'].update(status='invented'),
                     lambda g: g['traversal']['certificate'].update(residualNoNegativeCycle=False)]
        for mutate in mutations:
            bad = copy.deepcopy(graph)
            mutate(bad)
            self.assertTrue(verify_coverage(model, bad))

    def test_restart_requires_authorization(self):
        model = fixture([('A', 'B')])
        del model['requirementTraversal']['authorization']
        with self.assertRaises(ValueError):
            requirement_graph(model)

    def test_unknown_cost_is_not_silently_ignored(self):
        model = fixture([('A', 'B')])
        model['requirementTraversal']['restartCost'] = 99
        with self.assertRaises(ValueError):
            requirement_graph(model)

    def test_fixed_endpoint_optimum_is_not_free_endpoint_optimum(self):
        model = fixture([('A', 'B'), ('B', 'A')], restart=False)
        graph = self.assert_optimal(model)
        graph['traversal'].update(totalVisits=3, repeatedVisits=1, visitCounts={'R0': 2, 'R1': 1})
        route = graph['traversal']['routes'][0]
        route['transitionIds'] = ['T0', 'T1', 'T0']
        route['requirementIds'] = ['R0', 'R1', 'R0']
        graph['edges'] = [{**e, 'usageCount': 1} for e in full_requirement_graph(model)['edges']]
        graph['reduction'].update(retainedEdgeCount=2, removedEdgeCount=0)
        self.assertTrue(any('globally optimal' in e for e in verify_coverage(model, graph)))

    def test_false_infeasibility_claim_is_rejected(self):
        for restart in (False, True):
            model = fixture([('A', 'B'), ('B', 'A')], restart=restart)
            graph = self.assert_optimal(model)
            graph['edges'] = []
            graph['reduction'].update(uncoveredRequirementIds=['R0', 'R1'], retainedEdgeCount=0, removedEdgeCount=2)
            graph['traversal'].update(routes=[], status='infeasible', totalVisits=0, repeatedVisits=0, visitCounts={})
            self.assertTrue(any('infeasibility claim' in e for e in verify_coverage(model, graph)))

    def test_empty_model_has_no_artificial_requirement(self):
        self.assertEqual(0, requirement_graph(fixture([]))['traversal']['totalVisits'])

    def test_context_conflict_cannot_be_published_as_optimal_coverage(self):
        model = fixture([('A', 'B'), ('B', 'A'), ('A', 'C')], restart=False)
        for t in model['transitions']:
            t['sourceIds'] = ['P']
        model['pathContext'] = {
            'domains': {'kind': {'values': ['x', 'y'], 'labels': {'x': '可编辑', 'y': '只读'}, 'description': '模式'}},
            'entryContexts': {'A': {'kind': ['x']}},
            'transitionRules': {t['id']: {'reason': 'test', 'sourceRefs': [{'sourceId': 'P', 'locator': 'test'}],
                                         'cases': [{'set': {'kind': ['y']}} if t['id'] == 'T1' else {'requires': {'kind': ['x']}}]}
                                for t in model['transitions']}}
        graph = requirement_graph(model)
        self.assertEqual([],verify_coverage(model,graph))
        self.assertEqual('partial', graph['traversal']['status'])
        self.assertEqual('not_proven', graph['traversal']['optimality'])
        self.assertTrue(graph['reduction']['uncoveredRequirementIds'])
        self.assertTrue(all(r['contextCheck']['status']=='finite_domain_passed' for r in graph['traversal']['routes']))

    def test_all_three_state_simple_graphs_against_subset_oracle(self):
        pairs = list(itertools.product('ABC', repeat=2))
        for bits in range(1, 1 << len(pairs)):
            chosen = [pair for i, pair in enumerate(pairs) if bits & (1 << i)]
            for roots, restart in [(('A',), True), (('A', 'C'), True), (('A',), False)]:
                with self.subTest(bits=bits, roots=roots, restart=restart):
                    self.assert_optimal(fixture(chosen, roots, restart))


if __name__ == '__main__':
    unittest.main(verbosity=2)
