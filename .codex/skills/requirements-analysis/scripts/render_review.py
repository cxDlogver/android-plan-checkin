"""Presentation only: consume accepted graph/path data without solving again."""
import base64
import hashlib
import json
import math
import re
from collections import deque
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]


def layout(nodes, edges, entries):
    outgoing = {n['id']: [] for n in nodes}
    for edge in edges:
        outgoing[edge['from']].append(edge['to'])
    ranks = {entry: 0 for entry in entries}
    queue = deque(entries)
    while queue:
        current = queue.popleft()
        for target in outgoing.get(current, []):
            if target not in ranks:
                ranks[target] = ranks[current] + 1
                queue.append(target)
    last = max(ranks.values(), default=0) + 1
    layers = {}
    for node in nodes:
        layers.setdefault(ranks.get(node['id'], last), []).append(node)
    positions = {}
    for rank, group in sorted(layers.items()):
        y = 100
        for node in group:
            height = max(78, 30 + math.ceil(len(node['title']) / 15) * 22)
            positions[node['id']] = {'x': 100 + rank * 400, 'y': y, 'w': 240, 'h': height}
            y += height + 65
    return positions


def presentation(run, state, requirements, analysis):
    media = {}
    refs = [ref for s in state['states'] for ref in s['ui']['refs']]
    refs += [ref for r in requirements['requirements'] for c in r['visualAcceptance']['checks']
             for ref in c.get('uiRefs', [])]
    types = {'.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
             '.webp': 'image/webp', '.gif': 'image/gif'}
    for ref in refs:
        name = ref.get('previewPath')
        if not name or name in media:
            continue
        image = run / name
        if image.suffix.lower() not in types:
            raise ValueError('unsupported local preview image: ' + name)
        media[name] = 'data:' + types[image.suffix.lower()] + ';base64,' + base64.b64encode(image.read_bytes()).decode('ascii')
    graph = requirements['graph']
    return {'scope': state['scope'], 'states': state['states'], 'transitions': state['transitions'],
            'features': state['features'], 'sources': state['sources'], 'entries': state['entryStateIds'],
            'requirements': requirements['requirements'], 'graph': graph, 'analysis': analysis,
            'pathContext': state.get('pathContext'), 'media': media,
            'layouts': {'state': layout(state['states'], state['transitions'], state['entryStateIds']),
                        'requirements': layout(graph['nodes'], graph['edges'], graph['reduction']['entryRequirementIds'])}}


def render(payload):
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    fingerprint = hashlib.sha256(raw.encode('utf-8')).hexdigest()
    escaped = raw.replace('<', '\\u003c').replace('\u2028', '\\u2028').replace('\u2029', '\\u2029')
    template = (SKILL / 'assets/review.html').read_text(encoding='utf-8')
    if template.count('__PAYLOAD__') != 1 or template.count('__DATA_DIGEST__') != 1:
        raise ValueError('HTML template must contain exactly one data and fingerprint placeholder')
    if re.search(r'<script\b[^>]*\bsrc\s*=|<link\b[^>]*\bhref\s*=|<form\b|contenteditable', template, re.I):
        raise ValueError('template must be self-contained and read-only')
    if re.search(r'\b(?:fetch|WebSocket|XMLHttpRequest)\s*\(|\b(?:localStorage|sessionStorage)\b|sendBeacon\s*\(', template):
        raise ValueError('template must not send or persist business data')
    return template.replace('__DATA_DIGEST__', fingerprint).replace('__PAYLOAD__', escaped)


def extract_payload(html):
    match = re.search(r'<script id="analysis-data" type="application/json">(.*?)</script>', html, re.S)
    if not match:
        raise ValueError('embedded analysis data missing')
    return json.loads(match.group(1))
