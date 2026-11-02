#!/usr/bin/env python3
"""Serialize acceptance visits and synchronize their status before granting the next visit."""
import argparse
import copy
import json
import os
import sys
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from execution import (case_contract, plan_contract, inspect as inspect_inputs, required_checks,
                       assertion_evidence, file_current, target, stamp, require,
                       load_json, schema_errors, digest, html_text, md_text, check_source)

SKILL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL.parent / 'code-execution/scripts'))
from implementation import inspect as inspect_implementation
from schedule import build_schedule, entry_prefix
import case_contracts
import artifact_copies
import harness_archives
from input_snapshot import InputSnapshot


def now():
    return datetime.now(timezone.utc).isoformat()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    os.replace(temp, path)


@contextmanager
def lock(path):
    file = path.with_suffix('.lock')
    with file.open('x', encoding='utf-8') as out:
        out.write(str(os.getpid()))
    try:
        yield
    finally:
        file.unlink(missing_ok=True)


def inputs(record, workspace):
    if 'planningSource' in record:
        artifact_copies.validate(record, workspace)
    model = load_json(target(record['testCasesPath'], workspace))
    plan = load_json(target(record['taskPlanPath'], workspace))
    require(case_contract(model) == record['caseContract'], 'Test Case contract changed')
    require(plan_contract(plan) == record['planContract'], 'Task plan contract changed')
    # Reuse input/source/optimal-route validation without adopting mixed task/test results.
    probe = {'schemaVersion': '1.0.0', 'testCasesPath': record['testCasesPath'],
             'taskPlanPath': record['taskPlanPath'], 'caseContract': record['caseContract'],
             'planContract': record['planContract'], 'tasks': {
                 t['id']: {'implementation': None, 'resources': []} for t in plan['tasks']}, 'runs': []}
    data = inspect_inputs(probe, workspace)
    data['plan'] = plan  # Acceptance does not rewrite implementation task/check states.
    return data


def scope_checks(case, record):
    return [(a, i, d) for a, i, d in required_checks(case) if d['testType'] in record['testTypes']]


def session_for(record, index):
    return next(s for s in record['sessions'] if s['from'] <= index <= s['to'])


def _inspect(record, workspace):
    errors = schema_errors(record, load_json(SKILL / 'assets/acceptance.schema.json'))
    require(not errors, '; '.join(map(str, errors)))
    data = inputs(record, workspace)
    require(record['testTypes'] in (['script'], ['script', 'browser']), 'Select script scope or complete acceptance scope')
    implementation = inspect_implementation(load_json(target(record['implementationPath'], workspace)), workspace)
    source = artifact_copies.validate(record, workspace)
    source_plan = artifact_copies.relocate(data['plan'], data['planPath'], target(source['taskPlanPath'], workspace), workspace)
    source_plan['testCases']['path'] = os.path.relpath(target(source['testCasesPath'], workspace), target(source['taskPlanPath'], workspace).parent).replace(os.sep, '/')
    require(implementation['record']['planContract'] == plan_contract(source_plan), 'Wrong implementation handoff')
    implementation_ready = all(s == 'implemented' for s in implementation['statuses'].values())
    sequence = data['model']['coverage']['sequence']
    require(sequence == record['sequence'], 'Logical acceptance route changed; return to task planning')
    require(record['upstream'] == {k: data['model'][k] for k in ('stateGraph', 'atomicGraph')},
            'Requirement facts changed; return to requirement analysis')
    scheduled = [i for s in record['sessions'] for i in range(s['from'], s['to'] + 1)]
    require(scheduled == list(range(len(sequence))), 'Sessions must partition the unchanged route in order')
    require(len({s['id'] for s in record['sessions']}) == len(record['sessions']), 'Duplicate session ID')
    schedule = dict(sessions=record['sessions'], planning=record['planning'])
    require(digest(schedule) == record['scheduleContract'], 'Acceptance execution schedule changed')
    require(build_schedule(data['model'], data['state'], record['planning']['profiles'], record['testTypes']) == schedule,
            'Execution grouping does not achieve the declared minimum entry/setup/session cost')
    cases = {c['id']: c for c in data['model']['cases']}
    require(record['currentDefinitions'] == {c['id']: case_contracts.definition_hash(c, data['model']) for c in cases.values()},
            'Test Case definition changed outside the repair workflow')
    require(all(digest(value) == key for key, value in record['definitions'].items()), 'Frozen definition content/hash mismatch')
    harness_archives.validate(record, workspace)
    latest, details, ids = {}, {}, set()
    for attempt in record['attempts']:
        run = attempt['run']
        rid = run['id']
        require(rid not in ids, 'Duplicate attempt identity')
        ids.add(rid)
        require(len(run['visits']) == 1 and not run['taskResults'], 'Submit exactly one visit, not a batch')
        visit = run['visits'][0]
        index = visit['visitIndex']
        require(0 <= index < len(sequence), 'Visit outside route')
        session = session_for(record, index)
        require(run['command'] == session['command'] and run['cwd'] == session['cwd'], 'Unplanned driver command')
        require(stamp(run['authoredAt']) <= stamp(run['startedAt']) <= stamp(run['finishedAt']), 'Attempt time order')
        require(stamp(attempt['authorizedAt']) <= stamp(run['startedAt']), 'Action began before begin authorization')
        if attempt['closedAt']:
            require(stamp(run['finishedAt']) <= stamp(attempt['closedAt']), 'Closure predates observation')
        stale = []
        for ref in [run['script'], run['context']] + run['files']:
            if not harness_archives.current(ref, attempt, record, workspace):
                stale.append(ref['path'])
        context = None if not file_current(run['context'], workspace) else load_json(target(run['context']['path'], workspace))
        require(context is not None or stale, 'Missing context')
        if context is not None:
            require(all(k in context for k in ('build', 'inputs', 'mocks', 'environments', 'entry')),
                    'Context needs build/inputs/mocks/environments/entry')
            native = [e for e in context['environments'] if e['environment'] in ('native', 'browser')]
            require(all(isinstance(e.get('host'), str) and e['host'].strip() for e in native), 'Actual host identity missing')
            used_environments = {e['environment'] for e in context['environments']}
            require(used_environments, 'Actual execution environment missing')
            require(used_environments <= set(session['environments']), 'Unplanned acceptance environment')
            require(run['environment'] == ('mixed' if len(used_environments) > 1 else next(iter(used_environments))),
                    'Attempt environment differs from actual context')
            entry = context['entry']
            case = cases[sequence[index]]
            if entry['kind'] == 'handoff':
                require(index > 0 and entry['previousAttemptId'] == attempt['predecessorAttemptId'], 'Wrong predecessor')
                require(entry['previousAttemptId'] in ids, 'Unobserved predecessor')
                previous_case = cases[sequence[index - 1]]
                require(case['kind'] == previous_case['kind'] == 'primary', 'Independent cases need their isolated entry')
                require(previous_case['expected']['stateId'] == case['given']['stateId'], 'Handoff state differs from current given; use permitted entry')
            elif entry['kind'] == 'initial':
                require(case['kind'] != 'primary' or any(s['id'] == case['given']['stateId'] and s['isInitial'] for s in data['state']['states']),
                        'Cannot reset to a noninitial state')
            elif entry['kind'] == 'replay':
                state = entry['initialStateId']
                require(any(s['id'] == state and s['isInitial'] for s in data['state']['states']), 'Replay needs a permitted entry')
                require(entry['steps'], 'Replay prefix missing')
                for step in entry['steps']:
                    c = cases[step['caseId']]
                    require(c['kind'] == 'primary' and c['given']['stateId'] == state, 'Illegal replay handoff')
                    require(step['operationObserved'].strip() and step['evidence'], 'Replay actual/evidence missing')
                    for ref in step['evidence']:
                        if not file_current(ref, workspace):
                            stale.append(ref['path'])
                    state = c['expected']['stateId']
                require(state == case['given']['stateId'], 'Replay did not reach current given')
                require(len(entry['steps']) == len(entry_prefix(data['model'], data['state'], index)),
                        'Replay must use a shortest necessary entry prefix')
            else:
                require(False, 'Unknown entry kind')
            if index == session['from'] and session['entryReplay']:
                require(entry['kind'] == 'replay', 'The planned context change requires its entry replay')
        current_case = cases[sequence[index]]
        require(attempt['definitionHash'] in record['definitions'], 'Frozen Test Case definition missing')
        case = record['definitions'][attempt['definitionHash']]
        require(case['id'] == current_case['id'], 'Attempt is bound to another Test Case')
        if attempt['definitionHash'] != record['currentDefinitions'][case['id']]:
            stale.append('Test Case definition changed after reviewed repair')
        if context is not None:
            missing = {p['id'] for p in data['plan']['prerequisites'] if p['status'] == 'missing' and case['id'] in p['affects']}
            ready = {p['id']: p for p in context.get('readyPrerequisites', [])}
            require(missing <= set(ready) or visit['outcome'] == 'blocked', 'Unresolved acceptance prerequisite')
            for p in ready.values():
                require(p['observation'].strip() and p['evidence'], 'Prerequisite observation/evidence missing')
                for ref in p['evidence']:
                    if not file_current(ref, workspace):
                        stale.append(ref['path'])
        responsible = {t['id'] for t in data['plan']['tasks'] if case['id'] in t['testCaseIds']}
        require(responsible <= set(run['taskIds']), 'Missing responsible implementation')
        expected_files = set().union(*(set(r['path'] for r in implementation['record']['tasks'][tid]['files']) for tid in responsible))
        require(expected_files <= {r['path'] for r in run['files']}, 'Attempt lacks implementation/config snapshots')
        defs = {(a, i): d for a, i, d in scope_checks(case, record)}
        seen = set()
        for result in visit['checks']:
            key = (result['aspect'], result['checkIndex'])
            require(key in defs and key not in seen, 'Unknown/duplicate/out-of-scope check')
            seen.add(key)
            definition = defs[key]
            require({e['form'] for e in definition['evidence']} <= {e['form'] for e in result['evidence']}, 'Required evidence missing')
            if context is not None:
                require(definition['environment'] in {e['environment'] for e in context['environments']}, 'Check environment absent')
            assertion_evidence(result, 'case:' + case['id'] + ':' + key[0] + ':' + str(key[1]) + ':' + str(index), workspace, stale)
        if visit['outcome'] == 'passed':
            require(seen == set(defs) and seen and all(c['status'] == 'passed' for c in visit['checks']),
                    'Current visit must complete all applicable checks before advancing')
        elif visit['outcome'] == 'blocked' and not visit['checks']:
            blockage = visit.get('blockage')
            require(blockage and blockage['reason'].strip(), 'Blocked entry needs a reason and actual evidence')
            assertion_evidence(dict(status='blocked', evidence=blockage['evidence']),
                               'case:' + case['id'] + ':entry:' + str(index), workspace, stale)
        else:
            require(any(c['status'] in ('failed', 'blocked') for c in visit['checks']), 'Failure/block needs an actual check report')
        status = ('stale' if stale else 'failed' if run['exitCode'] not in (None, 0) else visit['outcome'])
        latest[index] = attempt
        details[index] = (status, run, stale)
    cursor = next((i for i in range(len(sequence)) if i not in latest or
                   details[i][0] != 'passed' or not latest[i]['closedAt']), len(sequence))
    data.update(record=record, latest=latest, details=details, cursor=cursor,
                implementationReady=implementation_ready)
    return data


def inspect(record, workspace):
    if InputSnapshot.active() is not None:
        return _inspect(record, workspace)
    snapshot = InputSnapshot()
    with snapshot:
        data = _inspect(record, workspace)
    require(snapshot.current(), 'Acceptance input changed while reviewing candidate; retry without advancing')
    return data


def project(data):
    record = data['record']
    sequence = data['model']['coverage']['sequence']
    for case in data['model']['cases']:
        rows, evidence, values = [], [], []
        indices = [i for i, cid in enumerate(sequence) if cid == case['id']]
        total = len(indices) * len(required_checks(case))
        for i in indices:
            if i not in data['details']:
                continue
            status, run, stale = data['details'][i]
            if not run['visits'][0]['checks'] and status in ('failed', 'blocked', 'stale'):
                values.append(status)
                for ref in copy.deepcopy(run['visits'][0].get('blockage', {}).get('evidence', [])):
                    ref['path'] = os.path.relpath(target(ref['path'], data['workspace']), data['casePath'].parent).replace(os.sep, '/')
                    evidence.append(dict(runId=run['id'], **ref))
            for result in run['visits'][0]['checks']:
                row = dict(runId=run['id'], visitIndex=i, aspect=result['aspect'], checkIndex=result['checkIndex'],
                           status='stale' if stale else 'failed' if run['exitCode'] not in (None, 0) else result['status'],
                           actual=result['actual'], evidence=copy.deepcopy(result['evidence']))
                for ref in row['evidence']:
                    ref['path'] = os.path.relpath(target(ref['path'], data['workspace']), data['casePath'].parent).replace(os.sep, '/')
                    evidence.append(dict(runId=run['id'], **ref))
                rows.append(row)
                values.append(row['status'])
        active = record['active']
        running = active and active['stage'] == 'running' and sequence[active['visitIndex']] == case['id']
        status = ('running' if running else 'stale' if 'stale' in values else 'failed' if 'failed' in values else
                  'blocked' if 'blocked' in values else 'passed' if len(values) == total and total and all(s == 'passed' for s in values)
                  else 'partial' if values else 'not_run')
        labels = {'running': '当前路径访问正在验收。', 'stale': '当前文件变化，需重新确认受影响证据。',
                  'failed': '当前访问验收失败，路径已停止。', 'blocked': '当前访问缺少可验证前提，路径已停止。',
                  'passed': '全部必要访问与检查已经通过并登记。', 'partial': '已完成部分访问或检查，其余保持待验收。'}
        case['execution'] = dict(status=status, actual=labels.get(status), evidence=evidence)
        if rows:
            case['execution']['checks'] = rows
    data['plan']['testCases']['sha256'] = digest(data['model'])
    return data


def _projections(data):
    model, plan = data['model'], data['plan']
    outputs = [(data['casePath'], json.dumps(model, ensure_ascii=False, indent=2) + '\n'),
            (data['planPath'], json.dumps(plan, ensure_ascii=False, indent=2) + '\n'),
            (data['casePath'].with_suffix('.html'), html_text(model, data['state'], plan, data['atomic'])),
            (data['planPath'].with_suffix('.md'), md_text(plan, model))]
    for path, value in case_contracts.projections(data):
        errors = schema_errors(value, load_json(SKILL / 'assets/test-case-contract.schema.json'))
        require(not errors, 'Invalid per-case contract: ' + '; '.join(map(str, errors)))
        outputs.append((path, json.dumps(value, ensure_ascii=False, indent=2) + '\n'))
    return outputs


def projections(data):
    if InputSnapshot.active() is not None:
        return _projections(data)
    snapshot = InputSnapshot()
    with snapshot:
        outputs = _projections(data)
    require(snapshot.current(), 'Projection input changed while rendering; synchronize again')
    return outputs


def sync_views(data):
    outputs = projections(data)
    artifact_copies.validate(data['record'], data['workspace'], [path for path, _ in outputs])
    for path, text in outputs:
        # Keep the same byte-independent view check; avoid rewriting every unchanged contract.
        try:
            if path.read_text(encoding='utf-8') == text:
                continue
        except (FileNotFoundError, UnicodeError):
            pass
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix(path.suffix + '.acceptance.tmp')
        temp.write_text(text, encoding='utf-8')
        os.replace(temp, path)


def check_views(data):
    for path, text in projections(data):
        require(path.is_file() and path.read_text(encoding='utf-8') == text, 'Unsynchronized view: ' + str(path))


def load_data(path, workspace):
    def inspect_and_project():
        data = inspect(load_json(path), workspace)
        data['workspace'] = workspace
        return project(data)

    # An outer execution-plan projection already verifies the same complete snapshot.
    if InputSnapshot.active() is not None:
        return inspect_and_project()
    snapshot = InputSnapshot()
    with snapshot:
        data = inspect_and_project()
    require(snapshot.current(), 'Acceptance input changed while inspecting; retry without advancing')
    return data


def repair(command, path, record, workspace, args):
    require(record['active'] is None, 'Recover the current visit submission before repair')
    item = next((r for r in reversed(record['repairs']) if r['visitIndex'] == args['index']), None)
    require(item is not None, 'Repair must refer to an actual failed/blocked visit')
    payload = load_json(target(args['run'], workspace))
    if command == 'repair-open':
        require(item['status'] != 'resolved', 'Resolved repair cannot be rewritten')
        data = load_data(path, workspace)
        require(payload['category'] in ('code', 'test-case', 'harness', 'environment'), 'Diagnose the cause before repairing')
        affected = payload['affectedCaseIds']
        failed_case = record['sequence'][item['visitIndex']]
        require(failed_case in affected and set(affected) <= set(record['currentDefinitions']), 'Invalid affected case scope')
        require(payload['reason'].strip() and payload['evidence'], 'Diagnosis needs observation and actual evidence')
        require(all(file_current(e, workspace) for e in payload['evidence']), 'Diagnosis evidence missing/changed')
        standards = payload.get('standardSources', [])
        if payload['category'] == 'test-case':
            require(standards, 'A Test Case correction needs independent authoritative standards')
        actual_evidence = {target(e['path'], workspace) for a in record['attempts'] for v in a['run']['visits'] for c in v['checks'] for e in c['evidence']}
        for ref in standards:
            require(target(ref['path'], workspace) != target(record['testCasesPath'], workspace) and target(ref['path'], workspace) not in actual_evidence,
                    'The faulty Test Case or actual result cannot authorize changing expected requirements')
            check_source(ref, workspace / '_anchor.json', workspace)
        item.update(category=payload['category'], status='repairing', affectedCaseIds=affected,
                    diagnosis=dict(reason=payload['reason'], evidence=payload['evidence'], standardSources=standards))
    else:
        require(item['diagnosis'] is not None, 'Diagnose the failure before closing repair')
        if item['status'] == 'resolved':
            require(item['resolution'] == payload, 'Immutable resolved repair changed')
        else:
            require(payload['observation'].strip(), 'Repair resolution observation required')
            assertion_evidence(dict(status='passed', evidence=payload['evidence']), 'repair:' + item['attemptId'], workspace, [])
            require(all(file_current(e, workspace) for e in payload['evidence'] + payload['changedFiles']),
                    'Repair evidence or changed file snapshot missing')
            implementation = inspect_implementation(load_json(target(record['implementationPath'], workspace)), workspace)
            require(all(s == 'implemented' for s in implementation['statuses'].values()), 'Repair requires current implementation/static-check handoff')
            if item['category'] == 'test-case':
                model = load_json(target(record['testCasesPath'], workspace))
                require(model['coverage']['sequence'] == record['sequence'], 'Expected correction changes route; return to task planning')
                require({k: model[k] for k in ('stateGraph', 'atomicGraph')} == record['upstream'],
                        'Do not change requirement facts to make an actual result pass')
                current = {c['id']: case_contracts.definition_hash(c, model) for c in model['cases']}
                require(set(current) == set(record['currentDefinitions']), 'Case identities changed; return to task planning')
                changed = {cid for cid in current if current[cid] != record['currentDefinitions'][cid]}
                require(changed and changed <= set(item['affectedCaseIds']), 'Test Case correction exceeds reviewed scope or changes no definition')
                require(record['sequence'][item['visitIndex']] in changed, 'The failed Test Case definition was not corrected')
                for ref in item['diagnosis']['standardSources']:
                    check_source(ref, workspace / '_anchor.json', workspace)
                record['caseContract'] = case_contract(model)
                record['currentDefinitions'] = current
                record['definitions'].update({case_contracts.definition_hash(c, model): case_contracts.definition(c, model) for c in model['cases']})
                review = inspect(record, workspace)
                requirements = {r['id']: r for r in review['atomic']['requirements']}
                transitions = {t['id']: t for t in review['state']['transitions']}
                from plan import check_acceptance
                states = {s['id']: s for s in review['state']['states']}
                for case in model['cases']:
                    if case['id'] not in changed:
                        continue
                    transition = None
                    if case['kind'] == 'primary':
                        requirement = requirements[case['requirementId']]
                        transition = transitions[requirement['transitionId']]
                        require(case['given']['stateId'] == transition['from'] and case['expected']['stateId'] == transition['to']
                                and case['operation'] == transition['operation'], 'Corrected Test Case must match the original requirement transition')
                    errors = []
                    check_acceptance(case, transition, states, errors)
                    require(not errors, 'Corrected Test Case violates acceptance rules: ' + '; '.join(map(str, errors)))
            elif item['category'] in ('code', 'harness'):
                require(payload['changedFiles'], 'Code/script repair must identify changed files')
                previous = next(a['run'] for a in record['attempts'] if a['run']['id'] == item['attemptId'])
                old_files = {f['path']: f['sha256'] for f in previous['files'] + [previous['script']]}
                require(any(f['path'] in old_files and old_files[f['path']] != f['sha256'] for f in payload['changedFiles']),
                        'No actual code/script change relative to failed attempt')
            item.update(status='resolved', resolution=payload, closedAt=now())
    inspect(record, workspace)
    save(path, record)
    data = load_data(path, workspace)
    sync_views(data)
    check_views(data)
    return {'status': item['status'], 'scope': 'acceptance-repair', 'visitIndex': item['visitIndex'],
            'synced': True, 'checked': True, 'canAdvance': False, 'nextVisitIndex': data['cursor']}


def execute(command, path, workspace, **args):
    workspace = workspace.resolve()
    if path is None:
        path = workspace / 'plan' / 'acceptance' / ('.work/schedule.json' if command == 'plan' else 'acceptance.json')
    else:
        path = path if path.is_absolute() else workspace / path
    path = path.resolve()
    path.relative_to(workspace)
    if command == 'preflight':
        model = load_json(target(args['cases'], workspace))
        plan = load_json(target(args['plan'], workspace))
        probe = dict(testCasesPath=args['cases'], taskPlanPath=args['plan'], caseContract=case_contract(model), planContract=plan_contract(plan))
        inputs(probe, workspace)
        implementation = inspect_implementation(load_json(target(args['implementation'], workspace)), workspace)
        require(implementation['record']['planContract'] == plan_contract(plan), 'Wrong implementation handoff')
        require(all(s == 'implemented' for s in implementation['statuses'].values()), 'Implementation/static checks are incomplete or stale')
        return dict(status='ready', scope='acceptance-preparation', implementation=implementation['statuses'],
                    preparationRequired=['Review driver capabilities and prepare missing resources', 'Plan sessions without changing coverage.sequence',
                                         'Initialize isolated Test Case copies and contracts', 'Start and observe the required host and legal initial state'])
    if command == 'plan':
        model = load_json(target(args['cases'], workspace))
        source = target(args['cases'], workspace)
        state_path = (source.parent / model['stateGraph']['path']).resolve()
        state_path.relative_to(workspace)
        state = load_json(state_path)
        require(digest(state) == model['stateGraph']['sha256'], 'State graph version changed')
        profiles = load_json(target(args['profiles'], workspace))['profiles']
        schedule = build_schedule(model, state, profiles, args.get('test_types', ['script']))
        require(not path.exists(), 'Do not overwrite an execution schedule in use')
        save(path, schedule)
        return {'status': 'planned', 'scope': 'acceptance-execution-plan', 'schedulePath': path.relative_to(workspace).as_posix(), **schedule['planning']['objective'],
                'sessions': schedule['sessions']}
    if command == 'init':
        require(not path.exists(), 'Existing acceptance record must be resumed')
        model = load_json(target(args['cases'], workspace))
        plan = load_json(target(args['plan'], workspace))
        # Source history remains in the frozen planning originals; this ledger starts a separate round.
        schedule_input = args.get('schedule') or (path.parent / '.work' / 'schedule.json').relative_to(workspace).as_posix()
        schedule = load_json(target(schedule_input, workspace))
        preflight = execute('preflight', None, workspace, **args)
        require(preflight['status'] == 'ready', 'Acceptance preparation is blocked')
        state = load_json((target(args['cases'], workspace).parent / model['stateGraph']['path']).resolve())
        require(build_schedule(model, state, schedule['planning']['profiles'], args.get('test_types', ['script'])) == schedule,
                'Execution schedule must match reviewed capabilities and the unchanged route')
        source, model, plan, case_path, plan_path = artifact_copies.create(
            target(args['cases'], workspace), target(args['plan'], workspace), path.parent, workspace)
        record = dict(schemaVersion='1.0.0', planningSource=source,
                      testCasesPath=case_path.relative_to(workspace).as_posix(), taskPlanPath=plan_path.relative_to(workspace).as_posix(),
                      implementationPath=args['implementation'], caseContract=case_contract(model), planContract=plan_contract(plan),
                      testTypes=args.get('test_types', ['script']), sessions=schedule['sessions'], planning=schedule['planning'],
                      scheduleContract=digest(schedule), active=None, attempts=[], sessionResults=[], repairs=[],
                      sequence=copy.deepcopy(model['coverage']['sequence']), upstream={k: model[k] for k in ('stateGraph', 'atomicGraph')},
                      contractsDirectory=(path.parent / 'contracts').relative_to(workspace).as_posix(),
                      currentDefinitions={c['id']: case_contracts.definition_hash(c, model) for c in model['cases']},
                      definitions={case_contracts.definition_hash(c, model): case_contracts.definition(c, model) for c in model['cases']})
        data = inspect(record, workspace)
        require(data['implementationReady'], 'Code implementation/static checks must finish before acceptance')
        save(path, record)
        data = load_data(path, workspace)
        sync_views(data)
        check_views(data)
        return {'status': 'initialized', 'scope': 'acceptance-route',
                'recordPath': path.relative_to(workspace).as_posix(), 'artifactRoot': path.parent.relative_to(workspace).as_posix()}
    artifact_copies.validate(load_json(path), workspace, [path])
    with lock(path):
        record = load_json(path)
        if command in ('repair-open', 'repair-close'):
            return repair(command, path, record, workspace, args)
        data = load_data(path, workspace)
        if command in ('begin', 'next', 'finish'):
            require(record['active'] is None, 'Current visit not closed; resume its submit before advancing')
            check_views(data)
            require(data['implementationReady'], 'Implementation/static checks are incomplete or stale')
            require(not any(r['status'] != 'resolved' for r in record['repairs']), 'Enter and complete the repair workflow before resuming acceptance')
        if command in ('begin', 'next'):
            index = data['cursor']
            if command == 'begin':
                require(args['index'] == index and index < len(data['model']['coverage']['sequence']), 'Only the next unaccepted visit may begin')
                session = session_for(record, index)
                preceding = [s for s in record['sessions'] if s['to'] < session['from']]
                for s in preceding:
                    closed = [r for r in record['sessionResults'] if r['sessionId'] == s['id']]
                    require(closed and closed[-1]['exitCode'] == 0 and file_current(closed[-1]['log'], workspace),
                            'Previous driver session not successfully closed')
                record['active'] = dict(token=str(uuid.uuid4()), visitIndex=index, startedAt=now(), sessionId=session['id'],
                                        predecessorAttemptId=data['latest'][index - 1]['run']['id'] if index else None,
                                        stage='running', runId=None)
                save(path, record)
                data = load_data(path, workspace)
                sync_views(data)
                check_views(data)
                return {'status': 'authorized', 'visitIndex': index, 'token': record['active']['token'], 'synced': True, 'checked': True}
            return {'status': 'ready', 'nextVisitIndex': index, 'scope': 'acceptance-route'}
        if command == 'submit':
            run = load_json(target(args['run'], workspace))
            active = record['active']
            already = next((a for a in record['attempts'] if a['run']['id'] == run['id']), None)
            if active is None and already is not None and already['closedAt']:
                require(already['run'] == run, 'Immutable attempt identity changed')
                check_views(data)
                index = run['visits'][0]['visitIndex']
                status = data['details'][index][0]
                return {'status': status, 'visitIndex': index, 'recorded': True, 'synced': True,
                        'checked': True, 'canAdvance': status == 'passed' and data['implementationReady'] and not any(r['status'] != 'resolved' for r in record['repairs']), 'resumed': True}
            require(active is not None and active['token'] == args['token'], 'Missing/current authorization token')
            require(len(run.get('visits', [])) == 1 and run['visits'][0]['visitIndex'] == active['visitIndex'], 'Submit the authorized current visit only')
            previous = next((a for a in record['attempts'] if a['run']['id'] == run['id']), None)
            if previous:
                require(previous['run'] == run and active['stage'] == 'recorded', 'Immutable attempt identity changed')
            else:
                require(active['stage'] == 'running', 'Recover current submit before starting another attempt')
                record['attempts'].append(dict(run=run, authorizedAt=active['startedAt'],
                                              predecessorAttemptId=active['predecessorAttemptId'], closedAt=None,
                                              definitionHash=record['currentDefinitions'][data['model']['coverage']['sequence'][active['visitIndex']]]))
                active.update(stage='recorded', runId=run['id'])
                inspect(record, workspace)  # Reject invalid candidate before any canonical write.
                save(path, record)
            data = load_data(path, workspace)
            index = active['visitIndex']
            status = data['details'][index][0]
            if status in ('failed', 'blocked') and not any(r['attemptId'] == run['id'] for r in record['repairs']):
                case_id = data['model']['coverage']['sequence'][index]
                record['repairs'].append(dict(attemptId=run['id'], visitIndex=index, affectedCaseIds=[case_id],
                                              category='undetermined', status='diagnosing', diagnosis=None, resolution=None,
                                              openedAt=now(), closedAt=None))
                save(path, record)
                data = load_data(path, workspace)
            sync_views(data)
            check_views(data)
            index = active['visitIndex']
            record['attempts'][-1]['closedAt'] = now()
            record['active'] = None
            save(path, record)
            status = data['details'][index][0]
            return {'status': status, 'visitIndex': index, 'recorded': True, 'synced': True, 'checked': True,
                    'canAdvance': status == 'passed' and data['implementationReady'] and not any(r['status'] != 'resolved' for r in record['repairs'])}
        if command == 'close-session':
            require(record['active'] is None, 'Close current visit first')
            result = load_json(target(args['run'], workspace))
            session = next(s for s in record['sessions'] if s['id'] == result['sessionId'])
            require(result['command'] == session['command'] and result['cwd'] == session['cwd'], 'Wrong session command')
            require(data['cursor'] > session['to'] or result['exitCode'] != 0, 'Successful session ended before its visits were accepted')
            require(file_current(result['log'], workspace), 'Session actual output missing/changed')
            require(stamp(result['startedAt']) <= stamp(result['finishedAt']), 'Session time order')
            record['sessionResults'].append(result)
            inspect(record, workspace)
            save(path, record)
            return {'status': 'closed' if result['exitCode'] == 0 else 'failed', 'sessionId': session['id']}
        if command == 'sync':
            sync_views(data)
        check_views(data)
        if command == 'finish':
            require(data['cursor'] == len(data['model']['coverage']['sequence']), 'Unaccepted route visits remain')
            for session in record['sessions']:
                results = [r for r in record['sessionResults'] if r['sessionId'] == session['id']]
                require(results and results[-1]['exitCode'] == 0 and file_current(results[-1]['log'], workspace), 'Unclosed/failed driver session')
            pending = [c['id'] for c in data['model']['cases'] if c['execution']['status'] != 'passed']
            require(not pending or record['testTypes'] == ['script'], 'Test Cases not fully accepted')
            return {'status': 'passed', 'scope': 'script-acceptance' if record['testTypes'] == ['script'] else 'complete-acceptance',
                    'browserPending': pending, 'synced': True, 'checked': True}
        return {'status': 'consistent', 'scope': 'acceptance-projections', 'nextVisitIndex': data['cursor'],
                'acceptanceStatus': 'incomplete' if data['cursor'] < len(data['model']['coverage']['sequence']) else 'visits-complete'}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('command', choices=['preflight', 'plan', 'init', 'next', 'begin', 'submit', 'repair-open', 'repair-close', 'close-session', 'sync', 'check', 'finish'])
    p.add_argument('record', type=Path, nargs='?', help='Record path; default: <workspace>/plan/acceptance/acceptance.json (plan: .work/schedule.json)')
    p.add_argument('--workspace', type=Path, required=True)
    for name in ('cases', 'plan', 'implementation', 'schedule', 'profiles', 'run', 'token'):
        p.add_argument('--' + name)
    p.add_argument('--index', type=int)
    p.add_argument('--test-types', nargs='+', choices=['script', 'browser'], default=['script'])
    a = vars(p.parse_args())
    try:
        result = execute(a.pop('command'), a.pop('record'), a.pop('workspace'), **a)
    except (OSError, ValueError, KeyError, TypeError, IndexError, StopIteration) as error:
        result = {'status': 'failed', 'error': str(error), 'canAdvance': False}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return int(result['status'] in ('failed', 'blocked', 'stale'))


if __name__ == '__main__':
    sys.exit(main())
