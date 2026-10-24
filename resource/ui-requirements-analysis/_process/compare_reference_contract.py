import json
from pathlib import Path
repo=Path(__file__).resolve().parents[3]
items={}
for name,p in [('reference',repo/'plans/history/requirements-analysis-project-test'),('current',repo/'plans/ui-requirements-analysis')]:
 m=json.loads((p/'analysis-model.json').read_text(encoding='utf-8-sig'))
 sg=json.loads((p/'state-graph.json').read_text(encoding='utf-8-sig'))
 rg=json.loads((p/'requirement-graph.json').read_text(encoding='utf-8-sig'))
 rs={r['id']:r for r in m['requirements']}
 ss={s['id']:s for s in m['states']}
 items[name]={'scope':m['scope'],'counts':{k:len(m[k]) for k in ['features','states','transitions','requirements']},
    'entryTitles':[ss[s]['title'] for s in m.get('entryStateIds',[])],
    'transitionExamples':[{'from':ss[t['from']]['title'],'event':t['event'],'guard':t['guard'],'to':ss[t['to']]['title'],'requirement':rs[t['requirementId']]['title']} for t in m['transitions'][:20]],
    'requirementKinds':list({r.get('kind','behavior') for r in m['requirements']}),
    'requirementGraph':{k:rg.get(k) for k in ['reduction']}}
print(json.dumps(items,ensure_ascii=False,indent=2))

