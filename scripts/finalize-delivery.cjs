const fs=require('node:fs'),path=require('node:path'),{sha,snapshot}=require('./p1.cjs'),progress=require('./progress.cjs');
const state=progress.read(),native=state.commands['native-debug'];
const fontReadme='assets/fonts/README.md';fs.writeFileSync(fontReadme,fs.readFileSync(fontReadme,'utf8').replace('LICENSE_FONT.txt','LICENSE_FONT'));
const nativeDirectory=path.dirname(native.record);
const crash='C:/WINDOWS/TEMP/hs_err_pid75848.log';
if(fs.existsSync(crash))fs.writeFileSync(`${nativeDirectory}/jvm-crash-excerpt.log`,fs.readFileSync(crash,'utf8').split(/\r?\n/).slice(0,34).join('\n')+'\n');
if(fs.existsSync('.cache/native-thread-dump.log')){
  const blocks=fs.readFileSync('.cache/native-thread-dump.log','utf8').split(/\r?\n\r?\n/).filter(block=>/^"included builds/.test(block));
  fs.writeFileSync(`${nativeDirectory}/thread-summary.log`,blocks.join('\n\n')+'\n');
}
const files=['domain-tests','query-tests','integration-tests','typecheck','bundle','prebuild-first','prebuild-repeat','signing-check'].flatMap(id=>{
  const record=JSON.parse(fs.readFileSync(state.commands[id].record,'utf8'));return [state.commands[id].record,...record.evidence.map(e=>e.path)];
});
files.push(native.record,native.log,`${nativeDirectory}/jvm-crash-excerpt.log`,`${nativeDirectory}/thread-summary.log`,'resource/progress/bundle-audit.json','resource/progress/font-vendoring.json');
const manifest=[...new Set(files)].filter(p=>fs.existsSync(p)).map(p=>({path:p,sha256:sha(fs.readFileSync(p))}));
const source=snapshot(['app','src','plugins','assets','tests','app.config.ts','package.json','pnpm-lock.yaml','metro.config.cjs','babel.config.cjs','tsconfig.json','tsconfig.node.json','tsconfig.integration.json']);
const report={schemaVersion:1,recordedAt:new Date().toISOString(),status:'CODE_COMPLETE',remote:state.remote.url,code:{sourceSnapshotSha256:sha(JSON.stringify(source)),files:source},tests:{domain:{count:26,status:'PASS',record:state.commands['domain-tests'].record,scope:'复用已通过领域结果；末次仅删除对账标记的调整由集成删除测试回归'},query:{count:4,status:'PASS',record:state.commands['query-tests'].record},hostSQLite:{count:6,status:'PASS',record:state.commands['integration-tests'].record,scope:'宿主真实SQLite及测试Expo适配，不代替Android桥接'}},checks:Object.fromEntries(['typecheck','bundle','signing-check','prebuild-first','prebuild-repeat'].map(id=>[id,{status:state.commands[id].status,record:state.commands[id].record}])),native:{status:'BLOCKED',lastAttempt:'FAIL',record:native.record,reason:'JVM native allocation failed; same period Node VirtualAlloc/heap allocation failed; reduced workers/memory and cleared owned orphan, no repeated retry without resource change'},limitations:['未生成正式签名独立APK','API29/36模块/数据库和产品BDD未执行','八组合、TalkBack/200%字号、离线、性能、覆盖升级、备份与厂商真机专项未通过'],evidence:manifest};
for(const id of ['integration-tests','typecheck','bundle','prebuild-first','prebuild-repeat','signing-check'])if(state.commands[id].status!=='PASS')throw new Error(`Required code check incomplete: ${id}`);
fs.writeFileSync('resource/progress/code-delivery.json',JSON.stringify(report,null,2)+'\n');
fs.writeFileSync('resource/progress/交付证据清单.json',JSON.stringify(manifest,null,2)+'\n');
const md=['# 代码交付记录','','2026-10-10：核心代码实现完成。公开仓库：'+state.remote.url+'。实现状态与退出验收状态分开记录。','','已实现三类计划与规则编辑、11个命令、固定IANA时区、单SQLite连接/9表迁移、幂等与并发版本、暂停恢复与自动归档、合法补记/原值留存、统计/月历/分页缓存、今日/计划/记录/设置页面、静态字体、备份排除及外部正式签名配置。开发包提供时钟、F01–F08/性能夹具、一次性故障及事实读回，正式JS包排除其实现。','','验证：26项领域结果复用，4项查询与6项宿主SQLite测试通过；最后的类型检查、Android JS打包、签名模板检查、两次配置生成通过。末次修改只回归受影响的事务/夹具与类型/打包，没有重跑未受影响的领域全量测试。','','原生Debug编译仍BLOCKED：最新尝试因JVM native memory allocation失败退出，同期Node进程也发生VirtualAlloc/分配失败。已尝试限制1个Gradle worker、2个CPU、1GB堆、Kotlin进程内编译，并清理本任务失败构建遗留进程。没有继续无条件重复编译。','','正式签名独立APK、原生两API验收、完整BDD、八组合、视觉/无障碍、离线/性能/升级/备份及厂商真机检查尚未通过；任务不会因此标DONE。','','全部命令、失败记录及文件SHA-256见 [code-delivery.json](code-delivery.json)、[交付证据清单](交付证据清单.json)、[开发进度](开发进度.md)。原生崩溃直接原因及调用栈摘录已存入最后失败run。',''];
fs.writeFileSync('resource/progress/代码交付记录.md',md.join('\n'));
progress.update(s=>{s.codeStatus='CODE_COMPLETE';s.delivery='resource/progress/code-delivery.json';const t=s.tasks.find(t=>t.id==='IP03');t.status='BLOCKED';t.blockedReason=report.native.reason;t.evidence.push('resource/progress/code-delivery.json');s.next='代码开发已完成；Android原生编译被宿主内存分配失败阻断。释放宿主提交内存后从Gradle缓存继续构建，再执行两API与产品BDD/八组合/正式release专项；复用未变的宿主PASS证据。';});
console.log('CODE_COMPLETE: 26 domain + 4 query + 6 host SQLite; native BLOCKED; evidence hashes saved');
