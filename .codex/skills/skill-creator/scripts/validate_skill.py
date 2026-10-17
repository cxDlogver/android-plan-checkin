#!/usr/bin/env python3
"""Fast, dependency-free structural checks for a local Codex Skill.

This is not a YAML schema validator or a test of Skill behavior.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from urllib.parse import unquote, urlsplit


NAME_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
LINK_PATTERN = re.compile(r"\]\(([^)]+)\)")


def validate(target: Path) -> dict:
    skill_file = target / "SKILL.md" if target.is_dir() else target
    errors: list[str] = []
    warnings: list[str] = []

    if not skill_file.is_file():
        return {"status": "FAIL", "errors": [f"Missing file: {skill_file}"], "warnings": []}

    contents = skill_file.read_text(encoding="utf-8-sig")
    match = re.match(r"\A---\s*\n(.*?)\n---\s*\n", contents, re.S)
    if not match:
        errors.append("SKILL.md must start with a closed YAML frontmatter block")
        metadata = ""
        body = contents
    else:
        metadata = match.group(1)
        body = contents[match.end():]

    def get_field(key: str) -> str:
        found = re.findall(rf"(?m)^{re.escape(key)}:\s*(.*)$", metadata)
        if len(found) != 1:
            errors.append(f"Expected exactly one frontmatter '{key}' field")
            return ""
        return found[0].strip().strip('"').strip("'").strip()

    name = get_field("name")
    description = get_field("description")
    if name and (len(name) > 64 or not NAME_PATTERN.fullmatch(name)):
        errors.append("name must be kebab-case and at most 64 characters")
    if name and name != skill_file.parent.name:
        errors.append(f"name '{name}' differs from folder '{skill_file.parent.name}'")
    if not description:
        errors.append("description must explain what the Skill does and when to use it")
    if not body.strip():
        errors.append("Skill instruction body must not be empty")

    for raw_link in LINK_PATTERN.findall(body):
        link = raw_link.strip().split(" ", 1)[0].strip("<>")
        parsed = urlsplit(link)
        if parsed.scheme or link.startswith(("/", "#")):
            continue
        relative_path = unquote(parsed.path)
        if relative_path and not (skill_file.parent / relative_path).exists():
            errors.append(f"Missing relative link target: {relative_path}")

    if len(body.splitlines()) > 500:
        warnings.append("SKILL.md exceeds 500 lines; consider progressive disclosure")
    return {"status": "PASS" if not errors else "FAIL", "errors": errors, "warnings": warnings}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("skill", type=Path, help="Skill folder or SKILL.md file")
    args = parser.parse_args()
    result = validate(args.skill)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
