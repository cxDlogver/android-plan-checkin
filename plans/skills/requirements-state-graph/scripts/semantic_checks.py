"""Mechanical evidence checks for dual completeness; never claims business truth.

A witness documents one possible execution. Its event/guard/result reasons need
independent semantic review against actual sources before a final gate can pass.
"""
from collections import defaultdict

GATES = ("STRUCTURE-001", "FEASIBILITY-001", "COVERAGE-001", "CONTINUATION-001")
DISPOSITIONS = {"covered", "excluded_equivalent", "out_of_scope", "pending_decision"}
CONTINUATIONS = {"witnessed", "excluded", "pending"}


def candidates(model):
    """All structural adjacency candidates, including loops and parallel edges."""
    ts = {t["id"]: t for t in model["transitions"]}
    by_source = defaultdict(list)
    for requirement in model["requirements"]:
        by_source[ts[requirement["transitionId"]]["from"]].append(requirement["id"])
    pairs = []
    for requirement in model["requirements"]:
        for successor in by_source[ts[requirement["transitionId"]]["to"]]:
            pairs.append((requirement["id"], successor))
    return pairs


def inspect(model):
    """Return gate-specific mechanical diagnostics, not semantic acceptance."""
    problems = {gate: [] for gate in GATES}

    def error(gate, msg):
        problems[gate].append(msg)

    if not isinstance(model, dict):
        error("STRUCTURE-001", "model is not an object")
        return problems
    ts = {x["id"]: x for x in model.get("transitions", [])}
    states = {x["id"]: x for x in model.get("states", [])}
    reqs = {x["id"]: x for x in model.get("requirements", [])}
    sources = {x["id"]: x for x in model.get("sources", [])}
    questions = {x["id"]: x for x in model.get("questions", [])}
    ws = {x["id"]: x for x in model.get("witnesses", [])}
    claims = model.get("coverageClaims", [])
    assessments = model.get("continuationAssessments", [])
    if not isinstance(claims, list) or not isinstance(assessments, list):
        error("STRUCTURE-001", "coverage and continuation arrays required")
        return problems

    real_entries = set()
    for f in model.get("features", []):
        feature_entries = set(f.get("entryStateIds", []))
        evidence = f.get("entryEvidence", [])
        if not isinstance(evidence, list):
            error("STRUCTURE-001", f'{f["id"]}: entryEvidence must be array')
            continue
        covered = set()
        for e in evidence:
            sid = e.get("stateId")
            if sid not in feature_entries or sid not in states:
                error("STRUCTURE-001", f'{f["id"]}: unknown or undeclared real entry {sid}')
            if not isinstance(e.get("reason"), str) or not e["reason"].strip():
                error("STRUCTURE-001", f'{f["id"]}/{sid}: missing real-entry reason')
            ref_ids = e.get("sourceIds", [])
            if not ref_ids or any(s not in sources for s in ref_ids):
                error("STRUCTURE-001", f'{f["id"]}/{sid}: real-entry sources missing or invalid')
            covered.add(sid)
        if feature_entries != covered:
            error("STRUCTURE-001", f'{f["id"]}: entryStateIds lack entryEvidence: {sorted(feature_entries-covered)}')
        real_entries.update(feature_entries & covered)
    if ts and not real_entries:
        error("STRUCTURE-001", "no evidenced real entry states")
    # Topological reachability is necessary but never sufficient for business feasibility.
    reachable, frontier = set(real_entries), list(real_entries)
    while frontier:
        sid = frontier.pop()
        for t in ts.values():
            if t["from"] == sid and t["to"] not in reachable:
                reachable.add(t["to"])
                frontier.append(t["to"])
    for sid in states:
        if sid not in reachable:
            error("STRUCTURE-001", f"{sid}: no route from any real entry (guards still require review)")
    for tid, t in ts.items():
        if str(t.get("guard", "")).strip().lower() == "false":
            error("FEASIBILITY-001", f"{tid}: guard is explicitly false; no executable instance")

    witnesses_by_transition = defaultdict(list)
    for wid, w in ws.items():
        tid = w.get("transitionId")
        witnesses_by_transition[tid].append(wid)
        entry = w.get("entryStateId")
        path = w.get("pathTransitionIds")
        facts = w.get("scenarioFacts")
        steps = w.get("stepEvidence")
        if entry not in real_entries:
            error("FEASIBILITY-001", f"{wid}: entry {entry} has no true-entry evidence")
        if not isinstance(path, list) or not path or path[-1] != tid:
            error("FEASIBILITY-001", f"{wid}: path must end with its transition {tid}")
            continue
        if not isinstance(facts, list) or not facts or not all(isinstance(s, str) and s.strip() for s in facts):
            error("FEASIBILITY-001", f"{wid}: concrete scenarioFacts required")
        if not isinstance(steps, list) or len(steps) != len(path):
            error("FEASIBILITY-001", f"{wid}: every path step needs evidence")
            continue
        if not w.get("sourceIds") or any(x not in sources for x in w["sourceIds"]):
            error("FEASIBILITY-001", f"{wid}: traceable sources required")
        current = entry
        for i, step_tid in enumerate(path):
            t = ts.get(step_tid)
            if not t or t["from"] != current:
                error("FEASIBILITY-001", f"{wid}: broken executable path at step {i} ({step_tid})")
                break
            if t.get("status") == "candidate":
                error("FEASIBILITY-001", f"{wid}: unconfirmed candidate used in executable path ({step_tid})")
            current = t["to"]
            ev = steps[i]
            if not isinstance(ev, dict) or ev.get("transitionId") != step_tid:
                error("FEASIBILITY-001", f"{wid}: stepEvidence order mismatch at {i}")
                continue
            for field in ("eventEnabledReason", "guardSatisfiedReason", "resultReason"):
                if not isinstance(ev.get(field), str) or not ev[field].strip():
                    error("FEASIBILITY-001", f"{wid}/{step_tid}: missing {field}")
    for tid, t in ts.items():
        if t.get("status") != "candidate" and not witnesses_by_transition.get(tid):
            error("FEASIBILITY-001", f"{tid}: no real-start executable witness")
    for tid in witnesses_by_transition:
        if tid not in ts:
            error("FEASIBILITY-001", f"witness refers to deleted transition {tid}")

    covered_transitions = set()
    covered_sources = set()
    for claim in claims:
        cid = claim.get("id", "(missing id)")
        sid = claim.get("sourceId")
        if sid not in sources:
            error("COVERAGE-001", f"{cid}: source not found")
        else:
            covered_sources.add(sid)
        if not isinstance(claim.get("locator"), str) or not claim["locator"].strip():
            error("COVERAGE-001", f"{cid}: specific source locator required")
        disposition = claim.get("disposition")
        if disposition not in DISPOSITIONS:
            error("COVERAGE-001", f"{cid}: invalid disposition")
        if not isinstance(claim.get("reason"), str) or not claim["reason"].strip():
            error("COVERAGE-001", f"{cid}: explanation required")
        related = claim.get("relatedIds", [])
        if disposition in ("covered", "excluded_equivalent") and not related:
            error("COVERAGE-001", f"{cid}: coverage or equivalence claim has no mapping")
        if not isinstance(related, list):
            error("COVERAGE-001", f"{cid}: relatedIds must be an array")
            related = []
        for rid in related:
            if rid in ts:
                if disposition == "covered":
                    covered_transitions.add(rid)
            elif rid in reqs:
                if disposition == "covered":
                    covered_transitions.add(reqs[rid]["transitionId"])
            elif rid not in states and rid not in questions:
                error("COVERAGE-001", f"{cid}: unknown mapping {rid}")
        if disposition == "pending_decision":
            if not any(rid in questions and questions[rid].get("status") == "open" for rid in related):
                error("COVERAGE-001", f"{cid}: pending coverage needs open question reference")
            error("COVERAGE-001", f"{cid}: unresolved source obligation")
    for sid, source in sources.items():
        if source.get("kind") in ("prd", "ui") and sid not in covered_sources:
            error("COVERAGE-001", f"{sid}: no source obligation reviewed")
    for tid, t in ts.items():
        if t.get("status") != "candidate" and tid not in covered_transitions:
            error("COVERAGE-001", f"{tid}: no source coverage claim maps to valid transition")

    valid_pairs = set(candidates(model))
    assessments_by_pair = defaultdict(list)
    for a in assessments:
        aid = a.get("id", "(missing id)")
        pair = (a.get("fromRequirementId"), a.get("toRequirementId"))
        assessments_by_pair[pair].append(aid)
        if pair not in valid_pairs:
            error("CONTINUATION-001", f"{aid}: assessment does not match structural adjacency")
        status = a.get("status")
        if status not in CONTINUATIONS:
            error("CONTINUATION-001", f"{aid}: invalid classification")
        if not isinstance(a.get("reason"), str) or not a["reason"].strip():
            error("CONTINUATION-001", f"{aid}: disposition reason required")
        if not a.get("sourceIds") or any(s not in sources for s in a["sourceIds"]):
            error("CONTINUATION-001", f"{aid}: source references required")
        if status == "pending":
            error("CONTINUATION-001", f"{aid}: unresolved structural continuation")
        if status == "witnessed":
            wid = a.get("witnessId")
            w = ws.get(wid)
            if w is None:
                error("CONTINUATION-001", f"{aid}: witnessed continuation lacks witness")
            else:
                path = w.get("pathTransitionIds", [])
                left = reqs.get(pair[0], {}).get("transitionId")
                right = reqs.get(pair[1], {}).get("transitionId")
                if not any(path[i:i+2] == [left, right] for i in range(len(path)-1)):
                    error("CONTINUATION-001", f"{aid}: witness does not contain consecutive pair")
    for pair in valid_pairs:
        if len(assessments_by_pair[pair]) != 1:
            error("CONTINUATION-001", f"{pair}: expected exactly one classification, got {len(assessments_by_pair[pair])}")
    return problems


def summary(model):
    """Deterministic export; review against source is still required."""
    witnesses = model.get("witnesses", [])
    by_tid = {t["id"]: [w["id"] for w in witnesses if w.get("transitionId") == t["id"]]
              for t in model.get("transitions", [])}
    return {
        "execution-witnesses.json": {"witnesses": witnesses, "byTransitionId": by_tid,
                                     "semantics": "Documented existence claims; independent source review required"},
        "coverage-report.json": {"claims": model.get("coverageClaims", []),
                                 "continuations": model.get("continuationAssessments", []),
                                 "semantics": "Source-to-behavior coverage claims and structural continuation dispositions; independently reviewed"},
    }
