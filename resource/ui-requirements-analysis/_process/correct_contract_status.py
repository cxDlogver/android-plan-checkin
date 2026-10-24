import json
from pathlib import Path

work = Path(__file__).resolve().parent
root = work.parent
read = lambda path: json.loads(path.read_text(encoding='utf-8'))
write = lambda path, value: path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
model = read(work / 'analysis-model.json')
model['modelKind'] = 'visual_source_inventory'
model['phase'] = 'incomplete'
model['review']['independent'] = 'stale_after_contract_correction'
model['questions'] = [{'id': 'Q01', 'question': '\u5f53\u524dPRD\u4e0d\u9a8c\u6536\u4e1a\u52a1\u5207\u6362\uff0c\u4e14\u672a\u5b9a\u4e49\u771f\u5b9e\u5165\u53e3\u548c\u9875\u9762\u8fc1\u79fb\u5173\u7cfb\u3002\u53cc\u56fe\u6309\u4ec0\u4e48\u6709\u6765\u6e90\u7684\u5165\u53e3\u3001\u4e8b\u4ef6\u548c\u573a\u666f\u5207\u6362\u5173\u7cfb\u5efa\u6a21\uff1f\u5df2\u5411\u7528\u6237\u8be2\u95ee\u662f\u5426\u5141\u8bb8\u5206\u6790\u7a3f\u4e2d\u53ef\u89c1\u64cd\u4f5c\u5bf9\u5e94\u7684UI\u573a\u666f\u5207\u6362\uff0c\u7b54\u6848\u5c1a\u672a\u53d6\u5f97\u3002', 'status': 'open', 'blocking': True}]
model['deliveryCompliance'] = {'status': 'incomplete', 'reason': '\u4e0a\u6b21\u4ec5\u5b8c\u6210\u89c6\u89c9\u8d44\u6599\u6574\u7406\uff0c\u7f3a\u5c11\u901a\u7528Skill\u8981\u6c42\u7684\u72b6\u6001\u8fc1\u79fb\u56fe\u3001\u9700\u6c42\u56fe\u3001\u539f\u5b50\u9700\u6c42\u53ca\u5b8c\u6574\u9a8c\u6536\uff1b\u64a4\u56de\u6574\u4f53\u5b8c\u6210\u7ed3\u8bba\u3002', 'requiredMissing': [name for name in ['state-graph.json', 'atomic-requirements.json', 'requirement-graph.json', 'analysis-model.json', 'review-log.json', 'gate-result.json'] if not (root / name).is_file()], 'previousIndependentReport': '\u53ea\u5bf9\u65e7\u7248\u89c6\u89c9\u8d44\u6599\u6574\u7406\u4f5c\u590d\u6838\uff0c\u4e0d\u8bc1\u660e\u901a\u7528\u9700\u6c42\u5206\u6790\u5b8c\u6210\uff1b\u5185\u5bb9\u53d8\u66f4\u540e\u6458\u8981\u7ed1\u5b9a\u5931\u6548\u3002'}
for item in model['decisions']:
    if item['topic'] == '\u9759\u6001\u89c6\u89c9\u4e0e\u884c\u4e3a\u8fc1\u79fb':
        item['resolution'] = '\u53cc\u56fe\u53ca\u539f\u5b50\u9700\u6c42\u4ecd\u4e3a\u5fc5\u9700\u4ea4\u4ed8\u3002\u89c6\u89c9\u7ea6\u675f\u6302\u63a5\u72b6\u6001\u548c\u9a8c\u6536\uff0c\u4e0d\u51ed\u7a7a\u5236\u9020\u4e8b\u4ef6\uff1b\u5165\u53e3\u3001\u8fc1\u79fb\u7f3a\u53e3\u5217\u5f85\u51b3\uff0c\u5f53\u524d\u9700\u6c42\u5206\u6790\u672a\u5b8c\u6210\u3002'
        item['source'] = '\u7528\u6237\u672c\u8f6e\u6307\u51fa\u901a\u7528Skill\u4e0d\u80fd\u4e3a\u672c\u6b21\u4efb\u52a1\u8c41\u514d\uff1bSkill\u89c4\u8303\u4f9d\u636e\u4e0estate-boundary.md'
write(work / 'analysis-model.json', model)
shared = read(work / 'shared-analysis.json')
shared['decisions'] = model['decisions']
shared['questions'] = model['questions']
write(work / 'shared-analysis.json', shared)

def escaped(text):
    return ''.join('\\u%04x' % ord(c) if ord(c) > 127 else c for c in text)

builder_path = work / 'build_review.py'
builder = builder_path.read_text(encoding='utf-8')
builder = builder.replace("'fullSkillPipeline': 'not_applicable_to_static_visual_scope'", "'fullSkillPipeline': 'incomplete_required_outputs_missing'")
builder = builder.replace("'status': 'draft', 'fixedSkillPipeline': 'not_run'", "'status': 'incomplete', 'fixedSkillPipeline': 'required_not_completed'")
builder = builder.replace("'phase': 'review_ready_draft'", "'phase': 'incomplete'")
builder = builder.replace("'nextAction': 'Review the completed visual analysis draft; human final confirmation is pending.'", "'nextAction': 'Resolve sourced entry and transition boundaries; rebuild the required standard dual-graph analysis.'")
builder = builder.replace(escaped('\u9636\u6bb5\uff1a\u57fa\u4e8e\u5f53\u524d\u5bfc\u51fa\u8d44\u6599\u7684\u9700\u6c42\u5206\u6790\u8349\u6848\uff0c\u5f85\u4eba\u5de5\u5ba1\u9605\u3002\u552f\u4e00\u9700\u6c42\u4ecd\u4e3aUI-001\u3002'), escaped('\u9636\u6bb5\uff1a\u672a\u5b8c\u6210\u901a\u7528\u9700\u6c42\u5206\u6790\u89c4\u8303\u3002\u73b0\u6709\u6587\u4ef6\u4ec5\u4e3a\u89c6\u89c9\u8d44\u6599\u6574\u7406\uff0c\u5c1a\u7f3a\u72b6\u6001\u8fc1\u79fb\u56fe\u3001\u9700\u6c42\u56fe\u3001\u539f\u5b50\u9700\u6c42\u53ca\u5b8c\u6574\u9a8c\u6536\uff1b\u64a4\u56de\u6b64\u524d\u6574\u4f53\u5b8c\u6210\u7ed3\u8bba\u3002'))
builder = builder.replace(escaped('\u5b8c\u6574\u4e1a\u52a1\u8fc1\u79fb\u53cc\u56fe\u6d41\u7a0b\u4e0d\u9002\u7528\uff0c\u4e0d\u521b\u5efa\u5047\u5165\u53e3\u3001\u5047\u4e8b\u4ef6\u6216\u7531\u6837\u5f0f\u62c6\u51fa\u7684\u65b0\u529f\u80fd\u9700\u6c42\u3002'), escaped('\u72b6\u6001\u8fc1\u79fb\u56fe\u548c\u9700\u6c42\u56fe\u4ecd\u4e3a\u5fc5\u9700\u4ea4\u4ed8\uff1b\u4e0d\u5f97\u56e0\u4ec5\u89c6\u89c9\u8303\u56f4\u7701\u7565\uff0c\u4e5f\u4e0d\u5f97\u865a\u6784\u5165\u53e3\u3001\u4e8b\u4ef6\u6216\u7531\u6837\u5f0f\u62c6\u51fa\u4e1a\u52a1\u529f\u80fd\u3002\u5f53\u524d\u5165\u53e3\u4e0e\u8fc1\u79fb\u4f9d\u636e\u5f85\u6f84\u6e05\u3002'))
builder = builder.replace("{'completed_with_documented_limitations':", "{'stale_after_contract_correction': '" + escaped('\u4e0a\u6b21\u4ec5\u590d\u6838\u89c6\u89c9\u8d44\u6599\uff0c\u4e0d\u80fd\u4f5c\u4e3a\u5f53\u524d\u89c4\u8303\u5b8c\u6210\u8bc1\u636e') + "', 'completed_with_documented_limitations':")
builder = builder.replace(escaped('analysis.json\uff1a\u7ed3\u6784\u5316\u89c6\u89c9\u5206\u6790\uff0c\u4f9b\u540e\u7eed\u5b9e\u73b0\u89c4\u5212\u6216\u89c6\u89c9\u9a8c\u6536\u51c6\u5907\u6d88\u8d39\uff1b\u4e0d\u662f\u8fc1\u79fb\u53cc\u56feSchema v2\u7684\u6b63\u5f0f\u53d1\u5e03\u5305\u3002'), escaped('analysis.json\uff1a\u5c1a\u672a\u8f6c\u5165\u6b63\u5f0fSchema v2\u7684\u89c6\u89c9\u8d44\u6599\u6574\u7406\uff1b\u4e0d\u80fd\u66ff\u4ee3\u53cc\u56fe\u6a21\u578b\u6216\u4f5c\u4e3a\u5df2\u5b8c\u6210\u9700\u6c42\u5206\u6790\u4ea4\u4ed8\u3002'))
builder_path.write_text(builder, encoding='utf-8')
print(json.dumps({'status': 'incomplete', 'missing': model['deliveryCompliance']['requiredMissing']}, ensure_ascii=True))
