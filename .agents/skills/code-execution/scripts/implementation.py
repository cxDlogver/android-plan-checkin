#!/usr/bin/env python3
"""Validate implementation/static-check handoff; never run or accept Test Cases."""
import argparse
import copy
import json
import sys
from datetime import datetime
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL.parent / 'task-planning' / 'scripts'))
from plan import digest, load_json, raw_hash, safe_target, schema_errors


def require(ok, message):
    if not ok:
        raise ValueError(message)


def stamp(value):
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    require(result.tzinfo is not None, 'Timestamp needs an explicit timezone')
    return result


def contract(plan):
    value = copy.deepcopy(plan)
    value['testCases'].pop('sha256', None)
    for task in value['tasks']:
        task.pop('status', None)
        for check in task['checks']:
            check.pop('status', None)
    return digest(value)


def target(raw, workspace):
    return safe_target(workspace / '_anchor.json', raw, workspace)


def current(ref, workspace):
    file = target(ref['path'], workspace)
    return file.is_file() and raw_hash(file.read_bytes()) == ref['sha256']


def declared_files(tid, tasks, plan_path, workspace, seen=None):
    seen = set() if seen is None else seen
    if tid in seen:
        return set()
    seen.add(tid)
    task = tasks[tid]
    result = {safe_target(plan_path, f['path'], workspace).relative_to(workspace).as_posix()
              for f in task['files']}
    for dep in task['dependsOn']:
        result |= declared_files(dep, tasks, plan_path, workspace, seen)
    return result


def inspect(record, workspace):
    workspace = workspace.resolve()
    errors = schema_errors(record, load_json(SKILL / 'assets/implementation.schema.json'))
    require(not errors, '; '.join(map(str, errors)))
    plan_path = target(record['taskPlanPath'], workspace)
    plan = load_json(plan_path)
    errors = schema_errors(plan, load_json(SKILL.parent / 'task-planning/assets/task-plan.schema.json'))
    require(not errors, '; '.join(map(str, errors)))
    require(contract(plan) == record['planContract'], 'Task plan contract changed')
    tasks = {t['id']: t for t in plan['tasks']}
    require(set(tasks) == set(record['tasks']), 'Implementation task identities differ')
    visited, visiting, order = set(), set(), []
    def visit(tid):
        require(tid in tasks, 'Unknown implementation dependency: ' + tid)
        require(tid not in visiting, 'Implementation dependency cycle')
        if tid in visited:
            return
        visiting.add(tid)
        for dep in tasks[tid]['dependsOn']:
            visit(dep)
        visiting.remove(tid)
        visited.add(tid)
        order.append(tid)
    for tid in tasks:
        visit(tid)
    statuses = {}
    for tid, entry in record['tasks'].items():
        impl = entry['implementation']
        if impl is None:
            require(not entry['done'] and not entry['checks'], tid + ': results precede implementation')
            statuses[tid] = 'planned'
            continue
        start, end = stamp(impl['startedAt']), stamp(impl['completedAt'])
        require(start <= end, tid + ': implementation time order')
        require('unreviewed-resources' not in entry['resources'], tid + ': implementation resources not reviewed')
        indices = [d['index'] for d in entry['done']]
        require(len(indices) == len(set(indices)) and set(indices) <= set(range(len(tasks[tid]['done']))),
                tid + ': unknown/duplicate done index')
        refs = entry['files'] + [r for d in entry['done'] for r in d['sources']]
        require(len({r['path'] for r in entry['files']}) == len(entry['files']), tid + ': duplicate file')
        expected = declared_files(tid, tasks, plan_path, workspace)
        complete = (set(indices) == set(range(len(tasks[tid]['done'])))
                    and expected <= {r['path'] for r in entry['files']} and bool(entry['checks']))
        latest = {}
        for check in entry['checks']:
            a, b = stamp(check['startedAt']), stamp(check['finishedAt'])
            require(a <= b, tid + ': static check time order')
            require(target(check['cwd'], workspace).is_dir(), tid + ': check cwd missing')
            require(expected <= {r['path'] for r in check['files']}, tid + ': static snapshot lacks planned code')
            key = (check['kind'], tuple(check['command']), check['cwd'])
            if key not in latest or stamp(latest[key]['finishedAt']) <= b:
                latest[key] = check
        complete = complete and all(stamp(c['startedAt']) >= end for c in latest.values())
        for check in latest.values():
            refs += check['files'] + [check['log']]
        stale = any(not current(ref, workspace) for ref in refs)
        failed = any(check['exitCode'] != 0 for check in latest.values())
        statuses[tid] = ('stale' if stale else 'failed' if failed else
                         'implemented' if complete else 'partial')
        for dep in tasks[tid]['dependsOn']:
            previous = record['tasks'][dep]
            require(previous['implementation'] is not None, tid + ': dependency not implemented: ' + dep)
            require(stamp(previous['implementation']['completedAt']) <= start,
                    tid + ': dependency implementation was not complete: ' + dep)
            prior = [c for c in previous['checks'] if stamp(c['finishedAt']) <= start]
            require(prior and all(c['exitCode'] == 0 for c in _latest(prior)),
                    tid + ': dependency static checks were not complete: ' + dep)
    intervals = [(tid, stamp(e['implementation']['startedAt']), stamp(e['implementation']['completedAt']))
                 for tid, e in record['tasks'].items() if e['implementation']]
    for i, (a, start, end) in enumerate(intervals):
        for b, other_start, other_end in intervals[i + 1:]:
            if start < other_end and other_start < end:
                af = {str(safe_target(plan_path, f['path'], workspace)).casefold(): f['change'] for f in tasks[a]['files']}
                bf = {str(safe_target(plan_path, f['path'], workspace)).casefold(): f['change'] for f in tasks[b]['files']}
                conflict = (any(af[f] != 'read' or bf[f] != 'read' for f in af.keys() & bf.keys()) or
                            bool(set(record['tasks'][a]['resources']) & set(record['tasks'][b]['resources'])))
                require(not conflict, 'Concurrent implementation conflict: ' + a + ', ' + b)
    # Dependency freshness propagates in topological order.
    for tid in order:
        if statuses[tid] == 'implemented' and any(statuses[d] != 'implemented' for d in tasks[tid]['dependsOn']):
            statuses[tid] = 'stale'
    return {'plan': plan, 'planPath': plan_path, 'statuses': statuses, 'record': record}


def _latest(checks):
    rows = {}
    for c in sorted(checks, key=lambda v: stamp(v['finishedAt'])):
        rows[(c['kind'], tuple(c['command']), c['cwd'])] = c
    return rows.values()


def execute(command, path, workspace, plan=None):
    workspace, path = workspace.resolve(), path.resolve()
    path.relative_to(workspace)
    if command == 'init':
        require(not path.exists(), 'Existing implementation record must be resumed')
        source = target(plan, workspace)
        value = load_json(source)
        data = {'schemaVersion': '1.0.0', 'taskPlanPath': source.relative_to(workspace).as_posix(),
                'planContract': contract(value), 'tasks': {t['id']: {
                    'implementation': None, 'resources': ['unreviewed-resources'],
                    'done': [], 'files': [], 'checks': []} for t in value['tasks']}}
        inspect(data, workspace)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('x', encoding='utf-8') as out:
            out.write(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
        return {'status': 'initialized', 'scope': 'code-implementation'}
    data = inspect(load_json(path), workspace)
    statuses = data['statuses']
    if command == 'finish':
        require(all(s == 'implemented' for s in statuses.values()), 'Implementation/static checks incomplete: ' + str(statuses))
        return {'status': 'passed', 'scope': 'code-implementation', 'tasks': statuses}
    if command == 'ready':
        tasks = {t['id']: t for t in data['plan']['tasks']}
        ready = [tid for tid, t in tasks.items() if statuses[tid] != 'implemented'
                 and all(statuses[dep] == 'implemented' for dep in t['dependsOn'])
                 and 'unreviewed-resources' not in data['record']['tasks'][tid]['resources']]
        # Return candidates; grouping must still respect actual command/cache writes.
        return {'status': 'ready', 'scope': 'code-implementation', 'tasks': statuses, 'readyTasks': ready}
    return {'status': 'consistent', 'scope': 'implementation-record', 'tasks': statuses}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('command', choices=['init', 'ready', 'check', 'finish'])
    p.add_argument('record', type=Path)
    p.add_argument('--workspace', type=Path, required=True)
    p.add_argument('--plan')
    args = p.parse_args()
    try:
        result = execute(args.command, args.record, args.workspace, args.plan)
    except (OSError, ValueError, KeyError, TypeError) as error:
        result = {'status': 'failed', 'error': str(error)}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return int(result['status'] == 'failed')


if __name__ == '__main__':
    sys.exit(main())
