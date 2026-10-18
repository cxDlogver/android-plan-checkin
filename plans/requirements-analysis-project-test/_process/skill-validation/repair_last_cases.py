import json
from pathlib import Path
base=Path(__file__).parent
exec(compile((base/'repair_model.py').read_text(encoding='utf-8').split('\nproposal=json.loads')[0],str(base/'repair_model.py'),'exec'))
for name in ('weekly','partial','week_closed'):
 tid='T-SEM-detail-backfill-STATS-'+name
 cases=m['pathContext']['transitionRules'][tid]['cases']
 cases=[c for c in cases if not (c.get('requires',{}).get('detailOrigin')==['calendar'] and c.get('set',{}).get('recordCalendarRelation')==['same'])]
 update({'transitionId':tid,'cases':cases,'sourceIds':['PRD-FR10','PRD-FR14','PRD-FR19'],'reason':'周目标从日历主列表项进入详情时，该日已经有记录，不存在同一天首次补记；仍允许详情补记其他合法空白日，并保留日历独立补记区的原入口。'})
path.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
