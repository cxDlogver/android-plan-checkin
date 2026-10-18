import json,copy
from pathlib import Path
base=Path(__file__).parent
exec(compile((base/'repair_model.py').read_text(encoding='utf-8').split('\nproposal=json.loads')[0],str(base/'repair_model.py'),'exec'))
pc=m['pathContext'];classes=['empty','none_completed','mixed','all_completed']
key='selectedCalendarRecord';pc['domains'][key]={'values':['yes','no'],'labels':{'yes':'选中计划在保留选日已有记录','no':'选中计划在保留选日没有记录'},'description':'FR14/26：区分未记录安排与失败/跳过等已有记录，归档只取消前者。'}
for c in pc['entryContexts'].values():c[key]=['no']
# Binding an item reads whether that item is already a persisted record.
for t in m['transitions']:
 for c in pc['transitionRules'][t['id']]['cases']:
  s=c.get('set',{})
  if 'selectedCalendarContribution' not in s:continue
  item=s['selectedCalendarContribution'];typ=s.get('selectedType',[])
  if t['from'].startswith('CAL.') and not t['to'].startswith('CAL.'):
   if item==['absent'] or t['to'] in ('RECORD.backfill','RECORD.choose'):vs=['no']
   elif item==['completed'] or t['to'] in ('RECORD.readonly','RECORD.edit'):vs=['yes']
   elif typ==['one']:vs=['no'] if set(s.get('oneOutcome',[]))<=set(['pending','overdue']) else ['yes']
   else:vs=['yes','no']
   s[key]=vs
  elif t['id'] in ('T-RECORD-commit-normal','T-RECORD-commit-backfill'):s[key]=['no'] if item==['absent'] else ['yes']
  elif item==['absent']:s[key]=['no']

def projection(other,item):
 if item=='absent':return other
 if other=='empty':return 'all_completed' if item=='completed' else 'none_completed'
 if other=='mixed':return 'mixed'
 return other if (other=='all_completed')==(item=='completed') else 'mixed'
def rows(req,item,effects):
 out=[]
 for other in classes:
  whole=projection(other,item)
  groups={}
  for f in ('all','completed','uncompleted'):
   positive=whole!='empty' and (f=='all' or f=='completed' and whole in ('mixed','all_completed') or f=='uncompleted' and whole in ('mixed','none_completed'))
   groups.setdefault('positive' if positive else 'zero',[]).append(f)
  for count,filters in groups.items():
   out.append({'requires':{**req,'calendarOtherCompletionClass':[other],'calendarFilter':filters},'set':{**effects,'selectedCalendarContribution':[item],'calendarCompletionClass':[whole],'calendarTotal':['zero' if whole=='empty' else 'positive'],'calendarFilteredCount':[count]}})
 return out
# An immediate deadline edit moves only that task's unrecorded deadline contribution.
cs=copy.deepcopy(pc['transitionRules']['T-MANAGE-success']['cases'])
base_req={'selectedType':['one'],'selectedLife':['running'],'oneOutcome':['pending','overdue'],'detailOrigin':['calendar']}
cs+=rows({**base_req,'selectedCalendarContribution':['uncompleted'],key:['no']},'absent',{'oneOutcome':['pending']})
cs+=rows({**base_req,'selectedCalendarContribution':['absent'],'calendarDay':['today','future'],key:['no']},'uncompleted',{'oneOutcome':['pending']})
cs.append({'requires':{'selectedType':['one'],'selectedLife':['running'],'oneOutcome':['pending','overdue'],'detailOrigin':['today','plans']},'set':{'oneOutcome':['pending']}})
update({'transitionId':'T-MANAGE-success','cases':cs,'sourceIds':['PRD-FR14','PRD-FR23'],'reason':'名称等修改不改日历；一次性实际修改截止并成功提交时，原截止安排移出/新截止安排移入选日。分支只抽象本次实际保存字段与新旧日期关系，不在返回时改数据。'})
r=next(r for r in m['requirements'] if r['id']=='R-MANAGE-success');r['acceptance'].append({'id':r['id']+'/DEADLINE','given':'未终结一次性计划实际修改了截止日期，最终校验合法','when':'本机编辑事务成功','then':['新截止立即生效；原截止安排移除、新截止增加同一计划的安排，其他计划和已有记录不变。仅修改名称或保存未触及截止时，不触发此日期移动。']})
update({'transitionId':'T-TIME-extend','cases':[{'requires':{'selectedType':['one'],'selectedLife':['running'],'oneOutcome':['pending']}}],'sourceIds':['PRD-FR23'],'reason':'读取已合法保存的新截止结果；pending在实际成功编辑时生效，读页面本身不修改任务。'})
# Archive preserves saved records and past obligations; only unrecorded today/future arrangements disappear.
base_effect={'selectedLife':['archived'],'pendingChange':['none']};cs=[{'requires':{'detailOrigin':['today','plans','none']},'set':base_effect},{'requires':{'detailOrigin':['calendar'],'calendarDay':['past']},'set':base_effect},{'requires':{'detailOrigin':['calendar'],'calendarDay':['today','future'],key:['yes']},'set':base_effect},{'requires':{'detailOrigin':['calendar'],'calendarDay':['today','future'],key:['no'],'selectedCalendarContribution':['absent']},'set':base_effect}]
cs+=rows({'detailOrigin':['calendar'],'calendarDay':['today','future'],key:['no'],'selectedCalendarContribution':['uncompleted']},'absent',base_effect)
update({'transitionId':'T-LIFE-archive-submit','cases':cs,'sourceIds':['PRD-FR14','PRD-FR26'],'reason':'归档成功取消未记录当日/未来安排；过去有效要求和任何已保存记录保留。通过有据的记录存在性限制，不将失败/跳过记录误当空白删除。'})
# Permanent deletion re-reads remaining lists; navigation only consumes the result.
for c in pc['transitionRules']['T-LIFE-delete-success']['cases']:
 c['forget']=list(dict.fromkeys(c.get('forget',[])+['listCount','calendarTotal','calendarFilteredCount','calendarCompletionClass','calendarOtherCompletionClass']))
 c['set'].update({'selectedCalendarContribution':['absent'],key:['no']})
path.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'transitions':len(m['transitions']),'cases':sum(len(x['cases'])for x in pc['transitionRules'].values())}))
