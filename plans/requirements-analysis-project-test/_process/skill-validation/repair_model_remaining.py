import json,copy
from pathlib import Path
base=Path(__file__).parent
exec(compile((base/'repair_model.py').read_text(encoding='utf-8').split('\nproposal=json.loads')[0],str(base/'repair_model.py'),'exec'))
pc=m['pathContext']
def replace_cases(tid,cs,sources,reason):
    update({'transitionId':tid,'cases':cs,'sourceIds':sources,'reason':reason})
# Source-specific states cannot use cases copied from other types.
for t in m['transitions']:
    tid=t['id'];cs=pc['transitionRules'][tid]['cases']
    if tid.startswith('T-COVER-type-confirm-') and t['from'] in ('CREATE.fixed','CREATE.weekly','CREATE.one'):
        typ=t['from'].split('.')[1];replace_cases(tid,[c for c in cs if typ in c.get('requires',{}).get('draftType',[])],['PRD-FR02'],'类型页已确定原类型；删除其他类型页复制来的不适用条件，不删除实际切换需求。')
    if tid=='T-RECORD-FIX-ordinary-correct':
        replace_cases(tid,[c for c in cs if 'one' in c.get('requires',{}).get('selectedType',[])],['PRD-FR09','PRD-FR11'],'一次性当日终态只支持一次性修订；循环条件属于其他已有修订入口。')
    if tid.endswith('RECORD-FIX-detail-history') and t['from'].startswith(('STATS.','TIME.')):
        isone=t['from'] in ('STATS.one','TIME.on_time','TIME.late');replace_cases(tid,[c for c in cs if ('one' in c.get('requires',{}).get('selectedType',[]))==isone],['PRD-FR16','PRD-FR20'],'详情按当前所选计划类型读取其已有历史，不能在同一计划读取中切换为另一类型。')
# Cross-midnight preserves the selected date's saved facts and prior valid historical obligations.
tid='T-CAL-time-change';cs=[]
for c in pc['transitionRules'][tid]['cases']:
    if c.get('requires',{}).get('calendarDay')==['future']:continue
    c=copy.deepcopy(c)
    for key in ('calendarTotal','calendarFilteredCount','calendarCompletionClass','calendarOtherCompletionClass','selectedCalendarContribution'):c.get('set',{}).pop(key,None)
    c['forget']=[]
    if c not in cs:cs.append(c)
replace_cases(tid,cs,['PRD-FR14','PRD-COMMON'],'跨午夜改变今天标记及原今天的日期关系，保留同一选日的已有记录和历史要求；没有真实写入时不重新随机生成数量。')
# These clean exits have no corresponding source entry and no write which could create the destination.
for tid in ('T-SEM-clean-CREATE-fixed-ROOT-today','T-SEM-clean-RECORD-edit-CAL-no_items','T-SEM-clean-RECORD-edit-CAL-no_matches','T-SEM-clean-RECORD-edit-ROOT-empty'):
    delete(tid,'无修改退出只返回真实原入口；没有新增入口、删除或结果修改时不能改变来源分类。',['PRD-FR01','PRD-FR11','PRD-FR31'])
# Weekly existing calendar records cannot disappear just by viewing aggregate statistics.
for kind in ('weekly','partial','week_closed'):
    delete('T-LINK-return-COVER-STATS-'+kind+'-NAV-return-calendar-zero','周目标从日历项进入后，该日已有记录；详情/统计/补记不能删除单条已有记录，故不能返回选日零项。',['PRD-FR14','PRD-FR19','PRD-FR29'])
path.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'transitions':len(m['transitions'])}))
