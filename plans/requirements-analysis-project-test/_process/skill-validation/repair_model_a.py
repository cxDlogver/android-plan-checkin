import json,copy
from pathlib import Path
base=Path(__file__).parent
exec(compile((base/'repair_model.py').read_text(encoding='utf-8').split('\nproposal=json.loads')[0],str(base/'repair_model.py'),'exec'))
p=json.loads((base/'repair-proposal-a.json').read_text(encoding='utf-8'))
for op in p['exactBackfillRules']:update(op)
for op in p['newCalendarTodayTransitions']:add({**op,'transitionId':op['id']})
for t in list(m['transitions']):
 if t['id'].startswith('T-COVER-type-direct-'):
  cs=copy.deepcopy(m['pathContext']['transitionRules'][t['id']]['cases'])
  for c in cs:c.setdefault('requires',{})['draftType']=[v for v in ('fixed','weekly','one') if v not in c['set']['draftType']]
  update({'transitionId':t['id'],'cases':cs,'sourceIds':['PRD-FR02'],'reason':'切换必须选择不同类型；当前类型不可当作类型切换。'})
update({'transitionId':'T-RECORD-select','cases':[{'requires':{'selectedType':['fixed','weekly']},'set':{'recordResult':['success','failure','skip']}}],'sourceIds':['PRD-FR10'],'reason':'选择实际更新未提交结果；备注与选项不会提前写库。'})
# Discard-free exits are limited to reachable unmodified forms, never mechanically cloned to other form types.
for source in ('CREATE.fixed','RECORD.edit'):
 for old in list(m['transitions']):
  if old['from']!='DRAFT.ask' or '放弃' not in old['event']:continue
  cases=copy.deepcopy(m['pathContext']['transitionRules'][old['id']]['cases'])
  if source=='CREATE.fixed':
   cases=[c for c in cases if any(x in ('today','plans') for x in c.get('requires',{}).get('editorReturn',[]))]
  else:
   cases=[c for c in cases if any(x in ('today','calendar','detail') for x in c.get('requires',{}).get('editorReturn',[]))]
  if not cases:continue
  add({'transitionId':'T-SEM-clean-'+source.replace('.','-')+'-'+old['to'].replace('.','-'),'from':source,'to':old['to'],'event':'无未保存变化时直接返回','guard':'当前表单未发生未保存变化，键盘和弹层已关闭；'+old['guard'],'cases':cases,'then':['直接返回真实来源页面，保持其日期、筛选和数据；不显示放弃更改确认，不写入。'],'sourceIds':['PRD-FR31'],'reason':'FR31只对未保存变化确认；限定首次空新建和未改动的普通记录修订。'})
add({'transitionId':'T-SEM-day-changed-leave','from':'RECORD.day_changed','to':'DRAFT.ask','event':'返回并请求离开日期变化确认','guard':'仍有未保存记录输入，用户点击返回日历或返回键','cases':[{'set':{'draftOrigin':['RECORD.day_changed']}}],'then':['显示放弃更改确认；保留原输入与真实来源，未获确认不丢弃草稿。'],'sourceIds':['PRD-FR10','PRD-FR31','UI-HEOev'],'domainExtension':{'draftOrigin':{'value':'RECORD.day_changed','label':'业务日期已变化，原输入尚未提交'}}})
add({'transitionId':'T-SEM-day-changed-continue','from':'DRAFT.ask','to':'RECORD.day_changed','event':'继续编辑','guard':'离开确认来自业务日期变化提示','cases':[{'requires':{'draftOrigin':['RECORD.day_changed']}}],'then':['恢复日期变化提示及原未提交输入；不得绕过重新确认直接提交。'],'sourceIds':['PRD-FR10','PRD-FR31','UI-HEOev']})
for tid in ('T-RECORD-new-day','T-RECORD-one-new-day','T-LINK-record-failed-day-changed'):
 old=m['pathContext']['transitionRules'][tid]['cases'];cs=[]
 for c in old:
  for day,after in [('past',['past']),('today',['past']),('future',['past','today','future'])]:
   z=copy.deepcopy(c);z.setdefault('requires',{})['calendarDay']=[day];z.setdefault('set',{})['calendarDay']=after;cs.append(z)
 update({'transitionId':tid,'cases':cs,'sourceIds':['PRD-FR10','PRD-FR14'],'reason':'固定时区业务今天已变化，原完整日历日期保持；原今天已成为过去日，不能仍按今日允许普通写入。'})
# Separate changed date from archive: both remove edit permission but only changed date moves the day relation.
update({'transitionId':'T-RECORD-edit-new-day','guard':'原记录业务日期已经早于当前计划今天','cases':[{'requires':{'calendarDay':['today']},'set':{'calendarDay':['past'],'recordMode':['none']}},{'requires':{'calendarDay':['past','future']},'set':{'recordMode':['none']}}],'sourceIds':['PRD-FR11','PRD-FR14'],'reason':'跨日只读不改变原记录；日历选中今天已变过去，归档资格另走明确分支。'})
add({'transitionId':'T-SEM-record-edit-archived','from':'RECORD.edit','to':'RECORD.readonly','event':'保存前重新读取发现计划已归档','guard':'当前记录仍为同一业务日期，但所选计划已归档，尚未提交本次修改','cases':[{'set':{'selectedLife':['archived'],'recordMode':['none']}}],'then':['拒绝修改并显示原记录只读；本次输入没有覆盖旧记录。'],'sourceIds':['PRD-FR11','PRD-FR28']})
# Calendar aggregation is an assertion on real writes, not a freestanding event that fabricates data.
for tid in ('T-CAL-FIX-membership','T-CAL-reaggregate-empty'):delete(tid,'聚合是实际来源写入后的派生结果，不存在独立任意改变选日集合的用户事件；验收义务归入真实提交。',['PRD-FR14','PRD-FR15'])
for tid in ('T-RECORD-commit-normal','T-RECORD-commit-backfill','T-MANAGE-success'):
 t=next((x for x in m['transitions'] if x['id']==tid),None)
 if not t:continue
 r=next(x for x in m['requirements'] if x['id']==t['requirementId']);r['acceptance'].append({'id':r['id']+'/CALENDAR','given':'成功写入影响选中日期的执行项或结果；日历来源和筛选仍在','when':t['event'],'then':['按FR14的选日执行集合重算T与C，FR15筛选从同一集合投影；返回只读取此结果，不另造记录或执行项。']});r['sourceIds']=list(dict.fromkeys(r['sourceIds']+['PRD-FR14','PRD-FR15']))
# History rows obey completed/uncompleted membership, rather than assigning terminal outcomes independently.
tid='T-COVER-history-filtered';old=m['pathContext']['transitionRules'][tid]['cases'];cs=[]
for c in old:
 for f in ('completed','uncompleted'):
  z=copy.deepcopy(c);z['requires']['calendarFilter']=[f]
  if z['set']['selectedType']==['one']:z['set']['oneOutcome']=['on_time','late'] if f=='completed' else ['failed','cancelled']
  cs.append(z)
update({'transitionId':tid,'cases':cs,'sourceIds':['PRD-FR14','PRD-FR15'],'reason':'主列表筛选约束被点击记录，不能从未完成列表读取成已完成终态。'})
for tid in ('T-NAV-detail-today','T-NAV-detail-list'):
 old=m['pathContext']['transitionRules'][tid]['cases'][0];cs=[]
 cyc=copy.deepcopy(old);cyc['set']['selectedType']=['fixed','weekly'];cyc['set']['oneOutcome']=['none'];cyc['forget']=['pendingChange'];cs.append(cyc)
 one=copy.deepcopy(old);one['set']['selectedType']=['one'];one['set']['oneOutcome']=['pending','overdue','on_time','late','failed','cancelled'];one['set']['pendingChange']=['none'];one['forget']=[]
 if tid.endswith('list'):one['requires']['listFilter']=['running','archived']
 cs.append(one);update({'transitionId':tid,'cases':cs,'sourceIds':['PRD-FR01','PRD-FR21','PRD-FR28'],'reason':'循环计划没有一次性结果；一次性没有暂停分类和待生效暂停/恢复，选择时绑定真实分类。'})
path.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'transitions':len(m['transitions']),'batch':'A core'}))
