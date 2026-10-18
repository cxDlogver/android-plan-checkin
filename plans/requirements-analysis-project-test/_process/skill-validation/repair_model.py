"""Apply reviewed, source-backed corrections to the one current analysis model."""
import json,copy
from pathlib import Path
base=Path(__file__).parent
path=base.parent/'analysis-model.json'
m=json.loads(path.read_text(encoding='utf-8'))
round_=m['rounds'][-1]
assert round_['id']=='REPAIR-SEMANTIC-CONTEXT'

def change(kind,eid,meaning,sources):
    round_['changes'].append({'kind':kind,'entityId':eid,'meaning':meaning,'sourceIds':sources})

def delete(tid,reason,sources):
    t=next((t for t in m['transitions'] if t['id']==tid),None)
    if not t:return
    ids=[tid,t['requirementId']]
    m['transitions']=[x for x in m['transitions'] if x['id']!=tid]
    m['requirements']=[x for x in m['requirements'] if x['id']!=t['requirementId']]
    m['pathContext']['transitionRules'].pop(tid)
    for eid in ids:change('remove',eid,reason,sources)
    for r in m['rounds']:
        text=json.dumps(r,ensure_ascii=False)
        for eid in ids:
            if json.dumps(eid,ensure_ascii=False) in text:
                r['retiredIds']=list(dict.fromkeys(r.get('retiredIds',[])+[eid]))

def update(op):
    t=next(x for x in m['transitions'] if x['id']==op['transitionId'])
    r=next(x for x in m['requirements'] if x['id']==t['requirementId'])
    sources=list(dict.fromkeys(t['sourceIds']+op['sourceIds']))
    t['sourceIds']=sources;r['sourceIds']=list(dict.fromkeys(r['sourceIds']+sources))
    for field in ('guard','event'):
        if field in op:t[field]=op[field]
    if 'cases' in op:m['pathContext']['transitionRules'][t['id']]['cases']=op['cases']
    m['pathContext']['transitionRules'][t['id']]['reason']=op.get('reason','按来源校正条件及结果，与当前状态事实一致。')
    if 'then' in op:r['acceptance'][0]['then']=op['then']
    r['acceptance'][0]['given']=next(s['title'] for s in m['states'] if s['id']==t['from'])+'；'+t['guard']
    r['acceptance'][0]['when']=t['event']
    if t['from']==t['to'] and 'then' in op:t['selfLoopEvidence']['obligation']='；'.join(op['then'])
    change('update',t['id'],op.get('reason','按PRD/UI校正条件与预期结果。'),op['sourceIds'])

def add(op):
    tid=op['transitionId']
    if any(t['id']==tid for t in m['transitions']):return
    a=next(s for s in m['states'] if s['id']==op['from']);b=next(s for s in m['states'] if s['id']==op['to'])
    rid='R'+tid[1:];refs=copy.deepcopy(b['uiRefs']);sources=list(dict.fromkeys(op['sourceIds']+[r['sourceId'] for r in refs]))
    t={'id':tid,'featureIds':list(dict.fromkeys(a['featureIds']+b['featureIds'])),'from':a['id'],'to':b['id'],'event':op['event'],'guard':op['guard'],'requirementId':rid,'sourceIds':sources,'status':'draft'}
    assert a['id']!=b['id'],'new self-loop requires explicit evidence'
    r={'id':rid,'transitionId':tid,'title':op['event'],'ruleIds':[s.replace('PRD-','') for s in sources if s.startswith('PRD-FR')],
       'acceptance':[{'id':rid+'/AC','given':a['title']+'；'+op['guard'],'when':op['event'],'then':op['then']}],
       'uiRefs':refs,'uiApplicability':{'status':'mapped'} if refs else {'status':'not_applicable','reason':'该迁移只沿用来源文字明确的状态表现，不新增画板或视觉义务。'},'sourceIds':sources,'status':'draft'}
    m['transitions'].append(t);m['requirements'].append(r)
    m['pathContext']['transitionRules'][tid]={'cases':op['cases'],'sourceRefs':[{'sourceId':sid,'locator':'已有入口、返回、字段校验或事务约束；本条仅补足来源明确的迁移'} for sid in op['sourceIds']],
        'reason':op.get('reason','来源已有明确行为；补全入口或条件反面，不新增业务能力。')}
    for eid in (tid,rid):change('add',eid,op.get('reason','补齐已有资料明确的入口、返回或校验结果。'),op['sourceIds'])
    for key,value in op.get('domainExtension',{}).items():
        d=m['pathContext']['domains'][key]
        if value['value'] not in d['values']:d['values'].append(value['value'])
        d['labels'][value['value']]=value['label']
    if 'companion' in op:add({**op['companion'],'sourceIds':op['sourceIds']})

proposal=json.loads((base/'repair-proposal-b.json').read_text(encoding='utf-8'))
for op in proposal['operations']:
    action=op['action']
    if action=='merge_obligation_then_remove_transition':
        old=next((t for t in m['transitions'] if t['id']==op['transitionId']),None)
        if not old:continue
        target=next(r for r in m['requirements'] if r['id']==op['targetRequirementId'])
        edge=next(t for t in m['transitions'] if t['id']==target['transitionId'])
        state=next(s for s in m['states'] if s['id']==op['targetStateId'])
        for i,ac in enumerate(op['assertions']):
            target['acceptance'].append({'id':target['id']+'/FORMULA-'+op['transitionId']+'-'+str(i),'given':'已有合法提交后的已保存记录；'+ac['given']+'；先前已发生：'+ac['when'],'when':edge['event'],'then':ac['then']})
            state['facts']=list(dict.fromkeys(state['facts']+ac['then']))
        for obj in (target,edge,state):obj['sourceIds']=list(dict.fromkeys(obj['sourceIds']+op['sourceIds']))
        change('update',target['id'],op['meaning'],op['sourceIds'])
        delete(op['transitionId'],op['meaning'],op['sourceIds'])
    elif action=='update':update(op)
    elif action in ('add','add_failed_editor_back'):add(op)
    elif action=='add_returns_by_existing_origin':
        for t in list(m['transitions']):
            if t['from']!=op['copyFrom'] or t['event'] not in op['onlyEvents']:continue
            if t['to']=='CAL.no_items':continue
            cases=[]
            for case in m['pathContext']['transitionRules'][t['id']]['cases']:
                case=copy.deepcopy(case);req=case.setdefault('requires',{})
                valid=True
                for k,vs in op['casesConstraint'].items():
                    req[k]=[v for v in req.get(k,vs) if v in vs]
                    if not req[k]:valid=False
                if valid:cases.append(case)
            if not cases:continue
            add({'transitionId':'T-SEM-terminal-'+t['id'][2:],'from':op['from'],'to':t['to'],'event':t['event'],'guard':t['guard']+'；本项为普通当天一次性已保存终态','cases':cases,'then':op['then'],'sourceIds':op['sourceIds'],'reason':op['reason']})
    else:raise ValueError(action)

# Equivalent last-error correction applies to new-plan date input too.
tid='T-LINK-date-choice-CREATE-invalid'
update({'transitionId':tid,'guard':'弹层来自新建计划信息有误，所选日期合法，但其他字段或关联规则仍存在错误','sourceIds':['PRD-FR02','PRD-FR31'],'then':['所选日期仅更新未提交草稿；仍未修复字段继续显示错误，禁止最终保存。']})
add({'transitionId':'T-SEM-date-correct-create','from':'DRAFT.popup','to':'CREATE.ready','event':'选择日期并关闭日期弹层','guard':'弹层来自新建计划信息有误，所选日期修正后全部字段及关联规则合法','cases':[{'requires':{'draftOrigin':['CREATE.invalid']}}],'then':['日期更新同一未提交草稿，全部字段错误清除，保存资格恢复；尚未落盘。'],'sourceIds':['PRD-FR02','PRD-FR31']})
# Direct calendar save always leaves a record on the selected day.
delete('T-LINK-saved-calendar-zero','原直接日历记录入口保存后选日仍有记录；不能靠返回动作删去最后记录。',['PRD-FR10','PRD-FR14','PRD-FR15'])
path.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'states':len(m['states']),'transitions':len(m['transitions']),'changes':len(round_['changes'])}))
