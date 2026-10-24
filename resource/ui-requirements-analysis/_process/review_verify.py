import base64
import hashlib
import json
import re
from pathlib import Path

root = Path(__file__).parent.parent
sha = lambda b: hashlib.sha256(b).hexdigest()
read = lambda p: json.loads(p.read_text(encoding='utf-8'))
m = read(root/'analysis.json')
manifest = read(root/'manifest.json')
design = read(root/'_process/design-index.json')
html = (root/'review.html').read_text(encoding='utf-8')
payload = json.loads(re.search(r'<script id="analysis-data" type="application/json">(.*?)</script>',html,re.S)[1])
exclusions = m.get('digestExclusions', ['review','rounds','phase','semanticDigest'])
sem = {k:v for k,v in m.items() if k not in exclusions}
result = {'digest_exclusions':exclusions, 'semantic_claimed':m['semanticDigest'], 'semantic_actual':sha(json.dumps(sem,sort_keys=True,ensure_ascii=False).encode()), 'manifest_files':{}, 'source_checks':[], 'node_ref_errors':[], 'frames':[]}
for name,digest in manifest['files'].items():
    actual=sha((root/name).read_bytes())
    result['manifest_files'][name]={'actual':actual,'match':actual==digest}
result['bundle_claimed']=manifest['bundleDigest']
result['bundle_actual']=sha(json.dumps(manifest['files'],sort_keys=True).encode())
for src in m['sources']:
    cache=root/src['evidencePath']
    original=Path(src['uri'])
    result['source_checks'].append({'id':src['id'],'cache_digest_match':sha(cache.read_bytes())==src['sha256'],'original_matches_cache':original.read_bytes()==cache.read_bytes()})
for s in m['scenarios']:
    ds = next(x for x in design['screens'] if x['frameId']==s['frameId'])
    ps = next(x for x in payload['scenarios'] if x['id']==s['id'])
    for r in s['regions']:
        for ref in r['nodeRefs']:
            ns=[n for n in ds['nodes'] if n['id']==ref['nodeId'] and n['path']==ref['path']]
            if not ns or ns[0]['name']!=ref['name'] or ns[0].get('content')!=ref.get('content'):
                result['node_ref_errors'].append({'region':r['id'],'ref':ref})
    result['frames'].append({'id':s['id'],'frameId':s['frameId'],'region_ids':[r['id'] for r in s['regions']],'design_node_count':len(ds['nodes']),'html_image_match':base64.b64decode(ps['imageData'].split(',')[1])==(root/s['imagePath']).read_bytes(),'html_scenario_match':{k:v for k,v in ps.items() if k!='imageData'}==s})
result['payload_model_match']={k:v for k,v in payload.items() if k not in ['tokens','designDetails','scenarios']}=={k:v for k,v in m.items() if k!='scenarios'}
result['html_body_matches_template']=html==((root/'_process/review-template.html').read_text(encoding='utf-8').replace('__ANALYSIS_DATA__',re.search(r'<script id="analysis-data" type="application/json">(.*?)</script>',html,re.S)[1]))
print(json.dumps(result,ensure_ascii=False,indent=2))
(root/'_process/reviewer-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
