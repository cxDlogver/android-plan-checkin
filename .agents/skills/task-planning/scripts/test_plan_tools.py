import copy
import tempfile
import unittest
from pathlib import Path
import sys
sys.dont_write_bytecode=True
import plan_tools as p

class PlanGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.folder=Path(self.tmp.name);self.path=self.folder/'planning-model.json'
        def req(i,name):return {'id':i,'name':name,'functionalRequirements':{'statement':name,'acceptanceCriteria':['借阅登记与实际操作一致']},'visualRequirements':{'applicability':'not_applicable','criteria':[],'reason':'此测试夹具验证领域流转'}}
        self.source={'atomicRequirements':[req('R1','借出'),req('R2','归还')],'nonTransitionRequirements':[],'states':[],'transitions':[],'scope':{'objective':'图书借还'},'clarifications':[]}
        p.dump(self.folder/'requirements.json',self.source)
        p.dump(self.folder/'upstream-gate.json',{'result':'PASS','modelDigest':p.req_digest(self.source)})
        def case(cid,rid):return {'id':cid,'kind':'primary','requirementIds':[rid],'mappingRationale':'默认1:1','name':cid,'level':'unit','environment':'python unit','fixture':{'setup':['在用例内准备一本图书'],'cleanup':['清理本用例对象'],'externalPreconditions':[]},'steps':[{'id':'SETUP','action':'准备夹具','expectedResultIds':[]},{'id':'ACT','action':'执行借还操作','expectedResultIds':[]},{'id':'ASSERT','action':'观测真实登记','expectedResultIds':[cid+'_E']},{'id':'CLEAN','action':'清理对象','expectedResultIds':[]}],'expectedResults':[{'id':cid+'_E','expected':'登记状态等于规定结果','observe':'读取借阅登记','criterionRefs':[rid+':F:0']}],'actualObservation':self.not_run(),'testFile':'tests/library_test.py','plannedCommand':'图调度入口','limitations':[]}
        self.m={'schemaVersion':1,'analysisId':'library','revision':1,'source':{'requirementsPath':'requirements.json','requirementsSha256':p.sha(self.folder/'requirements.json'),'requirementsDigest':p.req_digest(self.source),'gatePath':'upstream-gate.json','gateSha256':p.sha(self.folder/'upstream-gate.json')},'executionPolicy':{'allowedLevels':['unit','integration'],'browserAcceptance':False,'fixtureMode':'isolated','onFailure':'stop','entryRule':'previous_passed_edge','rootRule':'no_external_preconditions'},'cases':[case('TC1','R1'),case('TC2','R2')],'graph':{'roots':['TC1'],'edges':[{'from':'TC1','to':'TC2','reason':'验收先后'}]},'traversal':{'route':['TC1','TC2'],'repeatCount':0,'lowerBoundVisits':2,'optimality':'proven_optimal','proof':'2个节点各一次达到访问下界'},'plan':{'objective':'图书操作实现计划','baseline':'只有PRD','decisions':[{'topic':'数据','choice':'领域对象','rationale':'可验证借阅事实'}],'modules':[{'path':'library.py','responsibility':'借还领域逻辑'}],'tasks':[{'id':'TASK1','title':'领域实现','dependsOn':[],'requirementIds':['R1','R2'],'caseIds':['TC1','TC2'],'outputs':['library.py'],'steps':['先测试再实现'],'doneCriteria':['可运行借还测试'],'status':'planned'}],'commands':[{'purpose':'验收','command':'run acceptance','status':'planned'}],'verificationLimitations':['测试夹具不声称证明实际应用正确'],'references':[]},'execution':{'runId':None,'implementationRef':None,'modelDigest':'','visits':[]},'reviews':[{'ruleId':x,'result':'pass','evidence':'测试夹具逐条验证模型与用例映射、准备、顺序及观察契约'} for x in sorted(p.REVIEW_RULES)],'reviewDigest':''}
        self.seal()
    def not_run(self):return {'status':'not_run','observedValues':[],'assertionResults':[],'evidence':[],'note':'尚未执行'}
    def seal(self):
        self.m['reviewDigest']=p.digest(self.m);self.m['execution']['modelDigest']=p.digest(self.m)
        p.dump(self.path,self.m);p.render(self.m,self.path)
    def report(self):return p.gate(self.m,self.path)
    def failed(self,key):self.assertEqual(next(c for c in self.report()['checks'] if c['id']==key)['result'],'FAIL')
    def visit(self,cid,status='pass'):
        (self.folder/'test-output.txt').write_text('synthetic gate-test fixture report',encoding='utf-8')
        c=next(c for c in self.m['cases'] if c['id']==cid)
        return {'caseId':cid,'status':status,'observedValues':[{'assertionId':e['id'],'actual':'fixture observed record'} for e in c['expectedResults']],'assertionResults':[{'assertionId':e['id'],'status':status} for e in c['expectedResults']],'evidence':[{'path':'test-output.txt','sha256':p.sha(self.folder/'test-output.txt'),'command':'synthetic gate test','exitCode':0 if status=='pass' else 1}],'note':'用于门禁测试的人工夹具，非项目应用测试'}
    def bind_visits(self,visits):
        self.m['execution'].update(runId='fixture-run',implementationRef='fixture-implementation',visits=visits)
        for v in visits:next(c for c in self.m['cases'] if c['id']==v['caseId'])['actualObservation']={k:x for k,x in v.items() if k!='caseId'}
    def test_valid_planning_is_not_execution(self):
        r=self.report();self.assertEqual(r['planningStatus'],'PASS');self.assertEqual(r['executionStatus'],'not_run')
    def test_stale_source(self):
        (self.folder/'requirements.json').write_text('{}');self.failed('source-and-upstream-gate')
    def test_failed_upstream_gate(self):
        p.dump(self.folder/'upstream-gate.json',{'result':'FAIL','modelDigest':p.req_digest(self.source)});self.m['source']['gateSha256']=p.sha(self.folder/'upstream-gate.json');self.failed('source-and-upstream-gate')
    def test_missing_primary(self):
        self.m['cases'][1]['requirementIds']=['R1'];self.failed('requirement-case-mapping')
    def test_unmapped_oracle(self):
        self.m['cases'][0]['expectedResults'][0]['criterionRefs']=['R1:F:77'];self.failed('expected-observed-steps-and-no-browser')
    def test_unobserved_expected_assertion(self):
        self.m['cases'][0]['steps'][2]['expectedResultIds']=[];self.failed('expected-observed-steps-and-no-browser')
    def test_duplicate_step_ids(self):
        self.m['cases'][0]['steps'][1]['id']='SETUP';self.failed('expected-observed-steps-and-no-browser')
    def test_root_with_external_precondition(self):
        self.m['cases'][0]['fixture']['externalPreconditions']=['另一个用例已造数据'];self.failed('directed-graph-entry')
    def test_unknown_edge_endpoint(self):
        self.m['graph']['edges'][0]['to']='UNKNOWN';self.failed('directed-graph-entry')
    def test_route_jump(self):
        self.m['graph']['edges']=[];self.failed('traversal-and-minimum-repeat-proof')
    def test_invalid_optimality_claim(self):
        self.m['traversal']['route']=['TC1','TC2','TC1'];self.m['traversal']['repeatCount']=1;self.failed('traversal-and-minimum-repeat-proof')
    def test_development_dependency_cycle(self):
        self.m['plan']['tasks'][0]['dependsOn']=['TASK1'];self.failed('implementation-plan-completeness')
    def test_entry_cannot_skip_root(self):
        self.assertIsNotNone(p.entry_error(self.m,'TC2',[]))
    def test_root_entry_rejects_external_precondition(self):
        self.m['cases'][0]['fixture']['externalPreconditions']=['另一个测试已造数据']
        self.assertIsNotNone(p.entry_error(self.m,'TC1',[]))
    def test_failure_needs_failure_evidence(self):
        v=self.visit('TC1');v['status']='fail';self.bind_visits([v]);self.failed('actual-observations-and-runtime-entry')
    def test_entry_stops_after_failure(self):
        self.assertIsNotNone(p.entry_error(self.m,'TC2',[{'caseId':'TC1','status':'fail'}]))
    def test_entry_requires_current_edge(self):
        self.m['graph']['edges']=[];self.assertIsNotNone(p.entry_error(self.m,'TC2',[{'caseId':'TC1','status':'pass'}]))
    def test_valid_first_pass_allows_next(self):
        self.bind_visits([self.visit('TC1')]);self.seal();self.assertEqual(self.report()['planningStatus'],'PASS');self.assertIsNone(p.entry_error(self.m,'TC2',self.m['execution']['visits']))
    def test_pass_requires_evidence(self):
        v=self.visit('TC1');v['evidence']=[];self.bind_visits([v]);self.failed('actual-observations-and-runtime-entry')
    def test_evidence_hash_is_checked(self):
        self.bind_visits([self.visit('TC1')]);(self.folder/'test-output.txt').write_text('altered report');self.failed('actual-observations-and-runtime-entry')
    def test_old_pass_without_visit_is_rejected(self):
        self.m['cases'][0]['actualObservation']={k:v for k,v in self.visit('TC1').items() if k!='caseId'};self.failed('actual-observations-and-runtime-entry')
    def test_not_run_must_not_have_actual_value(self):
        self.m['cases'][0]['actualObservation']['observedValues']=[{'assertionId':'TC1_E','actual':'copied expectation'}];self.failed('actual-observations-and-runtime-entry')
    def test_run_needs_implementation_revision(self):
        self.bind_visits([self.visit('TC1')]);self.m['execution']['implementationRef']=None;self.failed('actual-observations-and-runtime-entry')
    def test_failed_case_cannot_be_followed(self):
        self.bind_visits([self.visit('TC1','fail'),self.visit('TC2')]);self.failed('actual-observations-and-runtime-entry')
    def test_stale_markdown_detected(self):
        (self.folder/'plan.md').write_text('changed document');self.failed('complete-synchronized-artifacts')
    def test_browser_is_not_default(self):
        self.m['executionPolicy']['browserAcceptance']=True;self.failed('schema')
    def test_review_digest_cannot_be_reused_after_plan_change(self):
        self.m['plan']['objective']='changed scope';self.failed('semantic-review')
    def test_complete_trace_requires_every_node(self):
        self.bind_visits([self.visit('TC1'),self.visit('TC2')]);self.seal();r=self.report();self.assertEqual(r['planningStatus'],'PASS');self.assertEqual(r['executionStatus'],'passed')

if __name__=='__main__':unittest.main()
