"""Historical harness-version scope fixtures, never product acceptance."""
import copy
import unittest
import test_route as fixtures
from execution import load_json


class HarnessArchives(unittest.TestCase):
    def setUp(self):
        self.f=fixtures.SplitWorkflow('test_static_finish_does_not_accept_or_modify_cases')
        self.f.setUp()
        f=self.f
        f.submit(0,f.begin(0));f.submit(1,f.begin(1),failed=True)
        record=load_json(f.record);self.failed=record['attempts'][-1]['run']
        self.case0,self.case1=record['sequence'][:2]
        self.assertNotEqual(self.case0,self.case1)
        directory=(f.base/self.failed['context']['path']).parent/'repair';directory.mkdir()
        self.archive=directory/'driver.before.py';self.archive.write_bytes(f.script.read_bytes())
        evidence=dict(form='data-snapshot',**f.ref(self.archive),description='Actual historical fixture driver bytes.')
        diagnosis=directory/'diagnosis.json'
        fixtures.write(diagnosis,dict(category='harness',affectedCaseIds=[self.case1],reason='Fixture-specific collector change.',evidence=[evidence]))
        fixtures.route.execute('repair-open',f.record,f.base,index=1,run=f.rel(diagnosis))
        f.script.write_text('# Changed collector fixture; prior case assertion requirements were reviewed unchanged.\n',encoding='utf-8')
        report=directory/'review.json'
        fixtures.write(report,dict(assertions=[dict(target='repair:'+self.failed['id'],expected=1,actual=1,verdict='passed')]))
        self.payload=dict(observation='Reviewed scope and frozen actual source; affected case still requires reacceptance.',
                          evidence=[dict(form='assertion-report',**f.ref(report),description='Fixture scope review.')],
                          changedFiles=[f.ref(f.script)],harnessArchive=dict(original=copy.deepcopy(self.failed['script']),archive=f.ref(self.archive),unaffectedCaseIds=[self.case0]))
        self.resolution=directory/'resolution.json'

    def tearDown(self):
        self.f.tearDown()

    def close(self):
        fixtures.write(self.resolution,self.payload)
        return fixtures.route.execute('repair-close',self.f.record,self.f.base,index=1,run=self.f.rel(self.resolution))

    def test_only_reviewed_unaffected_script_results_are_preserved(self):
        result=self.close();self.assertEqual(result['nextVisitIndex'],1)
        data=fixtures.route.load_data(self.f.record,self.f.base)
        self.assertEqual(data['details'][0][0],'passed')
        self.assertNotEqual(data['details'][1][0],'passed')
        self.assertEqual(self.failed['visits'][0]['outcome'],'failed')
        self.assertFalse(result['canAdvance'])
        self.f.assert_planning_unchanged()
        (self.f.base/'source.py').write_text('# Actual product source changed\n',encoding='utf-8')
        data=fixtures.route.load_data(self.f.record,self.f.base)
        self.assertEqual(data['details'][0][0],'stale')

    def test_affected_case_cannot_be_declared_unaffected(self):
        self.payload['harnessArchive']['unaffectedCaseIds'].append(self.case1)
        with self.assertRaisesRegex(ValueError,'unaffected'):
            self.close()

    def test_archive_tampering_or_unreviewed_driver_edit_cannot_preserve(self):
        self.close()
        self.f.script.write_text('# Unreviewed later change\n',encoding='utf-8')
        self.assertEqual(fixtures.route.load_data(self.f.record,self.f.base)['details'][0][0],'stale')
        self.archive.write_text('# Tampered historic source\n',encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'archive bytes'):
            fixtures.route.load_data(self.f.record,self.f.base)


if __name__=='__main__':unittest.main()
