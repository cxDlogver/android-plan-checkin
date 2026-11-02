#!/usr/bin/env python3
"""Isolated workflow tests; no product Test Cases or device acceptance are executed."""
import copy
import argparse
import sys
import subprocess
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import route
import implementation
from execution import digest, raw_hash, load_json, plan_contract
from test_plan import fixture, write
from plan import execute as build_plan
from schedule import build_schedule
import case_contracts

TEMP_ROOT = None

class SplitWorkflow(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='skill-stage-', dir=TEMP_ROOT)
        self.base = Path(self.temp.name).resolve()
        self.model, self.plan, self.cases, self.state, self.atomic = fixture(self.base)
        self.assertEqual(build_plan('build', self.cases, self.base)['status'], 'passed')
        self.impl = self.base / 'implementation.json'
        self.record = self.base / 'acceptance.json'
        implementation.execute('init', self.impl, self.base, self.rel(self.cases.parent / 'task-plan.json'))
        self.make_implementation()
        self.script = self.base / 'driver.py'
        self.script.write_text('# Shared driver fixture; report payload is independently supplied by this test.\n', encoding='utf-8')
        self.command = ['python', '-B', 'driver.py']
        self.schedule = self.base / 'schedule.json'
        self.profiles = [dict(id='shared', contextKey='route-context', command=self.command, cwd='.', environments=['runtime'], resources=[], setupUnits=['runtime-host'], eligibleVisits=list(range(len(self.model['coverage']['sequence']))))]
        planned = build_schedule(self.model, self.state, self.profiles, ['script'])
        self.session_id = planned['sessions'][0]['id']
        write(self.schedule, planned)
        self.source_cases = self.cases
        self.source_artifacts = {p: p.read_bytes() for p in (self.cases, self.cases.with_suffix('.html'),
                                 self.cases.parent/'task-plan.json', self.cases.parent/'task-plan.md')}
        route.execute('init', self.record, self.base, cases=self.rel(self.cases),
                      plan=self.rel(self.cases.parent / 'task-plan.json'), implementation=self.rel(self.impl),
                      schedule=self.rel(self.schedule), test_types=['script'])
        self.cases = self.base / load_json(self.record)['testCasesPath']

    def tearDown(self):
        self.temp.cleanup()

    def rel(self, p):
        return p.relative_to(self.base).as_posix()

    def ref(self, p):
        return dict(path=self.rel(p), sha256=raw_hash(p.read_bytes()))

    def make_implementation(self):
        value = load_json(self.impl)
        log = self.base / 'static.log'
        log.write_text('Fixture static analyzer: no diagnostics\n', encoding='utf-8')
        source = self.ref(self.base / 'source.py')
        value['tasks']['P'] = dict(implementation=dict(startedAt='2020-01-01T00:00:00Z', completedAt='2020-01-01T00:00:01Z'),
                                  resources=[], done=[dict(index=0, observation='Fixture implementation inspected.', sources=[source])],
                                  files=[source], checks=[dict(kind='typecheck', command=['analyzer', '--check', 'source.py'], cwd='.',
                                                              startedAt='2020-01-01T00:00:02Z', finishedAt='2020-01-01T00:00:03Z',
                                                              exitCode=0, log=self.ref(log), files=[source])])
        write(self.impl, value)

    def begin(self, index):
        return route.execute('begin', self.record, self.base, index=index)['token']

    def run_file(self, index, failed=False, omit=False):
        record = load_json(self.record)
        active = record['active']
        case = next(c for c in self.model['cases'] if c['id'] == self.model['coverage']['sequence'][index])
        folder = self.base / ('step-' + str(index) + '-' + str(len(record['attempts'])))
        folder.mkdir()
        report = folder / 'assertions.json'
        results, assertions = [], []
        for aspect in ('visual', 'functional'):
            if omit and aspect == 'functional':
                continue
            status = 'failed' if failed else 'passed'
            assertions.append(dict(target=f'case:{case["id"]}:{aspect}:0:{index}', expected=1,
                                   actual=0 if failed else 1, verdict=status))
            results.append(dict(aspect=aspect, checkIndex=0, status=status, actual='Independently compared fixture observation.', evidence=[]))
        write(report, dict(assertions=assertions))
        for r in results:
            r['evidence'] = [dict(form='assertion-report', **self.ref(report), description='Independent fixture comparison.')]
        entry = {'kind': 'initial'} if index == 0 else dict(kind='handoff', previousAttemptId=active['predecessorAttemptId'])
        # Some primary route entries legally restart at the declared initial state.
        if index and next(c for c in self.model['cases'] if c['id'] == self.model['coverage']['sequence'][index - 1])['expected']['stateId'] != case['given']['stateId']:
            entry = {'kind': 'initial'}
        context = folder / 'context.json'
        write(context, dict(build='fixture', inputs={'index': index}, mocks=[], environments=[{'environment': 'runtime'}], entry=entry))
        begin_time = active['startedAt']
        run = dict(id=folder.name, taskIds=['P'], script=self.ref(self.script), authoredAt='2020-01-01T00:00:04Z',
                   command=self.command, cwd='.', startedAt=begin_time, finishedAt=route.now(), exitCode=None,
                   environment='runtime', files=[self.ref(self.base / 'source.py')], context=self.ref(context),
                   visits=[dict(visitIndex=index, entry='Observed permitted entry.', givenObserved='Actual given checked.',
                                operationObserved='Actual fixture operation.', targetObserved='Actual fixture result.',
                                outcome='failed' if failed else 'passed', checks=results)], taskResults=[])
        file = folder / 'run.json'
        write(file, run)
        return file

    def submit(self, index, token, **args):
        file = self.run_file(index, **args)
        return route.execute('submit', self.record, self.base, token=token, run=self.rel(file))

    def test_static_finish_does_not_accept_or_modify_cases(self):
        before = self.cases.read_bytes()
        result = implementation.execute('finish', self.impl, self.base)
        self.assertEqual(result['scope'], 'code-implementation')
        self.assertEqual(self.cases.read_bytes(), before)
        self.assertTrue(all(c['execution']['status'] == 'not_run' for c in load_json(self.cases)['cases']))

    def test_static_failure_blocks_acceptance_start(self):
        value = load_json(self.impl)
        value['tasks']['P']['checks'][0]['exitCode'] = 1
        write(self.impl, value)
        with self.assertRaisesRegex(ValueError, 'incomplete|stale'):
            self.begin(0)

    def test_static_evidence_change_is_stale(self):
        (self.base / 'source.py').write_text('changed\n', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'incomplete|stale'):
            self.begin(0)

    def test_static_record_rejects_behavior_test_kind(self):
        value = load_json(self.impl)
        value['tasks']['P']['checks'][0]['kind'] = 'integration-test'
        write(self.impl, value)
        with self.assertRaises(ValueError):
            implementation.execute('check', self.impl, self.base)

    def test_cannot_skip_route_index(self):
        with self.assertRaisesRegex(ValueError, 'next unaccepted'):
            self.begin(1)

    def test_active_visit_blocks_next_until_submission(self):
        self.begin(0)
        with self.assertRaisesRegex(ValueError, 'not closed'):
            route.execute('next', self.record, self.base)

    def test_missing_check_blocks_submission_and_keeps_active(self):
        token = self.begin(0)
        with self.assertRaisesRegex(ValueError, 'all applicable checks'):
            self.submit(0, token, omit=True)
        self.assertIsNotNone(load_json(self.record)['active'])
        self.assertFalse(load_json(self.record)['attempts'])

    def test_status_synced_before_next_authorization(self):
        token = self.begin(0)
        self.assertTrue(self.submit(0, token)['canAdvance'])
        model = load_json(self.cases)
        self.assertTrue(model['cases'][0]['execution'].get('checks'))
        self.assertEqual(route.execute('next', self.record, self.base)['nextVisitIndex'], 1)
        self.cases.with_suffix('.html').write_text('stale page', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'Unsynchronized'):
            self.begin(1)

    def test_failure_is_synced_and_cannot_advance(self):
        token = self.begin(0)
        result = self.submit(0, token, failed=True)
        self.assertFalse(result['canAdvance'])
        self.assertTrue(result['synced'])
        self.assertEqual(load_json(self.cases)['cases'][0]['execution']['status'], 'failed')
        with self.assertRaisesRegex(ValueError, 'repair workflow'):
            self.begin(1)

    def test_missing_entry_updates_blocked_without_fabricating_operation(self):
        token = self.begin(0)
        file = self.run_file(0)
        run = load_json(file)
        case_id = self.model['coverage']['sequence'][0]
        report = file.parent / 'entry-blocked.json'
        write(report, dict(assertions=[dict(target=f'case:{case_id}:entry:0', expected='Host ready',
                                           actual='Host unavailable', verdict='blocked')]))
        visit = run['visits'][0]
        visit.update(outcome='blocked', checks=[], operationObserved='Not executed: actual host unavailable.',
                     blockage=dict(reason='Actual host unavailable.', evidence=[dict(form='assertion-report', **self.ref(report),
                                                                                     description='Observed missing entry prerequisite.')]))
        write(file, run)
        result = route.execute('submit', self.record, self.base, token=token, run=self.rel(file))
        self.assertFalse(result['canAdvance'])
        self.assertEqual(load_json(self.cases)['cases'][0]['execution']['status'], 'blocked')
        self.assertTrue(load_json(self.cases)['cases'][0]['execution']['evidence'])

    def test_projection_interruption_resumes_same_submit(self):
        token = self.begin(0)
        file = self.run_file(0)
        with patch.object(route, 'sync_views', side_effect=OSError('fixture projection failure')):
            with self.assertRaises(OSError):
                route.execute('submit', self.record, self.base, token=token, run=self.rel(file))
        self.assertEqual(load_json(self.record)['active']['stage'], 'recorded')
        self.assertEqual(len(load_json(self.record)['attempts']), 1)
        with self.assertRaisesRegex(ValueError, 'not closed'):
            self.begin(1)
        result = route.execute('submit', self.record, self.base, token=token, run=self.rel(file))
        self.assertTrue(result['canAdvance'])
        self.assertEqual(len(load_json(self.record)['attempts']), 1)

    def test_closed_submit_is_idempotent_without_reexecuting_action(self):
        token = self.begin(0)
        file = self.run_file(0)
        route.execute('submit', self.record, self.base, token=token, run=self.rel(file))
        result = route.execute('submit', self.record, self.base, token=token, run=self.rel(file))
        self.assertTrue(result['resumed'])
        self.assertEqual(len(load_json(self.record)['attempts']), 1)

    def test_null_process_exit_does_not_replace_missing_evidence(self):
        token = self.begin(0)
        file = self.run_file(0)
        run = load_json(file)
        run['visits'][0]['checks'][0]['evidence'] = []
        write(file, run)
        with self.assertRaisesRegex(ValueError, 'evidence|Evidence'):
            route.execute('submit', self.record, self.base, token=token, run=self.rel(file))

    def test_finish_requires_real_driver_close_after_all_visits(self):
        for index in range(len(self.model['coverage']['sequence'])):
            self.assertTrue(self.submit(index, self.begin(index))['canAdvance'])
        with self.assertRaisesRegex(ValueError, 'Unclosed/failed'):
            route.execute('finish', self.record, self.base)
        log = self.base / 'driver.log'
        log.write_text('Fixture driver actually closed.\n', encoding='utf-8')
        result = self.base / 'driver-result.json'
        write(result, dict(sessionId=self.session_id, command=self.command, cwd='.', startedAt='2020-01-01T00:00:05Z',
                           finishedAt=route.now(), exitCode=0, log=self.ref(log)))
        route.execute('close-session', self.record, self.base, run=self.rel(result))
        self.assertEqual(route.execute('finish', self.record, self.base)['scope'], 'script-acceptance')

    def contract(self, index=0):
        record = load_json(self.record)
        cid = record['sequence'][index]
        return self.base / record['contractsDirectory'] / case_contracts.filename(cid)

    def diagnose(self, category):
        record = load_json(self.record)
        repair = record['repairs'][-1]
        previous = record['attempts'][-1]['run']
        evidence = previous['visits'][0]['checks'][0]['evidence']
        payload = dict(category=category, affectedCaseIds=repair['affectedCaseIds'],
                       reason='Observed fixture mismatch traced to the classified cause.', evidence=evidence, standardSources=[])
        if category == 'test-case':
            payload['standardSources'] = [dict(**self.ref(self.base / 'prd.md'), locator='L1')]
        file = self.base / 'diagnosis.json'
        write(file, payload)
        route.execute('repair-open', self.record, self.base, index=0, run=self.rel(file))

    def resolution(self, changed=None):
        repair = load_json(self.record)['repairs'][-1]
        report = self.base / 'repair-review.json'
        write(report, dict(assertions=[dict(target='repair:' + repair['attemptId'], expected='Reviewed fixture correction',
                                           actual='Reviewed fixture correction', verdict='passed')]))
        result = self.base / 'repair-resolution.json'
        write(result, dict(observation='Fixture correction reviewed against its independent source.',
                           evidence=[dict(form='assertion-report', **self.ref(report), description='Fixture correction review.')],
                           changedFiles=changed or []))
        return result

    def test_cli_defaults_use_workspace_even_from_another_cwd(self):
        profiles = self.base / 'profiles.json'
        write(profiles, dict(profiles=self.profiles))
        cwd = self.base / 'another-working-directory'
        cwd.mkdir()
        command = [sys.executable, '-B', str(Path(route.__file__).resolve())]
        planned = subprocess.run(command + ['plan', '--workspace', str(self.base), '--cases', self.rel(self.source_cases),
                                           '--profiles', self.rel(profiles)], cwd=cwd, capture_output=True, text=True)
        self.assertEqual(planned.returncode, 0, planned.stdout + planned.stderr)
        self.assertEqual(json.loads(planned.stdout)['schedulePath'], 'plan/acceptance/.work/schedule.json')
        initialized = subprocess.run(command + ['init', '--workspace', str(self.base), '--cases', self.rel(self.source_cases),
                                               '--plan', self.rel(self.source_cases.parent / 'task-plan.json'),
                                               '--implementation', self.rel(self.impl)], cwd=cwd, capture_output=True, text=True)
        self.assertEqual(initialized.returncode, 0, initialized.stdout + initialized.stderr)
        self.assertEqual(json.loads(initialized.stdout)['recordPath'], 'plan/acceptance/acceptance.json')
        record = load_json(self.base / 'plan/acceptance/acceptance.json')
        self.assertEqual(record['contractsDirectory'], 'plan/acceptance/contracts')
        self.assertEqual(len(list((self.base / 'plan/acceptance/contracts').glob('*.json'))), len(self.model['cases']))
        self.assertFalse((cwd / 'plan').exists())

    def test_explicit_record_path_overrides_default_artifact_root(self):
        path = self.base / 'custom-review/accepted.json'
        result = route.execute('init', path, self.base, cases=self.rel(self.source_cases),
                               plan=self.rel(self.source_cases.parent / 'task-plan.json'), implementation=self.rel(self.impl),
                               schedule=self.rel(self.schedule), test_types=['script'])
        self.assertEqual(result['artifactRoot'], 'custom-review')
        self.assertEqual(load_json(path)['contractsDirectory'], 'custom-review/contracts')
        self.assertEqual(len(list((path.parent / 'contracts').glob('*.json'))), len(self.model['cases']))

    def test_each_case_has_a_contract_before_any_observation(self):
        self.assertEqual(len(list((self.base / 'contracts').glob('*.json'))), len(self.model['cases']))
        value = load_json(self.contract())
        self.assertEqual(value['attempts'], [])
        self.assertEqual(value['execution']['status'], 'not_run')
        self.assertIn('expected', value['definition'])
        self.assertIn('expectedState', value)

    def test_contract_contains_expected_actual_and_evidence(self):
        self.submit(0, self.begin(0))
        value = load_json(self.contract())
        check = value['attempts'][0]['checks'][0]
        self.assertEqual(check['comparisons'][0], dict(expected=1, actual=1, verdict='passed'))
        self.assertTrue(check['evidence'])
        self.contract().write_text('{}', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'Unsynchronized'):
            self.begin(1)

    def test_failed_visit_requires_repair_before_retry(self):
        self.submit(0, self.begin(0), failed=True)
        self.assertEqual(load_json(self.record)['repairs'][-1]['status'], 'diagnosing')
        with self.assertRaisesRegex(ValueError, 'repair workflow'):
            self.begin(0)

    def test_code_repair_static_handoff_then_retry_preserves_failed_evidence(self):
        self.submit(0, self.begin(0), failed=True)
        self.diagnose('code')
        source = self.base / 'source.py'
        source.write_text(source.read_text(encoding='utf-8') + '# reviewed fixture correction\n', encoding='utf-8')
        self.make_implementation()
        result = self.resolution([self.ref(source)])
        route.execute('repair-close', self.record, self.base, index=0, run=self.rel(result))
        self.assertNotEqual(load_json(self.contract())['execution']['status'], 'passed')
        self.assertTrue(self.submit(0, self.begin(0))['canAdvance'])
        history = load_json(self.contract())['attempts']
        self.assertEqual([a['outcome'] for a in history], ['failed', 'passed'])
        self.assertEqual(history[0]['checks'][0]['comparisons'][0]['actual'], 0)

    def test_expected_correction_needs_independent_standard_then_reacceptance(self):
        self.submit(0, self.begin(0), failed=True)
        self.diagnose('test-case')
        model = load_json(self.cases)
        model['cases'][0]['acceptance']['visual']['checks'][0]['criterion'] = 'Corrected expectation grounded in original requirement.'
        write(self.cases, model)
        result = self.resolution()
        route.execute('repair-close', self.record, self.base, index=0, run=self.rel(result))
        self.assertNotEqual(load_json(self.contract())['execution']['status'], 'passed')
        self.assertTrue(self.submit(0, self.begin(0))['canAdvance'])
        value = load_json(self.contract())
        self.assertFalse(value['attempts'][0]['definitionCurrent'])
        self.assertEqual(value['attempts'][0]['checks'][0]['comparisons'][0]['actual'], 0)
        self.assertEqual(value['execution']['status'], 'passed')

    def test_expected_correction_cannot_cite_the_faulty_case_as_standard(self):
        self.submit(0, self.begin(0), failed=True)
        record = load_json(self.record)
        file = self.base / 'bad-diagnosis.json'
        write(file, dict(category='test-case', affectedCaseIds=record['repairs'][-1]['affectedCaseIds'],
                         reason='Try to authorize expected from itself.', evidence=record['attempts'][-1]['run']['visits'][0]['checks'][0]['evidence'],
                         standardSources=[dict(**self.ref(self.cases), locator='L1')]))
        with self.assertRaisesRegex(ValueError, 'cannot authorize'):
            route.execute('repair-open', self.record, self.base, index=0, run=self.rel(file))


    def assert_planning_unchanged(self):
        self.assertEqual({p: p.read_bytes() for p in self.source_artifacts}, self.source_artifacts)

    def test_preflight_allows_preparation_without_existing_acceptance_outputs(self):
        path = self.base / 'unprepared/deep/acceptance.json'
        result = route.execute('preflight', path, self.base, cases=self.rel(self.source_cases),
                               plan=self.rel(self.source_cases.parent/'task-plan.json'), implementation=self.rel(self.impl))
        self.assertEqual(result['status'], 'ready')
        self.assertEqual(result['scope'], 'acceptance-preparation')
        self.assertTrue(result['preparationRequired'])
        self.assertFalse(path.parent.exists())
        self.assert_planning_unchanged()

    def test_init_submit_failure_and_repair_never_modify_planning_originals(self):
        self.assertNotEqual(self.cases, self.source_cases)
        self.assert_planning_unchanged()
        self.submit(0, self.begin(0), failed=True)
        self.diagnose('test-case')
        model = load_json(self.cases)
        model['cases'][0]['acceptance']['visual']['checks'][0]['criterion'] = 'Reviewed correction on the acceptance copy.'
        write(self.cases, model)
        route.execute('repair-close', self.record, self.base, index=0, run=self.rel(self.resolution()))
        self.submit(0, self.begin(0))
        route.execute('sync', self.record, self.base)
        self.assert_planning_unchanged()

    def test_redirect_to_original_is_rejected_before_any_write(self):
        record = load_json(self.record)
        record['testCasesPath'] = self.rel(self.source_cases)
        write(self.record, record)
        with self.assertRaisesRegex(ValueError, 'isolated planning copies'):
            route.execute('sync', self.record, self.base)
        self.assert_planning_unchanged()

    def test_unisolated_legacy_record_cannot_sync_planning_originals(self):
        import execution
        source_plan = load_json(self.source_cases.parent/'task-plan.json')
        record = dict(schemaVersion='1.0.0', testCasesPath=self.rel(self.source_cases),
                      taskPlanPath=self.rel(self.source_cases.parent/'task-plan.json'),
                      caseContract=execution.case_contract(load_json(self.source_cases)), planContract=plan_contract(source_plan),
                      tasks={'P':dict(implementation=None, resources=[])}, runs=[])
        path = self.base/'legacy.json'
        write(path, record)
        before = path.read_bytes()
        with self.assertRaisesRegex(ValueError, 'Unisolated'):
            execution.execute('sync', path, self.base)
        self.assertEqual(path.read_bytes(), before)
        self.assert_planning_unchanged()

    def test_source_change_blocks_silent_rebinding(self):
        self.source_cases.with_suffix('.html').write_text('Changed planning baseline', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'Planning source changed'):
            self.begin(0)

    def test_nested_copy_keeps_references_and_implementation_handoff(self):
        path = self.base/'reviews/nested/run/acceptance.json'
        route.execute('init', path, self.base, cases=self.rel(self.source_cases),
                      plan=self.rel(self.source_cases.parent/'task-plan.json'), implementation=self.rel(self.impl),
                      schedule=self.rel(self.schedule), test_types=['script'])
        record = load_json(path)
        copied = self.base/record['testCasesPath']
        model = load_json(copied)
        self.assertEqual((copied.parent/model['stateGraph']['path']).resolve(),
                         (self.source_cases.parent/self.model['stateGraph']['path']).resolve())
        self.assertEqual(route.execute('check', path, self.base)['status'], 'consistent')
        self.assertEqual(implementation.execute('finish', self.impl, self.base)['status'], 'passed')
        self.assert_planning_unchanged()

    def test_init_refuses_existing_copies_without_overwriting_anything(self):
        path = self.base/'collision/acceptance.json'
        path.parent.mkdir()
        sentinel = path.parent/'test-cases.json'
        sentinel.write_text('Keep the existing acceptance file', encoding='utf-8')
        before = sentinel.read_bytes()
        with self.assertRaisesRegex(ValueError, 'copies already exist'):
            route.execute('init', path, self.base, cases=self.rel(self.source_cases),
                          plan=self.rel(self.source_cases.parent/'task-plan.json'), implementation=self.rel(self.impl),
                          schedule=self.rel(self.schedule), test_types=['script'])
        self.assertEqual(sentinel.read_bytes(), before)
        self.assertFalse(path.exists())
        self.assert_planning_unchanged()

    def test_bad_schedule_creates_no_partial_acceptance_copy(self):
        path = self.base/'bad-schedule/acceptance.json'
        value = load_json(self.schedule)
        value['planning']['objective']['sessionCount'] += 1
        schedule = self.base/'incorrect-schedule.json'
        write(schedule, value)
        with self.assertRaisesRegex(ValueError, 'schedule'):
            route.execute('init', path, self.base, cases=self.rel(self.source_cases),
                          plan=self.rel(self.source_cases.parent/'task-plan.json'), implementation=self.rel(self.impl),
                          schedule=self.rel(schedule), test_types=['script'])
        self.assertFalse(path.parent.exists())
        self.assert_planning_unchanged()


class ScheduleContracts(unittest.TestCase):
    def setUp(self):
        def case(cid, start, end):
            return dict(id=cid, kind='primary', given=dict(stateId=start), expected=dict(stateId=end),
                        acceptance=dict(visual=dict(checks=[dict(testType='script', environment='runtime')]), functional=dict(checks=[])))
        self.model = dict(cases=[case('A', 'D', 'S'), case('B', 'S', 'E'), case('C', 'E', 'D')],
                          coverage=dict(sequence=['A', 'B', 'C']))
        self.state = dict(states=[dict(id='D', isInitial=True), dict(id='S', isInitial=False), dict(id='E', isInitial=False)])

    def profile(self, name, indices, context='shared', units=None):
        return dict(id=name, contextKey=context, command=['driver', name], cwd='.', environments=['runtime'],
                    resources=[], setupUnits=units or ['host'], eligibleVisits=indices)

    def test_combines_contiguous_cases_and_preserves_route(self):
        result = build_schedule(self.model, self.state,
                                [self.profile('prefix', [0]), self.profile('tail', [1, 2]), self.profile('whole', [0, 1, 2])], ['script'])
        self.assertEqual(result['planning']['objective'], dict(routeVisits=3, additionalEntryVisits=0, preparationCount=1, sessionCount=1))
        self.assertEqual(result['sessions'][0]['profileId'], 'whole')

    def test_changed_context_records_shortest_entry_prefix(self):
        result = build_schedule(self.model, self.state,
                                [self.profile('first', [0], context='one'), self.profile('second', [1, 2], context='two')], ['script'])
        self.assertEqual(result['sessions'][1]['entryReplay'], ['A'])
        self.assertEqual(result['planning']['objective']['additionalEntryVisits'], 1)

    def test_looks_ahead_instead_of_choosing_the_cheapest_first_step(self):
        profiles = [self.profile('cheap-first', [0], context='one'), self.profile('tail', [1, 2], context='two'),
                    self.profile('whole', [0, 1, 2], context='three', units=['host', 'data'])]
        result = build_schedule(self.model, self.state, profiles, ['script'])
        self.assertEqual(result['sessions'][0]['profileId'], 'whole')
        self.assertEqual(result['planning']['objective']['additionalEntryVisits'], 0)

    def test_uncovered_required_environment_is_not_scheduled_as_pass(self):
        p = self.profile('missing', [0, 1, 2])
        p['environments'] = ['native']
        with self.assertRaisesRegex(ValueError, 'No preparation profile'):
            build_schedule(self.model, self.state, [p], ['script'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--temp-root', type=Path)
    args = parser.parse_args()
    TEMP_ROOT = args.temp_root
    unittest.main(argv=[sys.argv[0]])
