"""Read-only conversion/continuity regression against the supplied reference."""
from pathlib import Path
from collections import Counter
import sys,json
w=Path(__file__).resolve().parent
repo=w.parent.parent.parent
sys.path.insert(0,str(repo/'.codex/skills/requirements-analysis/scripts'))
import workflow as wf
from requirement_graph import full_requirement_graph
ref=repo/'plans/history/requirements-analysis-project-test'
model=wf.read(ref/'analysis-model.json')
graph=wf.read(ref/'requirement-graph.json')
before={p.name:wf.file_hash(p) for p in ref.iterdir() if p.is_file()}
full=full_requirement_graph(model)
nodes={n['id'] for n in full['nodes']}
candidates={(e['from'],e['to'],e['viaStateId']) for e in full['edges']}
transitions={t['id']:t for t in model['transitions']}
issues=[]
if nodes!={n['id'] for n in graph['nodes']}:issues.append('requirement node coverage differs')
visits=Counter();uses=Counter()
for route in graph['traversal']['routes']:
 current=route['entryStateId']
 if current not in model['entryStateIds']:issues.append('route starts outside documented entries')
 if len(route['transitionIds'])!=len(route['requirementIds']):issues.append('route length mismatch')
 for tid,rid in zip(route['transitionIds'],route['requirementIds']):
  edge=transitions[tid]
  if edge['from']!=current or edge['requirementId']!=rid:issues.append('route discontinuity or requirement mismatch')
  current=edge['to'];visits[rid]+=1
 uses.update(zip(route['requirementIds'],route['requirementIds'][1:]))
for edge in graph['edges']:
 if (edge['from'],edge['to'],edge['viaStateId']) not in candidates:issues.append('edge violates state continuation formula')
 if uses[(edge['from'],edge['to'])]!=edge['usageCount']:issues.append('edge usage mismatch')
if set(uses)!={(e['from'],e['to']) for e in graph['edges']}:issues.append('route edge set mismatch')
if set(visits)!=nodes:issues.append('route does not cover all atomic requirements')
if sum(visits.values())!=graph['traversal']['totalVisits']:issues.append('visit count mismatch')
after={p.name:wf.file_hash(p) for p in ref.iterdir() if p.is_file()}
result={'scope':'Read-only conversion mapping, node coverage and structural route continuity; does not re-solve optimization or business guards',
 'states':len(model['states']),'transitions':len(model['transitions']),'atomicRequirements':len(model['requirements']),
 'requirementNodes':len(full['nodes']),'candidateContinuations':len(full['edges']),'retainedContinuations':len(graph['edges']),
 'issues':issues,'referenceFilesUnchanged':before==after,
 'fullOptimizationRecompute':'not_completed; stopped optional expensive recomputation, no optimality or guard revalidation claim'}
wf.write(w/'evidence/skill-reference-conversion-check.json',result)
print(json.dumps(result,ensure_ascii=False))
raise SystemExit(bool(issues or before!=after))

