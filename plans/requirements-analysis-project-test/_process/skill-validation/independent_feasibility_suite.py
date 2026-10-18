"""Run current staged regressions with scratch space confined to validation."""
import hashlib,io,json,os,sys,tempfile,unittest
from pathlib import Path
HERE=Path(__file__).resolve().parent
SKILL=HERE.parent.parent.parents[1]/'.codex/skills/requirements-analysis'
sys.dont_write_bytecode=True
os.environ['PYTHONDONTWRITEBYTECODE']='1'
os.environ['PYTHONUTF8']='1'
scratch=HERE/'feasibility-scratch';scratch.mkdir(exist_ok=True)
tempfile.tempdir=str(scratch)
sys.path.insert(0,str(SKILL/'scripts'))
hashes={p.relative_to(SKILL).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in SKILL.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
output=io.StringIO()
suite=unittest.defaultTestLoader.discover(str(SKILL/'scripts'),pattern='test_*.py')
result=unittest.TextTestRunner(stream=output,verbosity=2).run(suite)
(HERE/'independent-feasibility-suite.log').write_text(output.getvalue(),encoding='utf-8')
changed=[p.relative_to(SKILL).as_posix() for p in SKILL.rglob('*') if p.is_file() and '__pycache__' not in p.parts and hashes.get(p.relative_to(SKILL).as_posix())!=hashlib.sha256(p.read_bytes()).hexdigest()]
record={'tests':result.testsRun,'passed':result.wasSuccessful(),'failures':len(result.failures),'errors':len(result.errors),'browserObserved':False,'resourceHashes':hashes,'resourcesChangedDuringRun':changed}
(HERE/'independent-feasibility-suite.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in record.items() if k!='resourceHashes'},indent=2))
