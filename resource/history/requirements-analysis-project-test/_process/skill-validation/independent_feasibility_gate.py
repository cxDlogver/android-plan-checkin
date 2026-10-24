"""Inspect actual current gate with all production writes intercepted."""
import hashlib,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
RUN=HERE.parent.parent
sys.dont_write_bytecode=True
sys.path.insert(0,str(RUN.parents[1]/'.codex/skills/requirements-analysis/scripts'))
import workflow
suppressed=[]
workflow.atomic_json=lambda path,value:suppressed.append(str(path.relative_to(RUN)))
model_bytes=(RUN/'_process/analysis-model.json').read_bytes()
before={p:hashlib.sha256((RUN/p).read_bytes()).hexdigest() for p in ['_process/analysis-model.json','_process/gate-contract.json','_process/run-state.json','manifest.json']}
record={'readOnly':True,'modelSha256':hashlib.sha256(model_bytes).hexdigest(),'browserObserved':False}
try:
    record['gate']=workflow.gate(RUN,RUN)
except Exception as exc:
    record['exception']=repr(exc)
record['suppressedWrites']=suppressed
record['inputsChangedDuringRun']=[p for p,h in before.items() if hashlib.sha256((RUN/p).read_bytes()).hexdigest()!=h]
(HERE/'independent-feasibility-gate.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(record,ensure_ascii=False,indent=2))
