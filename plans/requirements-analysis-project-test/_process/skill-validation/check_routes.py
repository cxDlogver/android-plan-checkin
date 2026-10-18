import sys,json,time
from pathlib import Path
base=Path(__file__).parent
sys.path.insert(0,str(base.parents[3]/'.codex/skills/requirements-analysis/scripts'))
from requirement_graph import requirement_graph
m=json.loads((base.parent/'analysis-model.json').read_text(encoding='utf-8'))
start=time.time();g=requirement_graph(m)
(base/'route-result.json').write_text(json.dumps(g,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'seconds':time.time()-start,'nodes':len(g['nodes']),'edges':len(g['edges']),'visits':g['traversal']['totalVisits'],'routes':len(g['traversal']['routes']),'status':g['traversal']['status'],'uncovered':g['reduction']['uncoveredRequirementIds'],'checks':dict(__import__('collections').Counter(r['contextCheck']['status'] for r in g['traversal']['routes']))},ensure_ascii=False))
