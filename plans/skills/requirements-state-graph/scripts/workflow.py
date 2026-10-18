#!/usr/bin/env python3
"""Persistent checkpoints and delivery gates. Python 3.10+, standard library only."""
import argparse
import json
import os
import shutil
import sys
import uuid
from pathlib import Path

from model_tools import DIMENSIONS, digest, exports, model_digest, scope_digest, validate
from semantic_checks import inspect as inspect_semantics

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


def atomic_json(path, value):
    temp = path.with_name(path.name + ".tmp-" + uuid.uuid4().hex)
    write(temp, value)
    os.replace(temp, path)


def entity_ids(model):
    return {x["id"] for k in ("states", "transitions", "requirements") for x in model[k]}


def verify_folder(folder):
    manifest = read(folder / "manifest.json")
    if not isinstance(manifest.get("files"), dict) or not manifest["files"]:
        raise ValueError("manifest files missing")
    actual = {p.relative_to(folder).as_posix() for p in folder.rglob("*") if p.is_file()}
    if actual != set(manifest["files"]) | {"manifest.json"}:
        raise ValueError("manifest file set mismatch: " + str(folder))
    for name, sha in manifest["files"].items():
        if file_hash(local(folder, name)) != sha:
            raise ValueError("file digest mismatch: " + name)
    if manifest.get("bundle_digest") != digest(manifest["files"]):
        raise ValueError("manifest digest mismatch")
    return manifest


def seal(folder, metadata):
    files = {p.relative_to(folder).as_posix(): file_hash(p)
             for p in sorted(folder.rglob("*")) if p.is_file() and p.name != "manifest.json"}
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
            media[source["id"]] = "data:" + mime + ";base64," + base64.b64encode(local(root, ref).read_bytes()).decode("ascii")
    return media


def export_bundle(model, target, root=None):
    """Publish only a complete new directory; never overwrite individual exports."""
    target = Path(target).resolve()
    if target.exists():
        raise ValueError("bundle target must not exist; select a new version directory")
    target.parent.mkdir(parents=True, exist_ok=True)
    stage = target.with_name("." + target.name + ".staging-" + uuid.uuid4().hex)
    stage.mkdir()
    try:
        write(stage / "analysis-model.json", model)
        data = exports(model)
        for name, content in data.items():
            write(stage / name, content)
        media = collect_media(root, model)
        write(stage / "ui-media.json", media)
        from render_review import render
        (stage / "review.html").write_text(render(model, data, media), encoding="utf-8")
        manifest = seal(stage, {"schema_version": 2, "revision": model["revision"],
                                "semantic_digest": model_digest(model), "kind": "review_snapshot"})
        verify_folder(stage)
        os.rename(stage, target)
        return manifest
    except Exception:
        # An unpublished staging directory is diagnostic evidence, never a valid bundle.
        raise


def contract(root):
    value, template = read(root / "gate-contract.json"), read(TEMPLATE)
    for key in ("contract_version", "model_schema_version", "required_rule_ids", "required_criteria"):
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


def load_checkpoint(root, checkpoint=None):
    pointer = read(root / "current.json") if checkpoint is None else {"checkpoint": checkpoint}
    folder = local(root, "checkpoints/" + pointer["checkpoint"])
    manifest = verify_folder(folder)
    if "manifest_digest" in pointer and digest(manifest) != pointer["manifest_digest"]:
        raise ValueError("checkpoint pointer digest mismatch")
    model, state, step = (read(folder / x) for x in ("analysis-model.json", "run-state.json", "step.json"))
    if (state.get("last_checkpoint_ref") != pointer["checkpoint"]
            or state.get("semantic_digest") != model_digest(model)
            or state.get("artifact_revision") != model.get("revision")
            or state.get("phase") != model.get("phase")):
        raise ValueError("checkpoint state/model mismatch")
    for evidence in step.get("evidence", []):
        if file_hash(local(root, evidence["path"])) != evidence["sha256"]:
            raise ValueError("checkpoint evidence changed: " + evidence["path"])
    return pointer["checkpoint"], model, state, step, manifest


def history(root):
    current = load_checkpoint(root)
    trail, visited = [], set()
    while True:
        identity, model, state, step, manifest = current
        if identity in visited:
            raise ValueError("checkpoint parent cycle")
        visited.add(identity)
        trail.append(current)
        parent = step.get("parent")
        if parent is None:
            if step.get("kind") != "init":
                raise ValueError("history does not begin with init")
            break
        current = load_checkpoint(root, parent)
    trail.reverse()
    if [x[3]["id"] for x in trail] != trail[-1][2]["completed_step_ids"]:
        raise ValueError("completed_step_ids do not match saved history")
    return trail


def commit(root, identity, model, state, step):
    folder = root / "checkpoints" / identity
    folder.mkdir(parents=True)
    write(folder / "analysis-model.json", model)
    write(folder / "run-state.json", state)
    write(folder / "step.json", step)
    manifest = seal(folder, {"checkpoint": identity})
    verify_folder(folder)
    atomic_json(root / "current.json", {"checkpoint": identity, "manifest_digest": digest(manifest)})
    # Editable working copies are conveniences; the verified pointer is authoritative.
    write(root / "analysis-model.json", model)
    write(root / "run-state.json", state)


def initialize(root, run_id, context):
    if root.exists():
        raise ValueError("init requires a new run directory")
    template = read(TEMPLATE)
    root.mkdir(parents=True)
    (root / "evidence").mkdir()
    value = {**template, "run_id": run_id, "analyzer_context_ref": context,
             "template_digest": digest(template)}
    write(root / "gate-contract.json", value)
    model = {"schemaVersion": 2, "revision": "r0", "phase": "clarifying",
             "scope": {"objective": "", "included": [], "excluded": [], "abstraction": ""},
             **{key: [] for key in ("sources", "features", "states", "transitions", "requirements",
                                    "questions", "confirmations", "rounds", "witnesses",
                                    "coverageClaims", "continuationAssessments")}}
    state = {"run_id": run_id, "phase": "clarifying", "round_id": None, "active_node_id": None,
             "pending_node_ids": [], "completed_step_ids": ["init"], "open_question_ids": [],
             "artifact_revision": "r0", "semantic_digest": model_digest(model),
             "last_checkpoint_ref": "000000-init", "waiting_for_user": False,
             "pause_reason": None, "next_action": "Read one source segment, cache it, and checkpoint observations."}
    commit(root, "000000-init", model, state,
           {"id": "init", "kind": "init", "parent": None, "entityIds": [], "evidence": [],
            "summary": "Fixed pending contract initialized"})
    return {"checkpoint": "000000-init", "gate_status": "pending"}


def node_check_digest(model, round_id, sid):
    round_ = next((r for r in model["rounds"] if r["id"] == round_id), {})
    checks = [c for c in round_.get("checks", []) if c.get("nodeId") == sid]
    if set(c.get("dimension") for c in checks) != DIMENSIONS:
        raise ValueError("node audit needs all dimensions: " + sid)
    return digest({"round": round_id, "revision": round_.get("revision"), "checks": checks})


def checkpoint(root, model_path, state_path, record_path, base):
    value = contract(root)
    previous_id, previous, previous_state, _, _ = load_checkpoint(root)
    if previous_id != base:
        raise ValueError("stale checkpoint base; resume current before writing")
    model, state, record = read(model_path), read(state_path), read(record_path)
    errors, _ = validate(model)
    if errors:
        raise ValueError("model invalid: " + "; ".join(errors))
    if record.get("kind") not in {"source", "model", "question", "node_audit", "round", "decision", "pause"}:
        raise ValueError("invalid work unit kind")
    if not isinstance(record.get("id"), str) or not record["id"].strip() or record["id"] in previous_state["completed_step_ids"]:
        raise ValueError("step id must be new and nonempty")
    if not isinstance(record.get("summary"), str) or not record["summary"].strip():
        raise ValueError("step summary required")
    ids, evidence_refs = record.get("entityIds"), record.get("evidenceRefs")
    known = {x["id"] for k in ("sources", "features", "states", "transitions", "requirements", "questions", "rounds") for x in model[k]}
    if not isinstance(ids, list) or not set(ids) <= known | {"scope"}:
        raise ValueError("step entityIds must resolve")
    if not isinstance(evidence_refs, list):
        raise ValueError("step evidenceRefs must be an array of cached paths")
    if record["kind"] in {"source", "decision"} and not evidence_refs:
        raise ValueError("source/decision units require saved evidence")
    evidence = [{"path": p, "sha256": file_hash(local(root, p))} for p in evidence_refs]
    changed = model_digest(model) != model_digest(previous)
    if changed and model["revision"] == previous["revision"]:
        raise ValueError("semantic changes require a new revision")
    if record["kind"] == "node_audit" and changed:
        raise ValueError("save semantic changes before beginning node audit")
    pending = set(s["id"] for s in model["states"]) if changed else set(previous_state["pending_node_ids"])
    node_digests = {}
    if record["kind"] == "node_audit":
        round_id = record.get("roundId")
        round_ = next((r for r in model["rounds"] if r["id"] == round_id), {})
        if round_.get("revision") != model["revision"] or round_.get("kind") != "audit":
            raise ValueError("node audit must bind current audit round")
        if len(ids) != 1 or not set(ids) <= set(round_.get("nodeIds", [])):
            raise ValueError("node audit must save one completed node at a time")
        node_digests = {sid: node_check_digest(model, round_id, sid) for sid in ids}
        pending.difference_update(ids)
    if not isinstance(state.get("next_action"), str) or not state["next_action"].strip():
        raise ValueError("state.next_action required")
    if not isinstance(state.get("waiting_for_user"), bool):
        raise ValueError("state.waiting_for_user must be boolean")
    if state.get("waiting_for_user") and record["kind"] == "node_audit":
        raise ValueError("do not complete a node audit while waiting for its decision")
    if state.get("active_node_id") is not None and state["active_node_id"] not in pending:
        raise ValueError("active node must be pending")
    if state.get("round_id") is not None and state["round_id"] not in {r["id"] for r in model["rounds"]}:
        raise ValueError("state round_id is unknown")
    if state.get("pause_reason") is not None and not isinstance(state["pause_reason"], str):
        raise ValueError("pause_reason must be null or text")
    if record["kind"] == "pause" and not state.get("pause_reason"):
        raise ValueError("pause checkpoint requires a pause_reason")
    identity = f"{len(previous_state['completed_step_ids']):06d}-" + uuid.uuid4().hex[:12]
    state.update(run_id=value["run_id"], phase=model["phase"], pending_node_ids=sorted(pending),
                 completed_step_ids=previous_state["completed_step_ids"] + [record["id"]],
                 open_question_ids=[q["id"] for q in model["questions"] if q["status"] == "open"],
                 artifact_revision=model["revision"], semantic_digest=model_digest(model), last_checkpoint_ref=identity)
    step = {**record, "parent": previous_id, "evidence": evidence, "node_check_digests": node_digests,
            "semantic_digest": model_digest(model)}
    # Serialize competing normal-channel commits with exclusive lock; do not guess stale locks.
    lock = root / "checkpoint.lock"
    fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    try:
        os.close(fd)
        if read(root / "current.json")["checkpoint"] != base:
            raise ValueError("stale checkpoint base")
        commit(root, identity, model, state, step)
    finally:
        lock.unlink()
    return {"checkpoint": identity, "semantic_digest": model_digest(model), "pending_node_ids": sorted(pending)}


def source_issues(root, model):
    issues = []
    for source in model["sources"]:
        try:
            if not source.get("readRanges") or not all(isinstance(x, str) and x.strip() for x in source["readRanges"]):
                raise ValueError("readRanges missing")
            if file_hash(local(root, source.get("evidencePath"))) != source.get("sha256"):
                raise ValueError("cached source digest mismatch")
            if "previewPath" in source and file_hash(local(root, source["previewPath"])) != source.get("previewSha256"):
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
    if report.get("reviewed_revision") != model["revision"] or report.get("semantic_digest") != model_digest(model):
        errors.append("review semantic digest/revision stale")
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
    files = report.get("evidence_files", {})
    if not isinstance(files, dict) or not evidence_refs <= set(files):
        errors.append("review evidence refs not indexed")
        files = {}
    for ref, sha in files.items():
        try:
            if file_hash(local(root, ref)) != sha:
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
    value = contract(root)
    trail = history(root)
    _, model, state, _, _ = trail[-1]
    result = {"run_id": value["run_id"], "revision": model["revision"], "semantic_digest": model_digest(model),
              "checks": {}, "gate_status": "pending", "failures": []}

    def check(rule, errors=(), pending=(), evidence=()):
        status = "failed" if errors else "pending" if pending else "passed"
        result["checks"][rule] = {"status": status, "evidence_refs": list(evidence)}
        for message in list(errors) + list(pending):
            result["failures"].append({"rule_id": rule, "failed_object": rule,
                "expected": "all conditions in references/gate-rules.md", "actual": message,
                "evidence_ref": list(evidence), "failure_reason": message,
                "repair_from": rule, "recheck_from": rule + " and dependent delivery gates"})

    check("INIT-001", evidence=["gate-contract.json", "checkpoints/" + trail[0][0]])
    check("SOURCE-001", source_issues(root, model), evidence=[s.get("evidencePath") for s in model["sources"]])
    scope_ok = any(c.get("stage") == "scope" and c.get("scopeDigest") == scope_digest(model) and c.get("humanReference") for c in model["confirmations"])
    check("SCOPE-001", [] if scope_ok else ["current scopeDigest lacks human confirmation"], evidence=["analysis-model.json#/confirmations"])
    errors, _ = validate(model)
    check("MODEL-001", errors, evidence=["analysis-model.json"])
    link_errors = []
    if not errors:
        data = exports(model)["requirement-graph.json"]
        if len({e["id"] for e in data["edges"]}) != len(data["edges"]):
            link_errors.append("duplicate continuation ID")
    else:
        link_errors.append("model invalid; cannot derive graph")
    check("LINK-001", link_errors, evidence=["analysis-model.json#/transitions"])
    mechanical_semantics = inspect_semantics(model) if not errors else {rule: ["model invalid; semantic evidence cannot be checked"] for rule in ("STRUCTURE-001", "FEASIBILITY-001", "COVERAGE-001", "CONTINUATION-001")}
    for rule in ("STRUCTURE-001", "FEASIBILITY-001", "COVERAGE-001", "CONTINUATION-001"):
        check(rule, mechanical_semantics[rule], evidence=["analysis-model.json", "execution-witnesses.json", "coverage-report.json"])
    steps = [x[3] for x in trail]
    process_errors = []
    if state["pending_node_ids"] or state["active_node_id"]:
        process_errors.append("unfinished node queue")
    for source in model["sources"]:
        if not any(source["id"] in s.get("entityIds", []) and s["kind"] in {"source", "decision"} for s in steps):
            process_errors.append("source never checkpointed as read: " + source["id"])
    for confirmation in model["confirmations"]:
        if confirmation.get("stage") == "scope" and not any(s["kind"] == "decision" and confirmation.get("sourceId") in s.get("entityIds", []) for s in steps):
            process_errors.append("scope confirmation not saved as a decision unit")
    if not any(s["kind"] == "model" for s in steps):
        process_errors.append("no incrementally saved model unit")
    last = model["rounds"][-1] if model["rounds"] else {}
    for sid in (s["id"] for s in model["states"]):
        try:
            expected = node_check_digest(model, last.get("id"), sid) if last.get("kind") == "audit" else None
        except ValueError as exc:
            expected = None
            process_errors.append(str(exc))
        if not any(s["kind"] == "node_audit" and s.get("semantic_digest") == model_digest(model)
                   and s.get("roundId") == last.get("id") and s.get("node_check_digests", {}).get(sid) == expected for s in steps):
            process_errors.append("current node audit not checkpointed: " + sid)
    check("PROCESS-001", process_errors, evidence=["current.json", "checkpoints/"])
    ready_errors, _ = validate(model, ready=True)
    if model["phase"] not in {"review_ready", "confirmed"}:
        ready_errors.append("final review requires phase=review_ready or confirmed")
    check("AUDIT-001", ready_errors, evidence=["analysis-model.json#/rounds"])
    open_questions = [q["id"] for q in model["questions"] if q["status"] == "open"]
    candidate_ids = [x["id"] for k in ("states", "transitions", "requirements") for x in model[k] if x["status"] == "candidate"]
    check("QUESTION-001", pending=(["open questions: " + str(open_questions)] if open_questions else [])
          + (["unresolved candidates: " + str(candidate_ids)] if candidate_ids else []), evidence=["analysis-model.json#/questions"])
    manifest, artifact_errors = None, []
    if bundle is not None:
        try:
            manifest = verify_folder(bundle)
            frozen = read(bundle / "analysis-model.json")
            if frozen != model or manifest.get("semantic_digest") != model_digest(model):
                raise ValueError("bundle does not match current checkpoint")
            expected_files = {"analysis-model.json", "state-graph.json", "atomic-requirements.json", "requirement-graph.json", "execution-witnesses.json", "coverage-report.json", "review-log.json", "review.html", "ui-media.json"}
            if set(manifest["files"]) != expected_files:
                raise ValueError("bundle missing required artifacts")
            for name, data in exports(model).items():
                if read(bundle / name) != data:
                    raise ValueError("derived artifact differs: " + name)
            from render_review import render
            media = collect_media(root, model)
            if read(bundle / "ui-media.json") != media:
                raise ValueError("UI previews differ from cached sources")
            if (bundle / "review.html").read_text(encoding="utf-8") != render(model, exports(model), media):
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
        expected = {"revision": model["revision"], "semantic_digest": model_digest(model),
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
            if file_hash(local(root, approval.get("evidence_path"))) != approval.get("evidence_sha256"):
                approval_errors.append("final approval evidence digest differs")
        except (ValueError, OSError):
            approval_errors.append("final approval evidence missing")
        if not any(s["kind"] == "decision" and any(e["path"] == approval.get("evidence_path") and e["sha256"] == approval.get("evidence_sha256") for e in s.get("evidence", [])) for s in steps):
            approval_errors.append("final human reply not checkpointed before use")
    check("APPROVAL-001", approval_errors, approval_pending, [str(approval_path)] if approval_path else [])
    statuses = {k: v["status"] for k, v in result["checks"].items()}
    if "failed" in statuses.values():
        result["gate_status"] = "failed"
    elif all(v == "passed" for k, v in statuses.items() if k != "APPROVAL-001") and statuses["APPROVAL-001"] == "pending":
        result["gate_status"] = "awaiting_final_confirmation"
    elif all(v == "passed" for v in statuses.values()):
        result["gate_status"] = "passed"
    value.update(checks=result["checks"], gate_status=result["gate_status"])
    atomic_json(root / "gate-contract.json", value)
    atomic_json(root / "gate-result.json", result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("init")
    p.add_argument("run", type=Path)
    p.add_argument("--run-id", required=True)
    p.add_argument("--context", required=True)
    p = sub.add_parser("checkpoint")
    p.add_argument("run", type=Path)
    for field in ("model", "state", "record"):
        p.add_argument("--" + field, required=True, type=Path)
    p.add_argument("--base", required=True)
    p = sub.add_parser("resume")
    p.add_argument("run", type=Path)
    p.add_argument("--restore", action="store_true")
    for command in ("prepare", "assert", "publish"):
        p = sub.add_parser(command)
        p.add_argument("run", type=Path)
        if command == "prepare":
            p.add_argument("output", type=Path)
        else:
            p.add_argument("--bundle", type=Path)
            p.add_argument("--review", type=Path)
            p.add_argument("--approval", type=Path)
            if command == "publish":
                p.add_argument("output", type=Path)
    args = parser.parse_args()
    try:
        root = args.run.resolve()
        if args.command == "init":
            result = initialize(root, args.run_id, args.context)
        elif args.command == "checkpoint":
            result = checkpoint(root, args.model, args.state, args.record, args.base)
        elif args.command == "resume":
            contract(root)
            trail = history(root)
            identity, model, state, _, _ = trail[-1]
            if args.restore:
                write(root / "analysis-model.json", model)
                write(root / "run-state.json", state)
            result = {"checkpoint": identity, "state": state, "model_path": str(root / "checkpoints" / identity / "analysis-model.json")}
        elif args.command == "prepare":
            contract(root)
            _, model, _, _, _ = load_checkpoint(root)
            errors, _ = validate(model)
            if errors:
                raise ValueError("cannot prepare invalid model: " + "; ".join(errors))
            result = export_bundle(model, args.output, root)
        else:
            result = gate(root, args.bundle, args.review, args.approval)
            if args.command == "publish":
                if result["gate_status"] != "passed":
                    print(json.dumps(result, ensure_ascii=False, indent=2))
                    return 1
                if args.output.exists():
                    raise ValueError("publish target must be new")
                args.output.parent.mkdir(parents=True, exist_ok=True)
                stage = args.output.with_name("." + args.output.name + ".staging-" + uuid.uuid4().hex)
                shutil.copytree(args.bundle, stage)
                shutil.copy2(args.review, stage / "model-review.json")
                shutil.copy2(args.approval, stage / "acceptance.json")
                write(stage / "gate-result.json", result)
                seal(stage, {"kind": "accepted_delivery", "revision": result["revision"],
                             "semantic_digest": result["semantic_digest"], "reviewed_bundle_digest": verify_folder(args.bundle)["bundle_digest"]})
                verify_folder(stage)
                os.rename(stage, args.output)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if args.command != "assert" or result["gate_status"] in {"passed", "awaiting_final_confirmation"} else 1
    except (OSError, ValueError, TypeError, KeyError, AttributeError) as exc:
        print(json.dumps({"gate_status": "failed", "failures": [{"rule_id": "COMMAND-001",
            "failed_object": args.command, "expected": "valid complete run inputs", "actual": str(exc),
            "evidence_ref": str(args.run), "failure_reason": str(exc),
            "repair_from": "resume the last verified checkpoint; repair identified input",
            "recheck_from": args.command}]}, ensure_ascii=False, indent=2))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
