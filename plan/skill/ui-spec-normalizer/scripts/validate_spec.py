#!/usr/bin/env python3
"""Validate a deterministic mobile/desktop UI JSON package."""
import argparse
import copy
import hashlib
import json
import math
import re
from pathlib import Path

BREAKPOINT = 768

def classify_width(width):
    """Classify a positive logical width using the single fixed breakpoint."""
    if isinstance(width, bool) or not isinstance(width, (int, float)) or not math.isfinite(width) or width <= 0:
        raise ValueError("logical width must be a positive finite number")
    return "mobile" if width < BREAKPOINT else "desktop"

def schema_errors(value, schema, root=None, at="$"):
    root = schema if root is None else root
    if schema is True:
        return []
    if schema is False:
        return [at + ": forbidden"]
    if "$ref" in schema:
        ref = schema["$ref"]
        if not ref.startswith("#/"):
            return [at + ": unsupported nonlocal schema reference"]
        target = root
        for key in ref[2:].split("/"):
            target = target[key.replace("~1", "/").replace("~0", "~")]
        return schema_errors(value, target, root, at)
    errors = []
    if "const" in schema and value != schema["const"]:
        errors.append(at + ": const mismatch")
    if "enum" in schema and value not in schema["enum"]:
        errors.append(at + ": enum mismatch")
    if "type" in schema:
        types = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
        actual = ("null" if value is None else "boolean" if isinstance(value, bool) else
                  "object" if isinstance(value, dict) else "array" if isinstance(value, list) else
                  "string" if isinstance(value, str) else "number" if isinstance(value, (int, float)) else "unknown")
        valid = actual in types or (
            "integer" in types and actual == "number" and isinstance(value, int))
        if not valid:
            return errors + [at + ": unexpected type " + actual]
    if isinstance(value, str):
        if "pattern" in schema and not re.search(schema["pattern"], value):
            errors.append(at + ": pattern mismatch")
        if len(value) < schema.get("minLength", 0):
            errors.append(at + ": minLength")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if not math.isfinite(value):
            errors.append(at + ": non-finite number")
        for key, predicate in [
            ("minimum", lambda a,b:a<b), ("maximum", lambda a,b:a>b),
            ("exclusiveMinimum", lambda a,b:a<=b), ("exclusiveMaximum", lambda a,b:a>=b)]:
            if key in schema and predicate(value, schema[key]):
                errors.append(at + ": " + key)
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            errors.append(at + ": minItems")
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            errors.append(at + ": maxItems")
        if "items" in schema:
            for i, item in enumerate(value):
                errors.extend(schema_errors(item, schema["items"], root, at + "[" + str(i) + "]"))
    if isinstance(value, dict):
        if len(value) < schema.get("minProperties", 0):
            errors.append(at + ": minProperties")
        for key in schema.get("required", []):
            if key not in value:
                errors.append(at + "." + key + ": required")
        for key, item in value.items():
            if key in schema.get("properties", {}):
                errors.extend(schema_errors(item, schema["properties"][key], root, at + "." + key))
            elif schema.get("additionalProperties") is False:
                errors.append(at + "." + key + ": extra property")
            elif isinstance(schema.get("additionalProperties"), dict):
                errors.extend(schema_errors(item, schema["additionalProperties"], root, at + "." + key))
    for child in schema.get("allOf", []):
        errors.extend(schema_errors(value, child, root, at))
    if "anyOf" in schema and not any(not schema_errors(value,s,root,at) for s in schema["anyOf"]):
        errors.append(at + ": no anyOf match")
    if "oneOf" in schema:
        matches = sum(not schema_errors(value,s,root,at) for s in schema["oneOf"])
        if matches != 1:
            errors.append(at + ": oneOf matched " + str(matches))
    if "if" in schema:
        branch = schema.get("then") if not schema_errors(value,schema["if"],root,at) else schema.get("else")
        if branch is not None:
            errors.extend(schema_errors(value,branch,root,at))
    return errors

def reject_constant(token):
    raise ValueError("non-finite JSON value: " + token)

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

def inside(base, relative):
    candidate = Path(relative)
    if candidate.is_absolute():
        raise ValueError("absolute artifact path: " + relative)
    resolved = (base / candidate).resolve()
    try:
        resolved.relative_to(base)
    except ValueError:
        raise ValueError("artifact path escapes package: " + relative)
    return resolved

def intervals_overlap(left, right):
    a,b = left
    c,d = right
    return max(-math.inf if a is None else a, -math.inf if c is None else c) < min(
        math.inf if b is None else b, math.inf if d is None else d)

def conditions_overlap(left, right):
    for key in ("width","height","fontScale"):
        if not intervals_overlap(left.get(key,[None,None]), right.get(key,[None,None])):
            return False
    for key in ("orientation","theme"):
        if key in left and key in right and left[key] != right[key]:
            return False
    return True

def changed_paths(value, prefix=""):
    paths = []
    for key, item in value.items():
        current = prefix + "." + key if prefix else key
        if isinstance(item,dict) and item:
            paths.extend(changed_paths(item,current))
        else:
            paths.append(current)
    return paths

def overlaps_path(a,b):
    return a == b or a.startswith(b+".") or b.startswith(a+".")

def apply_override(base, override):
    result = copy.deepcopy(base)
    for key, item in override.items():
        if isinstance(item,dict) and isinstance(result.get(key),dict):
            if "type" in item and item["type"] != result[key].get("type"):
                result[key] = copy.deepcopy(item)
            else:
                result[key] = apply_override(result[key],item)
        else:
            result[key] = copy.deepcopy(item)
    return result

def validate_package(directory, schema_path=None):
    base = Path(directory).resolve()
    errors, readiness, warnings = [], [], []
    counts = {"documents":0,"nodes":0,"styles":0,"assets":0}
    try:
        schema_file = Path(schema_path) if schema_path else Path(__file__).resolve().parents[1]/"assets"/"ui-spec.schema.json"
        schema = json.loads(schema_file.read_text(encoding="utf-8"))
        def read_record(relative, definition, expected_hash=None):
            full = inside(base,relative)
            raw = full.read_bytes()
            if expected_hash and digest(raw) != expected_hash:
                errors.append(relative+": SHA-256 mismatch")
            value = json.loads(raw.decode("utf-8"), parse_constant=reject_constant)
            errors.extend(relative+": "+e for e in schema_errors(value, schema["$defs"][definition],schema))
            return value
        manifest = read_record("manifest.json","manifest")
        if errors:
            return result_report(errors,readiness,warnings,counts,manifest.get("verification"))
        rules = read_record(manifest["artifacts"]["rules"]["file"],"rules",manifest["artifacts"]["rules"]["sha256"])
        library = read_record(manifest["artifacts"]["library"]["file"],"library",manifest["artifacts"]["library"]["sha256"])
        if errors:
            return result_report(errors,readiness,warnings,counts,manifest["verification"])
        if not (base/"UI规范.md").is_file():
            readiness.append("missing human-readable UI规范.md")
        if not (base/"schema"/"ui-spec.schema.json").is_file():
            readiness.append("missing bundled schema")
        profiles = rules["profiles"]
        if not manifest["documents"]:
            readiness.append("no classified UI documents; keep draft until logical width is known")
        source_ids = set()
        for source in manifest["sources"]:
            if not source["id"] or source["id"] in source_ids:
                errors.append("empty/duplicate source id")
            source_ids.add(source["id"])
            if not source["revision"] and not source["sha256"]:
                readiness.append("source without revision or hash: "+source["id"])
        issue_ids, document_ids = set(), set()
        for issue in manifest["issues"]:
            if not issue["id"] or issue["id"] in issue_ids:
                errors.append("empty/duplicate issue id")
            issue_ids.add(issue["id"])
            if issue["critical"] and issue["status"] == "open":
                readiness.append("open critical issue: "+issue["id"])
            if issue["status"] == "resolved" and not issue["resolution"]:
                errors.append("resolved issue without resolution: "+issue["id"])
        for pid,profile in profiles.items():
            modes = set()
            for mode in profile["modes"]:
                if mode["id"] == "base" or mode["id"] in modes or not mode["id"]:
                    errors.append(pid+": invalid/duplicate mode "+mode["id"])
                modes.add(mode["id"])
                for key in ("width","height","fontScale"):
                    if key in mode["when"]:
                        lo,hi = mode["when"][key]
                        if lo is not None and hi is not None and lo >= hi:
                            errors.append(pid+": empty condition interval "+mode["id"])
                if "width" in mode["when"]:
                    category_range = [0,BREAKPOINT] if pid == "mobile" else [BREAKPOINT,None]
                    if not intervals_overlap(mode["when"]["width"],category_range):
                        errors.append(pid+": mode cannot match within category "+mode["id"])
            for i,left in enumerate(profile["modes"]):
                for right in profile["modes"][i+1:]:
                    if conditions_overlap(left["when"],right["when"]):
                        errors.append(pid+": overlapping modes "+left["id"]+" / "+right["id"])
            if profile["formFactor"] != pid:
                errors.append(pid+": formFactor must equal profile id")
            base_width = profile["environment"]["baselineWidth"]
            if base_width is not None and base_width > 0 and classify_width(base_width) != pid:
                errors.append(pid+": baseline width contradicts fixed breakpoint")
            for case in profile["validationCases"]:
                if classify_width(case["width"]) != pid:
                    errors.append(pid+": validation case crosses category boundary")
            for dim in ("baselineWidth","baselineHeight"):
                if profile["environment"][dim] is None:
                    readiness.append(pid+": "+dim+" unspecified")
                elif profile["environment"][dim] <= 0:
                    errors.append(pid+": invalid "+dim)
        for aid,asset in library["assets"].items():
            exists = False
            if asset["file"]:
                full = inside(base,asset["file"])
                exists = full.is_file()
                if exists and asset["sha256"] and digest(full.read_bytes()) != asset["sha256"]:
                    errors.append("asset hash mismatch: "+aid)
            if asset["embedded"] is not None:
                exists = True
            if asset["availability"] == "available" and not exists:
                errors.append("available asset without data: "+aid)
            if asset["critical"] and (not exists or asset["availability"] != "available"):
                readiness.append("critical asset unavailable: "+aid)
            elif not exists:
                warnings.append("noncritical asset unavailable: "+aid)
        def require_asset(aid,context):
            if aid not in library["assets"]:
                errors.append(context+": missing asset "+aid)
        for sid,style in library["styles"].items():
            for fill in style["fills"]:
                if fill["type"] == "image":
                    require_asset(fill["assetRef"],sid)
            if style["typography"]:
                line = style["typography"]["lineHeight"]
                if line["mode"] == "font-metrics" and line["value"] is not None:
                    errors.append(sid+": font-metrics must use null value")
                if line["mode"] != "font-metrics" and (line["value"] is None or line["value"] <= 0):
                    errors.append(sid+": explicit line-height requires positive value")
        all_nodes, loaded_documents = {}, {}
        paths = set()
        for entry in manifest["documents"]:
            if entry["id"] in document_ids or not entry["id"]:
                errors.append("empty/duplicate document id")
            if entry["file"] in paths:
                errors.append("duplicate document file")
            document_ids.add(entry["id"]); paths.add(entry["file"])
            doc = read_record(entry["file"],"document",entry["sha256"])
            loaded_documents[entry["id"]] = doc
            if any(doc.get(k) != entry[k] for k in ("id","title","kind","profileId")):
                errors.append(entry["file"]+": manifest identity mismatch")
            if doc.get("profileId") not in profiles:
                errors.append(entry["file"]+": missing profile")
        if errors:
            return result_report(errors,readiness,warnings,counts,manifest["verification"])
        for did,doc in loaded_documents.items():
            profile = profiles[doc["profileId"]]
            if doc["kind"] == "screen" and classify_width(doc["referenceSize"]["width"]) != doc["profileId"]:
                errors.append(did+": screen width contradicts selected mobile/desktop profile")
            for issue_id in doc["issues"]:
                if issue_id not in issue_ids:
                    errors.append(did+": missing issue "+issue_id)
            mode_ids = {m["id"] for m in profile["modes"]}
            local_nodes, anchors = {}, {}
            def check_node(n,parent,resolved=False):
                ident = n["id"]
                if not resolved:
                    if ident in all_nodes:
                        errors.append("duplicate node id: "+ident)
                    all_nodes[ident] = n
                local_nodes[ident] = n
                if n["parentId"] != (parent["id"] if parent else None):
                    errors.append(ident+": parentId mismatch")
                if n["styleRef"] not in library["styles"]:
                    errors.append(ident+": missing style "+n["styleRef"])
                if n["componentRef"] is not None:
                    target = loaded_documents.get(n["componentRef"])
                    if not target or target["kind"] != "component":
                        errors.append(ident+": invalid component reference")
                    elif target["profileId"] != doc["profileId"]:
                        errors.append(ident+": cross-profile component requires explicit separate definition")
                if n["source"] and n["source"]["sourceId"] not in source_ids:
                    errors.append(ident+": missing source id")
                for decision in n["decisionRefs"]:
                    if decision not in rules["decisions"]:
                        errors.append(ident+": missing decision "+decision)
                for axis,dimension in n["sizing"].items():
                    mode,value,lo,hi = (dimension[k] for k in ("mode","value","min","max"))
                    if mode in ("fixed","fraction","percent") and value is None:
                        errors.append(ident+": size value required")
                    if mode not in ("fixed","fraction","percent") and value is not None:
                        errors.append(ident+": competing size value")
                    if value is not None and (value < 0 or mode=="fraction" and value<=0 or mode=="percent" and value>1):
                        errors.append(ident+": invalid "+axis+" value")
                    if lo is not None and lo < 0 or hi is not None and hi < 0 or lo is not None and hi is not None and lo > hi:
                        errors.append(ident+": size min/max conflict")
                if n["layout"] and n["layout"]["type"] == "grid":
                    for track in n["layout"]["columns"]:
                        if track["mode"] == "content" and track["value"] is not None:
                            errors.append(ident+": content track value must be null")
                        elif track["mode"] != "content" and (track["value"] is None or track["value"] <= 0):
                            errors.append(ident+": invalid grid track")
                if n["content"] and n["content"]["type"] in ("image","vector"):
                    require_asset(n["content"]["assetRef"],ident)
                if n["kind"] == "text" and n["styleRef"] in library["styles"] and library["styles"][n["styleRef"]]["typography"] is None:
                    errors.append(ident+": text without typography")
                position = n["placement"]
                if position["mode"] == "flow" and (position["anchorId"] is not None or any(v is not None for v in position["insets"].values())):
                    errors.append(ident+": flow contains position anchors")
                if position["mode"] != "flow" and not position["anchorId"]:
                    errors.append(ident+": positioned node needs anchor")
                if position["gridArea"] is not None and (not parent or not parent["layout"] or parent["layout"]["type"] != "grid"):
                    errors.append(ident+": gridArea outside grid")
                elif position["gridArea"] is not None:
                    area = position["gridArea"]
                    if area["column"] + area["columnSpan"] - 1 > len(parent["layout"]["columns"]):
                        errors.append(ident+": gridArea creates undeclared columns")
                if position["anchorId"]:
                    anchors[ident] = position["anchorId"]
                for left in n["policy"]["locked"]:
                    for right in n["policy"]["adaptive"]:
                        if overlaps_path(left,right):
                            errors.append(ident+": locked/adaptive conflict "+left+" / "+right)
                if not resolved:
                    seen = set()
                    for variant in n["responsive"]:
                        mid = variant["modeId"]
                        if mid not in mode_ids or mid in seen:
                            errors.append(ident+": missing/duplicate responsive mode "+mid)
                        seen.add(mid)
                        for changed in changed_paths(variant["overrides"]):
                            if not any(changed == p or changed.startswith(p+".") for p in n["policy"]["adaptive"]):
                                errors.append(ident+": responsive writes undeclared adaptive field "+changed)
                            if any(overlaps_path(changed,p) for p in n["policy"]["locked"]):
                                errors.append(ident+": responsive writes locked field "+changed)
                        merged = apply_override(n,variant["overrides"])
                        errors.extend(ident+" mode "+mid+": "+e for e in schema_errors(merged,schema["$defs"]["node"],schema))
                for child in n["children"]:
                    check_node(child,n,resolved)
            check_node(doc["tree"],None)
            def check_graph():
                for ident,target in anchors.items():
                    if target != "$viewport" and target not in local_nodes:
                        errors.append(ident+": anchor outside document or missing")
                    if local_nodes[ident]["placement"]["mode"] == "sticky" and target in local_nodes:
                        if not any(v=="scroll" for v in local_nodes[target]["overflow"].values()):
                            errors.append(ident+": sticky anchor is not a scroll container")
                    visited = set()
                    at = ident
                    while at in anchors:
                        if at in visited:
                            errors.append(ident+": anchor cycle")
                            break
                        visited.add(at); at = anchors[at]
            check_graph()
            def resolve_mode(node, mode_id):
                out = copy.deepcopy(node)
                for variant in node["responsive"]:
                    if variant["modeId"] == mode_id:
                        out = apply_override(out, variant["overrides"])
                out["children"] = [resolve_mode(c, mode_id) for c in out["children"]]
                return out
            for mode in profile["modes"]:
                local_nodes.clear(); anchors.clear()
                resolved_tree = resolve_mode(doc["tree"], mode["id"])
                check_node(resolved_tree, None, True)
                check_graph()
        for issue in manifest["issues"]:
            if issue["documentId"] is not None and issue["documentId"] not in document_ids:
                errors.append("issue references missing document: "+issue["id"])
        visual = manifest["verification"]
        for evidence in visual["evidence"]:
            if not inside(base,evidence).is_file():
                errors.append("missing visual evidence: " + evidence)
        if ("passed" in (visual["baselineVisual"],visual["responsiveVisual"])) and not visual["evidence"]:
            errors.append("visual passed without evidence")
        counts = {"documents":len(loaded_documents),"nodes":len(all_nodes),"styles":len(library["styles"]),"assets":len(library["assets"])}
        report = result_report(errors,readiness,warnings,counts,visual)
        report["authority"] = manifest["authority"]
        return report
    except (OSError,ValueError,KeyError,TypeError,RecursionError) as exc:
        errors.append(str(exc))
        return result_report(errors,readiness,warnings,counts,None)

def result_report(errors,readiness,warnings,counts,visual):
    visual = visual or {}
    return {
        "structure":{"status":"failed" if errors else "passed","failures":errors},
        "readiness":{"status":"blocked" if errors or readiness else "ready","reasons":readiness},
        "baselineVisual":visual.get("baselineVisual","not-tested"),
        "responsiveVisual":visual.get("responsiveVisual","not-tested"),
        "counts":counts,"warnings":warnings,
        "scope":"schema subset and semantic consistency; does not render or establish visual correctness",
        "sourceFilesRead":False
    }

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory")
    parser.add_argument("--schema")
    parser.add_argument("--report")
    args = parser.parse_args()
    report = validate_package(args.directory,args.schema)
    output = json.dumps(report,ensure_ascii=False,indent=2)+"\n"
    if args.report:
        Path(args.report).write_text(output,encoding="utf-8")
    print(output,end="")
    valid = report["structure"]["status"] == "passed" and (report.get("authority") != "canonical" or report["readiness"]["status"] == "ready")
    return 0 if valid else 1

if __name__ == "__main__":
    raise SystemExit(main())
