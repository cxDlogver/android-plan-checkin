const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { spawn } = require('node:child_process');
const { node, env, toolRoot } = require('./task-env.cjs');
const progress = require('./progress.cjs');
const sha = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
const baseFiles=['package.json','pnpm-lock.yaml','.npmrc','pnpm-workspace.yaml'];
const configFiles=['app.config.ts','babel.config.cjs','metro.config.cjs','expo-env.d.ts'];
function filesUnder(file) {
  if(!fs.existsSync(file))return [file];
  if(!fs.statSync(file).isDirectory())return [file];
  return fs.readdirSync(file).sort().flatMap(entry=>filesUnder(path.join(file,entry)));
}
function snapshot(paths) { return paths.flatMap(filesUnder).sort().map(p=>({path:p.replaceAll('\\','/'),sha256:fs.existsSync(p)&&fs.statSync(p).isFile()?sha(fs.readFileSync(p)):null})); }
function fingerprint(paths){return sha(JSON.stringify(snapshot(paths)));}
const pnpm=path.join(toolRoot,'appium/node_modules/pnpm/bin/pnpm.cjs');
const source=['app','src','assets','plugins','tsconfig.json',...configFiles];
const specs={
  install:{args:[pnpm,'install','--no-frozen-lockfile','--reporter=append-only'],inputs:['package.json','.npmrc','pnpm-workspace.yaml'],outputs:['pnpm-lock.yaml','node_modules/.modules.yaml'],task:'IP01'},
  'frozen-install':{args:[pnpm,'install','--frozen-lockfile','--reporter=append-only'],inputs:baseFiles,outputs:['pnpm-lock.yaml','node_modules/.modules.yaml'],task:'IP01'},
  'expo-check':{args:['node_modules/expo/bin/cli','install','--check'],inputs:baseFiles,outputs:['pnpm-lock.yaml'],task:'IP01'},
  typecheck:{args:['node_modules/typescript/bin/tsc','--noEmit'],inputs:[...baseFiles,...source],outputs:[],task:'IP01'},
  'domain-compile':{args:['node_modules/typescript/bin/tsc','-p','tsconfig.node.json'],inputs:[...baseFiles,'tsconfig.node.json','src/domain','src/application/projections.ts','tests/domain'],outputs:['.artifacts/tests/tests/domain/rules.test.js'],task:'IP06'},
  'domain-tests':{args:['--test','.artifacts/tests/tests/domain/rules.test.js'],inputs:['src/domain','tests/domain/rules.test.ts',...baseFiles],outputs:[],task:'IP06'},
  'query-tests':{args:['--test','.artifacts/tests/tests/domain/projections.test.js'],inputs:['src/domain','src/application/projections.ts','tests/domain/projections.test.ts',...baseFiles],outputs:[],task:'IP16'},
  'date-acceptance-tests':{args:['--test','.artifacts/tests/tests/domain/date-acceptance.test.js'],inputs:['src/domain/date.ts','src/application/projections.ts','tests/domain/date-acceptance.test.ts',...baseFiles],outputs:[],task:'IP06'},
  'timezone-domain-tests':{args:['--test','.artifacts/tests/tests/domain/timezone-candidate.test.js'],inputs:['src/domain/date.ts','tests/domain/timezone-candidate.test.ts',...baseFiles],outputs:[],task:'IP06'},
  'validation-acceptance-tests':{args:['--test','.artifacts/tests/tests/domain/bdd-validation.test.js'],inputs:['src/domain/commands.ts','tests/domain/bdd-validation.test.ts',...baseFiles],outputs:[],task:'IP09'},
  'business-rule-acceptance-tests':{args:['--test','.artifacts/tests/tests/domain/bdd-service-rules.test.js'],inputs:['src/domain','tests/domain/bdd-service-rules.test.ts',...baseFiles],outputs:[],task:'IP09'},
  'integration-compile':{args:['node_modules/typescript/bin/tsc','-p','tsconfig.integration.json'],inputs:['tsconfig.integration.json','tsconfig.node.json','src/domain','src/application/service.ts','src/infrastructure/database','src/verification/fixtures.ts','src/verification/runtime-contract.ts','tests/integration',...baseFiles],outputs:['.artifacts/integration/tests/integration/database.test.js'],task:'IP08'},
  'integration-tests':{args:['--require','./tests/integration/register.cjs','--test','.artifacts/integration/tests/integration/database.test.js'],inputs:['src/domain','src/application/service.ts','src/infrastructure/database','src/verification/fixtures.ts','src/verification/runtime-contract.ts','tests/integration',...baseFiles],outputs:[],task:'IP08'},
  'fixture-tests':{args:['--require','./tests/integration/register.cjs','--test','--test-name-pattern=F01–F08','.artifacts/integration/tests/integration/database.test.js'],inputs:['src/verification/fixtures.ts','tests/integration/database.test.ts',...baseFiles],outputs:[],task:'IP05'},
  'migration-tests':{args:['--require','./tests/integration/register.cjs','--test','.artifacts/integration/tests/integration/migrations.test.js'],inputs:['src/infrastructure/database','tests/integration/migrations.test.ts','tests/integration/host-adapter.cjs',...baseFiles],outputs:[],task:'IP07'},
  'migration-success-test':{args:['--require','./tests/integration/register.cjs','--test','--test-name-pattern=commits once','.artifacts/integration/tests/integration/migrations.test.js'],inputs:['src/infrastructure/database','tests/integration/migrations.test.ts','tests/integration/host-adapter.cjs',...baseFiles],outputs:[],task:'IP07'},
  'migration-fk-test':{args:['--require','./tests/integration/register.cjs','--test','--test-name-pattern=deferred foreign key failure','.artifacts/integration/tests/integration/migrations.test.js'],inputs:['src/infrastructure/database','tests/integration/migrations.test.ts','tests/integration/host-adapter.cjs',...baseFiles],outputs:[],task:'IP07'},
  'signing-check':{args:['scripts/signing-check.cjs'],inputs:['scripts/signing-check.cjs','plugins/with-release-signing.cjs'],outputs:[],task:'IP03'},
  bundle:{args:['node_modules/expo/bin/cli','export','--platform','android','--output-dir','.artifacts/bundle','--max-workers','2'],inputs:[...baseFiles,...source],outputs:['.artifacts/bundle/metadata.json'],task:'IP01'},
  'prebuild-first':{args:['node_modules/expo/bin/cli','prebuild','--platform','android','--no-install'],inputs:[...baseFiles,...configFiles,'plugins'],outputs:[],task:'IP02',environment:{APP_VARIANT:'development'}},
  'prebuild-repeat':{args:['node_modules/expo/bin/cli','prebuild','--platform','android','--no-install'],inputs:[...baseFiles,...configFiles,'plugins'],outputs:[],task:'IP02',environment:{APP_VARIANT:'development'}},
};
async function run(id) {
  const spec=specs[id]; if(!spec)throw new Error(`可选命令：${Object.keys(specs).join(', ')}`);
  const identity={node,pnpm,environment:spec.environment||{},args:spec.args};
  const inputSha256=sha(JSON.stringify({identity,files:snapshot(spec.inputs)}));
  const previous=progress.read().commands[id];
  if(previous?.status==='RUNNING') {
    const interruption=`resource/progress/interrupted-${id}-${Date.now()}.json`;
    fs.writeFileSync(interruption,JSON.stringify({...previous,status:'BLOCKED',endedAt:new Date().toISOString(),exitCode:null,reason:'执行会话中断，未收到进程退出状态；不能推断PASS。后续执行复用已下载缓存。'},null,2)+'\n');
    previous.status='BLOCKED'; previous.record=interruption;
  }
  if(previous?.status==='PASS' && previous.inputSha256===inputSha256 && previous.outputSha256===fingerprint(spec.outputs) && fs.existsSync(previous.record)) {
    const saved=JSON.parse(fs.readFileSync(previous.record,'utf8'));
    if(saved.evidence.every(file=>fs.existsSync(file.path)&&sha(fs.readFileSync(file.path))===file.sha256)) {console.log(`SKIP ${id}: 输入与已通过证据摘要一致；${previous.record}`);return previous;}
  }
  const startedAt=new Date().toISOString();
  const lockfileBefore=fs.existsSync('pnpm-lock.yaml')?sha(fs.readFileSync('pnpm-lock.yaml')):null;
  const runId=`${startedAt.replace(/[:.]/g,'-')}-${inputSha256.slice(0,10)}`;
  const directory=`resource/acceptance/runs/${runId}/commands/${id}`;
  fs.mkdirSync(directory,{recursive:true});
  const nativeFiles=['android/app/src/main/AndroidManifest.xml','android/app/src/main/res/xml/backup_rules.xml','android/app/src/main/res/xml/data_extraction_rules.xml','android/gradle.properties','android/app/build.gradle'];
  const beforeNative=id.startsWith('prebuild-')?snapshot(nativeFiles):null;
  const logPath=`${directory}/commands.log`;
  const stream=fs.createWriteStream(logPath);
  stream.write(`${startedAt}\n${node} ${spec.args.join(' ')}\n`);
  progress.update(state=> {state.commands[id]={status:'RUNNING',inputSha256,startedAt,record:null};const task=state.tasks.find(t=>t.id===spec.task);task.status='IN_PROGRESS';task.startedAt??=startedAt;task.blockedReason=null;});
  console.log(`RUN ${id}: ${logPath}`);
  const child=spawn(node,spec.args,{env:{...env,...spec.environment},windowsHide:true,stdio:['ignore','pipe','pipe']});
  progress.update(state=>{state.commands[id].processId=child.pid;state.commands[id].logPath=logPath;});
  let tail='';
  for(const output of [child.stdout,child.stderr])output.on('data',chunk=>{stream.write(chunk);tail=(tail+chunk.toString()).slice(-5000);});
  const exitCode=await new Promise(resolve=> {child.once('error',error=>{stream.write(error.stack+'\n');resolve(-1);});child.once('close',code=>resolve(code??-1));});
  const endedAt=new Date().toISOString();
  stream.write(`\n${endedAt} exitCode=${exitCode}\n`);
  await new Promise(resolve=>stream.end(resolve));
  const sourceFiles=snapshot([...source,...baseFiles]);
  if(beforeNative){fs.writeFileSync(`${directory}/native-before.json`,JSON.stringify(beforeNative,null,2)+'\n');fs.writeFileSync(`${directory}/native-after.json`,JSON.stringify(snapshot(nativeFiles),null,2)+'\n');for(const file of nativeFiles){const target=path.join(directory,'native',file.slice('android/'.length));fs.mkdirSync(path.dirname(target),{recursive:true});fs.copyFileSync(file,target);}}
  fs.writeFileSync(`${directory}/source-snapshot.json`,JSON.stringify(sourceFiles,null,2)+'\n');
  const evidence=[logPath,`${directory}/source-snapshot.json`,...(beforeNative?filesUnder(`${directory}/native`).concat([`${directory}/native-before.json`,`${directory}/native-after.json`]):[])].map(p=>({profile:id.startsWith('domain-')||['query-tests','date-acceptance-tests','timezone-domain-tests','validation-acceptance-tests','business-rule-acceptance-tests'].includes(id)?'E-DOMAIN':'E-BUILD',path:p,sha256:sha(fs.readFileSync(p))}));
  const record=`${directory}/result.json`;
  const result={schemaVersion:1,id,task:spec.task,status:exitCode===0?'PASS':'FAIL',startedAt,endedAt,exitCode,inputSha256,outputSha256:fingerprint(spec.outputs),sourceSnapshotSha256:sha(JSON.stringify(sourceFiles)),lockfileBefore,lockfileSha256:fs.existsSync('pnpm-lock.yaml')?sha(fs.readFileSync('pnpm-lock.yaml')):null,nodeVersion:process.version,command:{binary:node,args:spec.args,environment:spec.environment||{}},evidence,regressionOf:previous?.status==='FAIL'?[previous.record]:[]};
  fs.writeFileSync(record,JSON.stringify(result,null,2)+'\n');
  progress.update(state=> {state.commands[id]={...result,record};const task=state.tasks.find(t=>t.id===spec.task);if(!task.evidence.includes(record))task.evidence.push(record);if(exitCode!==0)task.blockedReason=`${id}失败，原始日志：${logPath}`;});
  console.log(`${result.status} ${id}: exitCode=${exitCode} ${record}`);
  if(exitCode!==0){console.log(tail);process.exitCode=1;}
  return result;
}
module.exports={run,snapshot,fingerprint,sha};
if(require.main===module)run(process.argv[2]||'expo-check').catch(error=>{console.error(error);process.exitCode=1;});
