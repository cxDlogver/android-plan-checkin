from pathlib import Path
import json
import sys

WORK = Path(__file__).parent
model = json.loads((WORK / 'analysis-model.json').read_text(encoding='utf-8'))
design = json.loads((WORK / 'design-index.json').read_text(encoding='utf-8'))
scenarios = {s['order']: s for s in model['scenarios']}
for filename in sys.argv[1:]:
    items = json.loads((WORK / filename).read_text(encoding='utf-8'))
    for item in items:
        screen = next(s for s in design['screens'] if s['order'] == item['order'])
        item.update({key: screen[key] for key in [
            'title', 'frameId', 'canvasSize', 'pngSize', 'treeSize', 'imageSourceId', 'imagePath'
        ]})
        item['id'] = 'V' + str(item['order']).zfill(2)
        item['sourceRefs'] = [
            {'sourceId': 'PRD', 'locator': 'section 3, figure ' + str(item['order'])},
            {'sourceId': item['imageSourceId'], 'locator': 'full frame and named regions'},
            {'sourceId': 'TREE', 'locator': 'frame ' + item['frameId']}
        ]
        for number, region in enumerate(item['regions'], 1):
            region['id'] = item['id'] + '-R' + str(number)
            region['nodeRefs'] = [{'nodeId': n['id'], 'path': n['path'],
                                   'name': n.get('name'), 'content': n.get('content')}
                                  for n in screen['nodes'] if n.get('name') in region['anchors'] or n.get('content') in region['anchors']]
            if not region['nodeRefs']:
                raise ValueError(f"No source nodes for {region['id']}")
        item['status'] = 'draft'
        item['observationStatus'] = 'png_viewed_and_tree_read'
        scenarios[item['order']] = item
        source = next(s for s in model['sources'] if s['id'] == item['imageSourceId'])
        source['readRanges'] = ['full image visually inspected', *[r['name'] for r in item['regions']]]
model['scenarios'] = [scenarios[n] for n in sorted(scenarios)]
(WORK / 'analysis-model.json').write_text(json.dumps(model, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
state = json.loads((WORK / 'run-state.json').read_text(encoding='utf-8'))
state['observedFrames'] = [s['frameId'] for s in model['scenarios']]
state['pendingFrames'] = [s['frameId'] for s in design['screens'] if s['order'] not in scenarios]
state['nextAction'] = 'Inspect remaining PNGs and save observations' if state['pendingFrames'] else 'Build shared constraints and source coverage; generate review artifacts'
(WORK / 'run-state.json').write_text(json.dumps(state, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(f"Saved {len(scenarios)} observed frames; pending {len(state['pendingFrames'])}")
