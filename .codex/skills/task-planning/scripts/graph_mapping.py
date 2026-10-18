"""Lossless requirement-to-test projection. Route checks never rewrite topology."""
import copy
import json
import re
from pathlib import Path


def entry_requirements(model, graph):
    transitions = {t['id']: t for t in model['transitions']}
    derived = [n['id'] for n in graph['nodes']
               if transitions[next(r['transitionId'] for r in model['requirements'] if r['id'] == n['id'])]['from'] in model['entryStateIds']]
    declared = graph.get('reduction', {}).get('entryRequirementIds', derived)
    if len(declared) != len(set(declared)) or set(declared) != set(derived):
        raise ValueError('requirement entry declarations differ from real state entries')
    return declared


def project_graph(model, graph, cases):
    by_req = {c['requirementId']: c for c in cases if c['kind'] == 'primary'}
    nodes = []
    for source in graph['nodes']:
        c = by_req[source['id']]
        nodes.append({**copy.deepcopy(source), 'id': c['id'], 'requirementId': source['id'],
                      'transitionId': c['transitionId'], 'from': c['from'], 'to': c['to'],
                      'title': c['title'], 'kind': 'primary', 'status': c['result']['status']})
    edges = []
    pairs = set()
    for source in graph['edges']:
        pair = (source['from'], source['to'])
        if pair in pairs:
            raise ValueError('duplicate requirement continuation; resolve upstream instead of multiplying test arrows')
        pairs.add(pair)
        source_id = source.get('id', 'C:' + json.dumps(pair, ensure_ascii=False, separators=(',', ':')))
        edges.append({**copy.deepcopy(source), 'id': 'TC-' + source_id, 'sourceEdgeId': source_id,
                      'from': by_req[source['from']]['id'], 'to': by_req[source['to']]['id']})
    return {'nodes': nodes, 'edges': edges, 'entryStateIds': copy.deepcopy(model['entryStateIds']),
            'entryCaseIds': [by_req[r]['id'] for r in entry_requirements(model, graph)],
            'semantics': '原样映射输入需求图；一项需求对应一个测试节点，一条需求衔接对应一条测试边；使用次数仅作元数据，不重画边。'}


def inherit_routes(model, graph):
    source = graph.get('traversal', {})
    ts = {t['id']: t for t in model['transitions']}
    routes, covered = [], set()
    pairs = {(e['from'], e['to']) for e in graph['edges']}
    for i, r in enumerate(source.get('routes', []), 1):
        tids = r['transitionIds']
        if r['entryStateId'] not in model['entryStateIds'] or not tids:
            raise ValueError('invalid inherited route entry')
        state = r['entryStateId']
        steps = []
        for tid in tids:
            t = ts[tid]
            if t['from'] != state:
                raise ValueError('inherited route jumps between states')
            if steps and (ts[steps[-1]['transitionId']]['requirementId'], t['requirementId']) not in pairs:
                raise ValueError('inherited route uses an edge absent from requirement graph')
            steps.append({'transitionId': tid, 'caseId': 'TC-' + t['requirementId']})
            state = t['to']
            covered.add(tid)
        if r.get('requirementIds', [ts[t]['requirementId'] for t in tids]) != [ts[t]['requirementId'] for t in tids]:
            raise ValueError('inherited route requirement mapping differs')
        check = copy.deepcopy(r.get('contextCheck', {'status': 'not_modeled'}))
        routes.append({'id': 'source-route-' + str(i), 'entryStateId': r['entryStateId'], 'steps': steps,
                       'contextCheck': check, 'contextStatus': check['status'], 'fixtureStatus': 'pending',
                       'preparation': '沿用需求分析路线；实际数据、时钟和故障准备待明确。',
                       'sourceRouteIndex': i - 1})
    visits = sum(len(r['steps']) for r in routes)
    if 'totalVisits' in source and visits != source['totalVisits']:
        raise ValueError('upstream visit count differs from route occurrences')
    missing = sorted(set(ts) - covered)
    return {'mode': 'inherit_requirement_graph', 'routes': routes, 'complete': not missing,
            'uncoveredTransitionIds': missing,
            'uncoveredDetails': [{'transitionId': t, 'reason': '输入需求路线未包含此项；不补为新起点。'} for t in missing],
            'searchComplete': True, 'optimality': 'inherited_'+source.get('optimalityScope','structure_only'),
            'sourceOptimality': source.get('optimality',source.get('status', 'not_provided')),
            'objective': source.get('objective'), 'visits': visits, 'repeatedVisits': visits - len(covered),
            'lowerBoundVisits': source.get('lowerBoundVisits',len(ts)),
            'executable': bool(routes) and not missing and all(r['contextStatus'] in {'passed','finite_domain_passed','no_guard_constraints'} for r in routes)}


def read_review(path, model, graph):
    html = Path(path).read_text(encoding='utf-8')
    match = re.search(r'<script id="data" type="application/json">([\s\S]*?)</script>', html)
    if not match:
        raise ValueError('requirements review has no supported embedded data; explicit adapter required')
    data = json.loads(match.group(1))
    for key, expected in [('states', model['states']), ('transitions', model['transitions']),
                          ('requirements', model['requirements']),
                          ('requirementGraph', {k:graph[k] for k in ('nodes','edges','reduction','traversal','semantics') if k in graph}),
                          ('starts', model['entryStateIds']), ('requirementStarts', entry_requirements(model, graph))]:
        if data.get(key) != expected:
            raise ValueError('requirements HTML differs from declared input: ' + key)
    for key in ('semanticDigest','features'):
        if key in graph and data.get(key)!=graph[key]:
            raise ValueError('requirements HTML metadata differs: '+key)
    for key, ids in [('layout', {s['id'] for s in model['states']}),
                     ('requirementLayout', {n['id'] for n in graph['nodes']})]:
        positions = data.get(key, {}).get('positions', {})
        if set(positions) != ids:
            raise ValueError('requirements HTML layout is incomplete: ' + key)
    return html, data
