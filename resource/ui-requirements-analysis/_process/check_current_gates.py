import json,sys
from pathlib import Path
w=Path(__file__).resolve().parent
sys.path.insert(0,str(w.parent.parent.parent/'.codex/skills/requirements-analysis/scripts'))
import workflow as wf
r=wf.gate(w.parent,w.parent,w/'model-review.json' if (w/'model-review.json').exists() else None)
print(json.dumps({'gate_status':r['gate_status'],'checks':{k:v['status'] for k,v in r['checks'].items()},'failures':r.get('failures',[])},ensure_ascii=False,indent=2))

