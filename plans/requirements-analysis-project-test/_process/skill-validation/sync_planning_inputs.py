import json,hashlib
from pathlib import Path
root=Path(__file__).resolve().parents[4]
analysis=root/'plans/requirements-analysis-project-test'
path=root/'plans/task-planning-project-test/_process/planning.json'
m=json.loads((analysis/'analysis-model.json').read_text(encoding='utf-8'));p=json.loads(path.read_text(encoding='utf-8'))
ids={r['id'] for r in m['requirements']};old={x for t in p['tasks']for x in t['requirementIds']}
for t in p['tasks']:t['requirementIds']=[x for x in t['requirementIds'] if x in ids]
byid={t['id']:t for t in p['tasks']}
map_={'BOOT':'boot','ROOT':'boot','CREATE':'create','RECORD':'record','CAL':'calendar','MANAGE':'manage','LIFE':'manage','STATS':'stats','TIME':'stats','DRAFT':'draft'}
for t in m['transitions']:
 if t['requirementId'] in old:continue
 key=map_[t['from'].split('.')[0]]
 byid[key]['requirementIds'].append(t['requirementId'])
for x in p['inputs']:x['sha256']=hashlib.sha256(Path(x['path']).read_bytes()).hexdigest()
p['upstreamApproved']=False
path.write_text(json.dumps(p,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'requirements':len(ids),'taskMappings':sum(len(t['requirementIds'])for t in p['tasks']),'productAcceptance':'not_run'}))
