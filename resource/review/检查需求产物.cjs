const fs = require('fs');
const path = require('path');
const root = process.argv[2];
const resource = path.join(root, 'resource');
const names = ['设计需求文档-计划打卡-Android-v1.md', '需求分析与待确认项.md', 'UIUX-计划打卡-Android-v1.md', 'Windows安卓模拟器验证方案.md'];
const missing = [];
const forbidden = ['ios', 'plan', 'checkin'].join('-');
for (const name of names) {
  const file = path.join(resource, name);
  const text = fs.readFileSync(file, 'utf8');
  if (text.includes(forbidden)) throw new Error('Forbidden project reference');
  for (const match of text.matchAll(/!?\[[^\]]*\]\(([^)]+)\)/g)) {
    const href = match[1];
    if (/^(https?:|app:|plugin:)/.test(href)) continue;
    const local = path.resolve(path.dirname(file), href.split('#')[0]);
    if (!fs.existsSync(local)) missing.push({ file: name, href });
  }
}
const prd = fs.readFileSync(path.join(resource, names[0]), 'utf8').replace(/\r\n/g, '\n');
const map = JSON.parse(fs.readFileSync(path.join(resource, 'design', 'page-map.json'), 'utf8'));
const snapshot = JSON.parse(fs.readFileSync(path.join(resource, 'design', 'canvas-snapshot.json'), 'utf8'));
const snapshotScript = fs.readFileSync(path.join(resource, 'design', 'pen-create-v1.js'), 'utf8');
const end = snapshotScript.indexOf(';\nconst created={}');
const scriptSnapshot = JSON.parse(snapshotScript.slice('const designSnapshot='.length, end));
if (JSON.stringify(snapshot) !== JSON.stringify(scriptSnapshot)) throw new Error('Reconstruction snapshot mismatch');

const html = fs.readFileSync(path.join(resource, 'design', 'preview.html'), 'utf8');
const frSections = new Map([...prd.matchAll(/^### (FR\d{2})｜[^\n]+\n([\s\S]*?)(?=^## |^### FR|$(?![\s\S]))/gm)].map(match => [match[1], match[2]]));
const anchors = new Set([...prd.matchAll(/<a id="([^"]+)"><\/a>/g)].map(match => match[1]));
const brokenAnchors = [...prd.matchAll(/\]\(#([^)]+)\)/g)].map(match => match[1]).filter(id => !anchors.has(id));
const pairedScreenshots = map.screens.filter(screen => {
  const section = frSections.get(screen.primaryRequirement) || '';
  return section.includes('(design/' + screen.preview + ')') && section.includes('id="' + screen.documentAnchor + '"') && html.includes('<article id="' + screen.documentAnchor + '">') && html.includes('src="' + screen.preview + '"');
}).length;
const requirementsCovered = new Set(map.screens.flatMap(screen => screen.requirements));
const acceptanceCovered = new Set(map.screens.flatMap(screen => screen.acceptance));
for (const id of requirementsCovered) if (!frSections.has(id)) throw new Error('Unknown requirement: ' + id);
for (const id of acceptanceCovered) if (!prd.includes('| ' + id + ' / ')) throw new Error('Unknown acceptance: ' + id);
const report = {
  date: '2026-10-09',
  documentStatus: /版本：[\d.]+ 已确认/.test(prd) ? 'confirmed' : 'revision_review',
  requirements: (prd.match(/^### FR\d+/gm) || []).length,
  acceptanceGroups: (prd.match(/^\| AT\d+/gm) || []).length,
  embeddedScreenshots: (prd.match(/^!\[/gm) || []).length,
  mappedScreens: map.screens.length,
  pairedScreenshots,
  pairedRequirements: requirementsCovered.size,
  pairedAcceptanceGroups: acceptanceCovered.size,
  brokenDocumentAnchors: brokenAnchors,
  snapshotRoots: snapshot.nodes.length,
  colorVariables: Object.keys(snapshot.variables.variables).length,
  missingLinks: missing,
  allPngsNonempty: map.screens.every(screen => fs.statSync(path.join(resource, 'design', screen.preview)).size > 0),
  penDisk: { bytes: fs.statSync(path.join(resource, 'ui.pen')).size, status: map.diskSave === 'saved' ? 'saved' : 'pending_save' },
  verification: { design: 'PASS', documentationPairing: 'PASS', penLatestSaved: map.diskSave === 'saved' ? 'PASS' : 'PENDING_SAVE', implementation: 'NOT_RUN', nativeBuild: 'NOT_RUN', emulator: 'NOT_RUN', standaloneApk: 'NOT_RUN' }
};
if (report.requirements !== 32 || report.acceptanceGroups !== 28 || report.embeddedScreenshots !== 23 || report.mappedScreens !== 23 || pairedScreenshots !== 23 || requirementsCovered.size !== 32 || acceptanceCovered.size !== 28 || brokenAnchors.length || missing.length || !report.allPngsNonempty) throw new Error(JSON.stringify(report));
fs.writeFileSync(path.join(resource, 'review', '需求一致性检查结果.json'), JSON.stringify(report, null, 2) + '\n');
console.log(JSON.stringify(report));
