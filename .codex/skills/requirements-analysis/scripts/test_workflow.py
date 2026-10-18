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
from requirement_graph import full_requirement_graph

TEST_ROOT = None


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="requirements-current-", dir=TEST_ROOT)
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.run = self.home / "run"
        wf.initialize(self.run, "synthetic-test", "test-builder-context")

    def save(self, model, kind=None, ids=None, evidence=(), round_id=None):
        state = wf.read(wf.work(self.run, "run-state.json"))
        state.update(next_action="Continue synthetic test", active_node_id=None, waiting_for_user=False)
        model.pop("revision", None)
        for key in ("rounds", "confirmations"):
            for item in model[key]:
                item.pop("revision", None)
        if model["rounds"] and model["rounds"][-1]["kind"] == "audit":
            model["rounds"][-1].setdefault("modelDigest", mt.model_digest(model))
        wf.write(wf.work(self.run, "analysis-model.json"), model)
        wf.write(wf.work(self.run, "run-state.json"), state)
        return wf.save_current(self.run)


    def baseline(self):
        model = wf.read(wf.work(self.run, "analysis-model.json"))
        model.update(revision="r1", scope={"objective": "Headless value receiver TEST ONLY",
                     "included": ["receive value"], "excluded": ["UI"], "abstraction": "absent/present"})
        (self.run / "_process/evidence/prd.md").write_text("Synthetic PRD: receiving value moves absent to present; no UI.", encoding="utf8")
        model["sources"] = [{"id": "SRC", "kind": "prd", "uri": "synthetic:test", "locator": "whole",
            "version": "1", "readRanges": ["whole"], "evidencePath": "_process/evidence/prd.md", "sha256": wf.file_hash(self.run / "_process/evidence/prd.md")}]
        self.save(model, "source", ["SRC"], ["_process/evidence/prd.md"])
        (self.run / "_process/evidence/scope.md").write_text("SYNTHETIC HUMAN RECORD FOR TEST ONLY: scope confirmed", encoding="utf8")
        model["revision"] = "r2"
        model["sources"].append({"id": "HUMAN", "kind": "human", "uri": "synthetic:scope", "locator": "whole", "version": "1",
            "readRanges": ["whole"], "evidencePath": "_process/evidence/scope.md", "sha256": wf.file_hash(self.run / "_process/evidence/scope.md")})
        model["confirmations"] = [{"stage": "scope", "revision": "r2", "sourceId": "HUMAN", "humanReference": "SYNTHETIC-ONLY",
            "summary": "SYNTHETIC ONLY", "scopeDigest": mt.scope_digest(model)}]
        self.save(model, "decision", ["HUMAN", "scope"], ["_process/evidence/scope.md"])
        model.update(revision="r3", phase="analyzing")
        model["features"] = [{"id": "F", "title": "receiver", "scope": "value receiver", "entryStateIds": ["S0"]}]
        model["entryStateIds"] = ["S0"]
        model["states"] = [{"id": sid, "featureIds": ["F"], "title": title, "facts": [title], "uiRefs": [],
                           "sourceIds": ["SRC"], "status": "draft"} for sid, title in [("S0", "absent"), ("S1", "present")]]
        model["transitions"] = [{"id": "T", "featureIds": ["F"], "from": "S0", "to": "S1", "event": "receive value", "guard": "true",
                                 "requirementId": "R", "sourceIds": ["SRC"], "status": "draft"}]
        model["requirements"] = [{"id": "R", "transitionId": "T", "title": "receive value", "ruleIds": [],
            "acceptance": [{"id": "AC", "given": "value absent", "when": "value received", "then": ["value present"]}],
            "uiRefs": [], "uiApplicability": {"status": "not_applicable", "reason": "headless synthetic PRD"}, "sourceIds": ["SRC"], "status": "draft"}]
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
        bundle = self.run
        manifest = wf.export_bundle(model, bundle, self.run)
        (self.run / "_process/evidence/reviewer.md").write_text("SYNTHETIC MODEL CONTRACT RECORD ONLY; not actual independent acceptance", encoding="utf8")
        report = {"review_id": "SYNTHETIC", "reviewer_context_ref": "test-independent-context", "independent": True,
            "semantic_digest": mt.model_digest(model), "bundle_digest": manifest["bundle_digest"],
            "reviewed_entity_ids": sorted(wf.entity_ids(model)), "input_complete": True,
            "criteria_results": [{"criterion_id": key, "status": "passed", "reason": "Synthetic contract test only", "affected_ids": ["R"],
               "evidence_refs": ["_process/evidence/reviewer.md"]} for key in wf.read(wf.TEMPLATE)["required_criteria"]],
            "evidence_files": {"_process/evidence/reviewer.md": wf.file_hash(self.run / "_process/evidence/reviewer.md")},
            "findings": [], "limitations": ["SYNTHETIC NOT REAL REVIEW"], "html_runtime_verified": True}
        report_path = wf.work(self.run, "model-review.json")
        wf.write(report_path, report)
        return bundle, report_path, report

    def test_init_pending_and_template_tamper(self):
        value = wf.contract(self.run)
        self.assertTrue(all(c["status"] == "pending" for c in value["checks"].values()))
        value["required_rule_ids"].pop()
        wf.write(wf.work(self.run, "gate-contract.json"), value)
        with self.assertRaisesRegex(ValueError, "fixed template"):
            wf.contract(self.run)

    def test_transition_feasibility_gate_rejects_reachable_but_impossible_edge(self):
        model=self.baseline();model['phase']='analyzing'
        model['pathContext']={'domains':{'x':{'values':['zero','positive'],'labels':{'zero':'无','positive':'有'},'description':'数量'}},
            'entryContexts':{'S0':{'x':['zero']}},'transitionRules':{'T':{'cases':[{'requires':{'x':['positive']}}],'reason':'合成','sourceRefs':[{'sourceId':'SRC','locator':'合成'}]}}}
        self.save(model)
        result=wf.gate(self.run)
        self.assertEqual('failed',result['checks']['FEASIBILITY-001']['status'])
        self.assertEqual('failed',result['checks']['LINK-001']['status'])

    def test_declared_case_failure_blocks_even_when_transition_has_witness(self):
        model=self.baseline();model['phase']='analyzing'
        model['pathContext']={'domains':{'x':{'values':['zero','positive'],'labels':{'zero':'无','positive':'有'},'description':'数量'}},
            'entryContexts':{'S0':{'x':['zero']}},'transitionRules':{'T':{'cases':[{'requires':{'x':['zero']}},{'requires':{'x':['positive']}}],'reason':'合成','sourceRefs':[{'sourceId':'SRC','locator':'合成'}]}}}
        self.save(model)
        result=wf.gate(self.run)
        self.assertEqual('failed',result['checks']['FEASIBILITY-001']['status'])
        self.assertTrue(any('declared case' in str(f) for f in result['failures']))

    def test_unmodeled_guard_does_not_pass_feasibility_gate(self):
        model=self.baseline();model['phase']='analyzing';model['transitions'][0]['guard']='未编码的合成条件'
        self.save(model)
        result=wf.gate(self.run)
        self.assertEqual('pending',result['checks']['FEASIBILITY-001']['status'])
        self.assertEqual('failed',result['checks']['LINK-001']['status'])

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

    def test_export_reuses_directory_and_cleans_transient_staging(self):
        model = self.baseline()
        bundle, _, _ = self.bundle_and_report(model)
        before = wf.file_hash(bundle / "manifest.json")
        original_write = wf.write
        def fail(path, value):
            if Path(path).name == "atomic-requirements.json":
                raise OSError("injected output failure")
            return original_write(path, value)
        with patch.object(wf, "write", side_effect=fail):
            with self.assertRaises(OSError):
                wf.export_bundle(model, bundle, self.run)
        self.assertEqual(before, wf.file_hash(bundle / "manifest.json"))
        wf.export_bundle(model, bundle, self.run)
        self.assertEqual(before, wf.file_hash(bundle / "manifest.json"))
        self.assertFalse(list(wf.work(self.run).glob(".render-*")))


    def test_review_ready_without_rounds_rejected_F04(self):
        model = self.baseline()
        model["rounds"] = []
        self.assertTrue(mt.validate(model)[0])

    def test_nonblocking_question_backlink_enforced_F05(self):
        model = self.baseline()
        model["questions"] = [{"id": "Q", "question": "undefined", "blocking": False, "status": "open", "affectedIds": ["R"]}]
        self.assertTrue(any("backlink" in e for e in mt.validate(model)[0]))

    def test_requirement_coverage_gate_rejects_uncovered_nodes(self):
        model = self.baseline()
        model['phase'] = 'analyzing'
        for sid in ('ISOLATED_FROM', 'ISOLATED_TO'):
            state = copy.deepcopy(model['states'][0]);state['id'] = sid
            model['states'].append(state)
        t = copy.deepcopy(model['transitions'][0])
        t.update(id='ISOLATED_TRANSITION', requirementId='ISOLATED_REQUIREMENT', **{'from':'ISOLATED_FROM','to':'ISOLATED_TO'})
        r = copy.deepcopy(model['requirements'][0])
        r.update(id='ISOLATED_REQUIREMENT', transitionId=t['id'])
        model['transitions'].append(t);model['requirements'].append(r)
        self.save(model)
        data = mt.exports(model)['requirement-graph.json']
        self.assertIn('ISOLATED_REQUIREMENT', data['reduction']['unreachableRequirementIds'])
        self.assertEqual('failed', wf.gate(self.run)['checks']['LINK-001']['status'])

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
        candidates = full_requirement_graph(model)
        self.assertEqual(16, len(candidates["edges"]))
        self.assertEqual(16, len({e["id"] for e in candidates["edges"]}))
        data = mt.exports(model)["requirement-graph.json"]
        self.assertEqual(4, len(data["nodes"]))
        self.assertEqual(3, len(data["edges"]))  # Four requirements in one continuous sequence.

    def test_audit_unknown_node_and_related_id_rejected_F07(self):
        model = self.baseline()
        model["rounds"][-1]["checks"][0]["nodeId"] = "UNKNOWN"
        model["rounds"][-1]["checks"][1]["relatedIds"] = ["TYPO"]
        errors, _ = mt.validate(model)
        self.assertTrue(any("snapshot" in e for e in errors))
        self.assertTrue(any("relatedId" in e for e in errors))

    def test_current_updates_need_no_version_or_snapshots(self):
        model = self.baseline()
        self.assertNotIn("revision", model)
        model["phase"] = "analyzing"
        model["states"][0]["title"] = "updated absent state"
        self.save(model)
        self.assertEqual("updated absent state", wf.load_current(self.run)[0]["states"][0]["title"])
        for name in ("checkpoints", "current.json", "execution.jsonl", "step.json"):
            self.assertFalse((self.run / name).exists(), name)
        self.assertEqual(["S0", "S1"], wf.load_current(self.run)[1]["pending_node_ids"])


    def test_interruption_keeps_current_input_and_rejects_stale_state(self):
        model = self.baseline()
        model["phase"] = "analyzing"
        model["states"][0]["title"] = "unfinished current edit"
        with patch.object(wf, "atomic_json", side_effect=OSError("interrupted write")):
            with self.assertRaises(OSError):
                self.save(model)
        with self.assertRaisesRegex(ValueError, "current files changed"):
            wf.load_current(self.run)
        self.assertEqual("unfinished current edit", wf.read(wf.work(self.run, "analysis-model.json"))["states"][0]["title"])
        self.save(model)
        self.assertEqual(["S0", "S1"], wf.load_current(self.run)[1]["pending_node_ids"])


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

    def test_publish_requires_current_human_evidence_without_copying_output(self):
        model = self.baseline()
        bundle, report_path, report = self.bundle_and_report(model)
        reply = self.run / "_process/evidence/final.md"
        reply.write_text("SYNTHETIC HUMAN CONFIRMATION FOR MECHANICAL TEST ONLY", encoding="utf8")
        approval = {"semantic_digest": mt.model_digest(model),
            "bundle_digest": wf.verify_folder(bundle)["bundle_digest"], "review_digest": wf.file_hash(report_path),
            "covered_ids": sorted(wf.entity_ids(model)), "human_reference": "SYNTHETIC-ONLY", "summary": "Test only",
            "evidence_path": "_process/evidence/final.md", "evidence_sha256": wf.file_hash(reply)}
        ap = self.run / "acceptance.json"
        wf.write(ap, approval)
        self.assertEqual("passed", wf.gate(self.run, bundle, report_path, ap)["gate_status"])
        before = set(self.home.iterdir())
        completed = subprocess.run([sys.executable, str(wf.SKILL / "scripts/workflow.py"), "publish", str(self.run)], capture_output=True, text=True, encoding="utf8")
        self.assertEqual(0, completed.returncode, completed.stdout + completed.stderr)
        self.assertEqual(before, set(self.home.iterdir()))
        reply.write_text("changed reply", encoding="utf8")
        self.assertEqual("failed", wf.gate(self.run, bundle, report_path, ap)["checks"]["APPROVAL-001"]["status"])
        approval["semantic_digest"] = "stale"
        wf.write(ap, approval)
        self.assertEqual("failed", wf.gate(self.run, bundle, report_path, ap)["gate_status"])


    def test_corrupted_evidence_cannot_resume(self):
        self.baseline()
        (self.run / "_process/evidence/prd.md").write_text("changed", encoding="utf8")
        with self.assertRaisesRegex(ValueError, "evidence changed"):
            wf.load_current(self.run)


    def test_new_audit_round_reopens_full_queue_without_semantic_change(self):
        model = self.baseline()
        model["phase"] = "analyzing"
        model["rounds"].append({"id": "AUDIT-NEW", "kind": "audit",
                                "nodeIds": ["S0", "S1"], "checks": [], "changes": [], "openFrontier": []})
        result = self.save(model, "round", ["AUDIT-NEW"])
        self.assertEqual(["S0", "S1"], result["pending_node_ids"])

    def test_duplicate_transition_signature_is_rejected(self):
        model = self.baseline()
        model["phase"] = "analyzing"
        t, r = copy.deepcopy(model["transitions"][0]), copy.deepcopy(model["requirements"][0])
        t.update(id="T-DUPLICATE", requirementId="R-DUPLICATE")
        r.update(id="R-DUPLICATE", transitionId="T-DUPLICATE")
        model["transitions"].append(t)
        model["requirements"].append(r)
        self.assertTrue(any("duplicate transition signature" in e for e in mt.validate(model)[0]))


    def test_malformed_json_types_return_diagnostics(self):
        for model in [None, [], {"schemaVersion": 2, "scope": [], "states": [{"id": ["bad"]}]}]:
            self.assertTrue(mt.validate(model)[0])

    def test_output_refuses_unrelated_files(self):
        model = self.baseline()
        target = self.run
        user_file = target / "notes.txt"
        user_file.write_text("user notes", encoding="utf8")
        with self.assertRaisesRegex(ValueError, "unrelated"):
            wf.export_bundle(model, target, self.run)
        self.assertEqual("user notes", user_file.read_text(encoding="utf8"))

    def test_same_revision_label_cannot_keep_stale_review(self):
        model = self.baseline()
        bundle, report_path, report = self.bundle_and_report(model)
        model["phase"] = "analyzing"
        model["requirements"][0]["acceptance"][0]["then"] = ["new observable obligation"]
        self.save(model)
        wf.export_bundle(model, bundle, self.run)
        result = wf.gate(self.run, bundle, report_path)
        self.assertEqual("failed", result["checks"]["MODEL-REVIEW-001"]["status"])
        self.assertEqual("failed", result["checks"]["AUDIT-001"]["status"])

    def test_save_invalidates_previous_gate_result(self):
        model = self.baseline()
        bundle, report_path, _ = self.bundle_and_report(model)
        wf.gate(self.run, bundle, report_path)
        self.assertTrue((self.run / "gate-result.json").exists())
        self.save(model)
        self.assertFalse((self.run / "gate-result.json").exists())
        self.assertEqual("pending", wf.contract(self.run)["gate_status"])

    def test_init_creates_only_one_process_subdirectory(self):
        self.assertEqual({"_process"}, {p.name for p in self.run.iterdir()})
        self.assertEqual({"analysis-model.json", "run-state.json", "gate-contract.json", "evidence"},
                         {p.name for p in wf.work(self.run).iterdir()})

    def test_deliverables_at_root_and_working_data_stays_in_process(self):
        model = self.baseline()
        self.assertEqual({"_process"}, {p.name for p in self.run.iterdir()})
        wf.export_bundle(model, self.run, self.run)
        self.assertEqual(wf.GENERATED | {"_process"}, {p.name for p in self.run.iterdir()})
        self.assertEqual(["_process"], sorted(p.name for p in self.run.iterdir() if p.is_dir()))
        self.assertEqual(model, wf.read(self.run / "analysis-model.json"))
        self.assertTrue(wf.work(self.run, "analysis-model.json").is_file())

    def test_process_notes_not_hashed_but_deliverable_tampering_rejected(self):
        model = self.baseline()
        before = wf.export_bundle(model, self.run, self.run)
        wf.work(self.run, "notes.txt").write_text("intermediate analysis notes", encoding="utf8")
        self.assertEqual(before, wf.verify_folder(self.run))
        (self.run / "state-graph.json").write_text("{}", encoding="utf8")
        with self.assertRaisesRegex(ValueError, "file digest mismatch"):
            wf.verify_folder(self.run)

    def test_root_export_is_not_the_editing_source(self):
        model = self.baseline()
        wf.export_bundle(model, self.run, self.run)
        changed = copy.deepcopy(model)
        changed["states"][0]["title"] = "tampered root copy"
        wf.write(self.run / "analysis-model.json", changed)
        wf.save_current(self.run)
        self.assertEqual(model, wf.load_current(self.run)[0])
        result = wf.gate(self.run, self.run)
        self.assertEqual("failed", result["checks"]["ARTIFACT-001"]["status"])

    def test_export_cannot_create_an_extra_output_subdirectory(self):
        model = self.baseline()
        with self.assertRaisesRegex(ValueError, "run root"):
            wf.export_bundle(model, self.run / "review", self.run)
        self.assertFalse((self.run / "review").exists())


if __name__ == "__main__":
    if "--test-root" in sys.argv:
        index = sys.argv.index("--test-root")
        TEST_ROOT = Path(sys.argv[index + 1]).resolve()
        TEST_ROOT.mkdir(parents=True, exist_ok=True)
        del sys.argv[index:index + 2]
    unittest.main(verbosity=2)
