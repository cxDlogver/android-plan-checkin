import sys,copy,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
SCRIPTS=ROOT.parent/'skill/task-planning/scripts'
if not SCRIPTS.exists():SCRIPTS=ROOT.parents[3]/'.codex/skills/task-planning/scripts'
sys.path.insert(0,str(SCRIPTS))
import planning as p
reports=[]
# One-edge toy project, all data read from review-only fixtures.
r=ROOT/'toy';r.mkdir(exist_ok=True)
model={'entryStateIds':['s0'],'states':[{'id':'s0','title':'打开首页'},{'id':'s1','title':'内容已显示'}],'transitions':[{'id':'t','from':'s0','to':'s1','event':'读取成功','guard':'内容有效','featureIds':['f'],'requirementId':'r'}],'requirements':[{'id':'r','transitionId':'t','title':'显示内容','sourceIds':['prd'],'acceptance':[{'given':'内容有效','when':'读取成功','then':['显示正确内容','保留记录不变']}],'uiRefs':[]}]}
model['pathContext']={'domains':{'loaded':{'values':['no','yes'],'labels':{'no':'未读取','yes':'已读取'}}},'entryContexts':{'s0':{'loaded':['no']}},'transitionRules':{'t':{'cases':[{'requires':{'loaded':['no']},'set':{'loaded':['yes']}}]}}}
model['sources']=[{'id':'prd','title':'Toy PRD','path':'prd'}]
files={'analysisModel':model,'stateGraph':{'nodes':model['states'],'edges':model['transitions']},'requirements':{'requirements':model['requirements']},'requirementGraph':{'nodes':[{'id':'r'}],'edges':[]},'prd':'PRD','uiSpec':'UI','tokens':{},'pageMap':{'screens':[]}}
inputs=[]
for role,value in files.items():
 path=r/(role+'.json');p.write(path,value);inputs.append({'role':role,'path':str(path),'sha256':p.sha(path.read_bytes()),'readRanges':['all']})
repo=r/'repo';repo.mkdir(exist_ok=True);(repo/'src.txt').write_text('unchanged code')
cfg={'phase':'planning','outputs':p.OUTPUTS,'scope':{'objective':'toy','initialConfirmation':{'humanReply':'confirmed'}},'inputs':inputs,'repository':{'root':str(repo),'exists':True,'evidence':[],'codeRoots':['src.txt']},'issues':[],'tasks':[{'id':'impl','title':'实现','dependsOn':[],'codePaths':['src.txt'],'approach':['reuse'],'doneWhen':['matches'],'requirementIds':['r'],'regressionIds':[],'checks':[{'id':'static','kind':'static','command':'check','reason':'typecheck'}],'status':'pending'}],'regressions':[],'overrides':{'r':{'readiness':'ready'}},'results':{},'upstreamApproved':True,'routePolicy':{'resetAllowed':True,'resetReason':'fixture','maxConfigurations':100,'maxSegmentSteps':10}}
def build(c):
 p.write(p.work(r),c);return p.build(r)
def attempt(label,fn):
 try:
  val=fn();reports.append({'case':label,'accepted':True,'value':val})
 except Exception as exc:reports.append({'case':label,'accepted':False,'exception':str(exc)})

# Keep explicit expected acceptance/rejection rather than treating a crash as success.
def reject(label,fn):
 try:fn()
 except (ValueError,KeyError,OSError,TypeError) as e:reports.append({'case':label,'status':'PASS','rejected':str(e)});return
 raise AssertionError('unexpectedly accepted: '+label)
def approve(data):
 p.write(r/'_process/review.json',{'planningDigest':data['planningDigest'],'status':'PASS','context':'independent','findings':['Synthetic protocol test only']})
 p.write(r/'_process/approval.json',{'planningDigest':data['planningDigest'],'status':'PASS','humanReply':'Synthetic protocol test; not project authorization'})
p0,g=build(cfg)
assert g['mechanical']['status']=='PASS'
assert g['readiness']['status']=='draft'
reject('missing_fixture_blocks_development',lambda:p.advance_phase(r,'development'))
# Add an explicit preparation bound to the exact selected route.
route=p0['routes']['routes'][0]
cfg['routePreparations']={route['id']:{'routeDigest':route['routeDigest'],'setup':['seed valid content'],'controls':['complete read'],'restore':['delete toy content'],'sourceRefs':['prd'],'guardReview':'condition is valid content'}}
p0,g=build(cfg);assert g['readiness']['status']=='ready',g
reports.append({'case':'persistent_route_preparation_can_be_ready','status':'PASS'})
approve(p0)
p.advance_phase(r,'development')
# Cannot enter acceptance until code tasks/checks complete.
reject('unfinished_development_rejected',lambda:p.advance_phase(r,'acceptance'))
c=p.read(p.work(r));c['tasks'][0]['status']='complete'
evidence=r/'_process/evidence.txt';evidence.write_text('synthetic local review evidence')
e={'path':'_process/evidence.txt','sha256':p.sha(evidence.read_bytes()),'locator':'line 1'}
p1,g=build(c);c['developmentEvidence']={'impl/static':dict(e,status='passed',codeDigest=p1['codeDigest'])};build(c)
p.advance_phase(r,'acceptance')
p1=p.read(r/'test-plan.json');case=p1['cases'][0]
def result(data):
 return {'caseId':case['id'],'planningDigest':data['planningDigest'],'codeDigest':data['codeDigest'],'status':'passed','environment':{'platform':'test','build':'test','fixture':'test','executedAt':'test'},'observations':[{'instanceId':i['id'],'assertionId':a['id'],'verdict':'passed','actual':'verified '+a['text'],'evidence':[e]} for i in case['instances'] for a in case['assertions'] if a['applicability']=='supported']}
p.record(r,result(p1))
md=(r/'test-cases.md').read_text(encoding='utf-8');assert 'verified ' in md and 'evidence.txt' in md,md
reports.append({'case':'normal_lifecycle_and_record_updates_markdown','status':'PASS'})
basecfg=p.read(p.work(r))
# Normal working-model changes must not silently weaken approved plan.
c=copy.deepcopy(basecfg);c['overrides']['r']['assertions']=[{'id':'easy','kind':'functional','text':'page exists','sourceRefs':['prd'],'applicability':'supported'}]
reject('source_assertion_replacement_rejected',lambda:build(c))
c=copy.deepcopy(basecfg);c['results']={};c['overrides']['r']['additionalAssertions']=[{'id':'functional-1','kind':'functional','text':'colliding assertion','sourceRefs':['prd'],'applicability':'supported'}]
_,g=build(c);assert g['mechanical']['status']=='FAIL' and 'duplicate assertion id' in g['mechanical']['errors'];reports.append({'case':'duplicate_assertion_identity_rejected','status':'PASS'})
c=copy.deepcopy(basecfg);c['results']={};c['tasks'][0]['dependsOn']=['unknown'];data,g=build(c);reject('record_with_broken_gate_rejected',lambda:p.record(r,result(data)))
c=copy.deepcopy(basecfg);c['results']={};c['tasks'][0]['approach']=['changed plan'];data,g=build(c);reject('record_with_stale_approval_rejected',lambda:p.record(r,result(data)))
c=copy.deepcopy(basecfg);c['results']={};c['tasks'][0]['checks']=[];data,g=build(c);assert g['mechanical']['status']=='FAIL';reports.append({'case':'removed_checks_need_explicit_rationale','status':'PASS'})
# Code repair cannot reuse old check evidence; invalidate returns to development.
build(basecfg);(repo/'src.txt').write_text('changed code')
reject('code_change_blocks_old_exports',lambda:p.record(r,result(p1)))
p.invalidate(r,'synthetic repair invalidates old observations')
c=p.read(p.work(r));assert c['phase']=='development';assert c['results'][case['id']]['status']=='pending';assert c['results'][case['id']]['staleEvidence']['observations']
reject('repair_requires_fresh_development_check',lambda:p.advance_phase(r,'acceptance'))
data=p.read(r/'test-plan.json');c['developmentEvidence']={'impl/static':dict(e,status='passed',codeDigest=data['codeDigest'])};build(c);p.advance_phase(r,'acceptance');p.record(r,result(p.read(r/'test-plan.json')))
reports.append({'case':'normal_repair_and_reacceptance_path','status':'PASS'})
p.write(ROOT/'adversarial-results.json',{'status':'PASS','checks':reports,'note':'Synthetic fixtures only; no current project acceptance'})
print(json.dumps(reports,ensure_ascii=False,indent=2))
