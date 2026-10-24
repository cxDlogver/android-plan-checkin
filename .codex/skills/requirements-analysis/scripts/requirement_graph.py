"""Minimum-visit directed coverage, then retain only used continuations.

One requirement is one state edge. Original edges have lower bound 1 and cost 1;
authorized restarts have lower bound 0 and cost 0. State edges are never pruned.
Only standard-library code is used; business guards are checked separately.
"""
from collections import Counter, deque
import json
from functools import lru_cache
from feasibility import analyze, Solver
from feasible_routes import cover
from path_context import advance, validate_context, constrain_state


def continuation_id(a, b):
    return 'C:' + json.dumps([a, b], ensure_ascii=False, separators=(',', ':'))


def full_requirement_graph(model):
    requirements = {r['id']: r for r in model['requirements']}
    transitions = {t['id']: t for t in model['transitions']}
    if len(requirements) != len(model['requirements']) or len(transitions) != len(model['transitions']):
        raise ValueError('duplicate transition or atomic requirement')
    if len(requirements) != len(transitions):
        raise ValueError('each state transition must correspond to exactly one atomic requirement')
    for rid, requirement in requirements.items():
        tid = requirement.get('transitionId')
        if requirement.get('kind', 'behavior') != 'behavior' or 'stateIds' in requirement:
            raise ValueError(rid + ': static constraints cannot replace transition-derived atomic requirements')
        if tid not in transitions or transitions[tid].get('requirementId') != rid:
            raise ValueError(rid + ': transition/requirement reference mismatch')
    for tid, transition in transitions.items():
        rid = transition.get('requirementId')
        if rid not in requirements or requirements[rid].get('transitionId') != tid:
            raise ValueError(tid + ': transition/requirement reference mismatch')
    nodes, edges, outgoing = [], [], {}
    for t in model['transitions']:
        rid = t['requirementId']
        requirement = requirements.get(rid, {})
        nodes.append({'id': rid, 'title': requirement.get('title', t['event']),
                      'transitionId': t['id'], 'featureIds': t.get('featureIds', []),
                      'from': t['from'], 'to': t['to'], 'status': requirement.get('status', 'draft')})
        outgoing.setdefault(t['from'], []).append(rid)
    for node in nodes:
        for successor in outgoing.get(node['to'], []):
            edges.append({'id': continuation_id(node['id'], successor),
                          'from': node['id'], 'to': successor, 'type': 'continuation',
                          'viaStateId': node['to'], 'guardEvaluation': 'required_at_execution'})
    return {'nodes': nodes, 'edges': edges}


def policy(model):
    value = model.get('requirementTraversal', {'restartPolicy': 'none'})
    if not isinstance(value, dict) or value.get('restartPolicy') not in {'none', 'documented_entries'}:
        raise ValueError('requirementTraversal.restartPolicy must be none or documented_entries')
    if set(value) - {'restartPolicy', 'authorization'}:
        raise ValueError('unsupported requirementTraversal option or cost')
    if value['restartPolicy'] == 'documented_entries' and not (
            isinstance(value.get('authorization'), str) and value['authorization'].strip()):
        raise ValueError('restarts require an explicit authorization reference')
    return value['restartPolicy']


def reachable(model):
    roots = model.get('entryStateIds', [])
    adjacency = {}
    for t in model['transitions']:
        adjacency.setdefault(t['from'], []).append(t['to'])
    seen, queue = set(roots), deque(roots)
    while queue:
        for target in adjacency.get(queue.popleft(), []):
            if target not in seen:
                seen.add(target)
                queue.append(target)
    return seen


def residual_certificate(vertices, arcs):
    """Independently test optimality: no negative cycle in lower-bound residuals.

Each arc is (from, to, unit cost, flow, lower bound, can increase).
Potentials certify nonnegative reduced cost on EVERY residual arc.
"""
    if not vertices:
        return True
    residual = []
    for a, b, cost, flow, lower, increase in arcs:
        if increase:
            residual.append((a, b, cost))
        if flow > lower:
            residual.append((b, a, -cost))
    potential = {v: 0 for v in vertices}
    for iteration in range(len(vertices)):
        changed = False
        for a, b, cost in residual:
            if potential[b] > potential[a] + cost:
                potential[b] = potential[a] + cost
                changed = True
        if not changed:
            return True
    return not changed


def balance(edges, roots, restart, start=None, end=None):
    """Exact integral min-cost balancing; None means no feasible flow."""
    names = sorted({t[k] for t in edges for k in ('from', 'to')})
    index = {name: i for i, name in enumerate(names)}
    hub = len(names)
    n = hub + (1 if restart else 0)
    base = [{'from': index[t['from']], 'to': index[t['to']], 'kind': 'real', 't': t}
            for t in sorted(edges, key=lambda t: t['id'])]
    if not restart:
        base.append({'from': index[end], 'to': index[start], 'kind': 'close'})
    delta = [0] * n
    for e in base:
        delta[e['from']] += 1
        delta[e['to']] -= 1
    demand = sum(max(0, x) for x in delta)
    # Secondary objective: fewer restart arcs, without changing visit optimum.
    # Every auxiliary arc has capacity demand, so total resets < this multiplier.
    multiplier = 1 + max(1, demand) * (n + 1)
    source, sink = n, n + 1
    network = [[] for _ in range(n + 2)]

    def add(a, b, capacity, cost):
        # Self-loop forward/reverse slots must differ.
        forward = {'to': b, 'rev': len(network[b]) + (a == b), 'cap': capacity,
                   'initial': capacity, 'cost': cost}
        backward = {'to': a, 'rev': len(network[a]), 'cap': 0, 'initial': 0, 'cost': -cost}
        network[a].append(forward)
        network[b].append(backward)
        return forward

    additions = []
    for edge in base:
        if edge['kind'] == 'real':
            additions.append((edge, add(edge['from'], edge['to'], demand, multiplier)))
    if restart:
        for name in names:
            edge = {'from': index[name], 'to': hub, 'kind': 'restart'}
            additions.append((edge, add(edge['from'], hub, demand, 1)))
        for name in roots:
            edge = {'from': hub, 'to': index[name], 'kind': 'entry'}
            additions.append((edge, add(hub, edge['to'], demand, 0)))
    for i, d in enumerate(delta):
        if d < 0:
            add(source, i, -d, 0)
        elif d > 0:
            add(i, sink, d, 0)
    flow = 0
    while flow < demand:
        distance = [float('inf')] * len(network)
        parent = [None] * len(network)
        distance[source] = 0
        for _ in range(len(network) - 1):
            changed = False
            for a, rows in enumerate(network):
                if distance[a] == float('inf'):
                    continue
                for j, edge in enumerate(rows):
                    b = edge['to']
                    if edge['cap'] and distance[b] > distance[a] + edge['cost']:
                        distance[b] = distance[a] + edge['cost']
                        parent[b] = (a, j)
                        changed = True
            if not changed:
                break
        if parent[sink] is None:
            return None
        amount, v = demand - flow, sink
        while v != source:
            a, j = parent[v]
            amount = min(amount, network[a][j]['cap'])
            v = a
        v = sink
        while v != source:
            a, j = parent[v]
            edge = network[a][j]
            edge['cap'] -= amount
            network[v][edge['rev']]['cap'] += amount
            v = a
        flow += amount
    copies = list(base)
    for edge, arc in additions:
        copies.extend([edge] * (arc['initial'] - arc['cap']))
    adjacency = [[] for _ in range(n)]
    for i in reversed(range(len(copies))):
        adjacency[copies[i]['from']].append(i)
    origin = hub if restart and adjacency[hub] else index[roots[0] if restart else start]
    stack, reverse = [(origin, None)], []
    while stack:
        current, previous = stack[-1]
        if adjacency[current]:
            i = adjacency[current].pop()
            stack.append((copies[i]['to'], i))
        else:
            stack.pop()
            if previous is not None:
                reverse.append(previous)
    if len(reverse) != len(copies):
        return None  # No hidden disconnected circuit may count as coverage.
    walk = [copies[i] for i in reversed(reverse)]
    if not restart:
        cut = next(i for i, e in enumerate(walk) if e['kind'] == 'close')
        walk = walk[cut + 1:] + walk[:cut]
    routes, segment = [], []
    for edge in walk:
        if edge['kind'] == 'real':
            segment.append(edge['t'])
        elif edge['kind'] == 'restart' and segment:
            routes.append(segment)
            segment = []
    if segment:
        routes.append(segment)
    return routes, demand


def structural_routes(model):
    allow_restart = policy(model) == 'documented_entries'
    roots = model.get('entryStateIds', [])
    known = reachable(model)
    edges = [t for t in model['transitions'] if t['from'] in known]
    if not edges:
        return [], []
    if not allow_restart:
        best = None
        ends = sorted({t[k] for t in edges for k in ('from', 'to')})
        for start in roots:
            if start not in ends:
                continue
            for end in ends:
                candidate = balance(edges, roots, False, start, end)
                if candidate is None:
                    continue
                routes, demand = candidate
                score = sum(map(len, routes))
                if best is None or score < best[0]:
                    best = score, routes, demand
        return (best[1], [best[2]]) if best else ([], [])
    # Required edges in each weak component are connected. This is what makes
    # balancing sufficient; arbitrary disconnected required-edge problems differ.
    weak = {}
    for t in edges:
        weak.setdefault(t['from'], set()).add(t['to'])
        weak.setdefault(t['to'], set()).add(t['from'])
    handled, routes, demands = set(), [], []
    for root in roots:
        if root in handled or root not in weak:
            continue
        component, queue = {root}, deque([root])
        while queue:
            for target in sorted(weak[queue.popleft()]):
                if target not in component:
                    component.add(target)
                    queue.append(target)
        handled.update(component)
        result = balance([t for t in edges if t['from'] in component],
                         [r for r in roots if r in component], True)
        if result is None:
            raise ValueError('coverage flow failed for reachable component')
        segments, demand = result
        routes.extend(segments)
        demands.append(demand)
    return routes, demands


def check_context(model, route, max_contexts=200000):
    spec = model.get('pathContext')
    transitions = {t['id']: t for t in model['transitions']}
    if not spec:
        unmodeled = any(transitions[t].get('guard', 'true') != 'true' for t in route['transitionIds'])
        return {'status': 'not_modeled' if unmodeled else 'no_guard_constraints', 'checkedSteps': 0}
    errors = validate_context(model)
    if errors:
        raise ValueError('; '.join(errors))
    initial = {k: set(v['values']) for k, v in spec['domains'].items()}
    for k, values in spec['entryContexts'][route['entryStateId']].items():
        initial[k] &= set(values)
    initial=constrain_state(spec,route['entryStateId'],initial)
    if initial is None:return {'status':'conflict','checkedSteps':0,'step':0,'reason':'invalid_entry_context'}
    contexts = [(initial, [])]
    for step, tid in enumerate(route['transitionIds'], 1):
        updated = {}
        for context, choices in contexts:
            for ci, case in enumerate(spec['transitionRules'][tid]['cases']):
                for row in advance(spec, context, case):
                    row=constrain_state(spec,transitions[tid]['to'],row)
                    if row is None:continue
                    signature = tuple((k, tuple(sorted(v))) for k, v in sorted(row.items()))
                    updated.setdefault(signature, (row, choices + [ci]))
                    if len(updated) > max_contexts:
                        return {'status': 'incomplete', 'checkedSteps': step - 1,
                                'transitionId': tid, 'reason': 'context_limit'}
        if not updated:
            return {'status': 'conflict', 'checkedSteps': step - 1, 'step': step,
                    'transitionId': tid, 'reason': 'empty_context_intersection'}
        contexts = list(updated.values())
    solver=Solver(model); goal=solver.full; choices=contexts[0][1]
    for tid,ci in reversed(list(zip(route['transitionIds'],choices))):
        goal=solver.preimage(transitions[tid],spec['transitionRules'][tid]['cases'][ci],goal)
        if goal is None:raise ValueError('forward route disagrees with backward replay')
    goal=solver.meet(goal,solver.entries[route['entryStateId']])
    if goal is None:raise ValueError('route initial conditions disagree with entry')
    initial_context={k:[v for j,v in enumerate(solver.values[i]) if goal[i]&(1<<j)] for i,k in enumerate(solver.names)}
    return {'status': 'finite_domain_passed', 'checkedSteps': len(route['transitionIds']),
            'initialContext':initial_context,'ruleCases':choices}


def verify_coverage(model, graph):
    """Verify routes/support/counts and a primary-cost residual certificate."""
    try:
        full = full_requirement_graph(model)
    except ValueError as exc:
        return [str(exc)]
    original = {e['id']: e for e in full['edges']}
    transitions = {t['id']: t for t in model['transitions']}
    reqs = {t['requirementId']: t for t in model['transitions']}
    info = graph['reduction']
    plan = graph['traversal']
    errors, counts, uses = [], Counter(), Counter()
    for key, value in [('objective', 'minimum_total_requirement_visits'),
                       ('restartPolicy', policy(model)), ('restartCost', 0),
                       ('optimalityScope', 'finite_domain_feasibility' if plan.get('algorithm')=='witness_cover' else 'structure_only')]:
        if plan.get(key) != value:
            errors.append('incorrect traversal policy or claim: ' + key)
    if graph['nodes'] != full['nodes']:
        errors.append('all original requirement nodes and attributes must remain')
    arcs, hubs = [], set()
    route_rows = plan['routes']
    if policy(model) == 'none' and len(route_rows) > 1:
        errors.append('multiple routes require restart authorization')
    # An object sentinel cannot collide with a real state ID.
    hub = object()
    for route in route_rows:
        current = route['entryStateId']
        if current not in model.get('entryStateIds', []):
            errors.append('route starts outside documented entries')
        sequence = []
        for tid in route['transitionIds']:
            if tid not in transitions:
                return errors + ['route references unknown transition']
            t = transitions[tid]
            if t['from'] != current:
                errors.append('route teleports between states')
            current = t['to']
            counts[t['requirementId']] += 1
            sequence.append(t['requirementId'])
        if sequence != route['requirementIds'] or not sequence:
            errors.append('route requirement mapping invalid')
        if route['contextCheck'] != check_context(model, route):
            errors.append('context result differs from replay')
        uses.update(continuation_id(a, b) for a, b in zip(sequence, sequence[1:]))
        if policy(model) == 'documented_entries':
            arcs.extend([(current, hub, 0, 1, 0, True), (hub, route['entryStateId'], 0, 1, 0, True)])
            hubs.add(hub)
    expected = []
    for edge in full['edges']:
        if uses[edge['id']]:
            expected.append({**edge, 'usageCount': uses[edge['id']]})
    if graph['edges'] != expected or any(k not in original for k in uses):
        errors.append('retained edges must equal adjacent pairs actually used by routes')
    uncovered = [n['id'] for n in full['nodes'] if not counts[n['id']]]
    known = reachable(model)
    unreachable = [n['id'] for n in full['nodes'] if n['from'] not in known]
    expected_roots = [n['id'] for root in model.get('entryStateIds', [])
                      for n in sorted(full['nodes'], key=lambda n: n['id']) if n['from'] == root]
    if info['entryRequirementIds'] != expected_roots:
        errors.append('incorrect entry requirements')
    for key, expected_value in [('uncoveredRequirementIds', uncovered), ('unreachableRequirementIds', unreachable),
                                ('originalEdgeCount', len(full['edges'])), ('retainedEdgeCount', len(expected)),
                                ('removedEdgeCount', len(full['edges']) - len(expected))]:
        if info.get(key) != expected_value:
            errors.append('incorrect metadata: ' + key)
    total = sum(counts.values())
    if plan['totalVisits'] != total or plan['repeatedVisits'] != total - len(counts) or plan['visitCounts'] != dict(counts):
        errors.append('incorrect visit counts')
    if plan.get('algorithm')=='witness_cover':
        validation=analyze(model)
        if info.get('kind')!='feasible_route_support' or info.get('algorithm')!='shortest_witness_cover':errors.append('incorrect feasible route algorithm metadata')
        if plan.get('certificate')!={'kind':'replayed_finite_domain_witnesses','globalMinimumProven':False}:errors.append('heuristic certificate must not claim global minimum')
        for route in route_rows:
            if route['contextCheck']['status'] not in {'finite_domain_passed','no_guard_constraints'}:errors.append('feasible coverage contains a condition conflict or unknown result')
        if plan.get('status') != ('partial' if uncovered else 'feasible'):errors.append('incorrect feasible coverage status')
        if plan.get('optimality')!='not_proven':errors.append('heuristic coverage cannot claim minimum visits')
        if plan.get('transitionValidation')!= {'status':validation['status'],'counts':validation['counts'],'inputDigest':validation['inputDigest']}:errors.append('stale transition validation')
        lower_segments,_=structural_routes(model)
        lower=sum(map(len,lower_segments))
        if plan.get('lowerBoundVisits')!=lower or total<lower and not uncovered:errors.append('invalid structural lower bound')
        return errors
    # A fixed-endpoint residual certificate alone cannot prove a free-endpoint
    # optimum, or certify an infeasibility assertion. Re-solve all allowed
    # endpoint pairs before accepting either claim; small-graph tests use an
    # independent subset-search oracle to validate this planner.
    optimum = None
    if policy(model) == 'none':
        alternatives, _ = structural_routes(model)
        if alternatives:
            optimum = sum(map(len, alternatives))
    if not route_rows and reqs:
        if plan['status'] != 'infeasible':
            errors.append('missing routes cannot be optimal')
        if optimum is not None or (policy(model) == 'documented_entries' and len(unreachable) < len(reqs)):
            errors.append('infeasibility claim contradicted by a feasible coverage route')
        return errors
    if policy(model) == 'none' and route_rows and total != optimum:
        errors.append('route is not globally optimal over documented starts and free endpoints')
    if set(uncovered) != set(unreachable):
        errors.append('a reachable requirement is not covered')
    for t in model['transitions']:
        if t['requirementId'] in counts:
            arcs.append((t['from'], t['to'], 1, counts[t['requirementId']], 1, True))
    vertices = {v for a, b, *_ in arcs for v in (a, b)}
    if hubs:
        # Include unused restart/entry alternatives in the optimality test.
        for v in list(vertices - hubs):
            arcs.append((v, hub, 0, 0, 0, True))
        for root in model.get('entryStateIds', []):
            if root in vertices:
                arcs.append((hub, root, 0, 0, 0, True))
    certificate = residual_certificate(vertices, arcs)
    if not certificate or plan['certificate'].get('residualNoNegativeCycle') is not True:
        errors.append('minimum-cost certificate failed')
    expected_status = 'partial' if uncovered else 'optimal'
    if plan['status'] != expected_status:
        errors.append('incorrect structural coverage status')
    return errors


@lru_cache(maxsize=2)
def _graph_for_key(key):
    return json.dumps(_build_requirement_graph(json.loads(key)),ensure_ascii=False)


def requirement_graph(model):
    relevant={key:model.get(key) for key in ('entryStateIds','states','transitions','requirements','pathContext','requirementTraversal') if key in model}
    return json.loads(_graph_for_key(json.dumps(relevant,ensure_ascii=False,sort_keys=True,separators=(',',':'))))


def _build_requirement_graph(model):
    full = full_requirement_graph(model)
    node_ids = [n['id'] for n in full['nodes']]
    if len(node_ids) != len(set(node_ids)) or len({t['id'] for t in model['transitions']}) != len(node_ids):
        raise ValueError('duplicate transition or requirement')
    roots = model.get('entryStateIds', [])
    if len(roots) != len(set(roots)):
        raise ValueError('duplicate state entries')
    segments, demands = structural_routes(model)
    routes, counts, uses = [], Counter(), Counter()
    for segment in segments:
        route = {'entryStateId': segment[0]['from'], 'transitionIds': [t['id'] for t in segment],
                 'requirementIds': [t['requirementId'] for t in segment]}
        route['contextCheck'] = check_context(model, route)
        routes.append(route)
        counts.update(route['requirementIds'])
        uses.update(continuation_id(a, b) for a, b in zip(route['requirementIds'], route['requirementIds'][1:]))
    structural_total=sum(counts.values())
    context_aware=any(r['contextCheck']['status'] in {'conflict','incomplete','not_modeled'} for r in routes)
    validation=analyze(model)
    context_aware=context_aware or (bool(model.get('pathContext')) and validation['status']!='passed')
    if context_aware:
        routes=cover(model,validation,policy(model)=='documented_entries')
        counts=Counter();uses=Counter()
        for route in routes:
            route['requirementIds']=[next(t['requirementId'] for t in model['transitions'] if t['id']==tid) for tid in route['transitionIds']]
            route['contextCheck']=check_context(model,route)
            counts.update(route['requirementIds'])
            uses.update(continuation_id(a,b) for a,b in zip(route['requirementIds'],route['requirementIds'][1:]))
    kept = [{**e, 'usageCount': uses[e['id']]} for e in full['edges'] if uses[e['id']]]
    known = reachable(model)
    uncovered = [n for n in node_ids if n not in counts]
    unreachable = [n['id'] for n in full['nodes'] if n['from'] not in known]
    graph = {'nodes': full['nodes'], 'edges': kept,
             'reduction': {'kind': 'minimum_visit_route_support', 'algorithm': 'min_cost_flow_then_hierholzer',
                           'entryRequirementIds': [n['id'] for root in roots for n in sorted(full['nodes'], key=lambda n: n['id']) if n['from'] == root],
                           'unreachableRequirementIds': unreachable, 'uncoveredRequirementIds': uncovered,
                           'originalEdgeCount': len(full['edges']), 'retainedEdgeCount': len(kept),
                           'removedEdgeCount': len(full['edges']) - len(kept)},
             'traversal': {'objective': 'minimum_total_requirement_visits', 'restartPolicy': policy(model),
                           'restartCost': 0, 'optimalityScope': 'structure_only',
                           'status': ('partial' if uncovered else 'optimal') if segments or not node_ids else 'infeasible',
                           'totalVisits': sum(counts.values()), 'repeatedVisits': sum(counts.values()) - len(counts),
                           'visitCounts': dict(counts), 'routes': routes,
                           'certificate': {'balancingUnits': sum(demands), 'residualNoNegativeCycle': bool(segments) or not node_ids}},
             'semantics': 'All requirements remain. Retained original continuations are exactly adjacent pairs used by minimum-visit structural coverage routes, with multiplicity. Restart boundaries are explicit route boundaries, never business arrows. Edge count is not the optimization objective. Context checks do not prove unmodeled business conditions.'}
    if context_aware:
        graph['reduction']['algorithm']='shortest_witness_cover'
        graph['reduction']['kind']='feasible_route_support'
        graph['traversal'].update({'algorithm':'witness_cover','status':'partial' if uncovered else 'feasible',
            'optimalityScope':'finite_domain_feasibility','optimality':'not_proven','lowerBoundVisits':structural_total,
            'transitionValidation':{'status':validation['status'],'counts':validation['counts'],'inputDigest':validation['inputDigest']},
            'certificate':{'kind':'replayed_finite_domain_witnesses','globalMinimumProven':False}})
        graph['semantics']='所有原子需求保留；边仅来自条件重放通过的真实入口路线，相同有向连接合并计次。完整覆盖与可执行条件分开验证；当前路线未证明全局最短，结构求解只提供访问下界。'
    errors = verify_coverage(model, graph)
    if errors:
        raise ValueError('invalid coverage graph: ' + '; '.join(errors))
    return graph
