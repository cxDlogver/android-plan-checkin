from pathlib import Path
import hashlib
import json
import shutil
import struct

ROOT = Path(__file__).resolve().parents[3]
RUN = ROOT / 'plans/ui-requirements-analysis'
WORK = RUN / '_process'
EVIDENCE = WORK / 'evidence'
EVIDENCE.mkdir(parents=True, exist_ok=True)


def save(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


sources = []
paths = [
    ('PRD', next((ROOT / 'plans').glob('2026-10-17-*.md')), 'prd.md', ['sections 1-7']),
    ('MAP', ROOT / 'resource/design/page-map.json', 'page-map.json',
     ['screens: order, title, frameId, canvasSize, preview only']),
    ('TOKENS', ROOT / 'resource/design/design-tokens.json', 'design-tokens.json',
     ['colors, font, layout, radius, gradients, effects; visual scope only']),
    ('TREE', ROOT / 'resource/design/canvas-snapshot.json', 'canvas-snapshot.json',
     ['mapped frame subtrees and referenced reusable visual nodes only']),
]
for identity, origin, filename, ranges in paths:
    target = EVIDENCE / filename
    shutil.copyfile(origin, target)
    sources.append({'id': identity, 'uri': origin.as_posix(), 'readRanges': ranges,
                    'evidencePath': target.relative_to(RUN).as_posix(),
                    'sha256': hashlib.sha256(target.read_bytes()).hexdigest()})

page_map = json.loads((EVIDENCE / 'page-map.json').read_text(encoding='utf-8'))
snapshot = json.loads((EVIDENCE / 'canvas-snapshot.json').read_text(encoding='utf-8'))
index = {}


def index_nodes(node):
    if isinstance(node, dict):
        if 'id' in node:
            index[node['id']] = node
        for child in node.get('children', []):
            index_nodes(child)


for node in snapshot['nodes']:
    index_nodes(node)


def summarize(node, parent='', overrides=None):
    current = dict(node)
    if overrides and current.get('id') in overrides:
        current.update(overrides[current['id']])
    values = {key: current[key] for key in [
        'id', 'name', 'type', 'content', 'fontSize', 'fontWeight', 'fontFamily', 'lineHeight',
        'fill', 'stroke', 'strokeWidth', 'cornerRadius', 'padding', 'gap', 'layout',
        'width', 'height', 'icon', 'ref', 'effect', 'justifyContent', 'alignItems'
    ] if key in current}
    values['path'] = parent + '/' + current.get('name', current.get('id', ''))
    result = [values]
    if current.get('type') == 'ref' and current.get('ref') in index:
        original = index[current['ref']]
        for child in original.get('children', []):
            result.extend(summarize(child, values['path'], current.get('descendants', {})))
    for child in current.get('children', []):
        result.extend(summarize(child, values['path'], overrides))
    return result


screens = []
for item in page_map['screens']:
    screen = {key: item[key] for key in ['order', 'title', 'frameId', 'canvasSize', 'preview']}
    frame = index[screen['frameId']]
    screen['nodes'] = summarize(frame)
    image_origin = ROOT / 'resource/design' / screen['preview']
    image_target = EVIDENCE / image_origin.name
    shutil.copyfile(image_origin, image_target)
    raw = image_target.read_bytes()
    screen['pngSize'] = list(struct.unpack('>II', raw[16:24]))
    screen['treeSize'] = {'width': frame['width'], 'height': frame['height']}
    image_id = 'UI-' + screen['frameId']
    sources.append({'id': image_id, 'uri': image_origin.as_posix(),
                    'readRanges': ['full image; visual observation pending'],
                    'evidencePath': image_target.relative_to(RUN).as_posix(),
                    'sha256': hashlib.sha256(raw).hexdigest()})
    screen['imageSourceId'] = image_id
    screen['imagePath'] = image_target.relative_to(RUN).as_posix()
    screens.append(screen)

save(WORK / 'design-index.json', {'screens': screens})
model_path = WORK / 'analysis-model.json'
if not model_path.exists():
    save(model_path, {
        'schemaVersion': 1, 'modelKind': 'visual_requirements_draft',
        'phase': 'analyzing',
        'scope': {'requirementId': 'UI-001',
                  'basis': 'plans/2026-10-17 UI reconstruction PRD sections 1-6',
                  'abstraction': 'page visual scenarios with nested component samples and variable fixture data',
                  'included': ['23 mapped frames', 'drawn local samples', 'explicit visual parameters'],
                  'excluded': ['historical business rules', 'implementation assessment', 'product runtime acceptance']},
        'applicability': {'mode': 'static_visual_analysis', 'fullTransitionPipeline': False,
                          'reason': 'PRD excludes business workflow; no sourced behavioral graph is defined',
                          'fixedSkillGates': 'not_run', 'published': False},
        'sources': sources, 'scenarios': [], 'sharedConstraints': [], 'coverage': [], 'questions': [],
        'limitations': [{'id': 'L1', 'kind': 'original_design_unavailable',
                         'detail': 'Pencil MCP failed to connect after 3 retries; current native design was not inspected.'}],
        'review': {'independent': 'pending', 'humanAcceptance': 'pending'},
        'rounds': []
    })
save(WORK / 'run-state.json', {'phase': 'source_review', 'observedFrames': [],
    'pendingFrames': [s['frameId'] for s in screens],
    'nextAction': 'Inspect all PNGs, save source-based scenario definitions after each batch.',
    'plannedDeliverables': {'analysis.json': 'structured visual analysis for downstream use',
                           'review.html': 'read-only human review of frames, targets and source coverage',
                           'analysis.md': 'human-readable findings and boundaries',
                           'manifest.json': 'current generated artifact integrity'}})

for screen in screens:
    print(json.dumps({'order': screen['order'], 'title': screen['title'], 'frameId': screen['frameId'],
        'size': screen['canvasSize'], 'png': screen['pngSize'],
        'regions': [{'id': n.get('id'), 'name': n.get('name'), 'type': n.get('type'),
                     'text': n.get('content'), 'size': n.get('fontSize'), 'fill': n.get('fill')}
                    for n in screen['nodes'] if n.get('content') or n.get('type') in ['ref', 'icon']]},
        ensure_ascii=True))
