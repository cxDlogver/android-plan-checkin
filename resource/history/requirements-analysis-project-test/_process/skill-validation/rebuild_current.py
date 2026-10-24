import sys,json,time,faulthandler
faulthandler.dump_traceback_later(60,repeat=True)
from pathlib import Path
base=Path(__file__).parent.resolve();root=base.parent.parent
scripts=base/'skill/requirements-analysis/scripts'
if not scripts.exists():scripts=base.parents[3]/'.codex/skills/requirements-analysis/scripts'
sys.path.insert(0,str(scripts))
import workflow as wf
old=wf.read(wf.work(root,'gate-contract.json'));template=wf.read(wf.TEMPLATE)
wf.write(wf.work(root,'gate-contract.json'),{**template,'run_id':old['run_id'],'analyzer_context_ref':old['analyzer_context_ref'],'template_digest':wf.digest(template)})
state=wf.read(wf.work(root,'run-state.json'))
state.update(active_node_id=None,waiting_for_user=False,pause_reason=None,next_action='Complete current-digest full semantic audit and independent review; do not reuse old approvals. Deterministic transition witnesses and route replay are available.')
wf.write(wf.work(root,'run-state.json'),state)
wf.save_current(root)
model,_=wf.load_current(root)
start=time.time();manifest=wf.export_bundle(model,root,root)
result=wf.gate(root,bundle=root)
print(json.dumps({'seconds':time.time()-start,'semantic_digest':manifest['semantic_digest'],'bundle_digest':manifest['bundle_digest'],'gate':result['gate_status'],'checks':{k:v['status'] for k,v in result['checks'].items()},'failureCount':len(result['failures'])},ensure_ascii=False))
