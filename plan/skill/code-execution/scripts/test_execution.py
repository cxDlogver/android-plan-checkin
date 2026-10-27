#!/usr/bin/env python3
"""Execution-tool fixture tests. These do not execute or accept the product."""
import argparse
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path
from execution import (execute, inspect, load_json, digest, raw_hash, ready,
                       case_contract, plan_contract, conflict, assertion_evidence, pending_file)
from test_plan import fixture, write
from plan import execute as plan_execute, evaluate, html_text, derive_route
from atomic import derive

TEMP_ROOT = None


class ExecutionContracts(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='code-execution-', dir=TEMP_ROOT)
        self.base = Path(self.temp.name)
        self.model, self.plan, self.path, self.state, self.atomic = fixture(self.base)
        self.assertEqual(plan_execute('build', self.path, self.base)['status'], 'passed')
        self.record_path = self.base/'execution'/'execution.json'
        self.init()

    def tearDown(self):
        self.temp.cleanup()

    def init(self):
        execute('init', self.record_path, self.base,
                self.path.relative_to(self.base).as_posix(),
                (self.path.parent/'task-plan.json').relative_to(self.base).as_posix())
        self.record = load_json(self.record_path)
        self.record['tasks']['P']['resources'] = []

    def save(self):
        write(self.record_path, self.record)

    def ref(self, file):
        return {'path':file.relative_to(self.base).as_posix(), 'sha256':raw_hash(file.read_bytes())}

    def evidence(self, report):
        return dict(form='assertion-report', **self.ref(report), description='实际预期、观察与结论。')

    def add_run(self, rid='one', start=3, indices=None, aspects=('visual','functional')):
        # A real fixture script invokes the fixture function once per planned
        # visit and emits independently compared expected/actual assertions.
        # It exercises this tool's recording protocol, not product behavior.
        (self.base/'source.py').write_text('def save(value):\n    return dict(value)\n', encoding='utf-8')
        self.record['tasks']['P']['implementation'] = {
            'startedAt':'2020-01-01T00:00:00Z','completedAt':'2020-01-01T00:00:01Z'}
        folder = self.base/'execution'/rid
        folder.mkdir(exist_ok=True)
        script = folder/'accept.py'
        report = folder/'assertions.json'
        targets = []
        visits = []
        indices = list(range(len(self.model['coverage']['sequence']))) if indices is None else indices
        for index in indices:
            cid = self.model['coverage']['sequence'][index]
            case = next(c for c in self.model['cases'] if c['id']==cid)
            outcome = case['mocks'][0]['response']['value'] if case['mocks'] else {'visit':index}
            checks = []
            for aspect in aspects:
                targets.append({'target':'case:'+cid+':'+aspect+':0:'+str(index), 'value':outcome})
                checks.append({'aspect':aspect,'checkIndex':0,'status':'passed','actual':'实际保存响应等于已准备响应。','evidence':[]})
            visits.append({'visitIndex':index,'entry':'从允许的草稿入口准备。','givenObserved':'草稿仍未保存。',
                           'operationObserved':'调用真实 fixture 保存入口。','targetObserved':'保存响应符合当前分支。',
                           'outcome':'passed','checks':checks})
        script.write_text('import json,sys\nfrom pathlib import Path\nsys.path.insert(0,'+repr(str(self.base))+')\nfrom source import save\n'
                          +'targets='+repr(targets)+'\nrows=[]\nfor t in targets:\n'
                          +'    expected=t["value"]\n    actual=save(t["value"])\n'
                          +'    rows.append(dict(target=t["target"],expected=expected,actual=actual,verdict="passed" if actual==expected else "failed"))\n'
                          +'rows.append(dict(target="task:P:0",expected=True,actual=all(r["verdict"]=="passed" for r in rows),verdict="passed"))\n'
                          +'Path('+repr(str(report))+').write_text(json.dumps(dict(assertions=rows)),encoding="utf-8")\n', encoding='utf-8')
        # Disable bytecode to leave only intentional fixture files.
        subprocess.run([sys.executable,'-B',str(script)],check=True,cwd=self.base,capture_output=True)
        context = folder/'context.json'
        write(context, {'environment':'runtime','build':'fixture-v1','inputs':targets,'mocks':[], 'readyPrerequisites':[]})
        for visit in visits:
            for result in visit['checks']:
                result['evidence'] = [self.evidence(report)]
        run = {'id':rid,'taskIds':['P'],'script':self.ref(script),'authoredAt':'2020-01-01T00:00:02Z',
               'command':[sys.executable,'-B',str(script)],'cwd':'.',
               'startedAt':'2020-01-01T00:00:'+str(start).zfill(2)+'Z',
               'finishedAt':'2020-01-01T00:00:'+str(start+1).zfill(2)+'Z',
               'exitCode':0,'environment':'runtime','files':[self.ref(self.base/'source.py')],
               'context':self.ref(context),'visits':visits,
               'taskResults':[{'taskId':'P','checkIndex':0,'doneIndices':[0],'status':'passed',
                               'actual':'实现返回与独立输入一致。','evidence':[self.evidence(report)]}]}
        self.record['runs'].append(run)
        self.save()
        return run

    def inspect(self):
        return inspect(self.record, self.base)

    def loop_fixture(self):
        self.record_path.unlink()
        self.state['transitions'][1]['from']='S'
        for tr in self.state['transitions']:
            tr.pop('condition',None)
        self.state['transitions'][0]['operation']['label']='进入'
        self.state['transitions'][1]['operation']['label']='完成'
        back=copy.deepcopy(self.state['transitions'][0]);back.update(id='BACK',**{'from':'S','to':'D'})
        back['operation']['label']='返回';self.state['transitions'].append(back)
        graph=self.path.parent/'state-transitions.json';atomic_path=self.path.parent/'atomic-requirements.json'
        write(graph,self.state);self.atomic=derive(self.state,graph,atomic_path);write(atomic_path,self.atomic)
        template=copy.deepcopy(self.model['cases'][0]);cases=[]
        for tr in self.state['transitions']:
            case=copy.deepcopy(template);case.update(id='TC-'+tr['id'],requirementId='R-'+tr['id'],operation=tr['operation'],mocks=[])
            case['given']['stateId']=tr['from'];case['expected']['stateId']=tr['to'];cases.append(case)
        self.model['cases']=cases
        self.model['stateGraph']['sha256']=digest(self.state);self.model['atomicGraph']['sha256']=digest(self.atomic)
        self.model['edges'],self.model['coverage']=derive_route(self.model,self.state,self.atomic)
        self.plan['tasks'][0]['testCaseIds']=[c['id'] for c in cases]
        self.plan['tasks'][0]['requirementIds']=[c['requirementId'] for c in cases]
        self.plan['testCases']['sha256']=digest(self.model)
        write(self.path,self.model);write(self.path.parent/'task-plan.json',self.plan)
        self.assertEqual(plan_execute('build',self.path,self.base)['status'],'passed')
        self.init()

    def test_noninitial_entry_requires_replay_prefix(self):
        self.loop_fixture()
        index=next(i for i,cid in enumerate(self.model['coverage']['sequence'])
                   if next(c for c in self.model['cases'] if c['id']==cid)['given']['stateId']=='S')
        self.add_run(indices=[index])
        with self.assertRaisesRegex(ValueError,'permitted entry'):
            self.inspect()

    def test_repeated_case_requires_each_route_occurrence(self):
        self.loop_fixture();run=self.add_run()
        cid=next(c for c in self.model['coverage']['sequence'] if self.model['coverage']['sequence'].count(c)>1)
        matching=[v for v in run['visits'] if self.model['coverage']['sequence'][v['visitIndex']]==cid]
        self.assertGreater(len(matching),1)
        matching[-1]['checks']=[];matching[-1]['outcome']='deferred'
        case=next(c for c in self.inspect()['model']['cases'] if c['id']==cid)
        self.assertEqual(case['execution']['status'],'partial')
        self.save();execute('sync',self.record_path,self.base)
        with self.assertRaisesRegex(ValueError,'Unaccepted script'):
            execute('finish',self.record_path,self.base)

    def test_dependency_must_pass_before_dependent_implementation(self):
        run=self.add_run();run['visits']=[]
        plan=copy.deepcopy(self.plan);other=copy.deepcopy(plan['tasks'][0]);other.update(id='B',dependsOn=['P'])
        plan['tasks'].append(other);write(self.path.parent/'task-plan.json',plan)
        self.record['planContract']=plan_contract(plan)
        self.record['tasks']['B']={'implementation':{'startedAt':'2020-01-01T00:00:02Z','completedAt':'2020-01-01T00:00:03Z'},'resources':[]}
        with self.assertRaisesRegex(ValueError,'dependency was not script-accepted'):
            self.inspect()

    def test_conflicting_implementation_intervals_rejected(self):
        run=self.add_run();run['visits']=[]
        plan=copy.deepcopy(self.plan);other=copy.deepcopy(plan['tasks'][0]);other.update(id='B',dependsOn=[])
        plan['tasks'].append(other);write(self.path.parent/'task-plan.json',plan)
        self.record['planContract']=plan_contract(plan)
        self.record['tasks']['B']={'implementation':copy.deepcopy(self.record['tasks']['P']['implementation']),'resources':[]}
        with self.assertRaisesRegex(ValueError,'Concurrent implementation conflicts'):
            self.inspect()

    def test_shared_script_accepts_multiple_cases_and_syncs_all_views(self):
        run=self.add_run()
        self.assertGreater(len(run['visits']),1)
        result=execute('sync',self.record_path,self.base)
        self.assertEqual(set(result['cases'].values()),{'passed'})
        self.assertEqual(result['tasks'],{'P':'passed'})
        self.assertEqual(execute('finish',self.record_path,self.base)['status'],'passed')
        self.assertIn('全部检查与路线访问已通过',self.path.with_suffix('.html').read_text(encoding='utf-8'))
        self.assertIn('任务 通过 1', (self.path.parent/'task-plan.md').read_text(encoding='utf-8'))

    def test_initial_ready_and_not_run(self):
        self.assertEqual(execute('ready',self.record_path,self.base)['batches'],[['P']])
        self.assertEqual(self.inspect()['taskStatuses'],{'P':'planned'})

    def test_existing_record_cannot_be_overwritten(self):
        with self.assertRaisesRegex(ValueError,'already exists'):
            self.init()

    def test_case_contract_cannot_be_changed(self):
        self.model['cases'][0]['expected']['conclusion']='Different outcome'
        write(self.path,self.model)
        with self.assertRaisesRegex(ValueError,'contract changed'):
            self.inspect()

    def test_task_contract_cannot_be_changed(self):
        self.plan['tasks'][0]['done']=['Weaker criterion']
        write(self.path.parent/'task-plan.json',self.plan)
        with self.assertRaisesRegex(ValueError,'contract changed'):
            self.inspect()

    def test_planned_code_prerequisite_preserves_baseline_after_implementation(self):
        self.record_path.unlink()
        self.plan['prerequisites']=[{'id':'CODE','description':'Existing implementation baseline',
          'status':'missing','affects':[], 'resolution':'Implement the declared harness',
          'source':{'path':'../source.py','sha256':raw_hash((self.base/'source.py').read_bytes()),'locator':'L1-L2'}}]
        write(self.path.parent/'task-plan.json',self.plan)
        self.assertEqual(plan_execute('build',self.path,self.base)['status'],'passed')
        self.init();self.add_run()
        self.assertEqual(self.inspect()['taskStatuses']['P'],'passed')

    def test_planned_code_profile_source_preserves_baseline(self):
        self.record_path.unlink()
        self.model['dataProfiles'][0]['fields'].append({'name':'context.activeIdentity',
          'type':'object','mode':'context','resolve':'Use the entered object identity',
          'oracle':'Observe the actual object and unchanged boundary contract',
          'source':{'path':'../source.py','sha256':raw_hash((self.base/'source.py').read_bytes()),'locator':'L1-L2'}})
        write(self.path,self.model)
        self.plan['testCases']['sha256']=digest(self.model)
        write(self.path.parent/'task-plan.json',self.plan)
        self.assertEqual(plan_execute('build',self.path,self.base)['status'],'passed')
        self.init();self.add_run()
        self.assertEqual(self.inspect()['taskStatuses']['P'],'passed')

    def test_unplanned_profile_source_still_checks_current_digest(self):
        self.record_path.unlink()
        source=self.base/'data-contract.md';source.write_text('Stable input boundary',encoding='utf-8')
        self.model['dataProfiles'][0]['fields'].append({'name':'context.extra',
          'type':'object','mode':'context','resolve':'Use the supplied input',
          'oracle':'Read the unchanged input contract',
          'source':{'path':'../data-contract.md','sha256':raw_hash(source.read_bytes()),'locator':'$'}})
        write(self.path,self.model)
        self.plan['testCases']['sha256']=digest(self.model)
        write(self.path.parent/'task-plan.json',self.plan)
        self.assertEqual(plan_execute('build',self.path,self.base)['status'],'passed')
        self.init();self.add_run();source.write_text('Changed contract',encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'Stale source'):
            self.inspect()

    def test_source_drift_rejected(self):
        (self.base/'prd.md').write_text('different',encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'requirements failed'):
            self.inspect()

    def test_acceptance_script_cannot_precede_implementation(self):
        run=self.add_run();run['authoredAt']='2019-01-01T00:00:00Z'
        with self.assertRaisesRegex(ValueError,'after implementation'):
            self.inspect()

    def test_snapshot_missing_planned_file_rejected(self):
        run=self.add_run();run['files']=[run['script']]
        with self.assertRaisesRegex(ValueError,'missing planned code'):
            self.inspect()

    def test_changed_code_makes_results_stale(self):
        self.add_run();(self.base/'source.py').write_text('changed',encoding='utf-8')
        data=self.inspect()
        self.assertEqual(data['taskStatuses']['P'],'stale')
        self.assertEqual({c['execution']['status'] for c in data['model']['cases']},{'stale'})
        self.save();execute('sync',self.record_path,self.base)
        with self.assertRaisesRegex(ValueError,'lack passing'):
            execute('finish',self.record_path,self.base)

    def test_changed_script_makes_results_stale(self):
        run=self.add_run();(self.base/run['script']['path']).write_text('changed',encoding='utf-8')
        self.assertEqual(self.inspect()['taskStatuses']['P'],'stale')

    def test_missing_evidence_cannot_pass(self):
        run=self.add_run();(self.base/run['visits'][0]['checks'][0]['evidence'][0]['path']).unlink()
        self.assertEqual(self.inspect()['model']['cases'][0]['execution']['status'],'stale')

    def test_exit_code_zero_does_not_replace_required_evidence(self):
        run=self.add_run();run['visits'][0]['checks'][0]['evidence']=[]
        with self.assertRaisesRegex(ValueError,'evidence'):
            self.inspect()

    def test_report_needs_matching_assertion_target(self):
        run=self.add_run();e=run['visits'][0]['checks'][0]['evidence'][0]
        report=self.base/e['path'];write(report,{'assertions':[]})
        for visit in run['visits']:
            for result in visit['checks']:result['evidence'][0].update(self.ref(report))
        run['taskResults'][0]['evidence'][0].update(self.ref(report))
        with self.assertRaisesRegex(ValueError,'no matching assertion'):
            self.inspect()

    def test_report_expected_actual_required(self):
        run=self.add_run();ref=run['visits'][0]['checks'][0]['evidence'][0]
        report=self.base/ref['path'];data=load_json(report);del data['assertions'][0]['actual'];write(report,data)
        for visit in run['visits']:
            for result in visit['checks']:result['evidence'][0].update(self.ref(report))
        run['taskResults'][0]['evidence'][0].update(self.ref(report))
        with self.assertRaisesRegex(ValueError,'expected/actual'):
            self.inspect()

    def test_browser_result_rejected(self):
        run=self.add_run();run['environment']='browser'
        with self.assertRaises(ValueError):self.inspect()

    def test_mixed_case_never_passes_browser_check(self):
        # A planning-compatible new fixture is initialized before implementation.
        self.record_path.unlink()
        self.model['cases'][0]['acceptance']['visual']['checks'][0].update(testType='browser',environment='browser')
        self.plan['testCases']['sha256']=digest(self.model)
        write(self.path,self.model);write(self.path.parent/'task-plan.json',self.plan)
        self.assertEqual(plan_execute('build',self.path,self.base)['status'],'passed')
        self.init();run=self.add_run()
        for visit in run['visits']:
            if self.model['coverage']['sequence'][visit['visitIndex']] == self.model['cases'][0]['id']:
                visit['checks']=[r for r in visit['checks'] if r['aspect']!='visual']
        statuses={c['id']:c['execution']['status'] for c in self.inspect()['model']['cases']}
        self.assertEqual(statuses[self.model['cases'][0]['id']],'partial')
        self.save();execute('sync',self.record_path,self.base)
        final=execute('finish',self.record_path,self.base)
        self.assertEqual(final['browserPending'],[self.model['cases'][0]['id']])
        self.assertEqual(final['status'],'passed')

    def test_missing_one_check_is_partial(self):
        self.add_run(aspects=('functional',))
        self.assertEqual({c['execution']['status'] for c in self.inspect()['model']['cases']},{'partial'})

    def test_partial_task_done_coverage_is_not_passed(self):
        run=self.add_run();run['taskResults'][0]['doneIndices']=[]
        self.assertEqual(self.inspect()['taskStatuses']['P'],'partial')

    def test_nonzero_exit_cannot_pass(self):
        run=self.add_run();run['exitCode']=1
        self.assertEqual(self.inspect()['taskStatuses']['P'],'failed')
        self.assertEqual({c['execution']['status'] for c in self.inspect()['model']['cases']},{'failed'})

    def test_failed_predecessor_stops_route(self):
        run=self.add_run();run['visits'][0]['outcome']='failed';run['exitCode']=1
        with self.assertRaisesRegex(ValueError,'continue after'):
            self.inspect()

    def test_new_failure_does_not_leave_old_case_passed(self):
        self.add_run();run=self.add_run('retry',start=5,indices=[0]);run['visits'][0]['outcome']='failed'
        result=run['visits'][0]['checks'][0];result['status']='failed';result['actual']='实际响应与预期不同。'
        report=self.base/result['evidence'][0]['path'];data=load_json(report)
        data['assertions'][0].update(actual='unexpected',verdict='failed');write(report,data)
        for r in run['visits'][0]['checks']+run['taskResults']:
            r['evidence'][0].update(self.ref(report))
        self.assertEqual(self.inspect()['model']['cases'][0]['execution']['status'],'failed')

    def test_failed_visit_requires_assertion_evidence(self):
        run=self.add_run(indices=[0]);run['visits'][0]['outcome']='failed';run['visits'][0]['checks']=[]
        with self.assertRaisesRegex(ValueError,'failing check report'):
            self.inspect()

    def test_deferred_visit_cannot_claim_checks_passed(self):
        run=self.add_run(indices=[0]);run['visits'][0]['outcome']='deferred'
        with self.assertRaisesRegex(ValueError,'deferred visit'):
            self.inspect()

    def test_unknown_visit_rejected(self):
        run=self.add_run();run['visits'][0]['visitIndex']=100
        with self.assertRaisesRegex(ValueError,'outside route'):
            self.inspect()

    def test_duplicate_check_rejected(self):
        run=self.add_run();run['visits'][0]['checks'].append(copy.deepcopy(run['visits'][0]['checks'][0]))
        with self.assertRaisesRegex(ValueError,'duplicate visit/check'):
            self.inspect()

    def test_duplicate_run_rejected(self):
        self.add_run();self.record['runs'].append(copy.deepcopy(self.record['runs'][0]))
        with self.assertRaisesRegex(ValueError,'Duplicate run'):
            self.inspect()

    def test_overlapping_run_rejected(self):
        self.add_run();self.add_run('two',start=3)
        with self.assertRaisesRegex(ValueError,'resource conflict'):
            self.inspect()

    def test_workspace_escape_rejected(self):
        run=self.add_run();run['script']['path']='../outside.py'
        with self.assertRaises(ValueError):self.inspect()

    def test_html_and_json_must_sync_after_each_run(self):
        self.add_run()
        with self.assertRaisesRegex(ValueError,'Stale execution projection'):
            execute('check',self.record_path,self.base)
        execute('sync',self.record_path,self.base)
        self.assertEqual(execute('check',self.record_path,self.base)['status'],'passed')
        self.path.with_suffix('.html').write_text('stale',encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'Stale execution projection'):
            execute('check',self.record_path,self.base)
        execute('sync',self.record_path,self.base)
        self.assertEqual(execute('check',self.record_path,self.base)['status'],'passed')

    def pending_run(self, run):
        # The adapter has emitted a run, but has not appended it to the ledger.
        self.record['runs'].remove(run)
        self.save()
        file = self.base/'execution'/'run-input.json'
        write(file, run)
        return file.relative_to(self.base).as_posix()

    def test_ready_refuses_unsynchronized_batch_results(self):
        self.add_run()
        with self.assertRaisesRegex(ValueError, 'Stale execution projection'):
            execute('ready', self.record_path, self.base)
        execute('sync', self.record_path, self.base)
        self.assertEqual(execute('ready', self.record_path, self.base)['batches'], [])

    def test_submit_records_case_checks_and_closes_all_views(self):
        file = self.pending_run(self.add_run())
        result = execute('submit', self.record_path, self.base, run=file)
        self.assertEqual(result['status'], 'passed')
        self.assertTrue(result['recorded'] and result['synced'] and result['checked'])
        self.assertEqual(set(load_json(self.path)['cases'][0]['execution']), {'status','actual','evidence','checks'})
        self.assertEqual(execute('finish', self.record_path, self.base)['status'], 'passed')

    def test_case_submit_cannot_use_only_local_task_results(self):
        run = self.add_run()
        run['visits'] = []
        file = self.pending_run(run)
        with self.assertRaisesRegex(ValueError, 'per-visit Test Case results'):
            execute('submit', self.record_path, self.base, run=file)
        self.assertEqual(load_json(self.record_path)['runs'], [])
        result = execute('submit', self.record_path, self.base, run=file, local_only=True)
        self.assertEqual(result['scope'], 'local-batch')
        self.assertEqual(result['caseCounts'], {'not_run':len(self.model['cases'])})

    def test_submit_rejects_environment_mapping_without_mutating_ledger(self):
        run = self.add_run()
        run['environment'] = 'native'
        context = self.base/run['context']['path']
        value = load_json(context)
        value.update(environment='native', host='contract-fixture-only')
        write(context, value)
        run['context'] = self.ref(context)
        file = self.pending_run(run)
        old_views = {p:p.read_bytes() for p in (self.path, self.path.with_suffix('.html'))}
        with self.assertRaisesRegex(ValueError, 'check environment mismatch'):
            execute('submit', self.record_path, self.base, run=file)
        self.assertEqual(load_json(self.record_path)['runs'], [])
        self.assertTrue(all(p.read_bytes() == content for p,content in old_views.items()))

    def test_submit_failure_is_synchronized_but_cannot_report_batch_passed(self):
        run = self.add_run()
        run['exitCode'] = 1
        file = self.pending_run(run)
        result = execute('submit', self.record_path, self.base, run=file)
        self.assertEqual(result['status'], 'failed')
        self.assertTrue(result['recorded'] and result['synced'])
        self.assertEqual(execute('check', self.record_path, self.base)['status'], 'passed')
        self.assertEqual({c['execution']['status'] for c in load_json(self.path)['cases']}, {'failed'})

    def test_submit_partial_checks_preserve_partial_case_status(self):
        file = self.pending_run(self.add_run(aspects=('functional',)))
        result = execute('submit', self.record_path, self.base, run=file)
        self.assertEqual(result['status'], 'passed')
        self.assertEqual(result['caseCounts'], {'partial':len(self.model['cases'])})
        with self.assertRaisesRegex(ValueError, 'Unaccepted script check'):
            execute('finish', self.record_path, self.base)

    def test_submit_stale_evidence_records_stale_and_returns_failure(self):
        file = self.pending_run(self.add_run())
        (self.base/'source.py').write_text('changed', encoding='utf-8')
        result = execute('submit', self.record_path, self.base, run=file)
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['caseCounts'], {'stale':len(self.model['cases'])})

    def test_interrupted_submit_can_resume_without_duplicate_run(self):
        file = self.pending_run(self.add_run())
        import execution
        replace = execution.os.replace
        def interrupted(source, target):
            if target == self.path.with_suffix('.html'):
                raise OSError('fixture interruption after ledger commit')
            return replace(source, target)
        with patch('execution.os.replace', side_effect=interrupted):
            with self.assertRaisesRegex(OSError, 'fixture interruption'):
                execute('submit', self.record_path, self.base, run=file)
        self.assertEqual(len(load_json(self.record_path)['runs']), 1)
        with self.assertRaisesRegex(ValueError, 'Stale execution projection'):
            execute('ready', self.record_path, self.base)
        self.assertEqual(execute('submit', self.record_path, self.base, run=file)['status'], 'passed')
        self.assertEqual(len(load_json(self.record_path)['runs']), 1)

    def test_same_run_identity_cannot_replace_existing_evidence(self):
        file = self.pending_run(self.add_run())
        execute('submit', self.record_path, self.base, run=file)
        value = load_json(self.base/file)
        value['visits'][0]['targetObserved'] = 'rewritten observation'
        write(self.base/file, value)
        with self.assertRaisesRegex(ValueError, 'immutable evidence'):
            execute('submit', self.record_path, self.base, run=file)

    def test_finish_rejects_stale_visit_even_if_old_checks_passed(self):
        self.add_run()
        run = self.add_run('entry-retry', start=5, indices=[0])
        run['taskResults'] = []
        run['visits'][0].update(checks=[], outcome='deferred')
        (self.base/run['script']['path']).write_text('changed', encoding='utf-8')
        self.save()
        result = execute('sync', self.record_path, self.base)
        self.assertEqual(result['tasks']['P'], 'passed')
        self.assertEqual(result['cases'][self.model['coverage']['sequence'][0]], 'stale')
        with self.assertRaisesRegex(ValueError, 'Unaccepted'):
            execute('finish', self.record_path, self.base)

    def test_submit_cli_returns_nonzero_after_recording_failed_batch(self):
        run = self.add_run()
        run['exitCode'] = 1
        file = self.pending_run(run)
        import execution
        result = subprocess.run([sys.executable, '-B', execution.__file__, 'submit', str(self.record_path),
                                 '--workspace', str(self.base), '--run', file], capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertTrue(json.loads(result.stdout)['recorded'])
        self.assertEqual(load_json(self.path)['cases'][0]['execution']['status'], 'failed')

    def test_submit_obeys_the_same_single_writer_lock(self):
        file = self.pending_run(self.add_run())
        lock = self.record_path.with_suffix('.lock')
        lock.write_text('another-writer', encoding='utf-8')
        with self.assertRaises(FileExistsError):
            execute('submit', self.record_path, self.base, run=file)
        self.assertEqual(load_json(self.record_path)['runs'], [])
        self.assertEqual(lock.read_text(encoding='utf-8'), 'another-writer')

    def test_pending_batch_blocks_readiness_even_without_a_registered_run(self):
        marker = pending_file(self.record_path, 'unfinished')
        write(marker, {'runId':'unfinished', 'evidencePath':'execution/unfinished'})
        with self.assertRaisesRegex(ValueError, 'Unclosed acceptance batch'):
            execute('ready', self.record_path, self.base)

    def test_pending_batch_blocks_finish_even_with_old_passing_results(self):
        self.add_run()
        execute('sync', self.record_path, self.base)
        write(pending_file(self.record_path, 'unfinished'), {'runId':'unfinished'})
        with self.assertRaisesRegex(ValueError, 'Unclosed acceptance batch'):
            execute('finish', self.record_path, self.base)

    def test_successful_submission_closes_only_its_own_pending_marker(self):
        run = self.add_run()
        own, other = pending_file(self.record_path, run['id']), pending_file(self.record_path, 'other')
        write(own, {'runId':run['id']})
        write(other, {'runId':'other'})
        file = self.pending_run(run)
        self.assertEqual(execute('submit', self.record_path, self.base, run=file)['status'], 'passed')
        self.assertFalse(own.exists())
        self.assertTrue(other.exists())

    def test_rejected_submission_preserves_pending_marker(self):
        run = self.add_run()
        run['visits'] = []
        marker = pending_file(self.record_path, run['id'])
        write(marker, {'runId':run['id']})
        file = self.pending_run(run)
        with self.assertRaisesRegex(ValueError, 'per-visit Test Case results'):
            execute('submit', self.record_path, self.base, run=file)
        self.assertTrue(marker.exists())

    def test_planning_builder_refuses_execution_results(self):
        self.add_run();self.save();execute('sync',self.record_path,self.base)
        self.assertEqual(plan_execute('build',self.path,self.base)['status'],'failed')
        self.assertEqual(execute('check',self.record_path,self.base)['status'],'passed')

    def test_lock_prevents_two_status_writers(self):
        self.add_run();self.record_path.with_suffix('.lock').write_text('other-writer',encoding='utf-8')
        with self.assertRaises(FileExistsError):execute('sync',self.record_path,self.base)
        self.assertTrue(self.record_path.with_suffix('.lock').exists())

    def test_ready_batches_respect_dependencies_files_and_resources(self):
        p=copy.deepcopy(self.plan)
        a=p['tasks'][0];a['id']='A'
        b=copy.deepcopy(a);b.update(id='B',dependsOn=[]);b['files'][0]['path']='../other.py'
        c=copy.deepcopy(a);c.update(id='C',dependsOn=['A'])
        p['tasks']=[a,b,c]
        records={tid:{'implementation':None,'resources':[]} for tid in ('A','B','C')}
        data={'plan':p,'planPath':self.path.parent/'task-plan.json','taskStatuses':{'A':'planned','B':'planned','C':'planned'}}
        rec={'tasks':records}
        self.assertEqual(ready(data,rec,self.base),[['A','B']])
        b['files'][0]['path']=a['files'][0]['path']
        self.assertEqual(ready(data,rec,self.base),[['A'],['B']])
        b['files'][0]['path']='../other.py';records['A']['resources']=['device'];records['B']['resources']=['device']
        self.assertEqual(ready(data,rec,self.base),[['A'],['B']])
        data['taskStatuses']['A']='passed'
        self.assertEqual(ready(data,rec,self.base),[['B','C']])


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--temp-root',type=Path);args=parser.parse_args()
    TEMP_ROOT=args.temp_root
    unittest.main(argv=[sys.argv[0]])
