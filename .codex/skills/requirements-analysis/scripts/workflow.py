#!/usr/bin/env python3
"""Current-file incremental updates and delivery gates. Python 3.10+, standard library only."""
import argparse
import json
import os
import shutil
import sys
import time
import uuid
from pathlib import Path

from model_tools import DIMENSIONS, digest, exports, model_digest, scope_digest, validate

SKILL = Path(__file__).resolve().parent.parent
TEMPLATE = SKILL / "assets" / "gate-contract.json"


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def write(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def file_hash(path):
    import hashlib
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def local(root, name):
    if not isinstance(name, str) or not name.strip():
        raise ValueError("nonempty relative evidence path required")
    target = (root / name).resolve()
    if not target.is_relative_to(root.resolve()):
        raise ValueError("reference escapes run directory: " + name)
    return target


PROCESS_DIR = "_process"
DELIVERABLES = {"analysis-model.json", "state-graph.json", "atomic-requirements.json",
                "requirement-graph.json", "review-log.json", "review.html"}
GENERATED = DELIVERABLES | {"manifest.json"}
ROOT_ALLOWED = GENERATED | {"gate-result.json", "acceptance.json", PROCESS_DIR}


def work(root, name=""):
    return local(Path(root), PROCESS_DIR + "/" + name)


def evidence_file(root, name):
    target = local(Path(root), name)
    if not target.is_relative_to(work(root, "evidence")):
        raise ValueError("analysis evidence must be under _process/evidence: " + str(name))
    return target


def validate_layout(root):
    unknown = {p.name for p in root.iterdir()} - ROOT_ALLOWED
    wrong_dirs = [p.name for p in root.iterdir() if p.is_dir() and p.name != PROCESS_DIR]
    if unknown or wrong_dirs:
        raise ValueError("output root contains intermediate or unrelated files: " + str(sorted(unknown | set(wrong_dirs))))


def atomic_json(path, value):
    temp_dir = path.parent if path.parent.name == PROCESS_DIR else work(path.parent)
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp = temp_dir / (path.name + ".tmp-" + uuid.uuid4().hex)
    try:
        write(temp, value)
        # Windows file scanners and brief file locks can reject an otherwise
        # valid atomic replacement. Retry the *same* prepared file a bounded
        # number of times; persistent permission errors must still fail.
        for attempt in range(4):
            try:
                os.replace(temp, path)
                break
            except PermissionError:
                if attempt == 3:
                    raise
                time.sleep(0.05 * (2 ** attempt))
    finally:
        temp.unlink(missing_ok=True)


def entity_ids(model):
    return {x["id"] for k in ("states", "transitions", "requirements") for x in model[k]}


def verify_folder(folder):
    validate_layout(folder)
    manifest = read(folder / "manifest.json")
    if not isinstance(manifest.get("files"), dict) or set(manifest["files"]) != DELIVERABLES:
        raise ValueError("manifest deliverable set mismatch")
    for name, sha in manifest["files"].items():
        if file_hash(local(folder, name)) != sha:
            raise ValueError("file digest mismatch: " + name)
    if manifest.get("bundle_digest") != digest(manifest["files"]):
        raise ValueError("manifest digest mismatch")
    return manifest


def seal(folder, metadata):
    files = {name: file_hash(folder / name) for name in sorted(DELIVERABLES)}
    manifest = {**metadata, "files": files, "bundle_digest": digest(files)}
    write(folder / "manifest.json", manifest)
    return manifest


def collect_media(root, model):
    import base64
    media = {}
    if root is None:
        return media
    for source in model["sources"]:
        ref = source.get("previewPath", source.get("evidencePath", ""))
        suffix = Path(ref).suffix.lower() if isinstance(ref, str) else ""
        mime = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".gif": "image/gif", ".webp": "image/webp"}.get(suffix)
        if source["kind"] == "ui" and mime:
            media[source["id"]] = "data:" + mime + ";base64," + base64.b64encode(evidence_file(root, ref).read_bytes()).decode("ascii")
    return media


def collect_designs(root, model):
    """Only registered, verified UI JSON sources supply CSS design values."""
    designs = {}
    if root is None:
        return designs
    for source in model["sources"]:
        ref = source.get("evidencePath", "")
        if source["kind"] == "ui" and isinstance(ref, str) and Path(ref).suffix.lower() == ".json":
            raw = read(evidence_file(root, ref))
            if isinstance(raw, dict) and isinstance(raw.get("colors"), dict) and isinstance(raw.get("font"), dict):
                designs[source["id"]] = raw
    return designs


def replace_generated(stage, target):
    """Replace only root deliverables; leave the single process directory intact."""
    validate_layout(target)
    for item in sorted(stage.iterdir(), key=lambda p: p.name == "manifest.json"):
        os.replace(item, target / item.name)


def export_bundle(model, target, root=None):
    """Generate consumer artifacts at RUN root; keep every temporary file below _process."""
    target = Path(target).resolve()
    root = target if root is None else Path(root).resolve()
    if target != root:
        raise ValueError("deliverables must be generated at the run root")
    target.mkdir(parents=True, exist_ok=True)
    validate_layout(target)
    work(root).mkdir(exist_ok=True)
    stage = work(root, ".render-" + uuid.uuid4().hex)
    stage.mkdir()
    try:
        errors, _ = validate(model)
        if errors:
            raise ValueError("cannot export invalid model: " + "; ".join(errors))
        write(stage / "analysis-model.json", model)
        data = exports(model)
        for name, content in data.items():
            write(stage / name, content)
        media = collect_media(root, model)
        from render_review import render
        (stage / "review.html").write_text(render(model, data, media, collect_designs(root, model)), encoding="utf-8")
        manifest = seal(stage, {"schema_version": 2,
                                "semantic_digest": model_digest(model), "kind": "current_analysis"})
        verify_folder(stage)
        replace_generated(stage, target)
        return manifest
    finally:
        shutil.rmtree(stage)


def contract(root):
    value, template = read(work(root, "gate-contract.json")), read(TEMPLATE)
    for key in ("contract_version", "model_schema_version", "storage_mode", "output_layout", "required_rule_ids", "required_criteria"):
        if value.get(key) != template[key]:
            raise ValueError("contract differs from fixed template: " + key)
    if value.get("template_digest") != digest(template):
        raise ValueError("contract template digest differs; explicitly migrate the run")
    if set(value.get("checks", {})) != set(template["required_rule_ids"]):
        raise ValueError("contract checks changed")
    for check in value["checks"].values():
        if not isinstance(check, dict) or check.get("status") not in {"pending", "passed", "failed"}:
            raise ValueError("invalid contract check status")
    if not value.get("run_id") or not value.get("analyzer_context_ref"):
        raise ValueError("contract identity missing")
    return value


def initialize(root, run_id, context):
    if root.exists() and any(root.iterdir()):
        raise ValueError("init requires an empty directory; use save for an existing run")
    template = read(TEMPLATE)
    root.mkdir(parents=True, exist_ok=True)
    work(root, "evidence").mkdir(parents=True, exist_ok=True)
    write(work(root, "gate-contract.json"), {**template, "run_id": run_id,
          "analyzer_context_ref": context, "template_digest": digest(template)})
    model = {"schemaVersion": 2, "phase": "clarifying", "entryStateIds": [],
             "scope": {"objective": "", "included": [], "excluded": [], "abstraction": ""},
             **{key: [] for key in ("sources", "features", "states", "transitions", "requirements",
                                    "questions", "confirmations", "rounds")}}
    write(work(root, "analysis-model.json"), model)
    write(work(root, "run-state.json"), {"run_id": run_id, "phase": "clarifying", "round_id": None,
          "active_node_id": None, "pending_node_ids": [], "open_question_ids": [],
          "semantic_digest": model_digest(model), "waiting_for_user": False,
          "pause_reason": None, "next_action": "Read sources and update the current model in place."})
    return {"model_path": str(work(root, "analysis-model.json")), "gate_status": "pending"}


def pending_nodes(model):
    last = model["rounds"][-1] if model["rounds"] else {}
    if last.get("kind") != "audit" or last.get("modelDigest") != model_digest(model):
        return sorted(s["id"] for s in model["states"])
    return sorted(s["id"] for s in model["states"] if
                  {c.get("dimension") for c in last.get("checks", []) if c.get("nodeId") == s["id"]} != DIMENSIONS)


def save_current(root):
    value = contract(root)
    validate_layout(root)
    model, state = read(work(root, "analysis-model.json")), read(work(root, "run-state.json"))
    errors, _ = validate(model)
    if errors:
        raise ValueError("model invalid: " + "; ".join(errors))
    errors = source_issues(root, model) if model["sources"] else []
    if errors:
        raise ValueError("source evidence invalid: " + "; ".join(errors))
    if not isinstance(state.get("next_action"), str) or not state["next_action"].strip():
        raise ValueError("state.next_action required")
    if not isinstance(state.get("waiting_for_user"), bool):
        raise ValueError("state.waiting_for_user must be boolean")
    pending = pending_nodes(model)
    active = state.get("active_node_id")
    if active is not None and active not in pending:
        raise ValueError("active node must be pending")
    current_state = {"run_id": value["run_id"], "phase": model["phase"],
        "round_id": model["rounds"][-1]["id"] if model["rounds"] else None,
        "active_node_id": active, "pending_node_ids": pending,
        "open_question_ids": [q["id"] for q in model["questions"] if q["status"] == "open"],
        "semantic_digest": model_digest(model), "waiting_for_user": state["waiting_for_user"],
        "pause_reason": state.get("pause_reason"), "next_action": state["next_action"]}
    atomic_json(work(root, "run-state.json"), current_state)
    # Any further save invalidates the displayed gate result until assert recomputes it.
    template = read(TEMPLATE)
    value.update(checks=template["checks"], gate_status="pending")
    atomic_json(work(root, "gate-contract.json"), value)
    (root / "gate-result.json").unlink(missing_ok=True)
    return current_state


def load_current(root):
    value = contract(root)
    validate_layout(root)
    model, state = read(work(root, "analysis-model.json")), read(work(root, "run-state.json"))
    if state.get("run_id") != value["run_id"]:
        raise ValueError("current run identity mismatch")
    if state.get("semantic_digest") != model_digest(model) or state.get("phase") != model.get("phase"):
        raise ValueError("current files changed; validate and save before continuing")
    if state.get("pending_node_ids") != pending_nodes(model):
        raise ValueError("current audit queue changed; run save")
    issues = source_issues(root, model) if model["sources"] else []
    if issues:
        raise ValueError("current evidence changed: " + "; ".join(issues))
    return model, state


def source_issues(root, model):
    issues = []
    for source in model["sources"]:
        try:
            if not source.get("readRanges") or not all(isinstance(x, str) and x.strip() for x in source["readRanges"]):
                raise ValueError("readRanges missing")
            if file_hash(evidence_file(root, source.get("evidencePath"))) != source.get("sha256"):
                raise ValueError("cached source digest mismatch")
            if "previewPath" in source and file_hash(evidence_file(root, source["previewPath"])) != source.get("previewSha256"):
                raise ValueError("preview digest mismatch")
        except (ValueError, OSError, TypeError) as exc:
            issues.append(source["id"] + ": " + str(exc))
    if not model["sources"]:
        issues.append("no sources")
    return issues


def check_review(report, model, manifest, value, root):
    errors, pending = [], []
    if report is None:
        return [], ["independent model review not supplied"]
    for key in ("review_id", "reviewer_context_ref"):
        if not isinstance(report.get(key), str) or not report[key].strip():
            errors.append("missing " + key)
    if report.get("reviewer_context_ref") == value["analyzer_context_ref"] or report.get("independent") is not True:
        errors.append("independent reviewer context required")
    if report.get("semantic_digest") != model_digest(model):
        errors.append("review semantic digest stale")
    if not manifest or report.get("bundle_digest") != manifest.get("bundle_digest"):
        errors.append("review artifact bundle digest stale")
    if set(report.get("reviewed_entity_ids", [])) != entity_ids(model):
        errors.append("review entity coverage differs")
    rows = report.get("criteria_results", [])
    if not isinstance(rows, list) or len(rows) != len(value["required_criteria"]) or {r.get("criterion_id") for r in rows if isinstance(r, dict)} != set(value["required_criteria"]):
        errors.append("review criteria differ from fixed rubric")
        rows = []
    evidence_refs = set()
    for row in rows:
        key = row["criterion_id"]
        status = row.get("status")
        if status == "failed":
            errors.append(key + ": failed")
        elif status in {"pending", "inconclusive"}:
            pending.append(key + ": " + status)
        elif status != "passed":
            errors.append(key + ": invalid status")
        if not row.get("reason") or not row.get("evidence_refs") or not row.get("affected_ids") or not set(row["affected_ids"]) <= entity_ids(model):
            errors.append(key + ": reason/object/evidence required")
        evidence_refs.update(row.get("evidence_refs", []))
    expected_loops = {edge["id"] for edge in model["transitions"] if edge["from"] == edge["to"]}
    loop_rows = report.get("self_loop_reviews", [])
    if not isinstance(loop_rows, list):
        errors.append("self-loop review coverage must be an array")
        loop_rows = []
    reviewed_loops = [row.get("transition_id") for row in loop_rows if isinstance(row, dict)]
    if len(loop_rows) != len(expected_loops) or len(reviewed_loops) != len(expected_loops) or any(not isinstance(key, str) for key in reviewed_loops) or set(reviewed_loops) != expected_loops:
        errors.append("self-loop review coverage differs from current loops")
    for row in loop_rows:
        if not isinstance(row, dict):
            errors.append("self-loop review must be an object")
            continue
        key, status = row.get("transition_id"), row.get("status")
        if status == "failed":
            errors.append(str(key) + ": self-loop review failed")
        elif status in {"pending", "inconclusive"}:
            pending.append(str(key) + ": self-loop review " + status)
        elif status != "passed":
            errors.append(str(key) + ": invalid self-loop review status")
        refs = row.get("evidence_refs")
        if not isinstance(row.get("reason"), str) or not row["reason"].strip() or not isinstance(refs, list) or not refs or not all(isinstance(ref, str) and ref.strip() for ref in refs):
            errors.append(str(key) + ": self-loop reason/evidence required")
        else:
            evidence_refs.update(refs)
    files = report.get("evidence_files", {})
    if not isinstance(files, dict) or not evidence_refs <= set(files):
        errors.append("review evidence refs not indexed")
        files = {}
    for ref, sha in files.items():
        try:
            if file_hash(evidence_file(root, ref)) != sha:
                errors.append("review evidence changed: " + ref)
        except (ValueError, OSError):
            errors.append("review evidence missing: " + str(ref))
    if not isinstance(report.get("findings"), list) or not isinstance(report.get("limitations"), list):
        errors.append("review findings/limitations arrays required")
    if report.get("input_complete") is not True:
        pending.append("review input incomplete or truncated")
    if any(not isinstance(f, dict) or f.get("status") != "resolved" for f in report.get("findings", [])):
        errors.append("review has unresolved findings")
    if report.get("html_runtime_verified") is not True:
        pending.append("HTML browser observation incomplete")
    return errors, pending


def gate(root, bundle=None, report_path=None, approval_path=None):
    if bundle is not None and Path(bundle).resolve() != root.resolve():
        raise ValueError("only root deliverables can be reviewed")
    value = contract(root)
    validate_layout(root)
    model, state = load_current(root)
    result = {"run_id": value["run_id"], "semantic_digest": model_digest(model),
              "checks": {}, "gate_status": "pending", "failures": []}

    def check(rule, errors=(), pending=(), evidence=()):
        status = "failed" if errors else "pending" if pending else "passed"
        result["checks"][rule] = {"status": status, "evidence_refs": list(evidence)}
        for message in list(errors) + list(pending):
            result["failures"].append({"rule_id": rule, "failed_object": rule,
                "expected": "all conditions in references/gate-rules.md", "actual": message,
                "evidence_ref": list(evidence), "failure_reason": message,
                "repair_from": rule, "recheck_from": rule + " and dependent delivery gates"})

    check("INIT-001", evidence=["_process/gate-contract.json", "_process/analysis-model.json", "_process/run-state.json"])
    check("SOURCE-001", source_issues(root, model), evidence=[s.get("evidencePath") for s in model["sources"]])
    scope_ok = any(c.get("stage") == "scope" and c.get("scopeDigest") == scope_digest(model) and c.get("humanReference") for c in model["confirmations"])
    check("SCOPE-001", [] if scope_ok else ["current scopeDigest lacks human confirmation"], evidence=["_process/analysis-model.json#/confirmations"])
    errors, _ = validate(model)
    check("MODEL-001", errors, evidence=["_process/analysis-model.json"])
    from feasibility import analyze
    feasibility_errors=[];feasibility_pending=[]
    if not errors:
        try:
            feasibility=analyze(model)
            for tid,row in feasibility['transitions'].items():
                if row['status']=='infeasible':feasibility_errors.append(tid+': no entry can execute this transition under declared conditions')
                elif row['status'] not in {'finite_domain_passed','no_guard_constraints'}:feasibility_pending.append(tid+': transition feasibility '+row['status'])
            for tid,rows in feasibility['caseResults'].items():
                for ci,row in enumerate(rows):
                    if row['status']=='infeasible':feasibility_errors.append(tid+': declared case '+str(ci)+' has no executable entry witness')
                    elif row['status'] not in {'finite_domain_passed','no_guard_constraints'}:feasibility_pending.append(tid+': case '+str(ci)+' '+row['status'])
        except ValueError as exc:feasibility_errors.append(str(exc))
    else:feasibility_errors.append('model invalid; transition witnesses unavailable')
    check('FEASIBILITY-001',feasibility_errors,feasibility_pending,evidence=['state-graph.json#/transitionValidation'])
    link_errors = []
    if not errors:
        try:
            data = exports(model)["requirement-graph.json"]
            if data["reduction"]["uncoveredRequirementIds"]:
                link_errors.append("requirements not covered by continuous routes: " + ", ".join(data["reduction"]["uncoveredRequirementIds"]))
            for i, route in enumerate(data["traversal"]["routes"], 1):
                if route["contextCheck"]["status"] not in {"finite_domain_passed", "no_guard_constraints"}:
                    link_errors.append("coverage route %d context %s: %s" % (i, route["contextCheck"]["status"], route["contextCheck"].get("transitionId", "")))
        except ValueError as exc:
            link_errors.append(str(exc))
    else:
        link_errors.append("model invalid; cannot derive graph")
    check("LINK-001", link_errors, evidence=["_process/analysis-model.json#/transitions"])
    process_errors = []
    if state["pending_node_ids"] or state["active_node_id"]:
        process_errors.append("unfinished node queue")
    if not state.get("next_action"):
        process_errors.append("current next action missing")
    check("PROCESS-001", process_errors, evidence=["_process/analysis-model.json#/rounds", "_process/run-state.json"])
    ready_errors, _ = validate(model, ready=True)
    if model["phase"] not in {"review_ready", "confirmed"}:
        ready_errors.append("final review requires phase=review_ready or confirmed")
    check("AUDIT-001", ready_errors, evidence=["_process/analysis-model.json#/rounds"])
    open_questions = [q["id"] for q in model["questions"] if q["status"] == "open"]
    candidate_ids = [x["id"] for k in ("states", "transitions", "requirements") for x in model[k] if x["status"] == "candidate"]
    check("QUESTION-001", pending=(["open questions: " + str(open_questions)] if open_questions else [])
          + (["unresolved candidates: " + str(candidate_ids)] if candidate_ids else []), evidence=["_process/analysis-model.json#/questions"])
    manifest, artifact_errors = None, []
    if bundle is not None:
        try:
            manifest = verify_folder(bundle)
            frozen = read(bundle / "analysis-model.json")
            if frozen != model or manifest.get("semantic_digest") != model_digest(model):
                raise ValueError("bundle does not match current model")
            expected_files = {"analysis-model.json", "state-graph.json", "atomic-requirements.json", "requirement-graph.json", "review-log.json", "review.html"}
            if set(manifest["files"]) != expected_files:
                raise ValueError("bundle missing required artifacts")
            for name, data in exports(model).items():
                if read(bundle / name) != data:
                    raise ValueError("derived artifact differs: " + name)
            from render_review import render
            media = collect_media(root, model)
            if (bundle / "review.html").read_text(encoding="utf-8") != render(model, exports(model), media, collect_designs(root, model)):
                raise ValueError("HTML differs from deterministic rendering")
        except (OSError, ValueError, KeyError) as exc:
            artifact_errors.append(str(exc))
    check("ARTIFACT-001", artifact_errors, ["review bundle missing"] if bundle is None else [], evidence=[str(bundle)] if bundle else [])
    report = read(report_path) if report_path else None
    report_errors, report_pending = check_review(report, model, manifest, value, root)
    check("MODEL-REVIEW-001", report_errors, report_pending, [str(report_path)] if report_path else [])
    approval_errors, approval_pending = [], []
    if approval_path is None:
        approval_pending.append("final human confirmation missing")
    else:
        approval = read(approval_path)
        expected = {"semantic_digest": model_digest(model),
                    "bundle_digest": manifest.get("bundle_digest") if manifest else None,
                    "review_digest": file_hash(report_path) if report_path else None}
        for key, actual in expected.items():
            if actual is None or approval.get(key) != actual:
                approval_errors.append("final approval mismatch: " + key)
        if set(approval.get("covered_ids", [])) != entity_ids(model):
            approval_errors.append("final approval entity coverage differs")
        if not approval.get("human_reference") or not approval.get("summary"):
            approval_errors.append("final human reference and summary required")
        try:
            if file_hash(evidence_file(root, approval.get("evidence_path"))) != approval.get("evidence_sha256"):
                approval_errors.append("final approval evidence digest differs")
        except (ValueError, OSError):
            approval_errors.append("final approval evidence missing")
    check("APPROVAL-001", approval_errors, approval_pending, [str(approval_path)] if approval_path else [])
    statuses = {k: v["status"] for k, v in result["checks"].items()}
    if "failed" in statuses.values():
        result["gate_status"] = "failed"
    elif all(v == "passed" for k, v in statuses.items() if k != "APPROVAL-001") and statuses["APPROVAL-001"] == "pending":
        result["gate_status"] = "awaiting_final_confirmation"
    elif all(v == "passed" for v in statuses.values()):
        result["gate_status"] = "passed"
    value.update(checks=result["checks"], gate_status=result["gate_status"])
    atomic_json(work(root, "gate-contract.json"), value)
    atomic_json(root / "gate-result.json", result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("init")
    p.add_argument("run", type=Path)
    p.add_argument("--run-id", required=True)
    p.add_argument("--context", required=True)
    for command in ("save", "resume", "prepare", "assert", "publish"):
        p = sub.add_parser(command)
        p.add_argument("run", type=Path)
    args = parser.parse_args()
    try:
        root = args.run.resolve()
        if args.command == "init":
            result = initialize(root, args.run_id, args.context)
        elif args.command == "save":
            result = save_current(root)
        elif args.command == "resume":
            model, state = load_current(root)
            result = {"state": state, "model_path": str(work(root, "analysis-model.json"))}
        elif args.command == "prepare":
            model, _ = load_current(root)
            errors, _ = validate(model)
            if errors:
                raise ValueError("cannot prepare invalid model: " + "; ".join(errors))
            result = export_bundle(model, root, root)
        else:
            bundle = root if (root / "manifest.json").exists() else None
            report = work(root, "model-review.json") if work(root, "model-review.json").exists() else None
            approval = root / "acceptance.json" if (root / "acceptance.json").exists() else None
            result = gate(root, bundle, report, approval)
            # Publishing means accepting these same current files, with no copied release directory.
            if args.command == "publish" and result["gate_status"] != "passed":
                print(json.dumps(result, ensure_ascii=False, indent=2))
                return 1
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if args.command != "assert" or result["gate_status"] in {"passed", "awaiting_final_confirmation"} else 1
    except (OSError, ValueError, TypeError, KeyError, AttributeError) as exc:
        print(json.dumps({"gate_status": "failed", "failures": [{"rule_id": "COMMAND-001",
            "failed_object": args.command, "expected": "valid current run inputs", "actual": str(exc),
            "evidence_ref": str(args.run), "failure_reason": str(exc),
            "repair_from": "repair current files and run save; no historical restore is performed",
            "recheck_from": args.command}]}, ensure_ascii=False, indent=2))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
