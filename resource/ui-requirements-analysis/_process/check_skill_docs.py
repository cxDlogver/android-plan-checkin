from pathlib import Path
import json,re,sys
w=Path(__file__).resolve().parent
skill=w.parent.parent.parent/'.codex/skills/requirements-analysis'
issues=[]
for path in [skill/'SKILL.md',*(skill/'references').glob('*.md')]:
 for link in re.findall(r'\[[^\]]*\]\(([^)]+)\)',path.read_text(encoding='utf-8')):
  if '://' in link or link.startswith('#'):continue
  if not (path.parent/link.split('#')[0]).exists():issues.append(str(path)+': '+link)
result={'relativeLinks':'passed' if not issues else 'failed','issues':issues,'fixedRules':json.loads((skill/'assets/gate-contract.json').read_text(encoding='utf-8'))['required_rule_ids']}
(w/'evidence/skill-doc-checks.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False))
raise SystemExit(bool(issues))

