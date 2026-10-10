const fs = require('node:fs');
const path = require('node:path');
const directory = 'resource/progress';
const statePath = `${directory}/state.json`;
fs.mkdirSync(directory, { recursive: true });
const tracePath = 'resource/acceptance/追踪目录.json';
const trace = JSON.parse(fs.readFileSync(tracePath, 'utf8'));
const initial = {
  schemaVersion: 1,
  baseline: { prd: '1.1', technical: '0.8', plan: '1.0', bdd: '1.0', authorizedOn: '2026-10-10', authorization: '用户要求：根据resource中的实施计划和验收计划开始执行开发' },
  remote: { url: 'https://github.com/cxDlogver/android-plan-checkin', visibility: 'public', created: true, syncedCommit: null },
  tasks: trace.tasks.map(task => ({ id: task.id, title: task.title, phase: task.phase, status: 'NOT_STARTED', startedAt: null, completedAt: null, workDone: [], evidence: [], blockedReason: null })),
  commands: {},
  acceptance: {},
  reusedEvidence: [
    { gate: 'G0', scope: '文档评审核查；不代替应用验收', path: 'resource/review/实施与BDD文档检查结果.json' },
    { gate: 'G1', scope: 'API29/36系统设置控制链路；不代替原生模块或产品验收', path: 'resource/review/android-ai-environment/continuation/就绪复核结果.json' },
  ],
  next: 'IP01实际安装、Expo检查、类型检查、Android bundle和冻结重装；通过后执行IP02。',
};
function read() { return fs.existsSync(statePath) ? JSON.parse(fs.readFileSync(statePath,'utf8')) : initial; }
function save(state) {
  state.updatedAt = new Date().toISOString();
  const temp = `${statePath}.tmp`;
  fs.writeFileSync(temp, JSON.stringify(state, null, 2)+'\n');
  fs.renameSync(temp, statePath);
  const lines = [ '# 开发进度与证据', '', `更新：${new Date(state.updatedAt).toLocaleString('zh-CN', {timeZone:'Asia/Shanghai'})}（Asia/Shanghai）`, '', `公开仓库：[cxDlogver/android-plan-checkin](${state.remote.url})`, '', '执行基线：PRD/UI 1.1、技术 0.8、实施/BDD 1.0；用户于2026-10-10授权开始执行。', '', '任务 DONE 必须满足其退出验收范围；代码或文件存在不代表 PASS。已通过且输入与证据摘要未变的检查自动复用；输入改变后仅重跑受影响检查。失败报告保留，新执行记录关联前次失败。', '', '| 实施项 | 状态 | 已完成实现项 | 证据 / 阻碍 |', '| --- | --- | --- | --- |' ];
  for (const task of state.tasks) lines.push(`| ${task.id} ${task.title} | ${task.status}${task.implementationStatus==='CODE_WRITTEN'?'；代码已实现':''} | ${task.workDone.join('、') || '—'} | ${task.evidence.map(p=>`[报告](${path.relative(directory,p).replaceAll('\\','/')})`).join(' / ') || task.blockedReason || '—'} |`);
  lines.push('', '## 当前执行记录', '', '| 检查 | 状态 | 输入摘要 | 记录 |', '| --- | --- | --- | --- |');
  for (const [id, command] of Object.entries(state.commands)) lines.push(`| ${id} | ${command.status} | ${(command.inputSha256||'').slice(0,12)} | ${command.record ? `[证据](${path.relative(directory,command.record).replaceAll('\\','/')})` : '执行中'} |`);
  lines.push('', '## 已复用的历史证据', '', ...state.reusedEvidence.map(item=>`- ${item.gate}：${item.scope}。[原报告](${path.relative(directory,item.path).replaceAll('\\','/')})`), '', '## 下一步', '', state.next, '', '产品场景未执行前保持 NOT_RUN；后续原生测试、八组合、正式签名、离线、性能与升级均独立留证。', '');
  fs.writeFileSync(`${directory}/开发进度.md`,lines.join('\n'));
  for (const task of trace.tasks) { const actual = state.tasks.find(t=>t.id===task.id); task.status=actual.status; task.execution={startedAt:actual.startedAt,completedAt:actual.completedAt,evidence:actual.evidence,blockedReason:actual.blockedReason}; }
  trace.status='EXECUTION_BASELINE';
  trace.executionProgress='../../resource/progress/开发进度.md';
  fs.writeFileSync(tracePath,JSON.stringify(trace,null,2)+'\n');
  let plan = fs.readFileSync('resource/实施计划-checklist-计划打卡-Android-v1.md','utf8');
  plan=plan.replace(/> 版本1\.0 评审稿；[^\n]+/, '> 版本1.0 执行基线；用户于2026-10-10授权按实施与验收计划开始开发。依据PRD/UI 1.1及技术0.8。[实时进度与证据](progress/开发进度.md)。');
  plan=plan.replace(/仅G0文档与G1控制环境已有独立证据；[^\n]+/, 'G0文档与G1控制环境的已有证据复用，P1–P4按依赖拓扑执行；当前状态见实时进度。任务DONE仅在退出验收范围和证据齐全后记录。');
  for(const task of state.tasks) {
    plan=plan.replace(new RegExp(`- \\[[ x]\\] (\\[${task.id}｜[^\\n]+?) — ${task.phase}，(?:NOT_STARTED|IN_PROGRESS|BLOCKED|DONE)`),`- [${task.status==='DONE'?'x':' '}] $1 — ${task.phase}，${task.status}`);
    const marker=`### ${task.id}｜`;
    const first=plan.indexOf(marker), next=plan.indexOf('\n### IP',first+marker.length);
    if(first>=0) { const end=next<0?plan.length:next; let section=plan.slice(first,end); section=section.replace(/阶段：(P[1-4])；状态：(NOT_STARTED|IN_PROGRESS|BLOCKED|DONE)/,`阶段：$1；状态：${task.status}`); for(const check of task.workDone) section=section.replace(`- [ ] ${task.id}.${check} —`,`- [x] ${task.id}.${check} —`); section=section.replace('执行记录：负责人待填写；开始/完成时间待填写；源码/报告/阻碍链接待填写。',`执行记录：负责人Codex；开始${task.startedAt||'待开始'}；完成${task.completedAt||'未完成'}；[实时进度及证据](progress/开发进度.md)。`); plan=plan.slice(0,first)+section+plan.slice(end); }
  }
  plan=plan.replace('- [ ] PLAN-REVIEW — 用户确认本实施编排与BDD验收共同理解，文档1.0转为执行基线。','- [x] PLAN-REVIEW — 2026-10-10用户授权根据本实施与BDD计划开始执行，文档1.0转为执行基线。');
  fs.writeFileSync('resource/实施计划-checklist-计划打卡-Android-v1.md',plan);
}
function update(mutator) { const state=read(); mutator(state); save(state); return state; }
module.exports={read,save,update};
if(require.main===module){save(read());console.log('进度已写入 resource/progress/开发进度.md');}
