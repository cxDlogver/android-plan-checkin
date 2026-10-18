import copy, tempfile, unittest, json
from pathlib import Path
import planning as p
from routes import advance, invariant_conflicts, nearest, plan_routes, replay, validate_context

class PlanningTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name);self.repo=self.root/'repo';self.repo.mkdir();(self.repo/'app.txt').write_text('initial')
        m={'states':[{'id':i,'title':i,'facts':['事实'],'featureIds':['F']} for i in ('start','middle','end')],
           'entryStateIds':['start'],'sources':[],'transitions':[],'requirements':[],
           'pathContext':{'domains':{'x':{'values':['0','1'],'labels':{'0':'零','1':'一'}}},'entryContexts':{'start':{'x':['0']}},'transitionRules':{}}}
        for tid,fr,to in [('a','start','middle'),('b','middle','end')]:
            m['transitions'].append({'id':tid,'from':fr,'to':to,'event':'执行'+tid,'guard':'条件'+tid,'featureIds':['F'],'requirementId':'r'+tid,'sourceIds':['prd']})
            m['requirements'].append({'id':'r'+tid,'transitionId':tid,'title':'需求'+tid,'sourceIds':['prd'],'acceptance':[{'given':'准备','when':'执行','then':['结果一','结果二']}],'uiRefs':[]})
            m['pathContext']['transitionRules'][tid]={'cases':[{}]}
        self.m=m
        roles={'analysisModel':m,'stateGraph':{'nodes':m['states'],'edges':m['transitions']},'requirements':{'requirements':m['requirements']},'requirementGraph':{'nodes':[{'id':'ra'},{'id':'rb'}],'edges':[{'id':'ab','from':'ra','to':'rb','usageCount':1}], 'reduction':{'entryRequirementIds':['ra']}, 'traversal':{'status':'optimal','totalVisits':2,'routes':[{'entryStateId':'start','transitionIds':['a','b'],'requirementIds':['ra','rb'],'contextCheck':{'status':'passed'}}]}},'prd':'来源','uiSpec':'视觉文档','tokens':{},'pageMap':{'screens':[]}}
        rg=roles['requirementGraph']
        data={'states':m['states'],'transitions':m['transitions'],'requirements':m['requirements'],'starts':['start'],'requirementStarts':['ra'],'requirementGraph':rg,'layout':{'positions':{s['id']:{'x':0,'y':0,'w':200,'h':80} for s in m['states']}},'requirementLayout':{'positions':{n['id']:{'x':0,'y':0,'w':200,'h':80} for n in rg['nodes']}}}
        roles['requirementsReview']='<html><body><button id="requirement-mode" aria-pressed="false">需求覆盖图</button><script id="data" type="application/json">'+json.dumps(data)+'</script><script>function graph(){} function draw(){} function switchMode(next){} function selectRequirement(id){} function continuationDetail(id){} function coverageDetail(){}</script></body></html>'
        inp=[]
        for role,data in roles.items():
            f=self.root/(role+'.json');p.write(f,data);inp.append({'role':role,'path':str(f),'sha256':p.sha(f.read_bytes()),'readRanges':['fixture']})
        self.cfg={'phase':'planning','scope':{'objective':'synthetic skill contract test','initialConfirmation':{'humanReply':'SYNTHETIC fixture, not a user approval'}},'inputs':inp,
          'repository':{'root':str(self.repo),'exists':True,'evidence':[],'codeRoots':['app.txt']},'tasks':[{'id':'dev','title':'开发','codePaths':['app.txt'],'dependsOn':[],'approach':['调整'],'doneWhen':['满足'],'requirementIds':['ra','rb'],'regressionIds':[],'checks':[{'id':'static','kind':'static','command':'test-fixture','reason':'synthetic'}],'status':'pending'}],
          'issues':[],'upstreamApproved':True,'regressions':[],'overrides':{'ra':{'readiness':'ready'},'rb':{'readiness':'ready'}},'results':{},'routePolicy':{'resetAllowed':True,'resetReason':'独立夹具','maxConfigurations':100,'maxSegmentSteps':10},'routePreparations':{}}
        self.save();plan,_=p.build(self.root)
        for r in plan['routes']['routes']:self.cfg['routePreparations'][r['id']]={'routeDigest':r['routeDigest'],'setup':['明确数据'],'controls':['无故障'],'restore':['无修改'],'sourceRefs':['prd'],'guardReview':'synthetic finite guard check'}
        self.save();self.plan,self.gate=p.build(self.root)
    def save(self):p.write(p.work(self.root),self.cfg)
    def approve(self):
        for file in ('review.json','approval.json'):p.write(self.root/'_process'/file,{'planningDigest':self.plan['planningDigest'],'status':'PASS','context':'independent','findings':['SYNTHETIC TEST ONLY'],'humanReply':'SYNTHETIC TEST ONLY'})
    def to_acceptance(self):
        self.approve();p.advance_phase(self.root,'development');self.cfg=p.read(p.work(self.root));self.cfg['tasks'][0]['status']='complete'
        e=self.root/'_process/evidence/dev.txt';p.write(e,'synthetic static evidence')
        self.cfg['developmentEvidence']={'dev/static':{'status':'passed','codeDigest':self.plan['codeDigest'],'path':'_process/evidence/dev.txt','sha256':p.sha(e.read_bytes()),'locator':'line 1'}}
        self.save();self.plan,_=p.build(self.root);p.advance_phase(self.root,'acceptance');self.plan=p.read(self.root/'test-plan.json')
    def result(self):
        e=self.root/'_process/evidence/observed.txt';p.write(e,'synthetic actual evidence')
        c=self.plan['cases'][0]
        return {'caseId':c['id'],'planningDigest':self.plan['planningDigest'],'codeDigest':self.plan['codeDigest'],'status':'passed','environment':{'platform':'synthetic','build':'synthetic','fixture':'synthetic','executedAt':'test'},'observations':[{'instanceId':i['id'],'assertionId':a['id'],'verdict':'passed','actual':'synthetic match','evidence':[{'path':'_process/evidence/observed.txt','sha256':p.sha(e.read_bytes()),'locator':'line 1'}]} for i in c['instances'] for a in c['assertions'] if a['applicability']=='supported']}
    def test_direct_graph_mapping_and_inherited_entries(self):
        g=self.plan['testGraph'];self.assertEqual(g['entryCaseIds'],['TC-ra'])
        self.assertEqual([(e['from'],e['to']) for e in g['edges']],[('TC-ra','TC-rb')])
        self.assertEqual(len(g['nodes']),2);self.assertEqual(self.plan['routes']['visits'],2)
    def test_graph_tampering_fails_check(self):
        plan=copy.deepcopy(self.plan);plan['testGraph']['edges'].append(copy.deepcopy(plan['testGraph']['edges'][0]))
        self.assertEqual(p.check_model(self.root,self.cfg,plan,self.m)['mechanical']['status'],'FAIL')
    def test_conflict_is_inherited_without_replanning(self):
        from graph_mapping import inherit_routes
        rg=copy.deepcopy(self.plan['requirementGraph']);rg['traversal']['routes'][0]['contextCheck']={'status':'conflict','step':2}
        r=inherit_routes(self.m,rg);self.assertFalse(r['executable']);self.assertTrue(r['complete']);self.assertEqual(r['visits'],2)
    def test_finite_domain_success_preserves_upstream_limits_and_conditions(self):
        from graph_mapping import inherit_routes
        rg=copy.deepcopy(self.plan['requirementGraph'])
        rg['traversal'].update(status='feasible',optimalityScope='finite_domain_feasibility',optimality='not_proven',lowerBoundVisits=2)
        for status in ('finite_domain_passed','no_guard_constraints'):
            rg['traversal']['routes'][0]['contextCheck']={'status':status,'initialContext':{'mode':['ready']},'ruleCases':[0,0]}
            r=inherit_routes(self.m,rg)
            self.assertTrue(r['executable']);self.assertEqual('not_proven',r['sourceOptimality'])
            self.assertEqual(2,r['lowerBoundVisits']);self.assertEqual({'mode':['ready']},r['routes'][0]['contextCheck']['initialContext'])
    def test_duplicate_source_edge_rejected(self):
        from graph_mapping import project_graph
        rg=copy.deepcopy(self.plan['requirementGraph']);rg['edges'].append(copy.deepcopy(rg['edges'][0]))
        with self.assertRaises(ValueError):project_graph(self.m,rg,self.plan['cases'])
    def test_multiple_real_entries_are_inherited(self):
        from graph_mapping import project_graph
        model=copy.deepcopy(self.m);model['entryStateIds']=['start','middle']
        rg=copy.deepcopy(self.plan['requirementGraph']);rg['reduction']['entryRequirementIds']=['rb','ra']
        graph=project_graph(model,rg,self.plan['cases']);self.assertEqual(graph['entryCaseIds'],['TC-rb','TC-ra'])
        self.assertEqual(graph['entryStateIds'],['start','middle'])
    def test_entry_mismatch_rejected(self):
        from graph_mapping import project_graph
        rg=copy.deepcopy(self.plan['requirementGraph']);rg['reduction']['entryRequirementIds']=['rb']
        with self.assertRaises(ValueError):project_graph(self.m,rg,self.plan['cases'])
    def test_requirements_html_data_mismatch_rejected(self):
        from graph_mapping import read_review
        f=next(x['path'] for x in self.cfg['inputs'] if x['role']=='requirementsReview')
        rg=copy.deepcopy(self.plan['requirementGraph']);rg['edges']=[]
        with self.assertRaises(ValueError):read_review(f,self.m,rg)
    def test_deferred_regression_rejected(self):
        self.cfg['regressionPolicy']={'mode':'deferred'};self.cfg['regressions']=[{'id':'extra'}];self.save()
        with self.assertRaises(ValueError):p.build(self.root)
    def test_ready_route_preparation_survives_build(self):
        self.assertEqual(self.gate['readiness']['status'],'ready');again,_=p.build(self.root);self.assertEqual(self.plan,again)
    def test_missing_preparation_blocks(self):
        self.cfg['routePreparations']={};self.save();_,g=p.build(self.root);self.assertEqual(g['readiness']['status'],'draft')
    def test_cannot_replace_source_assertions(self):
        self.cfg['overrides']['ra']['assertions']=[];self.save()
        with self.assertRaises(ValueError):p.build(self.root)
    def test_duplicate_assertions_are_rejected(self):
        self.cfg['overrides']['ra']['additionalAssertions']=[copy.deepcopy(self.plan['cases'][0]['assertions'][0])];self.save();_,g=p.build(self.root);self.assertEqual(g['mechanical']['status'],'FAIL')
    def test_duplicate_instances_are_rejected(self):
        self.cfg['overrides']['ra']['instances']=[{'id':'x'},{'id':'x'}];self.save();_,g=p.build(self.root);self.assertEqual(g['mechanical']['status'],'FAIL')
    def test_missing_matrix_mapping_blocks(self):
        self.cfg['acceptanceMatrix']={'environments':['native-large']};self.save();_,g=p.build(self.root);self.assertEqual(g['readiness']['status'],'draft')
    def test_browser_check_not_development(self):
        self.cfg['tasks'][0]['checks'][0]['kind']='browser';self.save();_,g=p.build(self.root);self.assertEqual(g['mechanical']['status'],'FAIL')
    def test_cannot_accept_before_development(self):
        with self.assertRaises(ValueError):p.record(self.root,self.result())
    def test_current_plan_approval_required(self):
        self.to_acceptance();self.cfg=p.read(p.work(self.root));self.cfg['tasks'][0]['approach']=['changed'];self.save();p.build(self.root)
        with self.assertRaises(ValueError):p.record(self.root,self.result())
    def test_mechanical_failure_blocks_record(self):
        self.to_acceptance();self.cfg=p.read(p.work(self.root));self.cfg['tasks'][0]['dependsOn']=['missing'];self.save();p.build(self.root)
        with self.assertRaises(ValueError):p.record(self.root,self.result())
    def test_stale_artifact_rejected(self):
        with (self.root/'review.html').open('a') as f:f.write('modified')
        with self.assertRaises(ValueError):p.validate_current(self.root)
    def test_input_change_rejected(self):
        Path(self.cfg['inputs'][4]['path']).write_text('changed')
        with self.assertRaises(ValueError):p.build(self.root)
    def test_evidence_and_all_assertions_required(self):
        self.to_acceptance();r=self.result();r['observations'].pop()
        with self.assertRaises(ValueError):p.record(self.root,r)
        r=self.result();r['observations'][0]['evidence'][0]['sha256']='wrong'
        with self.assertRaises(ValueError):p.record(self.root,r)
    def test_full_normal_flow_updates_markdown(self):
        self.to_acceptance();p.record(self.root,self.result());out=p.read(self.root/'test-plan.json');self.assertEqual(out['cases'][0]['result']['status'],'passed')
        text=(self.root/'test-cases.md').read_text(encoding='utf-8');self.assertIn('；通过；',text);self.assertIn('synthetic match',text)
    def test_fix_invalidates_and_requires_current_dev_checks(self):
        self.to_acceptance();p.record(self.root,self.result());(self.repo/'app.txt').write_text('fixed');p.invalidate(self.root,'fixed code')
        self.assertEqual(p.read(p.work(self.root))['phase'],'development')
        with self.assertRaises(ValueError):p.advance_phase(self.root,'acceptance')
        self.cfg=p.read(p.work(self.root));self.plan=p.read(self.root/'test-plan.json');self.cfg['developmentEvidence']['dev/static']['codeDigest']=self.plan['codeDigest'];self.save();p.build(self.root);p.advance_phase(self.root,'acceptance');p.record(self.root,self.result())
    def test_no_jump_and_multiple_entries(self):
        m=copy.deepcopy(self.m);m['transitions'][1]['from']='end';m['transitions'][1]['to']='end';m['entryStateIds'].append('end');m['pathContext']['entryContexts']['end']={'x':['1']}
        routes=plan_routes(m,self.cfg['routePolicy']);self.assertTrue(routes['complete']);self.assertEqual(len(routes['routes']),2)
        for r in routes['routes']:self.assertFalse(replay(m,r))
    def test_invariant_conflict_is_preserved(self):
        m=copy.deepcopy(self.m);m['pathContext']['transitionRules']['b']['cases']=[{'requires':{'x':['1']}}]
        self.assertIn('b',invariant_conflicts(m));r=plan_routes(m,self.cfg['routePolicy']);self.assertEqual(r['uncoveredTransitionIds'],['b'])
    def test_copy_uses_pre_effect_values(self):
        spec={'domains':{k:{'values':['0','1']} for k in ('x','y')}}
        self.assertEqual(advance(spec,{'x':{'0'},'y':{'1'}},{'set':{'x':['1']},'setFrom':{'y':'x'}}),[{'x':{'1'},'y':{'0'}}])
    def test_unknown_operations_rejected(self):
        m=copy.deepcopy(self.m);m['pathContext']['transitionRules']['a']['cases']=[{'teleport':True}]
        with self.assertRaises(ValueError):validate_context(m)
    def test_search_limit_is_incomplete(self):
        path,_,info=nearest(self.m,'start',{'x':{'0'}},{'b'},1);self.assertIsNone(path);self.assertFalse(info['complete'])
    def test_missing_design_values_are_not_invented(self):
        css=p.css_tokens({'font':{'body':15},'layout':{}})
        self.assertIn('--font-body: 15px',css)
        for fake in ('0px','700','font-family','line-height','min-width','padding-inline'):self.assertNotIn(fake,css)

if __name__=='__main__':unittest.main()
