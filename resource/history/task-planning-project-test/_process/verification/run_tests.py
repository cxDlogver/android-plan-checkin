import sys,tempfile,unittest,json
from pathlib import Path
root=Path(__file__).resolve().parents[2]
skill=root/'_process/skill/task-planning'
if not skill.exists():skill=root.parents[1]/'.codex/skills/task-planning'
tempfile.tempdir=str(root/'_process/verification/scratch')
sys.path.insert(0,str(skill/'scripts'))
import test_planning
with (root/'_process/verification/unit-tests.log').open('w',encoding='utf-8') as out:
 result=unittest.TextTestRunner(stream=out,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(test_planning))
summary={'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'passed':result.wasSuccessful()}
(root/'_process/verification/unit-tests.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
print(json.dumps(summary))
if not result.wasSuccessful():
 print((root/'_process/verification/unit-tests.log').read_text(encoding='utf-8')[-12000:])
 sys.exit(1)
