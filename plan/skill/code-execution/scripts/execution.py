#!/usr/bin/env python3
"""Check script evidence and project execution status into the existing planning views.
No application launch, browser control, or arbitrary shell execution is performed here.
"""
import argparse
import copy
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL.parent / 'task-planning' / 'scripts'))
from plan import (digest, load_json, raw_hash, schema_errors, safe_target,
                  check_source, derive_route, html_text, md_text, evaluate)
from atomic import evaluate as evaluate_atomic


def require(ok, message):
    if not ok:
        raise ValueError(message)


def stamp(value):
    dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
    require(dt.tzinfo is not None, 'Timestamp needs an explicit timezone')
    return dt


def relative(file, workspace):
    return file.resolve().relative_to(workspace.resolve()).as_posix()


def target(raw, workspace):
    return safe_target(workspace / '_anchor.json', raw, workspace)


def case_contract(model):
    value = copy.deepcopy(model)
    for case in value['cases']:
        case.pop('execution', None)
    return digest(value)


def plan_contract(plan):
    value = copy.deepcopy(plan)
    value['testCases'].pop('sha256', None)
    for task in value['tasks']:
        task.pop('status', None)
        for check in task['checks']:
            check.pop('status', None)
    return digest(value)


def required_checks(case):
    return [(aspect, i, check) for aspect in ('visual', 'functional')
            for i, check in enumerate(case['acceptance'][aspect]['checks'])]


def task_files(tid, tasks, plan_path, workspace, seen=None):
    seen = set() if seen is None else seen
    if tid in seen:
        return set()
    seen.add(tid)
    task = tasks[tid]
    files = {relative(safe_target(plan_path, f['path'], workspace), workspace)
             for f in task['files']}
    for dep in task['dependsOn']:
        files |= task_files(dep, tasks, plan_path, workspace, seen)
    return files


def conflict(a, b, tasks, records, plan_path, workspace):
    af = {relative(safe_target(plan_path, f['path'], workspace), workspace).casefold(): f['change']
          for f in tasks[a]['files']}
    bf = {relative(safe_target(plan_path, f['path'], workspace), workspace).casefold(): f['change']
          for f in tasks[b]['files']}
    return (any(af[f] != 'read' or bf[f] != 'read' for f in af.keys() & bf.keys())
            or bool(set(records[a]['resources']) & set(records[b]['resources'])))


def file_current(ref, workspace):
    file = target(ref['path'], workspace)
    return file.is_file() and raw_hash(file.read_bytes()) == ref['sha256']


def assertion_evidence(result, key, workspace, stale):
    evidence = result['evidence']
    require(any(e['form'] == 'assertion-report' for e in evidence), key + ': assertion report required')
    reports = []
    for e in evidence:
        file = target(e['path'], workspace)
        if not file_current(e, workspace):
            stale.append('Missing or changed evidence: ' + e['path'])
            continue
        if e['form'] == 'assertion-report':
            report = load_json(file)
            rows = report.get('assertions', [])
            require(isinstance(rows, list), key + ': invalid assertion report')
            reports.extend(r for r in rows if isinstance(r, dict) and r.get('target') == key)
    if stale:
        return
    require(reports, key + ': no matching assertion target')
    for row in reports:
        require('expected' in row and 'actual' in row and row.get('verdict') in ('passed', 'failed', 'blocked'),
                key + ': expected/actual/verdict required')
    verdicts = {r['verdict'] for r in reports}
    require((result['status'] == 'passed' and verdicts == {'passed'})
            or (result['status'] == 'failed' and 'failed' in verdicts)
            or (result['status'] == 'blocked' and 'blocked' in verdicts),
            key + ': conclusion disagrees with assertion report')


def aggregate(values, total, empty='not_run'):
    if 'stale' in values:
        return 'stale'
    if 'failed' in values:
        return 'failed'
    if 'blocked' in values:
        return 'blocked'
    if total and len(values) == total and all(v == 'passed' for v in values):
        return 'passed'
    return 'partial' if values else empty


def inspect(record, workspace):
    errors = schema_errors(record, load_json(SKILL / 'assets' / 'execution.schema.json'))
    require(not errors, '; '.join(str(x) for x in errors))
    case_path = target(record['testCasesPath'], workspace)
    plan_path = target(record['taskPlanPath'], workspace)
    model, plan = load_json(case_path), load_json(plan_path)
    for value, name in ((model, 'test-cases'), (plan, 'task-plan')):
        errors = schema_errors(value, load_json(SKILL.parent / 'task-planning' / 'assets' / (name + '.schema.json')))
        require(not errors, '; '.join(str(x) for x in errors))
    require(case_contract(model) == record['caseContract'], 'Test Case contract changed; return to task planning')
    require(plan_contract(plan) == record['planContract'], 'Task plan contract changed; return to task planning')
    require(safe_target(plan_path, plan['testCases']['path'], workspace) == case_path, 'Wrong Test Case binding')
    # The live digest may be stale only while sync recovers an interrupted projection.
    state_path = safe_target(case_path, model['stateGraph']['path'], workspace)
    atomic_path = safe_target(case_path, model['atomicGraph']['path'], workspace)
    state, atomic = load_json(state_path), load_json(atomic_path)
    require(digest(state) == model['stateGraph']['sha256'] and digest(atomic) == model['atomicGraph']['sha256'],
            'Upstream graph changed')
    require(evaluate_atomic(atomic, atomic_path, workspace)['status'] == 'passed', 'Upstream requirements failed')
    require(derive_route(model, state, atomic) == (model['edges'], model['coverage']), 'Acceptance route changed')
    for ref in model['inputs']:
        check_source(ref, case_path, workspace)
    planned_writes = {safe_target(plan_path, f['path'], workspace) for task in plan['tasks']
                      for f in task['files'] if f['change'] != 'read'}
    for profile in model['dataProfiles']:
        for field in profile['fields']:
            # Code cited to define a data boundary is an inspected baseline.
            # init checked it; the case contract pins that original reference.
            # Declared implementation changes are pinned by each actual run.
            if safe_target(case_path, field['source']['path'], workspace) not in planned_writes:
                check_source(field['source'], case_path, workspace)
    for p in plan['prerequisites']:
        # A code prerequisite describes the inspected implementation baseline.
        # init validated its source; the immutable plan contract preserves it.
        # Runtime readiness and the changed file version are evidenced per run.
        if safe_target(plan_path, p['source']['path'], workspace) not in planned_writes:
            check_source(p['source'], plan_path, workspace)
    tasks = {t['id']: t for t in plan['tasks']}
    cases = {c['id']: c for c in model['cases']}
    require(set(record['tasks']) == set(tasks), 'Execution task identities must match the plan')
    intervals = []
    for tid, status in record['tasks'].items():
        impl = status['implementation']
        if impl:
            start, end = stamp(impl['startedAt']), stamp(impl['completedAt'])
            require(start <= end, tid + ': implementation time order')
            intervals.append((tid, start, end))
    for i, (a, start, end) in enumerate(intervals):
        for b, other_start, other_end in intervals[i + 1:]:
            if start < other_end and other_start < end:
                require(not conflict(a, b, tasks, record['tasks'], plan_path, workspace),
                        'Concurrent implementation conflicts: ' + a + ', ' + b)
    sequence = model['coverage']['sequence']
    state_map = {s['id']: s for s in state['states']}
    case_results, task_results, visit_results, run_info = {}, {}, {}, {}
    run_ids = set()
    ordered = sorted(record['runs'], key=lambda r: (stamp(r['finishedAt']), r['id']))
    run_intervals = []
    hosts = {}
    for run in ordered:
        rid = run['id']
        require(rid not in run_ids, 'Duplicate run ' + rid)
        run_ids.add(rid)
        start, end, authored = stamp(run['startedAt']), stamp(run['finishedAt']), stamp(run['authoredAt'])
        require(authored <= start <= end, rid + ': script/run time order')
        require(len(set(run['taskIds'])) == len(run['taskIds']) and set(run['taskIds']) <= set(tasks), rid + ': unknown/duplicate task')
        for tid in run['taskIds']:
            impl = record['tasks'][tid]['implementation']
            require(impl is not None and stamp(impl['completedAt']) <= authored, rid + ': write acceptance assertions after implementation')
        require(target(run['cwd'], workspace).is_dir(), rid + ': working directory missing')
        stale = []
        for ref in [run['script'], run['context']] + run['files']:
            if not file_current(ref, workspace):
                stale.append('Missing or changed snapshot: ' + ref['path'])
        filenames = [ref['path'].casefold() for ref in run['files']]
        require(len(set(filenames)) == len(filenames), rid + ': duplicate snapshot file')
        expected_files = set().union(*(task_files(t, tasks, plan_path, workspace) for t in run['taskIds']))
        require(expected_files <= {ref['path'] for ref in run['files']}, rid + ': missing planned code snapshot')
        context = None if not file_current(run['context'], workspace) else load_json(target(run['context']['path'], workspace))
        if context is not None:
            require(isinstance(context, dict) and context.get('environment') == run['environment']
                    and all(k in context for k in ('build', 'inputs', 'mocks', 'readyPrerequisites')),
                    rid + ': context needs environment/build/inputs/mocks/readyPrerequisites')
        if run['environment'] == 'native' and context is not None:
            require(isinstance(context.get('host'),str) and context['host'].strip(), rid + ': native context needs the actual host identity')
        hosts[rid] = context.get('host') if context is not None else None
        results = run['taskResults']
        visits = run['visits']
        require(results or visits, rid + ': empty run')
        prior_index = None
        failed_visit = False
        seen_checks, seen_tasks = set(), set()
        for visit in visits:
            index = visit['visitIndex']
            require(index < len(sequence), rid + ': visit outside route')
            require(not failed_visit, rid + ': visits continue after failed/blocked predecessor')
            require(prior_index is None or index == prior_index + 1, rid + ': visits must be a continuous route slice')
            case = cases[sequence[index]]
            if prior_index is None:
                require(case['kind'] != 'primary' or state_map[case['given']['stateId']]['isInitial'],
                        rid + ': run must start at a permitted entry; include the replay prefix')
            elif cases[sequence[prior_index]]['expected']['stateId'] != case['given']['stateId']:
                require(case['kind'] != 'primary' or state_map[case['given']['stateId']]['isInitial'], rid + ': illegal route restart')
            responsible = {t['id'] for t in tasks.values() if case['id'] in t['testCaseIds']}
            require(responsible <= set(run['taskIds']), rid + ': full case needs all responsible implementations in run scope')
            if context is not None:
                missing = {p['id'] for p in plan['prerequisites'] if p['status'] == 'missing' and case['id'] in p['affects']}
                require(missing <= set(context['readyPrerequisites']) or visit['outcome'] == 'blocked', rid + ': unresolved case prerequisite')
            by_check = {}
            for result in visit['checks']:
                aspect, ci = result['aspect'], result['checkIndex']
                defs = case['acceptance'][aspect]['checks']
                require(ci < len(defs) and defs[ci]['testType'] == 'script', rid + ': unknown or browser check result')
                require(defs[ci]['environment'] == run['environment'], rid + ': check environment mismatch')
                key = (index, aspect, ci)
                require(key not in seen_checks, rid + ': duplicate visit/check result')
                seen_checks.add(key)
                needed = {e['form'] for e in defs[ci]['evidence']}
                require(needed <= {e['form'] for e in result['evidence']}, rid + ': missing required evidence form')
                assertion_evidence(result, 'case:' + case['id'] + ':' + aspect + ':' + str(ci) + ':' + str(index), workspace, stale)
                by_check[(aspect, ci)] = result
            if visit['outcome'] == 'passed':
                require(by_check and all(r['status'] == 'passed' for r in by_check.values()), rid + ': passed visit has no passing checks')
            if visit['outcome'] == 'failed':
                require(run['exitCode'] != 0 or any(r['status']=='failed' for r in by_check.values()), rid + ': failed visit needs a failing check report')
            if visit['outcome'] == 'blocked':
                require(any(r['status']=='blocked' for r in by_check.values()), rid + ': blocked visit needs a blocked check report')
            if visit['outcome'] == 'deferred':
                require(not by_check, rid + ': deferred visit must not claim completed checks')
            if visit['outcome'] in ('failed', 'blocked'):
                failed_visit = True
            visit_results[index] = (run, visit, stale)
            for (aspect, ci), result in by_check.items():
                case_results[(index, aspect, ci)] = (run, result, stale)
            prior_index = index
        for result in results:
            tid, ci = result['taskId'], result['checkIndex']
            require(tid in run['taskIds'] and ci < len(tasks[tid]['checks']), rid + ': unknown task check')
            require((tid, ci) not in seen_tasks, rid + ': duplicate task check')
            seen_tasks.add((tid, ci))
            require(len(set(result['doneIndices'])) == len(result['doneIndices'])
                    and set(result['doneIndices']) <= set(range(len(tasks[tid]['done']))), rid + ': unknown/duplicate task done criterion')
            for dep in tasks[tid]['checks'][ci]['requires']:
                require(record['tasks'][dep]['implementation'] is not None
                        and stamp(record['tasks'][dep]['implementation']['completedAt']) <= start, rid + ': check prerequisite not implemented')
            assertion_evidence(result, 'task:' + tid + ':' + str(ci), workspace, stale)
            task_results[(tid, ci)] = (run, result, stale)
        for previous, ps, pe in run_intervals:
            if start < pe and ps < end:
                overlap = set(run['taskIds']) & set(previous['taskIds'])
                same_host = (run['environment'] == previous['environment'] == 'native'
                             and (not hosts[rid] or not hosts[previous['id']] or hosts[rid] == hosts[previous['id']]))
                conflicts = any(conflict(a, b, tasks, record['tasks'], plan_path, workspace)
                                for a in run['taskIds'] for b in previous['taskIds'])
                require(not (overlap or same_host or conflicts), 'Concurrent run resource conflict: ' + previous['id'] + ', ' + rid)
        run_intervals.append((run, start, end))
        run_info[rid] = stale
    # Dependency completion is evaluated at the time implementation began. Later
    # source changes invalidate current status, not the historical action order.
    for tid, status in record['tasks'].items():
        impl = status['implementation']
        if not impl:
            continue
        for dep in tasks[tid]['dependsOn']:
            earlier = [r for r in ordered if stamp(r['finishedAt']) <= stamp(impl['startedAt'])]
            latest = {}
            covered = set()
            for r in earlier:
                for result in r['taskResults']:
                    if result['taskId'] == dep:
                        latest[result['checkIndex']] = (r, result)
            for r, result in latest.values():
                if r['exitCode'] == 0 and result['status'] == 'passed':
                    covered.update(result['doneIndices'])
            require(len(latest) == len(tasks[dep]['checks'])
                    and all(r['exitCode'] == 0 and v['status'] == 'passed' for r, v in latest.values())
                    and covered == set(range(len(tasks[dep]['done']))), tid + ': dependency was not script-accepted before implementation: ' + dep)
    return project(record, workspace, case_path, plan_path, model, plan, state, atomic,
                   case_results, task_results, visit_results, run_info)


def project(record, workspace, case_path, plan_path, model, plan, state, atomic,
            case_results, task_results, visit_results, run_info):
    statuses = {}
    for task in plan['tasks']:
        tid = task['id']
        values, covered = [], set()
        for i, check in enumerate(task['checks']):
            item = task_results.get((tid, i))
            status = 'not_run'
            if item:
                run, result, stale = item
                status = 'stale' if stale else 'failed' if run['exitCode'] != 0 else result['status']
                if status == 'passed':
                    covered.update(result['doneIndices'])
                values.append(status)
            check['status'] = status
        default = 'implemented' if record['tasks'][tid]['implementation'] else 'planned'
        task['status'] = aggregate(values, len(task['checks']), default)
        if task['status'] == 'passed' and covered != set(range(len(task['done']))):
            task['status'] = 'partial'
        statuses[tid] = task['status']
    summaries = {'not_run':'尚未执行。','passed':'全部检查与路线访问已通过。','partial':'部分检查或访问已完成，仍有待验收项。',
                 'failed':'实际验收未通过，请查看失败证据。','blocked':'执行前提尚不具备。','stale':'实际文件已变化，旧证据不能用于通过判断。'}
    sequence = model['coverage']['sequence']
    for case in model['cases']:
        values, checks, evidence = [], [], []
        indices = [i for i, cid in enumerate(sequence) if cid == case['id']]
        defs = required_checks(case)
        total = len(indices) * len(defs)
        for index in indices:
            visit_info = visit_results.get(index)
            for aspect, ci, definition in defs:
                item = case_results.get((index, aspect, ci))
                if not item:
                    continue
                run, result, stale = item
                vr, visit, vs = visit_info
                status = 'stale' if stale or vs else 'failed' if run['exitCode'] != 0 else result['status']
                row = dict(runId=run['id'], visitIndex=index, aspect=aspect, checkIndex=ci,
                           status=status, actual=result['actual'], evidence=copy.deepcopy(result['evidence']))
                for ref in row['evidence']:
                    ref['path'] = os.path.relpath(target(ref['path'], workspace), case_path.parent).replace(os.sep, '/')
                    evidence.append(dict(runId=run['id'], **ref))
                checks.append(row)
                values.append(status)
            if visit_info:
                run, visit, stale = visit_info
                if stale or run['exitCode'] != 0 or visit['outcome'] in ('failed', 'blocked'):
                    values.append('stale' if stale else 'failed' if run['exitCode'] != 0 or visit['outcome'] == 'failed' else 'blocked')
        status = aggregate(values, total)
        case['execution'] = {'status':status, 'actual':None if status == 'not_run' else summaries[status], 'evidence':evidence}
        if checks:
            case['execution']['checks'] = checks
    plan['testCases']['sha256'] = digest(model)
    return {'model':model, 'plan':plan, 'state':state, 'atomic':atomic, 'casePath':case_path,
            'planPath':plan_path, 'taskStatuses':statuses, 'staleRuns':{r:v for r,v in run_info.items() if v}}


def ready(data, record, workspace):
    tasks = {t['id']:t for t in data['plan']['tasks']}
    ready_ids = [tid for tid,t in tasks.items() if data['taskStatuses'][tid] != 'passed'
                 and all(data['taskStatuses'][dep] == 'passed' for dep in t['dependsOn'])]
    batches = []
    for tid in ready_ids:
        for batch in batches:
            if not any(conflict(tid, other, tasks, record['tasks'], data['planPath'], workspace) for other in batch):
                batch.append(tid)
                break
        else:
            batches.append([tid])
    return batches


def views(data):
    return [(data['casePath'], json.dumps(data['model'], ensure_ascii=False, indent=2)+'\n'),
            (data['planPath'], json.dumps(data['plan'], ensure_ascii=False, indent=2)+'\n'),
            (data['casePath'].with_suffix('.html'), html_text(data['model'], data['state'], data['plan'], data['atomic'])),
            (data['planPath'].with_suffix('.md'), md_text(data['plan'], data['model']))]


def write_views(data):
    for file, content in views(data):
        temp = file.with_suffix(file.suffix + '.execution.tmp')
        temp.write_text(content, encoding='utf-8')
        os.replace(temp, file)


def check_views(data):
    for file, content in views(data):
        require(file.is_file() and file.read_text(encoding='utf-8') == content,
                'Stale execution projection: ' + file.name + '; run sync')


def pending_file(record_path, run_id):
    name = run_id if re.fullmatch(r'[A-Za-z0-9_.-]{1,160}', run_id) else raw_hash(run_id.encode('utf-8'))
    return record_path.with_name(record_path.stem + '.batch.' + name + '.pending.json')


def check_pending(record_path):
    pending = sorted(record_path.parent.glob(record_path.stem + '.batch.*.pending.json'))
    require(not pending, 'Unclosed acceptance batch: ' + ', '.join(p.name for p in pending))


def submit(record_path, workspace, run_path, local_only=False):
    """Record one real run and close its batch under the projection writer lock."""
    run = load_json(run_path)
    require(isinstance(run, dict), 'Batch input must be one execution run')
    if local_only:
        require(not run.get('visits'), 'Local-only batch cannot substitute for case visits')
        require(run.get('taskResults'), 'Local-only batch needs task acceptance results')
    else:
        require(any(v.get('checks') for v in run.get('visits', [])),
                'Case batch needs per-visit Test Case results; taskResults alone are insufficient')
    lock = record_path.with_suffix('.lock')
    with lock.open('x', encoding='utf-8') as stream:
        stream.write(str(os.getpid()))
    try:
        record = load_json(record_path)
        previous = next((r for r in record['runs'] if r['id'] == run['id']), None)
        require(previous is None or previous == run, 'Run identity already has different immutable evidence')
        if previous is None:
            record['runs'].append(run)
        # Rejected candidates never replace the canonical ledger or its views.
        data = inspect(record, workspace)
        temp = record_path.with_suffix('.json.execution.tmp')
        temp.write_text(json.dumps(record, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        os.replace(temp, record_path)
        write_views(data)
        # Reinspect the saved ledger against the actual files before closing.
        data = inspect(load_json(record_path), workspace)
        check_views(data)
        pending_file(record_path, run['id']).unlink(missing_ok=True)
        results = run['taskResults'] + [r for v in run['visits'] for r in v['checks']]
        accepted = (run['exitCode'] == 0 and run['id'] not in data['staleRuns']
                    and all(r['status'] == 'passed' for r in results)
                    and all(v['outcome'] not in ('failed', 'blocked') for v in run['visits']))
        counts = {}
        for case in data['model']['cases']:
            status = case['execution']['status']
            counts[status] = counts.get(status, 0) + 1
        return {'status':'passed' if accepted else 'failed', 'scope':'local-batch' if local_only else 'case-batch',
                'recorded':True, 'synced':True, 'checked':True, 'runId':run['id'],
                'caseCounts':counts, 'tasks':data['taskStatuses']}
    finally:
        lock.unlink(missing_ok=True)


def execute(command, record_path, workspace, cases=None, plan=None, run=None, local_only=False):
    workspace = workspace.resolve()
    record_path = record_path.resolve()
    record_path.relative_to(workspace)
    if command == 'init':
        require(not record_path.exists(), 'Execution record already exists; resume it')
        case_path, plan_path = target(cases, workspace), target(plan, workspace)
        require(plan_path == case_path.parent/'task-plan.json', 'Planning inputs must share their canonical directory')
        model, task_plan = load_json(case_path), load_json(plan_path)
        report = evaluate(model, case_path, workspace, with_views=True)
        require(report['status'] == 'passed', 'Planning gates failed: ' + json.dumps(report, ensure_ascii=False))
        record = {'schemaVersion':'1.0.0','testCasesPath':relative(case_path, workspace),
                  'taskPlanPath':relative(plan_path, workspace),'caseContract':case_contract(model),
                  'planContract':plan_contract(task_plan),
                  'tasks':{t['id']:{'implementation':None,'resources':['unreviewed-resources']} for t in task_plan['tasks']}, 'runs':[]}
        record_path.parent.mkdir(parents=True, exist_ok=True)
        with record_path.open('x', encoding='utf-8') as stream:
            stream.write(json.dumps(record, ensure_ascii=False, indent=2)+'\n')
        return {'status':'passed', 'scope':'execution-initialization', 'tasks':len(record['tasks'])}
    if command == 'submit':
        require(run is not None, 'submit requires --run with an actual execution run')
        return submit(record_path, workspace, target(run, workspace), local_only)
    if command in ('ready', 'finish'):
        check_pending(record_path)
    record = load_json(record_path)
    data = inspect(record, workspace)
    if command == 'sync':
        lock = record_path.with_suffix('.lock')
        # A leftover lock is an interruption signal. Confirm no writer is active
        # before removing it; never silently steal another writer's lock.
        with lock.open('x', encoding='utf-8') as stream:
            stream.write(str(os.getpid()))
        try:
            # Inspect under lock as well; the projection must correspond to
            # the exact ledger and current files visible to this writer.
            data = inspect(load_json(record_path), workspace)
            write_views(data)
        finally:
            lock.unlink(missing_ok=True)
    else:
        check_views(data)
    if command == 'ready':
        return {'status':'passed', 'scope':'dependency-and-resource-readiness', 'batches':ready(data, record, workspace),
                'tasks':data['taskStatuses']}
    pending_browser = [c['id'] for c in data['model']['cases'] if any(d['testType']=='browser' for a,i,d in required_checks(c))]
    if command == 'finish':
        require(all(v == 'passed' for v in data['taskStatuses'].values()), 'Some tasks lack passing script acceptance')
        for i,cid in enumerate(data['model']['coverage']['sequence']):
            case = next(c for c in data['model']['cases'] if c['id']==cid)
            for aspect, ci, definition in required_checks(case):
                if definition['testType'] != 'script':
                    continue
                require(any(r['visitIndex']==i and r['aspect']==aspect and r['checkIndex']==ci and r['status']=='passed'
                            for r in case['execution'].get('checks',[])), 'Unaccepted script check: '+cid+' / visit '+str(i))
        for case in data['model']['cases']:
            allowed = ('passed', 'partial', 'not_run') if case['id'] in pending_browser else ('passed',)
            require(case['execution']['status'] in allowed, 'Unaccepted Test Case status: '+case['id'])
    return {'status':'passed', 'scope':'script-execution-artifacts', 'tasks':data['taskStatuses'],
            'cases':{c['id']:c['execution']['status'] for c in data['model']['cases']},
            'staleRuns':data['staleRuns'], 'browserPending':pending_browser}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('init','ready','submit','sync','check','finish'))
    parser.add_argument('record', type=Path)
    parser.add_argument('--workspace', type=Path, required=True)
    parser.add_argument('--cases')
    parser.add_argument('--plan')
    parser.add_argument('--run', help='Workspace-relative JSON containing one actual execution run')
    parser.add_argument('--local-only', action='store_true', help='Explicitly record only local task acceptance')
    args = parser.parse_args()
    try:
        result = execute(args.command, args.record, args.workspace, args.cases, args.plan, args.run, args.local_only)
    except (OSError, ValueError, KeyError, TypeError, IndexError) as exc:
        result = {'status':'failed','error':str(exc)}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result['status']=='passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
