#!/usr/bin/env python3
"""Validate the requirements model and deterministically export its two graphs."""

import argparse
import hashlib
import json
import sys
from pathlib import Path
from requirement_graph import requirement_graph, policy

DIMENSIONS = {
    "sources", "events", "guard_complement", "boundaries", "failure",
    "cancel_return", "repeat_time", "permissions", "ui", "cross_feature",
}
DISPOSITIONS = {
    "covered", "added", "pending_decision", "excluded_equivalent", "not_applicable",
}
STATUSES = {"draft", "candidate", "confirmed"}
PHASES = {"clarifying", "analyzing", "review_ready", "confirmed", "incomplete"}
COLLECTIONS = ("sources", "features", "states", "transitions", "requirements", "questions", "rounds")


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(",", ":")).encode("utf-8")).hexdigest()


def scope_digest(model):
    return digest(model.get("scope"))


def model_digest(model):
    semantic = {key: model.get(key) for key in (
        "schemaVersion", "scope", "entryStateIds", "pathContext", "requirementTraversal", "sources", "features", "states",
        "transitions", "requirements", "questions",
    )}
    # Human confirmation metadata does not change the meaning under review.
    for key in ("states", "transitions", "requirements"):
        if isinstance(semantic.get(key), list):
            semantic[key] = [{k: v for k, v in x.items() if k != "status"}
                             if isinstance(x, dict) else x for x in semantic[key]]
    payload = json.dumps(semantic, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _validate(model, final=False, ready=False):
    errors, warnings = [], []

    def need(condition, message):
        if not condition:
            errors.append(message)

    def text(value):
        return isinstance(value, str) and bool(value.strip())

    def array(value, label, nonempty=False):
        need(isinstance(value, list), f"{label}: expected array")
        items = value if isinstance(value, list) else []
        if nonempty:
            need(bool(items), f"{label}: must not be empty")
        return items

    def strings(value, label, nonempty=False):
        items = array(value, label, nonempty)
        need(all(text(x) for x in items), f"{label}: expected nonempty strings")
        return [x for x in items if text(x)]

    if not isinstance(model, dict):
        return ["model: expected object"], warnings
    need(model.get("schemaVersion") == 2, "schemaVersion must be 2; migrate v1 explicitly")
    need(model.get("phase") in PHASES, "phase is invalid")
    scope = model.get("scope")
    need(isinstance(scope, dict), "scope: expected object")
    if isinstance(scope, dict):
        for key in ("objective", "abstraction"):
            need(text(scope.get(key)), f"scope.{key} is required")
        strings(scope.get("included"), "scope.included", True)
        strings(scope.get("excluded"), "scope.excluded")

    tables, seen = {}, set()
    for key in COLLECTIONS:
        table = {}
        for i, item in enumerate(array(model.get(key), key)):
            label = f"{key}[{i}]"
            if not isinstance(item, dict):
                errors.append(f"{label}: expected object")
                continue
            identity = item.get("id")
            need(text(identity), f"{label}.id is required")
            if not text(identity):
                continue
            need(identity not in seen, f"duplicate global id: {identity}")
            seen.add(identity)
            table[identity] = item
        tables[key] = table

    def refs(value, table, label, nonempty=False):
        ids = strings(value, label, nonempty)
        for identity in ids:
            need(identity in tables[table], f"{label}: unknown {table} id {identity}")
        return ids

    def ui_refs(value, label):
        entries = array(value, label)
        for i, item in enumerate(entries):
            if not isinstance(item, dict):
                errors.append(f"{label}[{i}]: expected object")
                continue
            source = tables["sources"].get(item.get("sourceId"), {})
            need(source.get("kind") == "ui", f"{label}[{i}]: source must be UI")
            for key in ("frameId", "region", "stateLabel"):
                need(text(item.get(key)), f"{label}[{i}].{key} is required")
        return entries

    roots = refs(model.get("entryStateIds", []), "states", "entryStateIds", bool(tables["states"]))
    need(len(roots) == len(set(roots)), "entryStateIds must be unique")
    try:
        policy(model)
    except ValueError as exc:
        errors.append(str(exc))

    for identity, source in tables["sources"].items():
        need(source.get("kind") in {"prd", "ui", "human"}, f"{identity}: invalid source kind")
        for key in ("uri", "locator"):
            need(text(source.get(key)), f"{identity}.{key} is required")
        for key in ("evidencePath", "sha256"):
            need(text(source.get(key)), f"{identity}.{key} is required")
        sha = source.get("sha256", "")
        need(isinstance(sha, str) and len(sha) == 64 and all(c in "0123456789abcdef" for c in sha), f"{identity}: invalid source sha256")
        strings(source.get("readRanges"), f"{identity}.readRanges", True)
    for identity, feature in tables["features"].items():
        for key in ("title", "scope"):
            need(text(feature.get(key)), f"{identity}.{key} is required")
        refs(feature.get("entryStateIds"), "states", f"{identity}.entryStateIds", True)

    for key in ("states", "transitions", "requirements"):
        if model.get("phase") != "clarifying":
            need(bool(tables[key]), f"{key}: analysis must not be empty")
        for identity, item in tables[key].items():
            need(item.get("status") in STATUSES, f"{identity}: invalid entity status")
            refs(item.get("sourceIds"), "sources", f"{identity}.sourceIds", True)
            if "questionIds" in item or item.get("status") == "candidate":
                refs(item.get("questionIds"), "questions", f"{identity}.questionIds", item.get("status") == "candidate")
            if model.get("phase") != "confirmed" and item.get("status") == "confirmed":
                errors.append(f"{identity}: confirmed entity requires a confirmed current model")

    for identity, state in tables["states"].items():
        need(text(state.get("title")), f"{identity}.title is required")
        refs(state.get("featureIds"), "features", f"{identity}.featureIds", True)
        strings(state.get("facts"), f"{identity}.facts", True)
        ui_refs(state.get("uiRefs"), f"{identity}.uiRefs")

    mapped = {}
    signatures = {}
    for identity, transition in tables["transitions"].items():
        refs(transition.get("featureIds"), "features", f"{identity}.featureIds", True)
        for endpoint in ("from", "to"):
            need(transition.get(endpoint) in tables["states"], f"{identity}.{endpoint}: unknown state")
        for field in ("event", "guard"):
            need(text(transition.get(field)), f"{identity}.{field} is required")
        for forbidden in ("effects", "actions", "result", "expectedEffects"):
            need(forbidden not in transition, f"{identity}: put {forbidden} in target state or requirement assertions")
        loop_evidence = transition.get("selfLoopEvidence")
        if transition.get("from") == transition.get("to"):
            need(isinstance(loop_evidence, dict), f"{identity}: self-loop requires selfLoopEvidence")
            if isinstance(loop_evidence, dict):
                for field in ("obligation", "stateReason"):
                    need(text(loop_evidence.get(field)), f"{identity}.selfLoopEvidence.{field} is required")
                citations = array(loop_evidence.get("sourceRefs"), f"{identity}.selfLoopEvidence.sourceRefs", True)
                for citation in citations:
                    if not isinstance(citation, dict):
                        errors.append(f"{identity}.selfLoopEvidence.sourceRefs: expected object")
                        continue
                    source_id = citation.get("sourceId")
                    need(text(source_id) and source_id in tables["sources"], f"{identity}: self-loop source must exist")
                    source_ids = transition.get("sourceIds")
                    need(isinstance(source_ids, list) and source_id in source_ids, f"{identity}: self-loop source must be a transition source")
                    need(text(citation.get("locator")), f"{identity}: self-loop source locator is required")
        else:
            need("selfLoopEvidence" not in transition, f"{identity}: selfLoopEvidence is only valid for self-loops")
        signature = digest([transition.get(k) for k in ("from", "event", "guard", "to")])
        need(signature not in signatures, f"{identity}: duplicate transition signature with {signatures.get(signature)}")
        signatures[signature] = identity
        rid = transition.get("requirementId")
        need(text(rid) and rid in tables["requirements"], f"{identity}: unknown requirementId")
        if text(rid):
            need(rid not in mapped, f"{rid}: more than one transition points to this requirement")
            mapped[rid] = identity

    used_transitions = set()
    for identity, requirement in tables["requirements"].items():
        need(text(requirement.get("title")), f"{identity}.title is required")
        tid = requirement.get("transitionId")
        transition = tables["transitions"].get(tid, {}) if text(tid) else {}
        need(bool(transition), f"{identity}: unknown transitionId")
        need(text(tid) and tid not in used_transitions, f"{identity}: transition used by more than one requirement")
        if text(tid):
            used_transitions.add(tid)
        need(transition.get("requirementId") == identity, f"{identity}: transition/requirement reference mismatch")
        strings(requirement.get("ruleIds"), f"{identity}.ruleIds")
        checks = array(requirement.get("acceptance"), f"{identity}.acceptance", True)
        acceptance_ids = set()
        for check in checks:
            if not isinstance(check, dict):
                errors.append(f"{identity}.acceptance: expected object")
                continue
            for field in ("id", "given", "when"):
                need(text(check.get(field)), f"{identity}.acceptance.{field} is required")
            aid = check.get("id")
            if text(aid):
                need(aid not in acceptance_ids, f"{identity}: duplicate acceptance id {aid}")
                acceptance_ids.add(aid)
            strings(check.get("then"), f"{identity}.acceptance.then", True)
        ui = ui_refs(requirement.get("uiRefs"), f"{identity}.uiRefs")
        applicability = requirement.get("uiApplicability")
        need(isinstance(applicability, dict), f"{identity}.uiApplicability is required")
        if isinstance(applicability, dict):
            status = applicability.get("status")
            need(status in {"mapped", "not_applicable", "missing"}, f"{identity}: invalid UI applicability")
            if status == "mapped":
                need(bool(ui), f"{identity}: mapped UI must have uiRefs")
            else:
                need(text(applicability.get("reason")), f"{identity}: explain UI applicability")
                if status == "not_applicable":
                    need(not ui, f"{identity}: non-UI requirement cannot also be UI-mapped")
            if status == "missing":
                qid = applicability.get("decisionQuestionId")
                question = tables["questions"].get(qid, {}) if text(qid) else {}
                need(bool(question), f"{identity}: missing UI needs decisionQuestionId")
                if final or model.get("phase") == "confirmed":
                    need(question.get("status") in {"resolved", "out_of_scope"}, f"{identity}: UI gap not human-disposed")

    for identity, question in tables["questions"].items():
        need(text(question.get("question")), f"{identity}.question is required")
        need(isinstance(question.get("blocking"), bool), f"{identity}.blocking must be boolean")
        need(question.get("status") in {"open", "resolved", "out_of_scope"}, f"{identity}: invalid question status")
        affected = strings(question.get("affectedIds"), f"{identity}.affectedIds")
        entities = {**tables["states"], **tables["transitions"], **tables["requirements"]}
        for eid in affected:
            need(eid in entities or eid in tables["features"] or eid == "scope", f"{identity}: unknown affectedId {eid}")
            if eid in entities:
                need(identity in entities[eid].get("questionIds", []), f"{identity}/{eid}: missing questionIds backlink")
        if question.get("status") != "open":
            need(text(question.get("resolution")), f"{identity}.resolution is required")
            need(text(question.get("humanReference")), f"{identity}: resolution needs humanReference")
            need(tables["sources"].get(question.get("decisionSourceId"), {}).get("kind") == "human", f"{identity}: decisionSourceId must reference human evidence")
    for key in ("states", "transitions", "requirements"):
        for identity, entity in tables[key].items():
            for qid in entity.get("questionIds", []):
                need(identity in tables["questions"].get(qid, {}).get("affectedIds", []), f"{identity}/{qid}: missing affectedIds backlink")

    confirmations = array(model.get("confirmations"), "confirmations")
    valid_confirmations = []
    for record in confirmations:
        if not isinstance(record, dict):
            errors.append("confirmations: expected object")
            continue
        need(record.get("stage") in {"scope", "final"}, "confirmation: invalid stage")
        for key in ("humanReference", "summary"):
            need(text(record.get(key)), f"confirmation.{key} is required")
        if record.get("stage") == "scope":
            need(tables["sources"].get(record.get("sourceId"), {}).get("kind") == "human", "scope confirmation needs human sourceId")
        valid_confirmations.append(record)
    if model.get("phase") != "clarifying":
        need(any(c.get("stage") == "scope" and c.get("scopeDigest") == scope_digest(model)
                 and text(c.get("humanReference")) for c in valid_confirmations),
             "analysis requires human confirmation of current scopeDigest")

    removed = {c.get("entityId") for r in tables["rounds"].values()
               for c in (r.get("changes") if isinstance(r.get("changes"), list) else [])
               if isinstance(c, dict) and c.get("kind") == "remove" and text(c.get("entityId"))
               and text(c.get("meaning")) and c.get("sourceIds")}
    for identity, round_ in tables["rounds"].items():
        need(round_.get("kind") in {"build", "audit"}, f"{identity}: invalid round kind")
        snapshot = strings(round_.get("nodeIds"), f"{identity}.nodeIds")
        historical = round_.get("retiredIds", [])
        strings(historical, f"{identity}.retiredIds")
        need(set(historical) <= removed and not set(historical) & seen, f"{identity}: retiredIds need recorded deletion and cannot reuse live IDs")
        known = seen | set(historical)
        need(set(snapshot) <= (set(tables["states"]) | set(historical)), f"{identity}: unknown snapshot node")
        for eid in strings(round_.get("openFrontier"), f"{identity}.openFrontier"):
            need(eid in known, f"{identity}: unknown frontier id {eid}")
        for check in array(round_.get("checks"), f"{identity}.checks"):
            if not isinstance(check, dict):
                errors.append(f"{identity}.checks: expected object")
                continue
            need(text(check.get("nodeId")), f"{identity}: check needs nodeId")
            need(check.get("nodeId") in snapshot, f"{identity}: check node outside round snapshot")
            need(check.get("dimension") in DIMENSIONS, f"{identity}: invalid audit dimension")
            need(check.get("disposition") in DISPOSITIONS, f"{identity}: invalid audit disposition")
            need(text(check.get("reason")), f"{identity}: audit reason is required")
            refs(check.get("evidenceIds"), "sources", f"{identity}.evidenceIds")
            for eid in strings(check.get("relatedIds"), f"{identity}.relatedIds"):
                need(eid in known, f"{identity}: unknown relatedId {eid}")
        for change in array(round_.get("changes"), f"{identity}.changes"):
            if not isinstance(change, dict):
                errors.append(f"{identity}.changes: expected object")
                continue
            need(change.get("kind") in {"add", "update", "remove"}, f"{identity}: invalid change kind")
            need(text(change.get("entityId")) and text(change.get("meaning")), f"{identity}: change needs entityId and meaning")
            refs(change.get("sourceIds"), "sources", f"{identity}.change.sourceIds", True)

    closing_required = ready or final or model.get("phase") in {"review_ready", "confirmed"}
    if final or model.get("phase") == "confirmed":
        need(model.get("phase") == "confirmed", "final validation requires phase=confirmed")
        entity_ids = set(tables["states"]) | set(tables["transitions"]) | set(tables["requirements"])
        for key in ("states", "transitions", "requirements"):
            for identity, entity in tables[key].items():
                need(entity.get("status") == "confirmed", f"{identity}: final entity not confirmed")
                for qid in entity.get("questionIds", []) if isinstance(entity.get("questionIds", []), list) else []:
                    question = tables["questions"].get(qid, {}) if text(qid) else {}
                    need(question.get("status") in {"resolved", "out_of_scope"}, f"{identity}: unresolved candidate question")
        for identity, question in tables["questions"].items():
            need(question.get("status") != "open", f"{identity}: open question cannot enter final baseline")
        finals = [c for c in valid_confirmations if c.get("stage") == "final" and c.get("semanticDigest") == model_digest(model)]
        need(bool(finals), "final human confirmation for current model is missing")
        if finals:
            covered = strings(finals[-1].get("coveredIds"), "final.coveredIds")
            need(set(covered) == entity_ids, "final confirmation must cover exactly current state/transition/requirement IDs")
    if closing_required:
        rounds = list(tables["rounds"].values())
        need(len(rounds) >= 2, "final model needs build/review records and a closing audit")
        last = rounds[-1] if rounds else {}
        need(last.get("kind") == "audit", "closing round must be an audit")
        need(last.get("changes") == [] and last.get("openFrontier") == [], "closing audit has changes or unfinished frontier")
        nodes = strings(last.get("nodeIds"), "closing.nodeIds")
        need(set(nodes) == set(tables["states"]) and len(nodes) == len(set(nodes)), "closing audit must cover every current state exactly once")
        pairs = {(c.get("nodeId"), c.get("dimension")) for c in last.get("checks", []) if isinstance(c, dict)} if isinstance(last.get("checks"), list) else set()
        for check in last.get("checks", []) if isinstance(last.get("checks"), list) else []:
            if isinstance(check, dict):
                need(check.get("disposition") != "added", "closing audit still has added checks")
                if final or model.get("phase") == "confirmed":
                    need(check.get("disposition") != "pending_decision", "final closing audit still has undecided checks")
        for sid in tables["states"]:
            for dimension in sorted(DIMENSIONS):
                need((sid, dimension) in pairs, f"closing audit missing {sid}/{dimension}")
        need(last.get("modelDigest") == model_digest(model), "closing audit semantic digest is stale or missing")

    if any(q.get("status") == "open" for q in tables["questions"].values()):
        warnings.append("Open questions remain; drafts are not a confirmed baseline.")
    from path_context import validate_context
    errors.extend(validate_context(model))
    warnings.append("Structural validation cannot authenticate human replies or prove business completeness.")
    return errors, warnings


def validate(model, final=False, ready=False):
    """Return diagnostics even for malformed JSON types, never a traceback."""
    try:
        return _validate(model, final=final, ready=ready)
    except (TypeError, ValueError, KeyError, AttributeError) as exc:
        return ["malformed model field: " + str(exc)], []


def exports(model):
    header = {"schemaVersion": 2, "semanticDigest": model_digest(model)}
    errors, warnings = validate(model)
    transitions = {item["id"]: item for item in model["transitions"]}
    states = {item["id"]: item for item in model["states"]}
    details = []
    for requirement in model["requirements"]:
        transition = transitions[requirement["transitionId"]]
        rid = requirement["id"]
        source, target = states[transition["from"]], states[transition["to"]]
        guard = "无附加条件" if transition["guard"] == "true" else transition["guard"]
        statement = f"在{'; '.join(source['facts'])}时，发生{transition['event']}且{guard}，应达到：{'; '.join(target['facts'])}。"
        details.append({**requirement, "featureIds": transition["featureIds"], "statement": statement,
                        "sourceState": source, "transition": transition, "targetState": target})
    graph = requirement_graph(model)
    from feasibility import analyze
    feasibility=analyze(model)
    return {
        "state-graph.json": {**header, "scope": model["scope"], "sources": model["sources"],
                             "entryStateIds": model.get("entryStateIds", []), "pathContext": model.get("pathContext"), "features": model["features"], "nodes": model["states"], "edges": model["transitions"], "transitionValidation":feasibility},
        "atomic-requirements.json": {**header, "requirements": details},
        "requirement-graph.json": {**header, "features": model["features"], **graph},
        "review-log.json": {**header, "phase": model["phase"], "scope": model["scope"],
                            "questions": model["questions"], "confirmations": model["confirmations"],
                            "rounds": model["rounds"], "semanticDigest": model_digest(model),
                            "validationSummary": {"structuralValid": not errors, "errors": errors,
                                                  "warnings": warnings, "businessCompleteness": "not_proven",
                                                  "humanAuthenticity": "not_verifiable_by_script"}},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("validate", "export", "digest", "scope-digest"))
    parser.add_argument("model", type=Path)
    parser.add_argument("output", type=Path, nargs="?")
    parser.add_argument("--final", action="store_true")
    parser.add_argument("--ready", action="store_true")
    args = parser.parse_args()
    try:
        model = json.loads(args.model.read_text(encoding="utf-8-sig"))
        if args.command in {"digest", "scope-digest"}:
            print(model_digest(model) if args.command == "digest" else scope_digest(model))
            return 0
        errors, warnings = validate(model, final=args.final, ready=args.ready)
        if errors:
            print(json.dumps({"valid": False, "errors": errors, "warnings": warnings}, ensure_ascii=False, indent=2))
            return 1
        if args.command == "export":
            if args.output is None:
                parser.error("export requires output directory")
            # Regenerate the same output directory; content digests detect stale reviews.
            from workflow import export_bundle
            root = args.output.resolve()
            if args.model.resolve() != (root / "_process" / "analysis-model.json"):
                raise ValueError("export source must be RUN/_process/analysis-model.json")
            export_bundle(model, root, root)
        print(json.dumps({"valid": True, "semantic_digest": model_digest(model), "warnings": warnings}, ensure_ascii=False, indent=2))
        return 0
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError, TypeError, KeyError) as exc:
        print(json.dumps({"valid": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
