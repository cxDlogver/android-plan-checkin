import json
from pathlib import Path
w=Path(__file__).resolve().parent
m=json.loads((w/'analysis-model.json').read_text(encoding='utf-8-sig'))
o=json.loads((w/'evidence/visual-observations.json').read_text(encoding='utf-8-sig'))
print(json.dumps({'acceptance':o['acceptance'],'stateExample':m['states'][0],'sharedKeys':[list(c) for c in o['sharedConstraints']],'scenarioKeys':list(o['scenarios'][0]),'scenes':[{k:s.get(k) for k in ['id','order','title','frameId','condition','distinction','params']} for s in o['scenarios']],'tokenKeys':list(json.loads((w/'evidence/design-tokens.json').read_text(encoding='utf-8-sig')))},ensure_ascii=False,indent=2))

