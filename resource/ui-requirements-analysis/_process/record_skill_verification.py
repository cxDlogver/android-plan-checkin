import json,sys,re,subprocess
from pathlib import Path
w=Path(__file__).resolve().parent
repo=w.parent.parent.parent
sys.path.insert(0,str(repo/'.codex/skills/requirements-analysis/scripts'))
import workflow as wf
log=(w/'verification/unit-tests.log').read_text(encoding='utf-8')
summary={'skill':'requirements-analysis','contract_version':3,'model_schema':2,
    'pythonTests':{'tests':106,'status':'passed' if 'Ran 106 tests' in log and log.rstrip().endswith('OK') else 'failed',
                   'log':'_process/verification/unit-tests.log','sha256':wf.file_hash(w/'verification/unit-tests.log')},
    'canvasTests':wf.read(w/'evidence/canvas-contract-tests.json'),
    'docs':wf.read(w/'evidence/skill-doc-checks.json'),
    'scope':'Library/contract and model review checks; not product implementation or visual acceptance'}
wf.write(w/'evidence/skill-verification.json',summary)
print(json.dumps({'python':summary['pythonTests']['status'],'canvas':{k:v['returncode'] for k,v in summary['canvasTests'].items()},'docs':summary['docs']['relativeLinks']},ensure_ascii=False))

