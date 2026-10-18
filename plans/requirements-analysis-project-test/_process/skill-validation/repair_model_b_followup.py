import json,copy
from pathlib import Path
base=Path(__file__).parent
exec(compile((base/'repair_model.py').read_text(encoding='utf-8').split('\nproposal=json.loads')[0],str(base/'repair_model.py'),'exec'))
p=json.loads((base/'repair-proposal-b.json').read_text(encoding='utf-8'))
for op in p['operations'][21:]:
 if op['action']!='merge_obligation_then_remove_transition':continue
 old=next((t for t in m['transitions'] if t['id']==op['transitionId']),None)
 if not old:continue
 target=next(r for r in m['requirements'] if r['id']==op['targetRequirementId']);edge=next(t for t in m['transitions'] if t['id']==target['transitionId'])
 for i,ac in enumerate(next(r for r in m['requirements'] if r['id']==old['requirementId'])['acceptance']):target['acceptance'].append({'id':target['id']+'/TIME-'+str(i),'given':ac['given'],'when':edge['event'],'then':ac['then']})
 target['sourceIds']=list(dict.fromkeys(target['sourceIds']+op['sourceIds']));delete(op['transitionId'],op['meaning'],op['sourceIds'])
for op in p['followupOperations']:
 if op['id']=='B-FOLLOW-UNAVAILABLE':
  update({**op['update'],'sourceIds':op['sourceIds'],'reason':op['reason']})
  add({**op['add'],'sourceIds':op['sourceIds'],'reason':op['reason']});add({**op['addReturn'],'sourceIds':op['sourceIds'],'reason':op['reason']})
 elif op['id']=='B-FOLLOW-KEYBOARD':
  for k,v in op['domainDescription'].items():m['pathContext']['domains'][k]['description']=v
  state=next(s for s in m['states'] if s['id']==op['updateState']['id']);state['facts']+=op['updateState']['addFacts'];state['sourceIds']=list(dict.fromkeys(state['sourceIds']+op['sourceIds']))
  for val in op['addTransitions']:
   tid=val['transitionId'];rid='R'+tid[1:];sources=list(dict.fromkeys(op['sourceIds']+[r['sourceId'] for r in state['uiRefs']]))
   if any(t['id']==tid for t in m['transitions']):continue
   m['transitions'].append({'id':tid,'featureIds':state['featureIds'],'from':val['from'],'to':val['to'],'event':val['event'],'guard':val['guard'],'requirementId':rid,'sourceIds':sources,'status':'draft','selfLoopEvidence':op['selfLoopEvidence']})
   m['requirements'].append({'id':rid,'transitionId':tid,'title':val['event'],'ruleIds':[x.replace('PRD-','') for x in sources if x.startswith('PRD-FR')],'acceptance':[{'id':rid+'/AC','given':state['title']+'；'+val['guard'],'when':val['event'],'then':val['then']}],'uiRefs':copy.deepcopy(state['uiRefs']),'uiApplicability':{'status':'mapped'},'sourceIds':sources,'status':'draft'})
   m['pathContext']['transitionRules'][tid]={'cases':val['cases'],'sourceRefs':op['selfLoopEvidence']['sourceRefs'],'reason':op['reason']}
   for eid in (tid,rid):change('add',eid,op['reason'],op['sourceIds'])
  for t in list(m['transitions']):
   if t['from']=='DRAFT.keyboard' and t['to']!='DRAFT.keyboard':update({'transitionId':t['id'],'guard':'键盘所覆盖的当前表单状态为'+next(s['title'] for s in m['states'] if s['id']==t['to'])+'；关闭键盘后保留当前输入及当前字段合法性','sourceIds':op['sourceIds'],'reason':op['reason']})
 elif op['id']=='B-FOLLOW-UI':
  for ch in op['changes']:
   for sid in ch['stateIds']:
    s=next(s for s in m['states'] if s['id']==sid)
    if 'replaceNonTokenRefs' in ch:s['uiRefs']=[r for r in s['uiRefs'] if r['sourceId']=='UI-TOKENS']+ch['replaceNonTokenRefs']
    else:
     for r in s['uiRefs']:
      if r.get('frameId')==ch['frameId']:r['stateLabel']+='；'+ch['stateLabelSuffix']
    s['sourceIds']=list(dict.fromkeys(s['sourceIds']+[r['sourceId'] for r in s['uiRefs']]))
    for t in m['transitions']:
     if t['to']!=sid:continue
     r=next(r for r in m['requirements'] if r['id']==t['requirementId']);r['uiRefs']=copy.deepcopy(s['uiRefs']);r['sourceIds']=list(dict.fromkeys(r['sourceIds']+[x['sourceId'] for x in r['uiRefs']]))
    change('update',sid,'视觉对应仅按画板实际覆盖范围，缺画板字段依PRD文字，不误称完整视觉覆盖。',op['sourceIds'])
path.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'transitions':len(m['transitions']),'batch':'B followup'}))
