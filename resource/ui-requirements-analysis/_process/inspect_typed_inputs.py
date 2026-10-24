import json
from pathlib import Path
w=Path(__file__).resolve().parent
m=json.loads((w/'analysis-model.json').read_text(encoding='utf-8-sig'))
o=json.loads((w/'evidence/visual-observations.json').read_text(encoding='utf-8-sig'))
print(json.dumps({'modelFeatures':m['features'],'roundHeads':[{k:v for k,v in r.items() if k!='checks'} for r in m['rounds']],'confirmations':m['confirmations'],'scenarios':[{k:v for k,v in s.items() if k not in ['nodeRefs','params']} for s in o['scenarios']],'sharedConstraints':o['sharedConstraints'],'acceptance':o['acceptance'],'stateExample':m['states'][0],'tokenKeys':list(json.loads((w/'evidence/design-tokens.json').read_text(encoding='utf-8-sig')))},ensure_ascii=False,indent=2))

