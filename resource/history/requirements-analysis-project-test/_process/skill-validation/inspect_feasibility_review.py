import json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
m=json.loads((ROOT.parent/'analysis-model.json').read_text(encoding='utf-8'))
ids={'T-CAL-zero-filter-open','T-CAL-zero-filter-select','T-CAL-zero-filter-close'}
reqs={t['requirementId'] for t in m['transitions'] if t['id'] in ids}
print(json.dumps({'phase':m['phase'],'states':len(m['states']),'transitions':len(m['transitions']),
  'transitionsChanged':[t for t in m['transitions'] if t['id'] in ids],
  'requirementsChanged':[r for r in m['requirements'] if r['id'] in reqs],
  'rulesChanged':{tid:m['pathContext']['transitionRules'][tid] for tid in ids},
  'stateFacts':{s['id']:s['facts'] for s in m['states'] if s['id'] in m['pathContext']['stateConstraints']},
  'latestRoundSummary':{k:v for k,v in m['rounds'][-1].items() if k not in {'changes','checks','nodeIds','openFrontier','retiredIds'}}},ensure_ascii=False,indent=2))
