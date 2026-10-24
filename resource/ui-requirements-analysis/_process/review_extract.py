import json
import sys
from pathlib import Path

root = Path(__file__).parent.parent
m = json.loads((root / 'analysis.json').read_text(encoding='utf-8'))
mode = sys.argv[1] if len(sys.argv)>1 else 'top'
if mode == 'top':
    print('TOP LEVEL', list(m))
    print(json.dumps({k:v for k,v in m.items() if k not in ['sources','scenarios','coverage','rounds']}, ensure_ascii=False, indent=2))
if mode == 'rounds':
    print(json.dumps(m['rounds'], ensure_ascii=False, indent=2))
if mode == 'md_tail':
    content = (root/'analysis.md').read_text(encoding='utf-8')
    print(content[content.index('### 图14'):])
if mode == 'design_text':
    d=json.loads((root/'_process/design-index.json').read_text(encoding='utf-8'))
    print('TOP', list(d))
    for s in d['screens']:
        print('\n',s['order'],s['title'],s['frameId'],s['canvasSize'])
        for n in s['nodes']:
            if n.get('content') or n['type'] not in ['text','frame']:
                print(n['name'], n.get('content',''), n.get('fontSize',''), n.get('fill',''), n.get('width',''),n.get('height',''))
for s in (m['scenarios'][:11] if mode == 'first' else m['scenarios'][11:] if mode == 'second' else []):
    print(json.dumps({k:v for k,v in s.items() if k not in ['regions','sourceRefs']}, ensure_ascii=False))
    for r in s['regions']:
        print(json.dumps({k:v for k,v in r.items() if k != 'nodeRefs'}, ensure_ascii=False))
