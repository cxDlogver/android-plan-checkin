from pathlib import Path
import sys,json,time
root=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(root/'.codex/skills/requirements-analysis/scripts'))
from feasibility import analyze
m=json.loads((root/'plans/requirements-analysis-project-test/_process/analysis-model.json').read_text(encoding='utf-8'))
start=time.time();r=analyze(m,50000)
(root/'plans/requirements-analysis-project-test/_process/skill-validation/feasibility-result.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'seconds':time.time()-start,'counts':r['counts'],'issues':{k:v for k,v in r['transitions'].items() if v['status']!='finite_domain_passed'}},ensure_ascii=False))
