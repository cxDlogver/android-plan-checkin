import json,hashlib,sys
from collections import Counter
from pathlib import Path
base=Path(__file__).parent;run=base.parent.parent
sys.path.insert(0,str(base))
from independent_feasibility_checks import replay_boxes
m=json.loads((run/'analysis-model.json').read_text(encoding='utf-8'));sg=json.loads((run/'state-graph.json').read_text(encoding='utf-8'));g=json.loads((run/'requirement-graph.json').read_text(encoding='utf-8'))
v=sg['transitionValidation'];problems=[]
assert m==json.loads((run/'_process/analysis-model.json').read_text(encoding='utf-8'))
for tid,w in v['transitions'].items():
 if w['status']!='finite_domain_passed' or not replay_boxes(m,w['entryStateId'],w['transitionIds'],w['initialContext'],w['ruleCases']):problems.append(['edge',tid])
for tid,rows in v['caseResults'].items():
 for ci,w in enumerate(rows):
  if w['status']!='finite_domain_passed' or w['ruleCases'][-1]!=ci or not replay_boxes(m,w['entryStateId'],w['transitionIds'],w['initialContext'],w['ruleCases']):problems.append(['case',tid,ci])
for i,r in enumerate(g['traversal']['routes']):
 c=r['contextCheck']
 if c['status']!='finite_domain_passed' or not replay_boxes(m,r['entryStateId'],r['transitionIds'],c['initialContext'],c['ruleCases']):problems.append(['route',i])
counts=Counter(rid for r in g['traversal']['routes']for rid in r['requirementIds']);uses=Counter((a,b)for r in g['traversal']['routes']for a,b in zip(r['requirementIds'],r['requirementIds'][1:]))
assert dict(counts)==g['traversal']['visitCounts']
assert {(e['from'],e['to']):e['usageCount']for e in g['edges']}==dict(uses)
assert set(counts)=={r['id']for r in m['requirements']}
assert {x['id']for x in sg['edges']}=={x['id']for x in m['transitions']}
out={'status':'passed' if not problems else 'failed','scope':'Independent replay implementation executed by parent; not independent LLM semantic acceptance','semanticDigest':sg['semanticDigest'],'states':len(m['states']),'transitions':len(m['transitions']),'cases':sum(v['caseCounts'].values()),'routes':len(g['traversal']['routes']),'visits':g['traversal']['totalVisits'],'repeatedVisits':g['traversal']['repeatedVisits'],'lowerBoundVisits':g['traversal'].get('lowerBoundVisits'),'optimality':g['traversal'].get('optimality'),'problems':problems,'modelSha256':hashlib.sha256((run/'analysis-model.json').read_bytes()).hexdigest(),'independentSemanticReview':'not_completed_usage_limit','realBrowser':'not_tested','productAcceptance':'not_run'}
(base/'current-replay-result.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(out))
