import json,copy,itertools
from pathlib import Path
base=Path(__file__).parent
exec(compile((base/'repair_model.py').read_text(encoding='utf-8').split('\nproposal=json.loads')[0],str(base/'repair_model.py'),'exec'))
p=json.loads((base/'repair-proposal-a.json').read_text(encoding='utf-8'));pc=m['pathContext'];D=pc['domains']
classes=['empty','none_completed','mixed','all_completed']
clabels={'empty':'没有项','none_completed':'仅未完成项','mixed':'完成与未完成项都有','all_completed':'仅完成项'}
for key,labels,desc in [('calendarCompletionClass',clabels,'FR14/FR15：选日U、C和T-C的零/正数量类别；筛选只投影不改事实。'),('calendarOtherCompletionClass',clabels,'FR14/FR15：除当前选中计划外的其他选日执行项类别；单项写入不得任意改变其他项。'),('selectedCalendarContribution',{'absent':'所选计划在选日无执行项','uncompleted':'所选计划在选日贡献一个未完成项','completed':'所选计划在选日贡献一个完成项'},'FR14：同一计划在同一日最多一个执行项；区别当前项与其余项以确定写入的聚合结果。'),('recordCalendarRelation',{'none':'本次记录不关联来源日历','same':'记录业务日就是保留的选日','different':'记录业务日不同于保留选日'},'FR10/FR14：记录日与来源选日是否为同一天；一次性结果日替代原截止日，循环其他日写入不改选日。')]:
 D[key]={'values':list(labels),'labels':labels,'description':desc}
 for ctx in pc['entryContexts'].values():ctx[key]=list(labels) if key.startswith('calendar') else ['absent' if key=='selectedCalendarContribution' else 'none']
# Every true date read supplies a correlated count projection. Browsing/return never reinitializes it.
readids=set(p['filterProjection']['affectedReadTransitionIds'])|{'T-COVER-tab-CAL-all-ROOT-empty'}
for t in m['transitions']:
 if t['id'] not in readids:continue
 rule=pc['transitionRules'][t['id']];out=[]
 for old in rule['cases']:
  basecase=copy.deepcopy(old);s=basecase.setdefault('set',{})
  if t['id']=='T-CAL-time-change':s['calendarTotal']=['positive']
  total=s.get('calendarTotal',['positive' if t['to']!='CAL.no_items' else 'zero'])[0]
  kinds=['empty'] if total=='zero' else ['none_completed'] if s.get('calendarDay')==['future'] else classes[1:]
  for kind in kinds:
   c=copy.deepcopy(basecase);c['set'].update({'calendarCompletionClass':[kind],'calendarOtherCompletionClass':[kind],'selectedCalendarContribution':['absent'],'calendarFilteredCount':[total]})
   c['forget']=[k for k in c.get('forget',[]) if k not in c['set']];out.append(c)
 update({'transitionId':t['id'],'cases':out,'sourceIds':['PRD-FR14','PRD-FR15'],'reason':'只有进入日历或真正更换选日才读取该日集合；完成类别及筛选数量相关初始化。'})
for op in p['filterProjection']['exactRules']:update({**op,'sourceIds':['PRD-FR14','PRD-FR15'],'reason':'由同一选日的完成数量类别确定筛选结果，禁止切换筛选制造数据变化。'})
for sid,c in pc['stateConstraints'].items():
 if sid.startswith('CAL.') and sid not in ('CAL.filter_open',):
  if sid=='CAL.no_items':c['requires']['calendarCompletionClass']=['empty']
  elif sid=='CAL.future':c['requires']['calendarCompletionClass']=['none_completed']
  else:c['requires']['calendarCompletionClass']=classes[1:]
# Combine one selected contribution with stable other items.
def combine(other,item):
 if item=='absent':return other
 if other=='empty':return 'all_completed' if item=='completed' else 'none_completed'
 if other=='mixed':return 'mixed'
 if (other=='all_completed')==(item=='completed'):return other
 return 'mixed'
def count(kind,filt):
 if kind=='empty':return 'zero'
 if filt=='all':return 'positive'
 return 'positive' if (filt=='completed' and kind in ('mixed','all_completed')) or (filt=='uncompleted' and kind in ('mixed','none_completed')) else 'zero'
def compatible(c,key,vals):
 r=c.setdefault('requires',{});v=[x for x in r.get(key,vals) if x in vals]
 if not v:return False
 r[key]=v;return True
# Calendar item selection binds the real visible contribution and remaining items, including independent blank weekly rows.
for t in m['transitions']:
 if not t['from'].startswith('CAL.') or t['to'].startswith('CAL.'):continue
 oldcases=pc['transitionRules'][t['id']]['cases']
 if not any('selectedType' in c.get('set',{}) for c in oldcases):continue
 out=[]
 for old in oldcases:
  for typ in old.get('set',{}).get('selectedType',['none']):
   c0=copy.deepcopy(old);c0['set']['selectedType']=[typ]
   if t['to']=='RECORD.backfill':items=['absent'] if typ=='weekly' else ['uncompleted']
   elif t['to']=='RECORD.choose':items=['uncompleted']
   elif typ=='one':
    outcomes=c0['set'].get('oneOutcome',['on_time','late','failed','cancelled'] if t['to']=='RECORD.edit' else ['pending','overdue','on_time','late','failed','cancelled'])
    items=list(dict.fromkeys('completed' if x in ('on_time','late') else 'uncompleted' for x in outcomes))
   else:items=['completed','uncompleted']
   for item in items:
    c1=copy.deepcopy(c0)
    if typ=='one':
     outcomes=c1['set'].get('oneOutcome',['on_time','late','failed','cancelled'])
     c1['set']['oneOutcome']=[x for x in outcomes if (x in ('on_time','late'))==(item=='completed')]
     if not c1['set']['oneOutcome']:continue
     c1['set']['pendingChange']=['none']
    else:c1['set']['oneOutcome']=['none']
    if t['to']=='RECORD.edit':
     c1['set']['recordResult']=['complete'] if typ=='one' and item=='completed' else ['failure','cancelled'] if typ=='one' else ['success'] if item=='completed' else ['failure','skip']
     c1['forget']=[x for x in c1.get('forget',[]) if x!='recordResult']
    # Independent weekly empty-day area does not participate in current main-list filter.
    if item!='absent':
     allowed=['all','completed'] if item=='completed' else ['all','uncompleted']
     if not compatible(c1,'calendarFilter',allowed):continue
    for other in classes:
     whole=combine(other,item);c=copy.deepcopy(c1)
     if not compatible(c,'calendarCompletionClass',[whole]):continue
     if not compatible(c,'calendarTotal',['zero' if whole=='empty' else 'positive']):continue
     if t['from']=='CAL.future' and whole!='none_completed':continue
     if t['from']=='CAL.no_items' and whole!='empty':continue
     if t['from'] in ('CAL.all','CAL.filtered','CAL.no_matches') and whole=='empty':continue
     c['set'].update({'selectedCalendarContribution':[item],'calendarOtherCompletionClass':[other]})
     if t['to'] in ('RECORD.choose','RECORD.backfill','RECORD.edit'):c['set']['recordCalendarRelation']=['same']
     out.append(c)
 if out:update({'transitionId':t['id'],'cases':out,'sourceIds':['PRD-FR14','PRD-FR15'],'reason':'绑定被选择项及其余项；筛选可见性、一次性结果及后续保存采用同一组事实。'})
# Non-calendar entry resets correlation; detail entry retains its selected contribution.
for t in m['transitions']:
 if t['to'] not in ('RECORD.choose','RECORD.one','RECORD.backfill','RECORD.edit'):continue
 if t['from'].startswith(('CAL.','RECORD.','DRAFT.','LIFE.')):continue
 oldcases=pc['transitionRules'][t['id']]['cases'];out=[]
 for old in oldcases:
  if old.get('set',{}).get('recordOrigin')==['today']:
   c=copy.deepcopy(old);c['set']['recordCalendarRelation']=['none'];out.append(c);continue
  if old.get('set',{}).get('recordOrigin')!=['detail']:out.append(old);continue
  c=copy.deepcopy(old)
  if compatible(c,'detailOrigin',['today','plans','none']):c.setdefault('set',{})['recordCalendarRelation']=['none'];out.append(c)
  for day in ('past','today','future'):
   if t['to']=='RECORD.one':rels=['different'] if day=='future' else ['same','different']
   elif t['to']=='RECORD.backfill':rels=['same','different'] if day=='past' else ['different']
   else:rels=['same'] if day=='today' else ['different']
   for rel in rels:
    c=copy.deepcopy(old)
    if not compatible(c,'detailOrigin',['calendar']) or not compatible(c,'calendarDay',[day]):continue
    if rel=='same' and t['to']=='RECORD.backfill':
     typ=c.get('requires',{}).get('selectedType',[])
     if not compatible(c,'selectedCalendarContribution',['absent'] if typ==['weekly'] else ['uncompleted']):continue
    if rel=='same' and t['to']=='RECORD.choose' and not compatible(c,'selectedCalendarContribution',['absent','uncompleted']):continue
    if t['to']=='RECORD.edit' and c.get('requires',{}).get('selectedType')==['one']:
     if not compatible(c,'selectedLife',['running']) or not compatible(c,'oneOutcome',['on_time','late','failed','cancelled']):continue
    c.setdefault('set',{})['recordCalendarRelation']=[rel];out.append(c)
 if out:update({'transitionId':t['id'],'cases':out,'sourceIds':['PRD-FR10','PRD-FR11','PRD-FR14'],'reason':'按实际记录业务日绑定来源选日关系，其他日期写入不冒充改变当前选日。'})
# Save success mutates only selected contribution; all aggregate fields derive from that contribution and stable other items.
for tid in ('T-RECORD-commit-normal','T-RECORD-commit-backfill'):
 out=[]
 for old in pc['transitionRules'][tid]['cases']:
  types=old.get('requires',{}).get('selectedType',[])
  c=copy.deepcopy(old)
  if compatible(c,'recordCalendarRelation',['none']):out.append(c)
  if 'one' not in types:
   c=copy.deepcopy(old)
   if compatible(c,'recordCalendarRelation',['different']):out.append(c)
  for rel in (['same','different'] if types==['one'] else ['same']):
   for result,item in ([(['complete'],'completed'),(['failure','cancelled'],'uncompleted')] if types==['one'] else [(['success'],'completed'),(['failure','skip'],'uncompleted')]):
    for other in classes:
     for filt in ('all','completed','uncompleted'):
      c=copy.deepcopy(old)
      if not all(compatible(c,k,v) for k,v in [('recordCalendarRelation',[rel]),('recordResult',result),('calendarOtherCompletionClass',[other]),('calendarFilter',[filt])]):continue
      newitem='absent' if rel=='different' else item;whole=combine(other,newitem)
      c.setdefault('set',{}).update({'selectedCalendarContribution':[newitem],'calendarCompletionClass':[whole],'calendarTotal':['zero' if whole=='empty' else 'positive'],'calendarFilteredCount':[count(whole,filt)]})
      if types==['one']:
       valid=['on_time','late'] if item=='completed' else ['failed','cancelled']
       if not compatible(c,'proposedOneOutcome',valid):continue
      out.append(c)
 update({'transitionId':tid,'cases':out,'sourceIds':['PRD-FR10','PRD-FR14','PRD-FR15'],'reason':'真实提交只改变当前计划在选日的贡献；固定/周目标其他日保持选日，一次性异日结果移除原截止项；按其余项确定T/C和当前筛选。'})
# If cross-day failure/cancellation is explicitly re-confirmed for new today, it no longer targets the old selected calendar day.
r=pc['transitionRules']['T-RECORD-one-reset'];r['cases'][0].setdefault('set',{})['recordCalendarRelation']=['different']
# Actual disappearance needs a real fresh read; invalidate correlated derived facts together, never on ordinary return.
r=pc['transitionRules'].get('T-SEM-detail-confirmed-missing')
if r:
 for c in r['cases']:c['forget']=list(dict.fromkeys(c.get('forget',[])+['calendarCompletionClass','calendarOtherCompletionClass','selectedCalendarContribution']))
path.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'transitions':len(m['transitions']),'cases':sum(len(r['cases']) for r in pc['transitionRules'].values()),'batch':'calendar correlated projection'}))
