import json,copy
from pathlib import Path
base=Path(__file__).parent
exec(compile((base/'repair_model.py').read_text(encoding='utf-8').split('\nproposal=json.loads')[0],str(base/'repair_model.py'),'exec'))
pc=m['pathContext']
for t in m['transitions']:
 tid=t['id'];out=[];changed=False
 for old in pc['transitionRules'][tid]['cases']:
  c=copy.deepcopy(old);r=c.get('requires',{});drop=False
  if tid=='T-RECORD-commit-backfill' and r.get('selectedType')==['one'] and r.get('recordCalendarRelation') in (['same'],['different']):
   # Pending one-off tasks are visible only in all/uncompleted at their deadline.
   if 'calendarFilter' in r:r['calendarFilter']=[v for v in r['calendarFilter'] if v!='completed'];drop=not r['calendarFilter']
  if tid in ('T-MANAGE-success','T-LIFE-archive-submit') and r.get('detailOrigin')==['calendar'] and r.get('selectedCalendarRecord')==['no'] and r.get('selectedCalendarContribution') in (['absent'],['uncompleted']):
   if 'calendarFilter'in r:r['calendarFilter']=[v for v in r['calendarFilter'] if v!='completed'];drop=not r['calendarFilter']
  if tid.startswith(('T-SEM-detail-backfill-STATS-','T-SEM-detail-record-today-STATS-')) and r.get('selectedType')==['weekly'] and r.get('detailOrigin')==['calendar'] and r.get('calendarDay')==['future']:drop=True
  if drop or c!=old:changed=True
  if not drop:out.append(c)
 if changed:
  assert out
  update({'transitionId':tid,'cases':out,'sourceIds':['PRD-FR14','PRD-FR15'],'reason':'按实际入口特化聚合公式的条件：未终结一次性/未记录安排不在已完成列表，未来日历没有周目标记录；去掉公式笛卡尔展开造成的不适用组合，保留原行为及所有合法结果。'})
path.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'transitions':len(m['transitions']),'cases':sum(len(r['cases'])for r in pc['transitionRules'].values())}))
