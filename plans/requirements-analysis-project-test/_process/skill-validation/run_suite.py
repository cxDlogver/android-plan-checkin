import sys,tempfile,unittest,json,time
from pathlib import Path
base=Path(__file__).parent.resolve()
scratch=base/'scratch';scratch.mkdir(exist_ok=True);tempfile.tempdir=str(scratch)
scripts=base/'skill/requirements-analysis/scripts'
if not scripts.exists():scripts=base.parents[3]/'.codex/skills/requirements-analysis/scripts'
sys.path.insert(0,str(scripts))
start=time.time()
with (base/'test-suite.txt').open('w',encoding='utf-8') as log:
    result=unittest.TextTestRunner(stream=log,verbosity=2).run(unittest.defaultTestLoader.discover(str(scripts),pattern='test_*.py'))
summary={'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'seconds':time.time()-start,'status':'passed' if result.wasSuccessful() else 'failed'}
print(json.dumps(summary))
for test,error in result.failures+result.errors:print(str(test)+'\n'+error[-2500:])
(base/'unit-results.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
sys.exit(not result.wasSuccessful())
