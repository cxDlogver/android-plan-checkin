const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const resource = path.resolve(__dirname, '..');
const technicalName = '技术设计文档-计划打卡-Android-v1.md';
const decisionsName = '技术决策与待确认项.md';
const prd = fs.readFileSync(path.join(resource, '设计需求文档-计划打卡-Android-v1.md'), 'utf8');
const technical = fs.readFileSync(path.join(resource, technicalName), 'utf8');
const decisions = fs.readFileSync(path.join(resource, decisionsName), 'utf8');
const statusMatch = technical.match(/^> 版本：0\.8 (已确认技术基线|技术评审草案)/m);
if (!statusMatch) throw new Error('Missing explicit technical baseline status');
const isConfirmed = statusMatch[1] === '已确认技术基线';
const requiredIds = new Set([...prd.matchAll(/^### (FR\d{2})｜/gm)].map(match => match[1]));
const traceRows = [...technical.matchAll(/^\| (FR\d{2}) \|/gm)].map(match => match[1]);
const covered = new Set(traceRows);
const missingLinks = [];
const appendixNames = ['数据结构与迁移契约.md', '命令与查询契约.md', '日期生命周期与统计决策表.md', '验收与构建证据规范.md'].map(name => path.join('technical', name));
const documentNames = [technicalName, decisionsName, '依赖可行性核查-20261009.md', ...appendixNames];
for (const name of documentNames) {
  const file = path.join(resource, name);
  const text = fs.readFileSync(file, 'utf8');
  if (text.includes(['ios', 'plan', 'checkin'].join('-'))) throw new Error('Forbidden project reference');
  for (const match of text.matchAll(/!?\[[^\]]*\]\(([^)]+)\)/g)) {
    const href = match[1];
    if (/^https?:/.test(href)) continue;
    if (!fs.existsSync(path.resolve(path.dirname(file), href.split('#')[0]))) missingLinks.push({ name, href });
  }
}
const notCovered = [...requiredIds].filter(id => !covered.has(id));
const unknown = [...covered].filter(id => !requiredIds.has(id));
const pending = [...technical.matchAll(/^\| (T\d+) \| [^\n]+\| 待回答 \|/gm)].map(match => match[1]);
const decisionIds = new Set([...technical.matchAll(/^\| (T\d+)(?: \/ Q\d+)? \|/gm)].map(match => match[1]));
const missingDecisions = Array.from({ length: 15 }, (_, index) => `T${index + 1}`).filter(id => !decisionIds.has(id));
const confirmationRecordValid = /^\| T15 \| [^\r\n]+\| 用户已整体确认 \|/m.test(technical) && decisions.includes('用户回复“确认技术0.8（推荐）”');
const sqlFile = path.join(resource, 'technical', 'schema-v1.sql');
const sqlReport = JSON.parse(fs.readFileSync(path.join(__dirname, 'SQL原型核查结果.json'), 'utf8'));
const sqlSha256 = crypto.createHash('sha256').update(fs.readFileSync(sqlFile)).digest('hex');
const sqlitePackage = JSON.parse(fs.readFileSync(path.join(__dirname, 'SQLite发布包核查结果.json'), 'utf8'));
const sqlEvidenceValid = sqlReport.status === 'PASS' && sqlReport.schemaSha256 === sqlSha256 && sqlReport.cases.length === 13 && sqlReport.androidExpoSQLite === 'NOT_RUN';
const sqliteEvidenceValid = sqlitePackage.packageVersion === '57.0.4' && sqlitePackage.integrityCheck === 'PASS' && sqlitePackage.sqliteVersion === '3.50.3' && sqlitePackage.androidRuntime === 'NOT_RUN';
const report = {
  date: '2026-10-09',
  documentVersion: '0.8',
  scope: 'technical_document_only',
  status: isConfirmed ? 'confirmed' : 'draft',
  prdRequirements: requiredIds.size,
  tracedRequirements: covered.size,
  traceRows: traceRows.length,
  missingRequirements: notCovered,
  unknownRequirements: unknown,
  missingLocalLinks: missingLinks,
  pendingDecisions: pending,
  confirmedDecisionCount: decisionIds.size,
  missingDecisions,
  detailedSpecifications: appendixNames.length,
  sqlPrototypeCases: sqlReport.cases.length,
  overallTechnicalConfirmation: isConfirmed ? 'CONFIRMED' : 'PENDING',
  confirmationId: isConfirmed ? 'T15' : null,
  verification: { documentation: 'PASS', hostSqlPrototype: sqlEvidenceValid ? 'PASS' : 'FAIL', pinnedSQLitePackageSource: sqliteEvidenceValid ? 'PASS' : 'FAIL', implementation: 'NOT_RUN', nativeBuild: 'NOT_RUN', emulator: 'NOT_RUN', standaloneApk: 'NOT_RUN' }
};
if (requiredIds.size !== 32 || covered.size !== 32 || traceRows.length !== 32 || notCovered.length || unknown.length || missingLinks.length || pending.length || missingDecisions.length || !sqlEvidenceValid || !sqliteEvidenceValid || (isConfirmed && !confirmationRecordValid)) throw new Error(JSON.stringify(report));
fs.writeFileSync(path.join(__dirname, '技术文档检查结果.json'), JSON.stringify(report, null, 2) + '\n');
console.log(JSON.stringify(report));
