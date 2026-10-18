"""Self-loop evidence shape tests; never semantic or human approval evidence."""
import copy
import unittest
import sys
from pathlib import Path

import model_tools as mt
import workflow as wf
import test_workflow as fixtures


class SelfLoopTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.WorkflowTests(methodName="runTest")
        self.fixture.setUp()
        self.model = self.fixture.baseline()
        self.model["phase"] = "analyzing"
        source_path = self.fixture.run / "_process/evidence/prd.md"
        source_path.write_text("Synthetic PRD: receive a value from absent to present. Repeating the same value while present preserves it without another write.", encoding="utf8")
        self.model["sources"][0]["sha256"] = wf.file_hash(source_path)
        original = self.model["transitions"][0]
        self.loop = copy.deepcopy(original)
        self.loop.update(id="LOOP", requirementId="LOOP-R", event="receive same value again", guard="same value already present", **{"from":"S1", "to":"S1"})
        self.loop["selfLoopEvidence"] = {
            "sourceRefs":[{"sourceId":"SRC", "locator":"Synthetic PRD second sentence"}],
            "obligation":"Retain the same value without another write",
            "stateReason":"The value-present control state and stored value remain unchanged"}
        requirement = copy.deepcopy(self.model["requirements"][0])
        requirement.update(id="LOOP-R", transitionId="LOOP", title="Repeat same value")
        requirement["acceptance"] = [{"id":"LOOP-AC", "given":"same value present", "when":"same value received again", "then":["same value present", "no second write"]}]
        self.model["transitions"].append(self.loop)
        self.model["requirements"].append(requirement)

    def tearDown(self):
        self.fixture.tearDown()
        self.fixture.doCleanups()

    def errors(self):
        return mt.validate(self.model)[0]

    def test_supported_evidence_has_valid_structure(self):
        self.assertEqual([], self.errors())

    def test_self_loop_without_evidence_rejected(self):
        del self.loop["selfLoopEvidence"]
        self.assertTrue(any("selfLoopEvidence" in e for e in self.errors()))

    def test_missing_obligation_state_reason_or_citation_rejected(self):
        original = copy.deepcopy(self.loop["selfLoopEvidence"])
        for field in ("obligation", "stateReason", "sourceRefs"):
            with self.subTest(field=field):
                self.loop["selfLoopEvidence"] = copy.deepcopy(original)
                del self.loop["selfLoopEvidence"][field]
                self.assertTrue(self.errors())

    def test_unrelated_source_rejected_even_if_source_exists(self):
        self.loop["selfLoopEvidence"]["sourceRefs"][0]["sourceId"] = "HUMAN"
        self.assertTrue(any("transition source" in e for e in self.errors()))

    def test_unknown_source_and_blank_locator_rejected(self):
        self.loop["selfLoopEvidence"]["sourceRefs"][0] = {"sourceId":"unknown", "locator":""}
        self.assertTrue(any("source must exist" in e for e in self.errors()))
        self.assertTrue(any("locator" in e for e in self.errors()))

    def test_evidence_on_non_loop_rejected(self):
        self.model["transitions"][0]["selfLoopEvidence"] = copy.deepcopy(self.loop["selfLoopEvidence"])
        self.assertTrue(any("only valid for self-loops" in e for e in self.errors()))

    def test_complete_fields_cannot_reuse_old_audit_as_semantic_approval(self):
        self.assertEqual([], self.errors())
        self.assertTrue(mt.validate(self.model, ready=True)[0])

    def test_report_cannot_omit_or_duplicate_current_self_loop(self):
        bundle, report_path, report = self.fixture.bundle_and_report(self.model)
        manifest = wf.verify_folder(bundle)
        contract = wf.contract(self.fixture.run)
        self.assertTrue(any("self-loop review coverage" in e for e in wf.check_review(report, self.model, manifest, contract, self.fixture.run)[0]))
        row = {"transition_id":"LOOP", "status":"passed", "reason":"Synthetic evidence structure test only",
               "evidence_refs":["_process/evidence/reviewer.md"]}
        report["self_loop_reviews"] = [row]
        self.assertEqual(([], []), wf.check_review(report, self.model, manifest, contract, self.fixture.run))
        report["self_loop_reviews"] = [row, copy.deepcopy(row)]
        self.assertTrue(any("coverage" in e for e in wf.check_review(report, self.model, manifest, contract, self.fixture.run)[0]))

    def test_failed_or_pending_self_loop_cannot_be_overridden_by_general_pass(self):
        bundle, report_path, report = self.fixture.bundle_and_report(self.model)
        manifest = wf.verify_folder(bundle)
        contract = wf.contract(self.fixture.run)
        row = {"transition_id":"LOOP", "status":"failed", "reason":"Synthetic unsupported obligation",
               "evidence_refs":["_process/evidence/reviewer.md"]}
        report["self_loop_reviews"] = [row]
        self.assertTrue(any("self-loop review failed" in e for e in wf.check_review(report, self.model, manifest, contract, self.fixture.run)[0]))
        row["status"] = "inconclusive"
        errors, pending = wf.check_review(report, self.model, manifest, contract, self.fixture.run)
        self.assertEqual([], errors)
        self.assertTrue(any("self-loop review inconclusive" in e for e in pending))


if __name__ == "__main__":
    if "--test-root" in sys.argv:
        index = sys.argv.index("--test-root")
        fixtures.TEST_ROOT = Path(sys.argv[index + 1]).resolve()
        fixtures.TEST_ROOT.mkdir(parents=True, exist_ok=True)
        del sys.argv[index:index + 2]
    unittest.main(verbosity=2)
