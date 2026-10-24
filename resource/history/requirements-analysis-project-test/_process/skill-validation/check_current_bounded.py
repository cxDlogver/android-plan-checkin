import sys,json,time
from pathlib import Path
base=Path(__file__).parent
sys.path.insert(0,str(base.parents[3]/'.codex/skills/requirements-analysis/scripts'))
from feasibility import Solver,model_key,verify_witnesses
from collections import Counter
import hashlib
m=json.loads((base.parent/'analysis-model.json').read_text(encoding='utf-8'));solver=Solver(m);out={};cases={};start=time.time()
for i,t in enumerate(m['transitions']):
 tid=t['id'];out[tid]=solver.witness(tid,5000);cases[tid]=[]
 for ci in range(len(solver.rules[tid])):
  if out[tid].get('ruleCases',[])[-1:]==[ci]:w=out[tid]
  else:w=solver.witness(tid,5000,ci)
  cases[tid].append(w)
 if i%50==0:print(json.dumps({'done':i+1,'elapsed':round(time.time()-start),'edge':tid}),flush=True)
ec=Counter(w['status'] for w in out.values());cc=Counter(w['status'] for rs in cases.values() for w in rs)
r={'method':'symbolic_backward_astar','scope':'declared_finite_domains','inputDigest':hashlib.sha256(model_key(m).encode()).hexdigest(),'status':'failed' if ec['infeasible'] or cc['infeasible'] else 'incomplete' if ec['incomplete'] or cc['incomplete'] or cc['structure_only'] else 'passed','counts':dict(ec),'transitions':out,'caseCounts':dict(cc),'caseResults':cases}
assert not verify_witnesses(m,r),verify_witnesses(m,r)
(base/'feasibility-result.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
bad=[{'id':tid,'case':ci,'status':w['status']}for tid,rs in cases.items()for ci,w in enumerate(rs)if w['status']!='finite_domain_passed']
(base/'current-case-failures.json').write_text(json.dumps({'inputDigest':r['inputDigest'],'caseCounts':dict(cc),'failures':bad},ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'seconds':time.time()-start,'edges':dict(ec),'cases':dict(cc),'issues':len(bad)}))
