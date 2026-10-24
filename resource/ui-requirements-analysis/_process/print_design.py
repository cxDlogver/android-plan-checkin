from pathlib import Path
import json
import sys

data = json.loads((Path(__file__).parent / 'design-index.json').read_text(encoding='utf-8'))
start = int(sys.argv[1])
end = int(sys.argv[2])
for screen in data['screens'][start - 1:end]:
    print(f"\n{screen['order']:02} {screen['frameId']} {screen['title']}")
    for node in screen['nodes']:
        if node.get('content') and 'system' not in node.get('path', '').lower():
            print(f"{node.get('id')} | {node.get('name')} | {node['content']} | {node.get('fontSize')} | {node.get('fill')}")
