"""Mechanical regressions with synthetic evidence; these are NOT real human/LLM approvals."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import model_tools as mt
import workflow as wf
import semantic_checks as sc

TEST_ROOT = None


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="requirements-dual-gates-", dir=TEST_ROOT)
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.run = self.home / "run"
        wf.initialize(self.run, "synthetic-test", "test-builder-context")

    def save(self, model, kind, ids, evidence=(), round_id=None):
        state = wf.read(self.run / "run-state.json")
        state.update(next_action="Continue synthetic test", active_node_id=None, waiting_for_user=False)
        count = len(state["completed_step_ids"])
        record = {"id": "step-" + str(count), "kind": kind, "entityIds": ids,
                  "evidenceRefs": list(evidence), "summary": "Synthetic mechanical regression unit"}
        if round_id:
            record["roundId"] = round_id
        wf.write(self.run / "analysis-model.json", model)
        wf.write(self.run / "step.json", record)
        wf.write(self.run / "run-state.json", state)
        return wf.checkpoint(self.run, self.run / "analysis-model.json", self.run / "run-state.json",
                             self.run / "step.json", wf.read(self.run / "current.json")["checkpoint"])

    def baseline(self):
        model = wf.read(self.run / "analysis-model.json")
        model.update(revision="r1", scope={"objective": "Headless value receiver TEST ONLY",
                     "included": ["receive value"], "excluded": ["UI"], "abstraction": "absent/present"})
        (self.run / "evidence/prd.md").write_text("Synthetic PRD: receiving value moves absent to present; no UI.", encoding="utf8")
        model["sources"] = [{"id": "SRC", "kind": "prd", "uri": "synthetic:test", "locator": "whole",
            "version": "1", "readRanges": ["whole"], "evidencePath": "evidence/prd.md", "sha256": wf.file_hash(self.run / "evidence/prd.md")}]
        self.save(model, "source", ["SRC"], ["evidence/prd.md"])
        (self.run / "evidence/scope.md").write_text("SYNTHETIC HUMAN RECORD FOR TEST ONLY: scope confirmed", encoding="utf8")
        model["revision"] = "r2"
        model["sources"].append({"id": "HUMAN", "kind": "human", "uri": "synthetic:scope", "locator": "whole", "version": "1",
            "readRanges": ["whole"], "evidencePath": "evidence/scope.md", "sha256": wf.file_hash(self.run / "evidence/scope.md")})
        model["confirmations"] = [{"stage": "scope", "revision": "r2", "sourceId": "HUMAN", "humanReference": "SYNTHETIC-ONLY",
            "summary": "SYNTHETIC ONLY", "scopeDigest": mt.scope_digest(model)}]
        self.save(model, "decision", ["HUMAN", "scope"], ["evidence/scope.md"])
        model.update(revision="r3", phase="analyzing")
        model["features"] = [{"id": "F", "title": "receiver", "scope": "value receiver", "entryStateIds": ["S0"],
            "entryEvidence": [{"stateId": "S0", "sourceIds": ["SRC"], "reason": "Synthetic receiver begins with absent value"}]}]
        model["states"] = [{"id": sid, "featureIds": ["F"], "title": title, "facts": [title], "uiRefs": [],
                           "sourceIds": ["SRC"], "status": "draft"} for sid, title in [("S0", "absent"), ("S1", "present")]]
        model["transitions"] = [{"id": "T", "featureIds": ["F"], "from": "S0", "to": "S1", "event": "receive value", "guard": "true",
                                 "requirementId": "R", "sourceIds": ["SRC"], "status": "draft"}]
        model["requirements"] = [{"id": "R", "transitionId": "T", "title": "receive value", "ruleIds": [],
            "acceptance": [{"id": "AC", "given": "value absent", "when": "value received", "then": ["value present"]}],
            "uiRefs": [], "uiApplicability": {"status": "not_applicable", "reason": "headless synthetic PRD"}, "sourceIds": ["SRC"], "status": "draft"}]
        model["witnesses"] = [{"id": "W", "transitionId": "T", "entryStateId": "S0",
            "pathTransitionIds": ["T"], "scenarioFacts": ["value is absent at startup"],
            "stepEvidence": [{"transitionId": "T", "eventEnabledReason": "receiver is ready",
                              "guardSatisfiedReason": "unconditional receive",
                              "resultReason": "value becomes present"}], "sourceIds": ["SRC"]}]
        model["coverageClaims"] = [{"id": "COV", "sourceId": "SRC", "locator": "whole",
            "disposition": "covered", "relatedIds": ["R"], "reason": "Synthetic receive clause maps to R"}]
        model["continuationAssessments"] = []
        model["rounds"] = [{"id": "BUILD", "kind": "build", "revision": "r3", "nodeIds": ["S0", "S1"],
            "checks": [], "changes": [{"kind": "add", "entityId": "T", "meaning": "value receiving obligation", "sourceIds": ["SRC"]}], "openFrontier": ["S0", "S1"]}]
        self.save(model, "model", ["S0", "S1", "T", "R"])
        model["rounds"].append({"id": "AUDIT", "kind": "audit", "revision": "r3", "nodeIds": ["S0", "S1"], "checks": [], "changes": [], "openFrontier": []})
        self.save(model, "round", ["AUDIT"])
        for sid in ("S0", "S1"):
            model["rounds"][-1]["checks"].extend({"nodeId": sid, "dimension": dim, "disposition": "not_applicable",
                 "reason": "Synthetic contract fixture; not a semantic completeness claim: " + dim, "evidenceIds": ["SRC"], "relatedIds": ["R"]}
                 for dim in sorted(mt.DIMENSIONS))
            self.save(model, "node_audit", [sid], round_id="AUDIT")
        model["phase"] = "review_ready"
        model["rounds"][-1]["modelDigest"] = mt.model_digest(model)
        self.save(model, "round", ["AUDIT"])
        return model

    def bundle_and_report(self, model):
        bundle = self.home / "review"
        manifest = wf.export_bundle(model, bundle, self.run)
        (self.run / "evidence/reviewer.md").write_text("SYNTHETIC MODEL CONTRACT RECORD ONLY; not actual independent acceptance", encoding="utf8")
        report = {"review_id": "SYNTHETIC", "reviewer_context_ref": "test-independent-context", "independent": True,
            "reviewed_revision": model["revision"], "semantic_digest": mt.model_digest(model), "bundle_digest": manifest["bundle_digest"],
            "reviewed_entity_ids": sorted(wf.entity_ids(model)), "input_complete": True,
            "criteria_results": [{"criterion_id": key, "status": "passed", "reason": "Synthetic contract test only", "affected_ids": ["R"],
               "evidence_refs": ["evidence/reviewer.md"]} for key in wf.read(wf.TEMPLATE)["required_criteria"]],
            "evidence_files": {"evidence/reviewer.md": wf.file_hash(self.run / "evidence/reviewer.md")},
            "findings": [], "limitations": ["SYNTHETIC NOT REAL REVIEW"], "html_runtime_verified": True}
        report_path = self.run / "model-review.json"
        wf.write(report_path, report)
        return bundle, report_path, report

    def test_init_pending_and_template_tamper(self):
        value = wf.contract(self.run)
        self.assertTrue(all(c["status"] == "pending" for c in value["checks"].values()))
        value["required_rule_ids"].pop()
        wf.write(self.run / "gate-contract.json", value)
        with self.assertRaisesRegex(ValueError, "fixed template"):
            wf.contract(self.run)

    def test_scope_content_change_rejects_old_confirmation_F01(self):
        model = self.baseline()
        model["scope"]["included"].append("new business")
        errors, _ = mt.validate(model)
        self.assertTrue(any("scopeDigest" in e for e in errors))

    def test_same_scope_new_revision_is_accepted(self):
        model = self.baseline()
        model.update(revision="r4", phase="analyzing")
        errors, _ = mt.validate(model)
        self.assertFalse(errors, errors)

    def test_final_confirmation_bound_to_semantic_digest_F02(self):
        model = self.baseline()
        model["phase"] = "confirmed"
        for key in ("states", "transitions", "requirements"):
            for entity in model[key]:
                entity["status"] = "confirmed"
        model["confirmations"].append({"stage": "final", "revision": "r3", "humanReference": "TEST-ONLY", "summary": "synthetic",
                                      "semanticDigest": mt.model_digest(model), "coveredIds": sorted(wf.entity_ids(model))})
        self.assertFalse(mt.validate(model, final=True)[0])
        model["requirements"][0]["acceptance"][0]["then"] = ["changed result"]
        model["rounds"][-1]["modelDigest"] = mt.model_digest(model)
        self.assertTrue(any("final human confirmation" in e for e in mt.validate(model, final=True)[0]))

    def test_export_failure_does_not_publish_partial_bundle_F03(self):
        model = self.baseline()
        target = self.home / "new-bundle"
        original_write = wf.write
        def fail(path, value):
            if Path(path).name == "atomic-requirements.json":
                raise OSError("injected output failure")
            return original_write(path, value)
        with patch.object(wf, "write", side_effect=fail):
            with self.assertRaises(OSError):
                wf.export_bundle(model, target, self.run)
        self.assertFalse(target.exists())
        bundle, _, _ = self.bundle_and_report(model)
        before = wf.file_hash(bundle / "manifest.json")
        with self.assertRaises(ValueError):
            wf.export_bundle(model, bundle, self.run)
        self.assertEqual(before, wf.file_hash(bundle / "manifest.json"))

    def test_review_ready_without_rounds_rejected_F04(self):
        model = self.baseline()
        model["rounds"] = []
        self.assertTrue(mt.validate(model)[0])

    def test_nonblocking_question_backlink_enforced_F05(self):
        model = self.baseline()
        model["questions"] = [{"id": "Q", "question": "undefined", "blocking": False, "status": "open", "affectedIds": ["R"]}]
        self.assertTrue(any("backlink" in e for e in mt.validate(model)[0]))

    def test_continuation_id_tuple_is_unambiguous_F06(self):
        model = self.baseline()
        model["phase"] = "analyzing"
        req, transition = model["requirements"][0], model["transitions"][0]
        model["requirements"], model["transitions"] = [], []
        for i, rid in enumerate(["A:B", "C", "A", "B:C"]):
            r, t = copy.deepcopy(req), copy.deepcopy(transition)
            r.update(id=rid, transitionId="T" + str(i))
            t.update(id="T" + str(i), requirementId=rid, **{"from": "S0", "to": "S0"})
            model["requirements"].append(r)
            model["transitions"].append(t)
        data = mt.exports(model)["requirement-graph.json"]
        self.assertEqual(16, len(data["edges"]))
        self.assertEqual(16, len({e["id"] for e in data["edges"]}))

    def test_audit_unknown_node_and_related_id_rejected_F07(self):
        model = self.baseline()
        model["rounds"][-1]["checks"][0]["nodeId"] = "UNKNOWN"
        model["rounds"][-1]["checks"][1]["relatedIds"] = ["TYPO"]
        errors, _ = mt.validate(model)
        self.assertTrue(any("snapshot" in e for e in errors))
        self.assertTrue(any("relatedId" in e for e in errors))

    def test_stale_checkpoint_base_rejected_F08(self):
        self.baseline()
        wf.write(self.run / "step.json", {"id": "stale", "kind": "pause", "entityIds": [], "evidenceRefs": [], "summary": "stale"})
        with self.assertRaisesRegex(ValueError, "stale"):
            wf.checkpoint(self.run, self.run / "analysis-model.json", self.run / "run-state.json", self.run / "step.json", "000000-init")

    def test_interrupted_commit_resumes_previous_complete_frontier(self):
        model = self.baseline()
        model.update(revision="r4", phase="analyzing")
        model["questions"] = [{"id": "Q", "question": "unknown new rule", "blocking": False, "status": "open", "affectedIds": ["R"]}]
        model["requirements"][0]["questionIds"] = ["Q"]
        self.save(model, "question", ["Q", "R"])
        before = wf.load_checkpoint(self.run)
        with patch.object(wf, "atomic_json", side_effect=OSError("interrupted before pointer switch")):
            with self.assertRaises(OSError):
                self.save(model, "round", ["AUDIT"])
        restored = wf.history(self.run)[-1]
        self.assertEqual(before[0], restored[0])
        self.assertEqual(["Q"], restored[2]["open_question_ids"])
        self.assertEqual(["S0", "S1"], restored[2]["pending_node_ids"])
        self.assertEqual("Continue synthetic test", restored[2]["next_action"])

    def test_independent_report_missing_failed_stale_and_inconclusive(self):
        model = self.baseline()
        bundle, path, report = self.bundle_and_report(model)
        result = wf.gate(self.run, bundle)
        self.assertEqual("pending", result["checks"]["MODEL-REVIEW-001"]["status"])
        self.assertEqual("awaiting_final_confirmation", wf.gate(self.run, bundle, path)["gate_status"])
        for field, value in [("semantic_digest", "stale"), ("reviewer_context_ref", "test-builder-context"), ("bundle_digest", "stale")]:
            bad = {**report, field: value}
            wf.write(path, bad)
            self.assertEqual("failed", wf.gate(self.run, bundle, path)["checks"]["MODEL-REVIEW-001"]["status"])
        for status, expected in [("failed", "failed"), ("inconclusive", "pending")]:
            bad = copy.deepcopy(report)
            bad["criteria_results"][0]["status"] = status
            wf.write(path, bad)
            self.assertEqual(expected, wf.gate(self.run, bundle, path)["checks"]["MODEL-REVIEW-001"]["status"])

    def test_publish_only_after_current_human_evidence(self):
        model = self.baseline()
        bundle, path, report = self.bundle_and_report(model)
        reply = self.run / "evidence/final.md"
        reply.write_text("SYNTHETIC HUMAN CONFIRMATION FOR MECHANICAL TEST ONLY", encoding="utf8")
        approval = {"revision": model["revision"], "semantic_digest": mt.model_digest(model),
            "bundle_digest": wf.verify_folder(bundle)["bundle_digest"], "review_digest": wf.file_hash(path),
            "covered_ids": sorted(wf.entity_ids(model)), "human_reference": "SYNTHETIC-ONLY", "summary": "Test only",
            "evidence_path": "evidence/final.md", "evidence_sha256": wf.file_hash(reply)}
        ap = self.run / "acceptance.json"
        wf.write(ap, approval)
        self.assertEqual("failed", wf.gate(self.run, bundle, path, ap)["checks"]["APPROVAL-001"]["status"])
        self.save(model, "decision", ["scope"], ["evidence/final.md"])
        self.assertEqual("passed", wf.gate(self.run, bundle, path, ap)["gate_status"])
        target = self.home / "accepted"
        completed = subprocess.run([sys.executable, str(wf.SKILL / "scripts/workflow.py"), "publish", str(self.run), str(target),
                 "--bundle", str(bundle), "--review", str(path), "--approval", str(ap)], capture_output=True, text=True, encoding="utf8")
        self.assertEqual(0, completed.returncode, completed.stdout + completed.stderr)
        self.assertEqual("accepted_delivery", wf.verify_folder(target)["kind"])
        approval["semantic_digest"] = "stale"
        wf.write(ap, approval)
        self.assertEqual("failed", wf.gate(self.run, bundle, path, ap)["gate_status"])

    def test_corrupted_evidence_cannot_resume(self):
        self.baseline()
        (self.run / "evidence/prd.md").write_text("changed", encoding="utf8")
        with self.assertRaisesRegex(ValueError, "evidence changed"):
            wf.history(self.run)

    def test_dual_completeness_evidence_and_exports(self):
        model = self.baseline()
        self.assertTrue(all(not x for x in sc.inspect(model).values()), sc.inspect(model))
        artifacts = mt.exports(model)
        self.assertIn("execution-witnesses.json", artifacts)
        self.assertIn("coverage-report.json", artifacts)
        original_digest = mt.model_digest(model)
        model["witnesses"][0]["scenarioFacts"].append("user is online")
        self.assertNotEqual(original_digest, mt.model_digest(model))

    def test_missing_entry_witness_and_coverage_are_rejected(self):
        model = self.baseline()
        model["features"][0]["entryEvidence"] = []
        self.assertTrue(sc.inspect(model)["STRUCTURE-001"])
        model["features"][0]["entryEvidence"] = [{"stateId": "S0", "sourceIds": ["SRC"], "reason": "from source"}]
        model["witnesses"] = []
        self.assertTrue(sc.inspect(model)["FEASIBILITY-001"])
        model["witnesses"] = [{"id": "W", "transitionId": "T", "entryStateId": "S0",
            "pathTransitionIds": ["T"], "scenarioFacts": ["value absent"],
            "stepEvidence": [{"transitionId": "T", "eventEnabledReason": "allowed",
                              "guardSatisfiedReason": "true", "resultReason": "now present"}],
            "sourceIds": ["SRC"]}]
        model["coverageClaims"] = []
        self.assertTrue(sc.inspect(model)["COVERAGE-001"])

    def test_broken_path_is_not_valid_executable_witness(self):
        model = self.baseline()
        model["witnesses"][0]["entryStateId"] = "S1"
        self.assertTrue(sc.inspect(model)["FEASIBILITY-001"])
        model["witnesses"][0]["entryStateId"] = "S0"
        model["witnesses"][0]["stepEvidence"][0]["guardSatisfiedReason"] = ""
        self.assertTrue(sc.inspect(model)["FEASIBILITY-001"])

    def test_continuation_requires_consecutive_witness(self):
        model = self.baseline()
        model["states"].append({"id": "S2", "featureIds": ["F"], "title": "finished",
            "facts": ["finished"], "uiRefs": [], "sourceIds": ["SRC"], "status": "draft"})
        model["transitions"].append({"id": "T2", "featureIds": ["F"], "from": "S1", "to": "S2",
            "event": "complete", "guard": "true", "requirementId": "R2",
            "sourceIds": ["SRC"], "status": "draft"})
        model["requirements"].append({"id": "R2", "transitionId": "T2", "title": "complete",
            "ruleIds": [], "acceptance": [{"id": "AC2", "given": "present",
            "when": "complete", "then": ["finished"]}], "uiRefs": [],
            "uiApplicability": {"status": "not_applicable", "reason": "headless"},
            "sourceIds": ["SRC"], "status": "draft"})
        model["witnesses"].append({"id": "W2", "transitionId": "T2",
            "entryStateId": "S0", "pathTransitionIds": ["T", "T2"],
            "scenarioFacts": ["value received before completing"],
            "stepEvidence": [
                {"transitionId": "T", "eventEnabledReason": "ready",
                 "guardSatisfiedReason": "true", "resultReason": "present"},
                {"transitionId": "T2", "eventEnabledReason": "present",
                 "guardSatisfiedReason": "true", "resultReason": "finished"}],
            "sourceIds": ["SRC"]})
        model["coverageClaims"][0]["relatedIds"].append("R2")
        self.assertTrue(sc.inspect(model)["CONTINUATION-001"])
        model["continuationAssessments"] = [{"id": "C1", "fromRequirementId": "R",
            "toRequirementId": "R2", "status": "witnessed", "witnessId": "W2",
            "reason": "W2 contains both steps", "sourceIds": ["SRC"]}]
        self.assertFalse(sc.inspect(model)["CONTINUATION-001"])
        model["continuationAssessments"][0]["witnessId"] = "W"
        self.assertTrue(sc.inspect(model)["CONTINUATION-001"])
        model["continuationAssessments"][0]["status"] = "pending"
        self.assertTrue(sc.inspect(model)["CONTINUATION-001"])

    def test_malformed_json_types_return_diagnostics(self):
        for model in [None, [], {"schemaVersion": 2, "scope": [], "states": [{"id": ["bad"]}]}]:
            self.assertTrue(mt.validate(model)[0])


if __name__ == "__main__":
    if "--test-root" in sys.argv:
        index = sys.argv.index("--test-root")
        TEST_ROOT = Path(sys.argv[index + 1]).resolve()
        TEST_ROOT.mkdir(parents=True, exist_ok=True)
        del sys.argv[index:index + 2]
    unittest.main(verbosity=2)
