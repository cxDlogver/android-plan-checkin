const fs=require('node:fs'),path=require('node:path');
const state=require('./progress.cjs').read();
for(const file of ['resource/acceptance/scenarios/01-工程准入.md','resource/BDD验收-checklist-计划打卡-Android-v1.md']){
  let text=fs.readFileSync(file,'utf8');
  text=text.replace(/> 版本1\.0评审稿；全体NOT_RUN。[^\n]*/, '> 版本1.0执行基线；各实例状态和报告独立记录，勾选需满足全部参数、范围、断言与证据。');
  for(const id of ['AC001','AC117','AC002','AC003']){
    const item=state.acceptance[id];if(item?.status!=='PASS')continue;
    const report=path.relative(path.dirname(file),item.report).replaceAll('\\','/');
    text=text.replace(new RegExp(`- \\[[ x]\\] ${id} — [^\\n]*`),`- [x] ${id} — 本项Windows范围PASS，[执行报告](${report})。`);
    const start=text.indexOf(`### ${id}｜`);if(start<0)continue;
    const next=text.indexOf('\n### AC',start+10),end=next<0?text.length:next;
    const section=text.slice(start,end).replace(/实际结果：[^\n]*/,`实际结果：PASS（Windows范围）；执行报告：[${id}](${report})；失败/阻断原因：无；缺陷及回归：详见报告关联记录。`).replace(new RegExp(`- \\[ \\] ${id}\\.E2 —`),`- [x] ${id}.E2 —`);
    text=text.slice(0,start)+section+text.slice(end);
  }
  fs.writeFileSync(file,text);
}
console.log('Updated existing PASS report links; no acceptance re-executed.');
