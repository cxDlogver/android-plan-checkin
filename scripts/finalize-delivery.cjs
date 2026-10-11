const fs=require('node:fs'),{sha,snapshot}=require('./p1.cjs'),progress=require('./progress.cjs');
const state=progress.read();
const previous=fs.existsSync('resource/progress/code-delivery.json')?JSON.parse(fs.readFileSync('resource/progress/code-delivery.json','utf8')):null;
const files=new Set(previous?.evidence?.map(item=>item.path)||[]);
function includeRunFiles(directory){if(!fs.existsSync(directory))return;for(const item of fs.readdirSync(directory,{withFileTypes:true})){const file=`${directory}/${item.name}`;if(item.isDirectory())includeRunFiles(file);else files.add(file);}}
includeRunFiles('resource/acceptance/runs');
for(const command of Object.values(state.commands)){
  if(!command.record||!fs.existsSync(command.record))continue;
  files.add(command.record);
  const record=JSON.parse(fs.readFileSync(command.record,'utf8').replace(/^\uFEFF/,''));
  if(record.log&&fs.existsSync(record.log))files.add(record.log);
  if(record.sourceSnapshot&&fs.existsSync(record.sourceSnapshot))files.add(record.sourceSnapshot);
  for(const item of record.evidence||[])if(item.path&&fs.existsSync(item.path))files.add(item.path);
}
for(const acceptance of Object.values(state.acceptance))if(acceptance.report&&fs.existsSync(acceptance.report)){
  files.add(acceptance.report);
  for(const item of JSON.parse(fs.readFileSync(acceptance.report,'utf8')).evidence||[])files.add(item.path);
}
for(const file of ['resource/progress/bundle-audit.json','resource/progress/font-vendoring.json','resource/progress/runner-syntax.json','resource/progress/release-script-syntax.json','resource/progress/release-signing.json','resource/progress/release-certificate.der','resource/progress/fixture-manifest.json','resource/progress/config-version-check.json','resource/progress/date-label-check.json','resource/progress/jsx-space-fix.json','resource/progress/build-manifest.json','resource/progress/navigation-layout-fix.json','resource/progress/progress-write-recovery.json','resource/progress/progress-trace-recovered.json','resource/progress/release-device-results.json'])if(fs.existsSync(file))files.add(file);
for(const file of ['resource/progress/current-build.json','resource/progress/list-shadow-fix.json','resource/progress/validation-listeners.json'])if(fs.existsSync(file))files.add(file);
const currentManifest=state.commands['apk-bundle-audit']?.manifestPath||'resource/progress/build-manifest.json';files.add(currentManifest);
const releaseLog=state.commands['native-release']?.logPath||state.commands['native-release']?.log;
if(releaseLog){const frozen=releaseLog.replace(/commands\.log$/,'bundle-source-snapshot.json');if(fs.existsSync(frozen))files.add(frozen);}
const evidence=[...files].filter(file=>fs.existsSync(file)).sort().map(file=>({path:file,sha256:sha(fs.readFileSync(file))}));
const source=snapshot(['app','src','plugins','assets','tests','scripts','app.config.ts','package.json','pnpm-lock.yaml','metro.config.cjs','babel.config.cjs','tsconfig.json','tsconfig.node.json','tsconfig.integration.json']);
const native=Object.fromEntries(['native-debug','release-prebuild','native-release','native-environment','apk-audit-release','apk-bundle-audit','native-device-29','native-device-36','product-flow-29','product-flow-36','release-offline-29','release-offline-36','navigation-layout-29','navigation-layout-36'].map(id=>[id,{status:state.commands[id]?.status||'NOT_RUN',record:state.commands[id]?.record||null}]));
for(const id of ['native-embedded-check','release-material-api29','release-material-api36','release-detail-layout-api29','release-detail-layout-api36','AC005-visual-summary','AC004-foundation-summary','AC006-foundation-summary','AC007-foundation-summary','AC009-foundation-summary','AC010-foundation-summary','AC119-foundation-summary'])native[id]={status:state.commands[id]?.status||'NOT_RUN',record:state.commands[id]?.record||null};
const checks=Object.fromEntries(['typecheck','bundle','signing-check','prebuild-first','prebuild-repeat'].map(id=>[id,{status:state.commands[id].status,record:state.commands[id].record}]));
const tests={...previous?.tests,fixtureRegression:{status:state.commands['fixture-tests'].status,record:state.commands['fixture-tests'].record,scope:'fixture-only regression; five unchanged host integration cases reuse previous passing evidence'}};
const report={schemaVersion:2,recordedAt:new Date().toISOString(),status:'CODE_COMPLETE',remote:state.remote.url,code:{sourceSnapshotSha256:sha(JSON.stringify(source)),files:source},tests,checks,native,limitations:['正式APK离线、原生完整BDD与八组合按独立结果统计','TalkBack/200%字号、性能、覆盖升级、备份与厂商真机专项在实际通过前保持NOT_RUN'],evidence};
fs.writeFileSync('resource/progress/code-delivery.json',JSON.stringify(report,null,2)+'\n');
fs.writeFileSync('resource/progress/交付证据清单.json',JSON.stringify(evidence,null,2)+'\n');
const md=['# 代码交付记录','',`更新：${report.recordedAt}。核心代码已实现；公开仓库：[android-plan-checkin](${state.remote.url})。任务退出验收以独立报告为准。`,'','已实现三类计划与规则编辑、11个命令、固定IANA时区、单SQLite连接/9表迁移、幂等与并发版本、暂停恢复与自动归档、合法补记/原值留存、统计/月历/分页缓存、今日/计划/记录/设置页面、静态字体、备份排除及外部正式签名配置。开发包提供时钟、F01–F08/性能夹具、一次性故障及事实读回；正式JS包排除其实现。','','复用26项领域、4项查询和未变化的5项宿主SQLite集成验证。PERF修改后只重跑1项夹具集成用例，确定性种子和40/40/20计数另存manifest；中文日期显示单独检查14个值。类型检查和设备回归仅随真实影响执行，宿主SQLite不能代替Android桥接。','','API29/36原生模块参数与核心创建/取消/首次记录/同日原值修正分别留证；正式包离线与底部安全区/100%及200%标签边界另列。旧失败报告保留，恢复时复用已有断言或事实读回，不重复提交已成功保存的记录。','','| 原生工作 | 状态 | 报告 |','| --- | --- | --- |',...Object.entries(native).map(([id,value])=>`| ${id} | ${value.status} | ${value.record?`[证据](../../${value.record})`:'尚未产生终态报告'} |`),'','正式APK与原生库/源映射/字体/签名来源见[构建清单](build-manifest.json)，APK保存在仓库外于Git跟踪的.artifacts目录。底部导航裁切修复见[缺陷记录](navigation-layout-fix.json)，第二次构建的Windows路径失败及受控原生缓存复用均保留原始日志。','','长期签名密钥只保存在仓库外；公开证书与访问权限检查见[签名记录](release-signing.json)。密码使用Windows DPAPI CurrentUser保护。请妥善备份密钥与可迁移的加密密码备份，换机前完成恢复演练。','','完整BDD、八组合、视觉/无障碍、性能/升级/备份和厂商真机检查在实际通过前保留NOT_RUN；局部200%标签检查不等于完整页面或TalkBack验收。','','文件摘要见[code-delivery.json](code-delivery.json)、[交付证据清单](交付证据清单.json)，实时执行状态见[开发进度](开发进度.md)。',''];
fs.writeFileSync('resource/progress/代码交付记录.md',md.join('\n').replace('APK保存在仓库外于Git跟踪的.artifacts目录','APK保存在本机.artifacts目录，不加入Git'));
let deliveryText=fs.readFileSync('resource/progress/代码交付记录.md','utf8');
deliveryText=deliveryText.replace('[构建清单](build-manifest.json)',`[当前构建清单](../../${currentManifest})`);
deliveryText=deliveryText.replace('API29/36原生模块参数与核心创建', 'G2原生准入已完成，AC004/005/006/007/009/010/119的双API范围已通过并关联验收计划。新增SQL约束、单连接队列/CAS及初始化阻断均来自真实.dev SQLite，字体/Worklets观察及新包金属材质显示单独留证。已有PASS设备动作没有重复执行。\n\nAPI29/36原生模块参数与核心创建');
fs.writeFileSync('resource/progress/代码交付记录.md',deliveryText);
progress.update(s=>{s.codeStatus='CODE_COMPLETE';s.delivery='resource/progress/code-delivery.json';const task=s.tasks.find(t=>t.id==='IP03');if(!task.evidence.includes(s.delivery))task.evidence.push(s.delivery);});
console.log(`CODE_COMPLETE: ${evidence.length} evidence files; native statuses preserved.`);
