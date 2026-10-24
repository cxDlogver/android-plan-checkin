import copy
import hashlib
import tempfile
import unittest
from pathlib import Path
import analyze as a

class GateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.path = self.root / 'analysis-model.json'
        source = '读者可以借出和归还图书。'
        (self.root/'PRD.md').write_text(source, encoding='utf-8')
        visual = {'applicability':'required','criteria':['借出与在馆状态可以辨认'],'reason':'PRD 业务状态显示'}
        def req(i,t):
            return {'id':i,'transitionId':t,'name':i,'functionalRequirements':{'statement':'图书流转','acceptanceCriteria':['借还后业务状态与登记结果一致']},'visualRequirements':copy.deepcopy(visual),'sourceIds':['P1']}
        self.m = {'schemaVersion':1,'analysisId':'library','revision':1,'phase':'review_ready',
          'scope':{'objective':'图书借还','included':['借出','归还'],'excluded':[],'abstraction':'单本图书借阅事实'},
          'sources':[{'id':'DOC','path':'PRD.md','sha256':hashlib.sha256(source.encode()).hexdigest()}],
          'clauses':[{'id':'P1','sourceId':'DOC','locator':'第1行','quote':source,'scope':'included','scopeReason':'业务范围','coverageIds':['R1','R2']}],
          'clarifications':[],
          'states':[{'id':'S1','name':'图书在馆','scope':'固定图书','businessFacts':['图书尚未借出'],'verification':{'method':'核对借阅登记','assertions':['无有效借阅记录']},'sourceIds':['P1'],'isStart':True},
                    {'id':'S2','name':'图书已借出','scope':'固定图书','businessFacts':['图书有有效借阅人'],'verification':{'method':'核对借阅登记','assertions':['存在有效借阅记录']},'sourceIds':['P1'],'isStart':False}],
          'transitions':[{'id':'T1','from':'S1','to':'S2','operation':'借出图书','actor':'读者','guard':'图书可借','effects':['新增有效借阅记录'],'sourceIds':['P1']},
                         {'id':'T2','from':'S2','to':'S1','operation':'归还图书','actor':'读者','guard':'借阅记录有效','effects':['关闭有效借阅记录'],'sourceIds':['P1']}],
          'atomicRequirements':[req('R1','T1'),req('R2','T2')],'nonTransitionRequirements':[],'scenarios':[],'reviews':[],'reviewDigest':''}
        self.seal()
    def seal(self):
        self.m['reviews']=[{'ruleId':key,'entityIds':[e['id'] for e in (self.m['atomicRequirements']+self.m['nonTransitionRequirements'] if coll=='requirements' else self.m[coll])],'result':'pass','evidence':'测试夹具基于借还 PRD 验证各实体的来源和借阅状态语义'} for key,coll in a.REVIEW_RULES.items()]
        self.m['reviewDigest']=a.digest(self.m)
        a.write_json(self.path,self.m)
        a.render(self.m,self.path)
    def report(self): return a.gate(self.m,self.path)
    def failed(self,key): self.assertNotEqual(next(c for c in self.report()['checks'] if c['id']==key)['result'],'PASS')
    def test_valid_cycle_and_exact_continuation(self):
        self.assertEqual(self.report()['result'],'PASS')
        edges=a.derived(self.m)['requirement-graph.json']['edges']
        self.assertEqual(edges,[{'from':'R1','to':'R2','viaStateId':'S2'},{'from':'R2','to':'R1','viaStateId':'S1'}])
    def test_missing_start(self):
        self.m['states'][0]['isStart']=False;self.failed('business-graph')
    def test_unreachable_state(self):
        node=copy.deepcopy(self.m['states'][1]);node['id']='S3';self.m['states'].append(node);self.failed('business-graph')
    def test_missing_endpoint(self):
        self.m['transitions'][0]['to']='S_UNKNOWN';self.failed('business-graph')
    def test_duplicate_atomic_mapping(self):
        r=copy.deepcopy(self.m['atomicRequirements'][0]);r['id']='R3';self.m['atomicRequirements'].append(r);self.failed('one-transition-one-requirement')
    def test_pending_answer_blocks(self):
        self.m['clarifications'].append({'id':'C1','question':'借阅规则？','proposal':'待用户决定','status':'open','resolution':'','confirmation':{'quote':'','conversationRef':''}})
        self.assertEqual(self.report()['result'],'BLOCKED')
    def test_unsupported_business_source(self):
        self.m['states'][0]['sourceIds']=['INVENTED'];self.failed('business-source-trace')
    def test_missing_visual_field(self):
        del self.m['atomicRequirements'][0]['visualRequirements'];self.failed('schema')
    def test_unjustified_visual_na(self):
        self.m['atomicRequirements'][0]['visualRequirements']['applicability']='not_applicable';self.failed('functional-visual-fields')
    def test_uncovered_clause(self):
        self.m['clauses'][0]['coverageIds']=[];self.failed('prd-coverage')
    def test_stale_source_and_review(self):
        (self.root/'PRD.md').write_text('新的范围',encoding='utf-8');self.failed('source-integrity')
        self.m['transitions'][0]['guard']='语义已变化';self.failed('semantic-review')
    def test_missing_and_drifted_artifacts(self):
        (self.root/'state-graph.md').unlink();self.failed('complete-synchronized-artifacts');self.seal()
        p=self.root/'requirement-graph.json';g=a.load(p);g['edges'].append({'from':'R1','to':'R1','viaStateId':'S1'});a.write_json(p,g);self.failed('complete-synchronized-artifacts')
    def test_nontransition_contract_is_enforced(self):
        r=copy.deepcopy(self.m['atomicRequirements'][0]);del r['transitionId'];r['id']='N1';r['kind']='delivery';del r['functionalRequirements'];self.m['nonTransitionRequirements'].append(r);self.failed('schema')
    def test_init_does_not_claim_complete(self):
        p=a.initialize(self.root/'draft',self.root/'PRD.md','draft')
        self.assertEqual(a.load(p.parent/'gate-report.json')['result'],'BLOCKED')
    def test_repeated_requirement_in_valid_cycle(self):
        self.m['scenarios']=[{'id':'CASE','name':'借还后再借','sourceIds':['P1'],'bindings':'同一本书','requirementIds':['R1','R2','R1'],'expected':'循环衔接'}]
        self.seal()
        self.assertEqual(self.report()['result'],'PASS')
    def test_disconnected_acceptance_sequence(self):
        self.m['scenarios']=[{'id':'CASE','name':'错误链','sourceIds':['P1'],'bindings':'同一本书','requirementIds':['R1','R1'],'expected':'应拒绝'}]
        self.failed('acceptance-sequences')
    def test_stale_markdown_detected(self):
        with (self.root/'atomic-requirements.md').open('a',encoding='utf-8') as f:f.write('\n用户未确认的篡改')
        self.failed('complete-synchronized-artifacts')

if __name__=='__main__': unittest.main()
