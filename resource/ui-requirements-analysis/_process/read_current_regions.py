import json
from pathlib import Path
w=Path(__file__).resolve().parent
o=json.loads((w/'evidence/visual-observations.json').read_text(encoding='utf-8-sig'))
for s in o['scenarios']:
 print(s['id']+' '+s['title']+': '+s['distinction'])
 for r in s['regions']:print('  '+r['name']+'：'+'；'.join(r['checks']))

