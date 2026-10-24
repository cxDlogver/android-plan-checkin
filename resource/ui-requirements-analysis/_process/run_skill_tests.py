import sys
import tempfile
import unittest
from pathlib import Path

work = Path(__file__).resolve().parent
scripts = work.parent.parent.parent / '.codex/skills/requirements-analysis/scripts'
testing = work / 'verification/temp'
testing.mkdir(parents=True, exist_ok=True)
tempfile.tempdir = str(testing)
sys.path.insert(0, str(scripts))
import test_workflow
test_workflow.TEST_ROOT = testing
suite = unittest.defaultTestLoader.discover(str(scripts), pattern='test_*.py')
with (work / 'verification/unit-tests.log').open('w', encoding='utf-8') as stream:
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
print('tests=' + str(result.testsRun) + ' failures=' + str(len(result.failures)) + ' errors=' + str(len(result.errors)))
for case, reason in (result.failures + result.errors)[:6]:
    print(str(case) + '\n' + reason[-2500:])
raise SystemExit(0 if result.wasSuccessful() else 1)
