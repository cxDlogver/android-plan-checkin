const fs=require('node:fs'),path=require('node:path'),progress=require('./progress.cjs');
function link(caseId,report,configurations,description){
  progress.update(state=>{state.acceptance[caseId]={status:'PASS',report,configurations};});
  for(const file of ['resource/BDD验收-checklist-计划打卡-Android-v1.md',...fs.readdirSync('resource/acceptance/scenarios').map(name=>`resource/acceptance/scenarios/${name}`)]){
    const text=fs.readFileSync(file,'utf8'),start=text.indexOf(`### ${caseId}｜`);if(start<0)continue;
    const next=text.indexOf('\n### AC',start+1),end=next<0?text.length:next;
    const target=path.relative(path.dirname(file),report).replaceAll('\\','/');
    const section=text.slice(start,end)
      .replace(`- [ ] ${caseId} — 场景/全部参数/配置完成（当前NOT_RUN）。`,`- [x] ${caseId} — 两API本项范围PASS，[汇总报告](${target})。`)
      .replace(new RegExp(`- \\[ \\] (${caseId}\\.(?:A|E)\\d+) —`,'g'),'- [x] $1 —')
      .replace(new RegExp(`- \\[ \\] (${caseId}/[^ —]+) — ([^\\n]+)；NOT_RUN`,'g'),'- [x] $1 — $2；两API本项范围PASS')
      .replace('实际结果：待执行；执行报告：待填写；失败/阻断原因：待填写；缺陷及回归：待填写。',`实际结果：两API本项范围PASS；[汇总报告](${target})。${description}`);
    fs.writeFileSync(file,text.slice(0,start)+section+text.slice(end));
  }
}
module.exports={link};
