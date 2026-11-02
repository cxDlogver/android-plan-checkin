#!/usr/bin/env python3
"""Planning contract counterexamples and read-only rendering tests; no product acceptance."""
import argparse
import copy
import json
import tempfile
import unittest
from pathlib import Path
from plan import evaluate, derive_route, execute, digest, raw_hash, html_text
from atomic import derive
from test_analyze import model_fixture

TEMP_ROOT=None

def write(file,value): file.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def fixture(base):
    state,graph=model_fixture(base);atomic_path=graph.parent/'atomic-requirements.json';atomic=derive(state,graph,atomic_path);write(atomic_path,atomic)
    source={'path':'../prd.md','sha256':raw_hash((base/'prd.md').read_bytes()),'locator':'L1'}
    profile={'id':'data','scope':'route','preparation':'从正式草稿入口捕获测试对象。','continuity':'同一对象沿用；起点重入才重建。','fields':[{'name':'title','type':'string','mode':'literal','value':'阅读','source':source}]}
    cases=[]
    for req in atomic['requirements']:
        t=next(t for t in state['transitions'] if t['id']==req['transitionId'])
        cases.append({'id':'TC-'+t['id'],'title':'保存分支 '+t['id'],'kind':'primary','requirementId':req['id'],'given':{'stateId':t['from'],'setup':'正式草稿入口准备独立内存对象。','verify':'读取草稿状态及标题。'},'operation':copy.deepcopy(t['operation']),'expected':{'stateId':t['to'],'conclusion':'查询目标状态事实及效果。'},'dataProfileId':'data','mocks':[{'boundary':'save-result','purpose':'替换外部结果，不替换保存处理。','trigger':'保存动作触发一次。','lifetime':'当前访问。','response':{'mode':'literal','value':copy.deepcopy(t['condition']['sampleOutcome'])},'verification':'参数等于当前草稿，按结果核对终态。','restore':'访问后移除。'}],'acceptance':{name:{'applicable':True,'reason':'本例需要核对相应事实。','checks':[{'testType':'script','environment':'runtime','criterion':'目标状态事实。','oracle':'正式迁移及捕获输入独立求预期。','procedure':'触发真实保存，读取目标状态。','evidence':[{'form':'assertion-report','description':'输入、独立预期及实际结果。'}],'sufficiency':'覆盖本组事实的状态变化。'}]} for name in ('visual','functional')},'constraintIds':[],'impactId':None,'execution':{'status':'not_run','actual':None,'evidence':[]}})
    model={'schemaVersion':'1.0.0','title':'通用规划夹具','revision':1,'stateGraph':{'path':'state-transitions.json','sha256':digest(state)},'atomicGraph':{'path':'atomic-requirements.json','sha256':digest(atomic)},'inputs':[dict(id='PRD',role='需求',**source)],'dataProfiles':[profile],'cases':cases,'edges':[],'coverage':{}}
    model['edges'],model['coverage']=derive_route(model,state,atomic)
    code=base/'source.py';code.write_text('def save(value):\n    return value\n',encoding='utf-8')
    evidence={'id':'C','path':'../source.py','sha256':raw_hash(code.read_bytes()),'locator':'L1-L2','excerpt':'def save(value):','role':'现有保存入口。'}
    ids=[c['id'] for c in cases]
    task={'id':'P','title':'实现明确保存结果','goal':'按需求处理保存结果。','dependsOn':[],'files':[{'path':'../source.py','change':'modify','purpose':'修改消费者。','evidenceIds':['C']}],'steps':['保留入口，处理对应结果。'],'testCaseIds':ids,'requirementIds':[r['id'] for r in atomic['requirements']],'done':['对应集成结果满足事实。'],'checks':[{'command':'python -m unittest tests','requires':[],'status':'not_run'}],'status':'planned'}
    plan={'schemaVersion':'1.0.0','title':'文件级实施计划','revision':1,'testCases':{'path':'test-cases.json','sha256':digest(model)},'codeEvidence':[evidence],'impacts':[],'prerequisites':[],'tasks':[task]}
    path=graph.parent/'test-cases.json';write(path,model);write(path.parent/'task-plan.json',plan)
    return model,plan,path,state,atomic

class PlanningContracts(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='task-plan-',dir=TEMP_ROOT);self.base=Path(self.temp.name)
        self.model,self.plan,self.path,self.state,self.atomic=fixture(self.base)
    def tearDown(self): self.temp.cleanup()
    def save(self):
        self.plan['testCases']['sha256']=digest(self.model);write(self.path,self.model);write(self.path.parent/'task-plan.json',self.plan)
    def report(self,views=False): self.save();return evaluate(self.model,self.path,self.base,with_views=views)
    def gate(self,name): return next(c for c in self.report()['checks'] if c['id']==name)['status']
    def add_independent(self,kind='constraint'):
        c=copy.deepcopy(self.model['cases'][0]);c.update(id='TC-AUX',kind=kind,requirementId=None,impactId='I' if kind=='regression' else None);c['given']['stateId']=None;c['expected']['stateId']=None
        c['dataProfileId']='fixture';c['mocks']=[]
        p=copy.deepcopy(self.model['dataProfiles'][0]);p.update(id='fixture',scope='case');self.model['dataProfiles'].append(p)
        if kind=='constraint':
            self.state['constraints']=[{'id':'G','statement':'显示和查询结果与输入一致。','source':copy.deepcopy(self.state['transitions'][0]['source'])}];c['constraintIds']=['G']
            write(self.path.parent/'state-transitions.json',self.state);self.atomic=derive(self.state,self.path.parent/'state-transitions.json',self.path.parent/'atomic-requirements.json');write(self.path.parent/'atomic-requirements.json',self.atomic)
            self.model['stateGraph']['sha256']=digest(self.state);self.model['atomicGraph']['sha256']=digest(self.atomic)
        else:
            self.plan['impacts']=[{'id':'I','behavior':'旧入口事件透传。','codeEvidenceIds':['C'],'changedFiles':['../source.py'],'mechanism':'提取消费者时事件参数可能丢失。','exposure':'带唯一标题保存。','decision':'regression','testCaseIds':['TC-AUX'],'reason':'主分支未覆盖旧回调参数。'}]
        self.model['cases'].append(c);self.plan['tasks'][0]['testCaseIds'].append(c['id']);self.model['edges'],self.model['coverage']=derive_route(self.model,self.state,self.atomic)
    def test_valid_planning_passes_without_product_execution(self):
        self.assertEqual(self.report()['status'],'passed');self.assertTrue(all(c['execution']['status']=='not_run' for c in self.model['cases']))
    def test_script_acceptance_does_not_require_browser(self):
        for c in self.model['cases']:
            for group in c['acceptance'].values(): group['checks'][0]['testType']='script'
        self.assertEqual(self.gate('acceptance'),'passed')
    def test_each_case_declares_both_acceptance_aspects(self):
        del self.model['cases'][0]['acceptance']['functional'];self.assertEqual(self.gate('schema'),'failed')
    def test_required_visual_or_functional_facts_cannot_be_marked_inapplicable(self):
        original=copy.deepcopy(self.model)
        for name in ('visual','functional'):
            self.model=copy.deepcopy(original);self.model['cases'][0]['acceptance'][name].update(applicable=False,checks=[])
            self.assertEqual(self.gate('acceptance'),'failed')
    def test_applicability_must_agree_with_checks(self):
        self.model['cases'][0]['acceptance']['visual']['checks']=[];self.assertEqual(self.gate('acceptance'),'failed')
    def test_inapplicable_aspect_needs_a_reason(self):
        group=self.model['cases'][0]['acceptance']['visual'];group.update(applicable=False,reason='',checks=[]);self.assertEqual(self.gate('schema'),'failed')
    def test_unknown_test_type_or_evidence_form_is_rejected(self):
        check=self.model['cases'][0]['acceptance']['visual']['checks'][0];check['testType']='native-ui';self.assertEqual(self.gate('schema'),'failed')
        check['testType']='script';check['evidence'][0]['form']='screenshot-or-DOM';self.assertEqual(self.gate('schema'),'failed')
    def test_only_script_and_browser_are_valid_acceptance_types(self):
        check=self.model['cases'][0]['acceptance']['visual']['checks'][0]
        for value in ('unit','integration','native-ui','manual'):
            check['testType']=value;self.assertEqual(self.gate('schema'),'failed')
        check['testType']='script';self.assertEqual(self.gate('schema'),'passed')
    def test_real_browser_checks_are_not_script_acceptance(self):
        check=self.model['cases'][0]['acceptance']['visual']['checks'][0];check.update(testType='script',environment='browser')
        self.assertEqual(self.gate('acceptance'),'failed');check['testType']='browser';self.assertEqual(self.gate('acceptance'),'passed')
    def test_bound_ui_image_must_exist(self):
        (self.base/'design.png').unlink();self.assertEqual(self.gate('inputs'),'failed')
    def test_browser_tests_need_browser_environment(self):
        check=self.model['cases'][0]['acceptance']['visual']['checks'][0];check['testType']='browser';self.assertEqual(self.gate('acceptance'),'failed')
        check['environment']='browser';self.assertEqual(self.gate('acceptance'),'passed')
    def test_evidence_must_match_actual_host(self):
        check=self.model['cases'][0]['acceptance']['visual']['checks'][0]
        for form in ('screenshot','dom','native-tree','layout-measurement'):
            check['evidence']=[{'form':'assertion-report','description':'结果对照。'},{'form':form,'description':'实际宿主观察。'}]
            self.assertEqual(self.gate('acceptance'),'failed')
        check['environment']='native';self.assertEqual(self.gate('acceptance'),'passed')
        check['evidence'][1]['form']='dom';self.assertEqual(self.gate('acceptance'),'failed')
    def test_screenshot_alone_does_not_prove_a_functional_result(self):
        check=self.model['cases'][0]['acceptance']['functional']['checks'][0];check.update(environment='browser',evidence=[{'form':'screenshot','description':'只显示成功提示。'}]);self.assertEqual(self.gate('acceptance'),'failed')
    def test_native_rendering_uses_script_acceptance_without_browser(self):
        check=self.model['cases'][0]['acceptance']['visual']['checks'][0];check.update(environment='native',evidence=[{'form':'screenshot','description':'实际原生界面。'},{'form':'native-tree','description':'实际原生节点。'},{'form':'assertion-report','description':'预期与实际对照。'}]);self.assertEqual(self.gate('acceptance'),'passed')
    def test_missing_duplicate_or_wrong_primary_mapping(self):
        for change in ('missing','duplicate','wrong'):
            with self.subTest(change=change):
                original=copy.deepcopy(self.model)
                if change=='missing': self.model['cases'].pop()
                elif change=='duplicate': self.model['cases'].append(copy.deepcopy(self.model['cases'][0]))
                else: self.model['cases'][0]['requirementId']='unknown'
                self.assertEqual(self.gate('one-to-one'),'failed');self.model=original
    def test_changed_given_operation_or_then_is_rejected(self):
        original=copy.deepcopy(self.model)
        for key in ('given','expected','operation'):
            self.model=copy.deepcopy(original)
            if key=='operation':self.model['cases'][0][key]['label']='直接设置终态'
            else:self.model['cases'][0][key]['stateId']='unknown'
            self.assertEqual(self.gate('one-to-one'),'failed')
    def test_real_branch_needs_matching_result(self):
        self.model['cases'][0]['mocks']=[];self.assertEqual(self.gate('data-mock'),'failed')
    def test_wrong_fixed_branch_response_rejected(self):
        self.model['cases'][0]['mocks'][0]['response']['value']={'outcome':{'status':'unknown'}};self.assertEqual(self.gate('data-mock'),'failed')
    def test_context_response_uses_branch_witness_without_freezing_payload(self):
        m=self.model['cases'][0]['mocks'][0];m['matches']=copy.deepcopy(m['response']['value']);m['response']={'mode':'context','resolve':'从当前请求对象构建响应，状态从结果控制端口选定。','oracle':'对象ID必须来自当前草稿，分支枚举命中条件。'}
        self.assertEqual(self.gate('data-mock'),'passed');m['response']['value']={'id':'fixed'};self.assertEqual(self.gate('data-mock'),'failed')
    def test_context_data_forbids_a_fixed_value(self):
        self.model['dataProfiles'][0]['fields'][0].update(mode='context',resolve='ctx.title',oracle='原输入标题');self.assertEqual(self.gate('data-mock'),'failed')
    def test_context_data_requires_independent_oracle(self):
        f=self.model['dataProfiles'][0]['fields'][0];f.pop('value');f.update(mode='context',resolve='ctx.title');self.assertEqual(self.gate('data-mock'),'failed')
    def test_fixed_data_type_and_duplicate_fields_rejected(self):
        f=self.model['dataProfiles'][0]['fields'][0];f['type']='integer';f['value']=True;self.assertEqual(self.gate('data-mock'),'failed')
        f['type']='string';f['value']='sample';self.model['dataProfiles'][0]['fields'].append(copy.deepcopy(f));self.assertEqual(self.gate('data-mock'),'failed')
    def test_missing_data_source_locator_rejected(self):
        self.model['dataProfiles'][0]['fields'][0]['source']['locator']='L999';self.assertEqual(self.gate('data-mock'),'failed')
    def test_primary_data_profile_reference_must_exist(self):
        self.model['cases'][0]['dataProfileId']='absent';self.assertEqual(self.gate('data-mock'),'failed')
    def test_independent_check_needs_isolated_data(self):
        self.add_independent();self.model['cases'][-1]['dataProfileId']='data';self.assertEqual(self.gate('data-mock'),'failed')
    def test_global_rule_coverage_is_complete(self):
        self.add_independent();self.assertEqual(self.report()['status'],'passed');self.model['cases'][-1]['constraintIds']=[];self.assertEqual(self.gate('acceptance'),'failed')
    def test_independent_case_cannot_impersonate_a_business_state(self):
        self.add_independent();self.model['cases'][-1]['given']['stateId']='D';self.assertEqual(self.gate('one-to-one'),'failed')
    def test_direct_regression_has_reciprocal_impact_mapping(self):
        self.add_independent('regression');self.assertEqual(self.report()['status'],'passed');self.plan['impacts'][0]['testCaseIds']=[];self.assertEqual(self.gate('regression'),'failed')
    def test_unaffected_module_does_not_add_regression(self):
        self.add_independent('regression');self.plan['impacts'][0]['decision']='unaffected';self.assertEqual(self.gate('regression'),'failed')
    def test_regression_cannot_reference_an_unmodified_chain(self):
        self.add_independent('regression');self.plan['impacts'][0]['changedFiles']=['../unmodified.py'];self.assertEqual(self.gate('regression'),'failed')
    def test_source_hash_drift_rejected(self):
        self.model['inputs'][0]['sha256']='0'*64;self.assertEqual(self.gate('inputs'),'failed')
    def test_upstream_digest_drift_rejected(self):
        self.model['atomicGraph']['sha256']='0'*64;self.assertEqual(self.gate('inputs'),'failed')
    def test_task_plan_digest_drift_rejected(self):
        self.save();self.plan['testCases']['sha256']='0'*64;write(self.path.parent/'task-plan.json',self.plan)
        self.assertEqual(evaluate(self.model,self.path,self.base)['status'],'failed')
    def test_code_hash_and_excerpt_are_checked(self):
        self.plan['codeEvidence'][0]['excerpt']='invented function';self.assertEqual(self.gate('code-task'),'failed')
        self.plan['codeEvidence'][0]['excerpt']='def save(value):';(self.base/'source.py').write_text('changed',encoding='utf-8');self.assertEqual(self.gate('code-task'),'failed')
    def test_task_dependencies_cannot_cycle(self):
        t=copy.deepcopy(self.plan['tasks'][0]);t['id']='P2';t['dependsOn']=['P'];self.plan['tasks'][0]['dependsOn']=['P2'];self.plan['tasks'].append(t);self.assertEqual(self.gate('code-task'),'failed')
    def test_task_mapping_is_closed(self):
        self.plan['tasks'][0]['testCaseIds'].pop();self.assertEqual(self.gate('code-task'),'failed')
    def test_new_file_cannot_claim_existing_source(self):
        self.plan['tasks'][0]['files'][0]['change']='create';self.assertEqual(self.gate('code-task'),'failed')
    def test_existing_file_requires_direct_same_file_evidence(self):
        self.plan['tasks'][0]['files'][0]['evidenceIds']=[];self.assertEqual(self.gate('code-task'),'failed')
    def test_file_scope_cannot_escape_workspace(self):
        self.plan['tasks'][0]['files'][0]['path']='../../escape.py';self.assertEqual(self.gate('code-task'),'failed')
    def test_unknown_prerequisite_case_rejected(self):
        self.plan['prerequisites']=[{'id':'RESOURCE','description':'资源缺失','status':'missing','affects':['missing-case'],'resolution':'取得资源与摘要。','source':copy.deepcopy(self.model['dataProfiles'][0]['fields'][0]['source'])}];self.assertEqual(self.gate('code-task'),'failed')
    def test_route_has_exact_lower_bound_with_isolated_case(self):
        self.add_independent();self.assertEqual(self.model['coverage']['minimumVisitCount'],self.atomic['coverage']['minimumVisitCount']+1);self.assertEqual(self.gate('route'),'passed')
        self.assertEqual(self.model['edges'][-1]['kind'],'restart');self.assertTrue(all('viaStateId' not in e for e in self.model['edges']))
    def test_projection_uses_distinct_state_and_fixture_namespaces(self):
        self.add_independent();from plan import endpoints
        requirements={r['id']:r for r in self.atomic['requirements']};transitions={t['id']:t for t in self.state['transitions']};states={s['id']:s for s in self.state['states']}
        ends=[endpoints(c,transitions,requirements,states) for c in self.model['cases']]
        self.assertEqual(ends[0][0][0],'state');self.assertEqual(ends[-1][0][0],'fixture');self.assertNotEqual(ends[0][0],ends[-1][0])
    def test_extra_route_edges_and_false_minimum_rejected(self):
        self.model['edges'].append({'id':'unused','from':self.model['cases'][0]['id'],'to':self.model['cases'][0]['id'],'kind':'restart'});self.assertEqual(self.gate('route'),'failed')
        self.model['edges'].pop();self.model['coverage']['minimumVisitCount']-=1;self.assertEqual(self.gate('route'),'failed')
    def test_illegal_primary_shortcut_rejected(self):
        self.model['coverage']['sequence'].reverse();self.assertEqual(self.gate('route'),'failed')
    def test_not_run_cannot_contain_observed_results(self):
        self.model['cases'][0]['execution']['actual']='passed';self.assertEqual(self.gate('schema'),'failed')
    def test_build_and_check_preserve_inputs_and_detect_stale_views(self):
        self.save();before=(self.path.parent/'state-transitions.json').read_bytes();self.assertEqual(execute('build',self.path,self.base)['status'],'passed');self.assertEqual((self.path.parent/'state-transitions.json').read_bytes(),before)
        saved={p:p.read_bytes() for p in self.path.parent.iterdir()};self.assertEqual(execute('check',self.path,self.base)['status'],'passed');self.assertTrue(all(p.read_bytes()==raw for p,raw in saved.items()))
        self.path.with_suffix('.html').write_text('obsolete viewer',encoding='utf-8');self.assertEqual(execute('check',self.path,self.base)['status'],'failed')
    def test_build_failure_preserves_previous_final_outputs(self):
        self.save();self.assertEqual(execute('build',self.path,self.base)['status'],'passed');plan_path=self.path.parent/'task-plan.json';p=json.loads(plan_path.read_text(encoding='utf-8'));p['tasks'][0]['files'][0]['evidenceIds']=[];write(plan_path,p)
        saved={p:p.read_bytes() for p in self.path.parent.iterdir()};self.assertEqual(execute('build',self.path,self.base)['status'],'failed');self.assertTrue(all(p.read_bytes()==raw for p,raw in saved.items()))
    def test_html_embeds_raw_models_and_escapes_script_terminator(self):
        self.model['title']='</script><img src=x onerror=alert(1)>';text=html_text(self.model,self.state,self.plan,self.atomic)
        self.assertNotIn(self.model['title'],text);self.assertIn('\\u003c/script>',text);self.assertIn('id="atomicModel"',text);self.assertIn('id="taskPlan"',text)

def main():
    global TEMP_ROOT
    p=argparse.ArgumentParser();p.add_argument('--temp-root',type=Path);args,other=p.parse_known_args();TEMP_ROOT=args.temp_root
    if TEMP_ROOT: TEMP_ROOT.mkdir(parents=True,exist_ok=True)
    unittest.main(argv=['test_plan.py']+other)
if __name__=='__main__': main()
