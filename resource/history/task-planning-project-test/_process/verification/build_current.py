import sys,json,contextlib
from pathlib import Path
root=Path(__file__).resolve().parents[2]
stage=root/'_process/skill/task-planning'
if not stage.exists():stage=root.parents[1]/'.codex/skills/task-planning'
sys.path.insert(0,str(stage/'scripts'))
import planning
p,g=planning.build(root)
print(json.dumps({'mechanical':g['mechanical'],'counts':g['counts'],'sourceRouteConflicts':sum(r['contextStatus']=='conflict' for r in p['routes']['routes']),'draftIssues':len(g['readiness']['issues'])},ensure_ascii=False))
(root/'_process/verification/forward-result.json').write_text(json.dumps({'planningDigest':p['planningDigest'],'codeDigest':p['codeDigest'],'mechanical':g['mechanical'],'counts':g['counts'],'readiness':g['readiness']['status'],'productAcceptance':'NOT_RUN'},ensure_ascii=False,indent=2),encoding='utf-8')
