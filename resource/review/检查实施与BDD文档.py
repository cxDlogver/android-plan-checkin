"""Check authoring artifacts only; never reports application acceptance PASS."""
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

RESOURCE = Path(__file__).resolve().parent.parent
REPORT = RESOURCE / "review/实施与BDD文档检查结果.json"
CATALOG = RESOURCE / "acceptance/追踪目录.json"
PLAN = RESOURCE / "实施计划-checklist-计划打卡-Android-v1.md"
BDD = RESOURCE / "BDD验收-checklist-计划打卡-Android-v1.md"
data = json.loads(CATALOG.read_text(encoding="utf-8"))
tasks = {x["id"]: x for x in data["tasks"]}
cases = {x["id"]: x for x in data["scenarios"]}
plan = PLAN.read_text(encoding="utf-8")
bdd = BDD.read_text(encoding="utf-8")
booklet_files = sorted({RESOURCE/x["document"] for x in cases.values()})
details = "\n".join(file.read_text(encoding="utf-8") for file in booklet_files)
prd = (RESOURCE / "设计需求文档-计划打卡-Android-v1.md").read_text(encoding="utf-8")
checks = []
errors = []


def check(name, condition, detail=None):
    item = {"check": name, "status": "PASS" if condition else "FAIL"}
    if detail is not None:
        item["detail"] = detail
    checks.append(item)
    if not condition:
        errors.append(name)


def section(text, prefix, identifier):
    pattern = rf'<a id="{identifier.lower()}"></a>\n([\s\S]*?)(?=<a id="{prefix}\d+"></a>|\Z)'
    found = re.search(pattern, text)
    return found.group(1) if found else ""


def acyclic(graph):
    done, active = set(), []
    cycles = []

    def visit(node):
        if node in active:
            cycles.append(active[active.index(node):] + [node])
            return
        if node in done:
            return
        active.append(node)
        for target in graph[node]:
            visit(target)
        active.pop()
        done.add(node)

    for node in graph:
        visit(node)
    return cycles


check("unique task/scenario identifiers", len(tasks) == len(data["tasks"]) == 30 and len(cases) == len(data["scenarios"]) == data["scenarioCount"])
check("all task and product statuses unexecuted", all(x["status"] == "NOT_STARTED" for x in tasks.values()) and all(x["status"] == "NOT_RUN" for x in cases.values()) and data["productExecution"] == "NOT_RUN")
check("review status not silently confirmed", data["status"] == "REVIEW_DRAFT" and "评审稿" in plan and "评审稿" in bdd)
check("no checked execution boxes", not re.search(r"^- \[[xX]\]", plan + "\n" + bdd + "\n" + details, re.M))
fr = set(re.findall(r"^### (FR\d{2})｜", prd, re.M))
at = set(re.findall(r"^\| (AT\d{2}) /", prd, re.M))
non_report = [x for x in cases.values() if x["layer"] != "REPORT"]
covered_fr = {v for x in non_report for v in x["fr"]}
covered_at = {v for x in non_report for v in x["at"]}
check("32 FR and 28 AT covered outside report aggregation", len(fr) == 32 and len(at) == 28 and fr == covered_fr and at == covered_at,
      {"missingFR": sorted(fr-covered_fr), "missingAT": sorted(at-covered_at)})
invalid = [x["id"] for x in cases.values() if not set(x["fr"]).issubset(fr) or not set(x["at"]).issubset(at)]
check("no unknown requirement or acceptance ids", not invalid, invalid)
relation_errors = []
exit_errors = []
graph = {identifier: set(item["depends"]) for identifier, item in tasks.items()}
for identifier, item in cases.items():
    expected = {item["owner"], *item["consumers"], *item["contributors"]}
    expected_exits = {item["owner"], *item["consumers"]}
    if not expected.issubset(tasks):
        relation_errors.append(identifier)
        continue
    if set(item["contributors"]) & expected_exits:
        relation_errors.append(identifier + ": contribution also exit")
    for task_id in tasks:
        if (identifier in tasks[task_id]["acceptance"]) != (task_id in expected):
            relation_errors.append(task_id + "/" + identifier)
        if (identifier in tasks[task_id]["exitAcceptance"]) != (task_id in expected_exits):
            exit_errors.append(task_id + "/" + identifier)
    for consumer in item["consumers"]:
        graph[consumer].add(item["owner"])
    case_section = section(details, "ac", identifier)
    if not all(f"[{task_id}](../../{PLAN.name}#{task_id.lower()})" in case_section for task_id in expected):
        relation_errors.append(identifier + ": BDD links")
for identifier, item in tasks.items():
    task_section = section(plan, "ip", identifier)
    if not item["exitAcceptance"] or set(item["depends"]) - tasks.keys():
        exit_errors.append(identifier + ": empty exits or unknown dependency")
    for case_id in item["acceptance"]:
        if f"[{case_id}]({cases[case_id]['document']}#{case_id.lower()})" not in task_section:
            relation_errors.append(identifier + ": plan link " + case_id)
    if {x["scenario"] for x in item["exitChecks"]} != set(item["exitAcceptance"]):
        exit_errors.append(identifier + ": exit scope missing")
check("bidirectional contributor/owner/consumer links exact", not relation_errors, relation_errors)
check("every task has explicit exit scopes", not exit_errors, exit_errors)
cycles = acyclic(graph)
check("dependency and acceptance-owner graph acyclic", not cycles, cycles)
check("P2 exits do not require UI evidence", all("UI" not in cases[case_id]["evidence"] and "A11Y" not in cases[case_id]["evidence"] for item in tasks.values() if item["phase"] == "P2" for case_id in item["exitAcceptance"]))
check("early tasks use scoped base matrix exits", all("BASE_FUNCTIONAL" in e["scope"] for item in tasks.values() if int(item["id"][2:]) <= 26 for e in item["exitChecks"] if cases[e["scenario"]]["core"]))
check("early semantic profiles do not pretend TalkBack", all("A11Y" not in cases[x]["evidence"] and "SEMANTIC" in cases[x]["evidence"] for x in ("AC072", "AC080", "AC105")))
check("three successful creations part of full core matrix", cases["AC120"]["core"] and {row[1] for row in cases["AC120"]["examples"][1:]} == {"fixed", "weekly", "one_time"})
check("default weekdays clarified in product and creation contract", "新建默认全部未选" in prd and "weekdayMask初值为空" in json.dumps(cases["AC016"], ensure_ascii=False) and "初始为空选择" in (RESOURCE/"technical/命令与查询契约.md").read_text(encoding="utf-8"))

outline_errors = []
checklist_errors = []
instances = 0
assertion_count = 0
for identifier, item in cases.items():
    text = section(details, "ac", identifier)
    if not all(item[k].strip() for k in ("given", "when", "then")):
        outline_errors.append(identifier + ": empty business step")
    code = re.search(r"```gherkin\n([\s\S]*?)\n```", text)
    if not code or not re.search(r"\n  Given .+\n  When .+\n  Then .+", code.group(1)):
        outline_errors.append(identifier + ": Given When Then structure")
    if not item["assertions"] or not item["evidence"]:
        checklist_errors.append(identifier + ": missing assertions/evidence")
    assertion_count += len(item["assertions"])
    for index in range(1, len(item["assertions"])+1):
        if f"- [ ] {identifier}.A{index} —" not in text:
            checklist_errors.append(identifier + ": assertion " + str(index))
    for index in range(len(item["evidence"])+1):
        if f"- [ ] {identifier}.E{index} —" not in text:
            checklist_errors.append(identifier + ": evidence " + str(index))
    placeholders = set(re.findall(r"<([^>]+)>", " ".join(item[k] for k in ("given", "when", "then"))))
    if item["examples"]:
        header, *rows = item["examples"]
        if len(set(header)) != len(header) or not placeholders.issubset(header) or any(len(row) != len(header) for row in rows) or len({row[0] for row in rows}) != len(rows):
            outline_errors.append(identifier + ": invalid Examples")
        for row in rows:
            if f"- [ ] {identifier}/{row[0]} —" not in text:
                checklist_errors.append(identifier + ": example checkbox " + row[0])
        instances += len(rows)
    else:
        instances += 1
        if placeholders:
            outline_errors.append(identifier + ": parameters without Examples")
check("Given When Then and Example structures", not outline_errors, outline_errors)
check("every assertion/example/evidence has a checkbox", not checklist_errors, checklist_errors)
check("expanded instance count matches catalog", instances == data["expandedExampleCount"], instances)
features = sorted((RESOURCE/"acceptance/features").glob("*.feature"))
seen = []
feature_errors = []
for file in features:
    content = file.read_text(encoding="utf-8")
    if len(re.findall(r"^Feature:", content, re.M)) != 1 or not content.startswith("# language: en\n"):
        feature_errors.append(file.name)
    blocks = re.findall(r"  (@AC\d+[\s\S]*?)(?=\n\n  @AC|\Z)", content)
    for block in blocks:
        identifier = re.search(r"@(AC\d+)", block).group(1)
        seen.append(identifier)
        normalized = "\n".join(line[2:] if line.startswith("  ") else line for line in block.splitlines()).rstrip()
        doc_block = re.search(r"```gherkin\n([\s\S]*?)\n```", section(details, "ac", identifier))
        if not doc_block or normalized != doc_block.group(1):
            feature_errors.append(identifier + ": feature/document mismatch")
check("features match all documented scenarios exactly", len(features) == len({x["group"] for x in cases.values()}) and len(seen) == len(set(seen)) == len(cases) and set(seen) == set(cases) and not feature_errors, feature_errors)

documents = [PLAN, BDD, *booklet_files, RESOURCE/"acceptance/执行与证据规则.md", RESOURCE/"acceptance/FR-AT追踪索引.md", RESOURCE.parent/"README.md", RESOURCE/"技术设计文档-计划打卡-Android-v1.md", RESOURCE/"technical/验收与构建证据规范.md"]
broken = []
for file in documents:
    content = file.read_text(encoding="utf-8")
    for match in re.finditer(r"!?\[[^\]]*\]\(([^)]+)\)", content):
        href = match.group(1)
        if re.match(r"^(https?:|app:|plugin:)", href):
            continue
        local, _, anchor = href.partition("#")
        target = (file.parent / local).resolve() if local else file
        if target == REPORT:
            continue  # This checker creates its own report below.
        if not target.exists():
            broken.append({"file": file.name, "href": href, "reason": "missing target"})
        elif anchor and target.suffix == ".md":
            target_text = target.read_text(encoding="utf-8")
            anchors = re.findall(r'<a id="([^\"]+)"></a>', target_text)
            if anchor not in anchors:
                broken.append({"file": file.name, "href": href, "reason": "missing explicit anchor"})
check("local files and explicit anchors accessible", not broken, broken)
template = json.loads((RESOURCE/"acceptance/单实例报告模板.json").read_text(encoding="utf-8"))
check("report is empty template not execution evidence", template["status"] == "NOT_RUN" and template["runId"] is None
      and all(x["path"] is None and x["sha256"] is None for x in template["evidence"])
      and all(x["expected"] is None and x["actual"] is None and x["status"] == "NOT_RUN" for x in template["assertions"]))
forbidden = "-".join(("ios", "plan", "checkin"))
check("new artifacts free of prohibited source reference", all(forbidden not in file.read_text(encoding="utf-8") for file in [PLAN, BDD, *booklet_files, CATALOG, *features]))
report = {
    "checkedAtUtc": datetime.now(timezone.utc).isoformat(),
    "scope": "document structure, checklist completeness, bidirectional references and dependency graph only",
    "status": "PASS" if not errors else "FAIL",
    "baseline": data["baseline"],
    "documentStatus": data["status"],
    "counts": {"implementationTasks": len(tasks), "bddScenarios": len(cases), "scenarioExampleInstancesBeforeDeviceExpansion": instances,
               "assertionChecklists": assertion_count, "featureFiles": len(features), "requirements": len(fr), "originalAcceptanceGroups": len(at)},
    "checks": checks,
    "sourceHashes": {str(file.relative_to(RESOURCE)): hashlib.sha256(file.read_bytes()).hexdigest() for file in [PLAN, BDD, *booklet_files, CATALOG]},
    "limits": {"officialGherkinParser": "NOT_RUN", "stepDefinitions": "NOT_IMPLEMENTED", "applicationBuild": "NOT_RUN",
               "nativeSQLiteAcceptance": "NOT_RUN", "uiAcceptance": "NOT_RUN", "releaseApk": "NOT_RUN"},
}
REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
print(json.dumps({"documentChecks": report["status"], **report["counts"], "failedChecks": errors, "productAcceptance": "NOT_RUN"}, ensure_ascii=False))
if errors:
    raise SystemExit(1)
