from pathlib import Path
import json
from graph_mapping import read_review

def render(plan, gate):
    inputs={r['role']:r for r in plan['inputs']}
    model=json.loads(Path(inputs['analysisModel']['path']).read_text(encoding='utf-8'))
    template,_=read_review(inputs['requirementsReview']['path'],model,plan['requirementGraph'])
    anchor='<button id="requirement-mode" aria-pressed="false">需求覆盖图</button>'
    hooks=['function graph()', 'function draw()', 'function switchMode(next)',
           'function selectRequirement(id)', 'function continuationDetail(id)', 'function coverageDetail()']
    if template.count(anchor)!=1 or template.count('</body>')!=1 or any(h not in template for h in hooks):
        raise ValueError('unsupported requirements HTML renderer; explicit adapter and verification required')
    payload_plan={k:plan[k] for k in ('cases','testGraph','routes','sharedConstraints','regressionPolicy','planningDigest','phase')}
    payload=json.dumps({'plan':payload_plan,'gate':gate},ensure_ascii=False,separators=(',',':')).replace('<','\\u003c').replace('\u2028','\\u2028').replace('\u2029','\\u2029')
    extension=(Path(__file__).parent.parent/'assets/test-review.js').read_text(encoding='utf-8')
    template=template.replace(anchor,anchor+'<button id="test-mode" aria-pressed="false">测试图</button>')
    template=template.replace('<title>需求图审查</title>','<title>需求与测试图审查</title>').replace('<h1>需求图审查</h1>','<h1>需求与测试图审查</h1>')
    return template.replace('</body>','<script id="test-data" type="application/json">'+payload+'</script><script>'+extension+'</script></body>')
