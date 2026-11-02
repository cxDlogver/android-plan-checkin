"""Execution-plan fixtures; no product Test Cases or devices are executed."""
import copy
import os
import unittest
from unittest.mock import patch

import test_route as fixtures
import execution_plan
from execution import load_json

class PlanProjection(unittest.TestCase):
    def setUp(self):
        self.workflow=fixtures.SplitWorkflow('test_static_finish_does_not_accept_or_modify_cases')
        self.workflow.setUp()

    def tearDown(self):
        self.workflow.tearDown()

    def plan(self):
        return execution_plan.build(self.workflow.record,self.workflow.base)

    def test_next_follows_actual_committed_progress_without_mutating_it(self):
        fixture=self.workflow
        before=fixture.record.read_bytes()
        plan=self.plan()
        self.assertEqual(fixture.record.read_bytes(),before)
        self.assertTrue(plan['next']['canBegin'])
        self.assertEqual(plan['next']['visit']['visitIndex'],0)
        fixture.submit(0,fixture.begin(0))
        after=fixture.record.read_bytes()
        plan=self.plan()
        self.assertEqual(plan['next']['visit']['visitIndex'],1)
        self.assertEqual(plan['progress']['acceptedVisits'],1)
        self.assertEqual(plan['visits'][0]['status'],'passed')
        self.assertEqual(fixture.record.read_bytes(),after)
        fixture.assert_planning_unchanged()

    def test_active_and_failed_visits_never_expose_a_later_case_as_ready(self):
        fixture=self.workflow
        token=fixture.begin(0)
        plan=self.plan()
        self.assertFalse(plan['next']['canBegin'])
        self.assertEqual(plan['next']['action'],'recover-active-visit')
        fixture.submit(0,token,failed=True)
        plan=self.plan()
        self.assertFalse(plan['next']['canBegin'])
        self.assertEqual(plan['next']['action'],'repair')
        self.assertEqual(plan['next']['visit']['visitIndex'],0)
        self.assertEqual(plan['progress']['acceptedVisits'],0)


    def test_deterministic_views_and_tamper_detection(self):
        fixture = self.workflow
        plan = self.plan()
        self.assertEqual(plan, self.plan())
        execution_plan.write_outputs(plan, fixture.record.parent, fixture.base)
        execution_plan.check_outputs(plan, fixture.record.parent, fixture.base)
        (fixture.record.parent/'execution-plan.md').write_text('stale', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'missing or stale'):
            execution_plan.check_outputs(plan, fixture.record.parent, fixture.base)
        execution_plan.write_outputs(plan, fixture.record.parent, fixture.base)
        self.assertEqual(plan['snapshotId'], self.plan()['snapshotId'])
        fixture.submit(0, fixture.begin(0))
        with self.assertRaisesRegex(ValueError, 'inputs changed'):
            execution_plan.check_outputs(plan, fixture.record.parent, fixture.base)

    def test_repeated_visits_and_round_partition_are_exact(self):
        fixture = self.workflow
        plan = self.plan()
        record = load_json(fixture.record)
        self.assertEqual([v['caseId'] for v in plan['visits']], record['sequence'])
        self.assertEqual([i for r in plan['rounds'] for i in range(r['fromVisitIndex'],r['toVisitIndex']+1)], list(range(len(record['sequence']))))
        self.assertTrue(all(r['boundaryReasons'] for r in plan['rounds']))
        self.assertTrue(all(v['contractHref'].startswith('contracts/') for v in plan['visits']))
        self.assertIn(str(len(record['sequence']))+' 次访问', execution_plan.markdown(plan))
        self.assertNotIn('211', execution_plan.markdown(plan))
        self.assertNotIn('plan/acceptance/scripts/', execution_plan.html_document(plan))

    def test_output_isolation_and_canonical_view_gate(self):
        fixture = self.workflow
        plan = self.plan()
        with self.assertRaisesRegex(ValueError, 'beside'):
            execution_plan.write_outputs(plan, fixture.source_cases.parent, fixture.base)
        fixture.cases.with_suffix('.html').write_text('stale', encoding='utf-8')
        plan = self.plan()
        self.assertFalse(plan['next']['canBegin'])
        self.assertEqual(plan['next']['action'], 'sync-projections')
        with self.assertRaisesRegex(ValueError, 'canonical'):
            execution_plan.write_outputs(plan, fixture.record.parent, fixture.base)
        fixture.assert_planning_unchanged()

    def test_session_boundary_waits_for_real_successful_close(self):
        fixture = self.workflow
        record = load_json(fixture.record)
        profiles = copy.deepcopy(record['planning']['profiles'])
        second = copy.deepcopy(profiles[0])
        profiles[0]['eligibleVisits'] = [0]
        second.update(id='second', contextKey='other-context', eligibleVisits=list(range(1,len(record['sequence']))))
        profiles.append(second)
        schedule = fixtures.build_schedule(fixture.model, fixture.state, profiles, ['script'])
        record.update(sessions=schedule['sessions'], planning=schedule['planning'], scheduleContract=fixtures.digest(schedule))
        fixtures.write(fixture.record, record)
        fixtures.route.execute('sync', fixture.record, fixture.base)
        fixture.submit(0, fixture.begin(0))
        plan = self.plan()
        self.assertEqual(len(schedule['sessions']), 2)
        self.assertIn(1,[r['fromVisitIndex'] for r in plan['rounds']])
        self.assertEqual(plan['next']['action'], 'close-previous-session')
        self.assertFalse(plan['next']['canBegin'])
        self.assertFalse(any(v['status']=='ready' for v in plan['visits']))
        session = schedule['sessions'][0]
        log = fixture.base/'session.log'
        log.write_text('Fixture driver exited successfully.', encoding='utf-8')
        result = dict(sessionId=session['id'],command=session['command'],cwd=session['cwd'],
                      exitCode=0,startedAt=load_json(fixture.record)['attempts'][0]['run']['startedAt'],
                      finishedAt=fixtures.route.now(),log=fixture.ref(log))
        result_path = fixture.base/'session-result.json'
        fixtures.write(result_path, result)
        fixtures.route.execute('close-session', fixture.record, fixture.base, run=fixture.rel(result_path))
        plan = self.plan()
        self.assertTrue(plan['next']['canBegin'])
        self.assertEqual(plan['next']['visit']['visitIndex'], 1)

    def test_reuse_requires_exact_input_bytes_even_with_preserved_mtime(self):
        fixture = self.workflow
        with patch.object(execution_plan.route,'load_data',wraps=execution_plan.route.load_data) as inspected:
            first = self.plan()
            self.assertEqual(first,self.plan())
            self.assertEqual(inspected.call_count,1)
            view = fixture.cases.with_suffix('.html')
            original = view.read_bytes()
            stamp = view.stat()
            changed = original.replace(b'<',b'>',1)
            self.assertNotEqual(changed,original)
            view.write_bytes(changed)
            os.utime(view,ns=(stamp.st_atime_ns,stamp.st_mtime_ns))
            next_plan = self.plan()
            self.assertEqual(inspected.call_count,2)
            self.assertEqual(next_plan['next']['action'],'sync-projections')
            self.assertFalse(next_plan['next']['canBegin'])

    def test_recorded_submit_recovers_same_visit(self):
        fixture = self.workflow
        token = fixture.begin(0)
        result = fixture.run_file(0)
        with patch.object(fixtures.route, 'sync_views', side_effect=OSError('fixture interrupted')):
            with self.assertRaises(OSError):
                fixtures.route.execute('submit', fixture.record, fixture.base, token=token, run=fixture.rel(result))
        plan = self.plan()
        self.assertFalse(plan['next']['canBegin'])
        self.assertEqual(plan['next']['action'], 'resume-submit')
        self.assertEqual(plan['next']['visit']['visitIndex'], 0)
        self.assertFalse(any(v['status']=='ready' for v in plan['visits']))
        fixtures.route.execute('submit', fixture.record, fixture.base, token=token, run=fixture.rel(result))
        self.assertEqual(self.plan()['next']['visit']['visitIndex'], 1)


if __name__ == '__main__':
    unittest.main()
