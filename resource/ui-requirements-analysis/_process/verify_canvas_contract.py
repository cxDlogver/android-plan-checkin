"""Execute the current Canvas contract on behavior models and an incomplete draft."""
import sys,tempfile,subprocess,json,copy
from pathlib import Path
w=Path(__file__).resolve().parent
s=w.parent.parent.parent/'.codex/skills/requirements-analysis'
sys.path.insert(0,str(s/'scripts'))
import test_workflow,test_atomic_contract
import model_tools as mt
from render_review import render
tempfile.tempdir=str(w/'verification/temp')
test_workflow.TEST_ROOT=w/'verification/temp'
t=test_atomic_contract.AtomicContractTests('test_single_transition_legitimately_has_no_continuation_edge')
t.setUp()
try:
 base=t.baseline()
 legacy3=copy.deepcopy(base);legacy3.update(schemaVersion=3,phase='analyzing')
 multi=copy.deepcopy(base);multi['phase']='analyzing'
 state=copy.deepcopy(multi['states'][1]);state.update(id='S2',title='confirmed',facts=['confirmed'])
 multi['states'].append(state)
 edge=copy.deepcopy(multi['transitions'][0]);edge.update(id='T2',requirementId='R2',event='confirm',**{'from':'S1','to':'S2'})
 req=copy.deepcopy(multi['requirements'][0]);req.update(id='R2',transitionId='T2',title='confirm')
 req['acceptance']=[{'id':'AC2','given':'present','when':'confirm','then':['confirmed']}]
 multi['transitions'].append(edge);multi['requirements'].append(req)
 cases={'legacy-behavior':base,'legacy-v3-behavior':legacy3,'multi-step-behavior':multi,'incomplete-draft':t.unsupported_draft()}
 results={}
 node=Path('D:/xiang/CX_application/1_Configuration_Files/Front_Rear_END/nodeJS/node.exe')
 for name,model in cases.items():
  errors,_=mt.validate(model)
  if errors:raise ValueError(name+': '+'; '.join(errors))
  html=w/'verification'/f'{name}.html'
  html.write_text(render(model,mt.exports(model)),encoding='utf-8')
  call=subprocess.run([str(node),str(s/'scripts/test_canvas.mjs'),str(html)],encoding='utf-8',capture_output=True)
  results[name]={'returncode':call.returncode,'result':json.loads(call.stdout) if call.stdout.startswith('{') else call.stdout,'stderr':call.stderr}
 (w/'evidence/canvas-contract-tests.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps(results,ensure_ascii=False,indent=2))
 raise SystemExit(any(r['returncode'] for r in results.values()))
finally:
 t.doCleanups()

