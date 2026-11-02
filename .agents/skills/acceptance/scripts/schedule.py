"""Minimize replay/setup/session counts without reordering the declared case route."""
from collections import deque
from functools import lru_cache
from execution import require, required_checks


def entry_prefix(model, state, index):
    cases = {c['id']: c for c in model['cases']}
    case = cases[model['coverage']['sequence'][index]]
    if case['kind'] != 'primary':
        return []
    initial = {s['id'] for s in state['states'] if s['isInitial']}
    goal = case['given']['stateId']
    queue = deque((s, []) for s in sorted(initial))
    seen = set(initial)
    while queue:
        current, path = queue.popleft()
        if current == goal:
            return path
        for c in model['cases']:
            if c['kind'] == 'primary' and c['given']['stateId'] == current:
                target = c['expected']['stateId']
                if target not in seen:
                    seen.add(target)
                    queue.append((target, path + [c['id']]))
    raise ValueError('No permitted entry path for visit ' + str(index))


def build_schedule(model, state, profiles, test_types):
    sequence = model['coverage']['sequence']
    cases = {c['id']: c for c in model['cases']}
    require(profiles and len({p['id'] for p in profiles}) == len(profiles), 'Unique preparation profiles required')
    contexts = {}
    eligible = {}
    for p in profiles:
        require(all(k in p for k in ('id', 'contextKey', 'command', 'cwd', 'environments', 'resources', 'setupUnits', 'eligibleVisits')),
                'Incomplete preparation profile')
        require(p['command'] and p['contextKey'] and p['setupUnits'], 'Preparation profile needs command/context/setup units')
        require(len(set(p['setupUnits'])) == len(p['setupUnits']), 'Duplicate setup unit')
        signature = (tuple(sorted(p['setupUnits'])), tuple(sorted(p['environments'])))
        require(p['contextKey'] not in contexts or contexts[p['contextKey']] == signature,
                'One context key must describe the same reusable prepared context')
        contexts[p['contextKey']] = signature
        indices = p['eligibleVisits']
        require(len(set(indices)) == len(indices) and all(isinstance(i, int) and 0 <= i < len(sequence) for i in indices),
                'Invalid eligible visit indices')
        eligible[p['id']] = set()
        for i in indices:
            needed = {d['environment'] for _, _, d in required_checks(cases[sequence[i]]) if d['testType'] in test_types}
            if needed <= set(p['environments']):
                eligible[p['id']].add(i)

    @lru_cache(None)
    def solve(index, previous_context):
        if index == len(sequence):
            return (0, 0, 0), []
        best = None
        for p in sorted(profiles, key=lambda item: item['id']):
            stop = index
            while stop < len(sequence) and stop in eligible[p['id']]:
                stop += 1
            for end in range(stop - 1, index - 1, -1):
                tail = solve(end + 1, p['contextKey'])
                if tail is None:
                    continue
                changed = previous_context != p['contextKey']
                prefix = entry_prefix(model, state, index) if changed else []
                cost = (len(prefix) + tail[0][0],
                        (len(p['setupUnits']) if changed else 0) + tail[0][1], 1 + tail[0][2])
                candidate = (cost, [(p, index, end, prefix)] + tail[1])
                if best is None or cost < best[0]:
                    best = candidate
        return best

    solved = solve(0, '')
    require(solved is not None, 'No preparation profile covers the required route and environments')
    cost, groups = solved
    sessions = [dict(id='session-' + str(n + 1).zfill(3), profileId=p['id'], **{'from': start, 'to': end},
                     command=p['command'], cwd=p['cwd'], environments=p['environments'], resources=p['resources'],
                     entryReplay=prefix) for n, (p, start, end, prefix) in enumerate(groups)]
    return dict(sessions=sessions, planning=dict(profiles=profiles,
                objective=dict(routeVisits=len(sequence), additionalEntryVisits=cost[0],
                               preparationCount=cost[1], sessionCount=cost[2]),
                method='fixed-route-lexicographic-dynamic-programming'))
