import sys,json,random,itertools
from pathlib import Path
from collections import deque
ROOT=Path(__file__).resolve().parent
SCRIPTS=ROOT.parent/'skill/task-planning/scripts'
if not SCRIPTS.exists():SCRIPTS=ROOT.parents[3]/'.codex/skills/task-planning/scripts'
sys.path.insert(0,str(SCRIPTS))
import routes
rng=random.Random(731)
def oracle(m,start,vals,wanted):
 q=deque((start,x,0) for x in vals);seen={(start,x) for x in vals};ts=m['transitions']
 while q:
  state,x,d=q.popleft()
  for t in ts:
   if t['from']!=state:continue
   rule=m['pathContext']['transitionRules'][t['id']]['cases'][0]
   if x not in rule.get('requires',{}).get('x',[0,1]):continue
   ys=rule.get('set',{}).get('x',[x])
   if t['id'] in wanted:return d+1
   for y in ys:
    if (t['to'],y) not in seen:seen.add((t['to'],y));q.append((t['to'],y,d+1))
 return None
count=0
for n in range(300):
 m={'states':[{'id':s} for s in ('A','B','C')],'entryStateIds':['A'],'transitions':[],'pathContext':{'domains':{'x':{'values':[0,1],'labels':{0:'zero',1:'one'}}},'entryContexts':{'A':{'x':[0,1]}},'transitionRules':{}}}
 for i in range(rng.randrange(1,9)):
  tid='t'+str(i);m['transitions'].append({'id':tid,'from':rng.choice(['A','B','C']),'to':rng.choice(['A','B','C'])})
  rule={}
  if rng.randrange(2):rule['requires']={'x':[rng.randrange(2)]}
  if rng.randrange(2):rule['set']={'x':[rng.randrange(2)]}
  m['pathContext']['transitionRules'][tid]={'cases':[rule]}
 conflicts=routes.invariant_conflicts(m)
 for bad in conflicts:assert oracle(m,'A',[0,1],{bad}) is None,(m,bad)
 for t in m['transitions']:
  expected=oracle(m,'A',[0,1],{t['id']});path,ctx,info=routes.nearest(m,'A',{'x':{0,1}},{t['id']},10000)
  actual=len(path) if path else None
  assert expected==actual,(m,t['id'],expected,actual)
  if path:assert routes.replay(m,{'entryStateId':'A','steps':path})==[]
  count+=1
out={'status':'PASS','seed':731,'graphs':300,'edge_target_queries':count,'checks':'independent concrete-state BFS shortest edge-prefix oracle and path replay; invariant-conflict soundness against concrete reachability; no product acceptance'}
(ROOT/'route-oracle-results.json').write_text(json.dumps(out,indent=2))
print(out)
