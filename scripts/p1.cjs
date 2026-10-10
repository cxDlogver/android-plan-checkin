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
  install:{args:[pnpm,'install','--reporter=append-only'],inputs:['package.json','.npmrc','pnpm-workspace.yaml'],outputs:['pnpm-lock.yaml','node_modules/.modules.yaml'],task:'IP01'},
  'frozen-install':{args:[pnpm,'install','--frozen-lockfile','--reporter=append-only'],inputs:baseFiles,outputs:['pnpm-lock.yaml','node_modules/.modules.yaml'],task:'IP01'},
  'expo-check':{args:['node_modules/expo/bin/cli','install','--check'],inputs:baseFiles,outputs:['pnpm-lock.yaml'],task:'IP01'},
  typecheck:{args:['node_modules/typescript/bin/tsc','--noEmit'],inputs:[...baseFiles,...source],outputs:[],task:'IP01'},
  bundle:{args:['node_modules/expo/bin/cli','export','--platform','android','--output-dir','.artifacts/bundle','--max-workers','2'],inputs:[...baseFiles,...source],outputs:['.artifacts/bundle/metadata.json'],task:'IP01'},
  'prebuild-first':{args:['node_modules/expo/bin/cli','prebuild','--platform','android','--no-install'],inputs:[...baseFiles,...configFiles,'plugins'],outputs:[],task:'IP02',environment:{APP_VARIANT:'development'}},
  'prebuild-repeat':{args:['node_modules/expo/bin/cli','prebuild','--platform','android','--no-install'],inputs:[...baseFiles,...configFiles,'plugins'],outputs:[],task:'IP02',environment:{APP_VARIANT:'development'}},
};
async function run(id) {
  const spec=specs[id]; if(!spec)throw new Error(`可选命令：${Object.keys(specs).join(', ')}`);
  const identity={node,pnpm,environment:spec.environment||{},args:spec.args};
  const inputSha256=sha(JSON.stringify({identity,files:snapshot(spec.inputs)}));
  const previous=progress.read().commands[id];
  if(previous?.status==='PASS' && previous.inputSha256===inputSha256 && previous.outputSha256===fingerprint(spec.outputs) && fs.existsSync(previous.record)) {
    const saved=JSON.parse(fs.readFileSync(previous.record,'utf8'));
    if(saved.evidence.every(file=>fs.existsSync(file.path)&&sha(fs.readFileSync(file.path))===file.sha256)) {console.log(`SKIP ${id}: 输入与已通过证据摘要一致；${previous.record}`);return previous;}
  }
  const startedAt=new Date().toISOString();
  const runId=`${startedAt.replace(/[:.]/g,'-')}-${inputSha256.slice(0,10)}`;
  const directory=`resource/acceptance/runs/${runId}/commands/${id}`;
  fs.mkdirSync(directory,{recursive:true});
  const logPath=`${directory}/commands.log`;
  const stream=fs.createWriteStream(logPath);
  stream.write(`${startedAt}\n${node} ${spec.args.join(' ')}\n`);
  progress.update(state=> {state.commands[id]={status:'RUNNING',inputSha256,startedAt,record:null};const task=state.tasks.find(t=>t.id===spec.task);task.status='IN_PROGRESS';task.startedAt??=startedAt;task.blockedReason=null;});
  console.log(`RUN ${id}: ${logPath}`);
  const child=spawn(node,spec.args,{env:{...env,...spec.environment},windowsHide:true,stdio:['ignore','pipe','pipe']});
  let tail='';
  for(const output of [child.stdout,child.stderr])output.on('data',chunk=>{stream.write(chunk);tail=(tail+chunk.toString()).slice(-5000);});
  const exitCode=await new Promise(resolve=> {child.once('error',error=>{stream.write(error.stack+'\n');resolve(-1);});child.once('close',code=>resolve(code??-1));});
  const endedAt=new Date().toISOString();
  stream.write(`\n${endedAt} exitCode=${exitCode}\n`);
  await new Promise(resolve=>stream.end(resolve));
  const sourceFiles=snapshot([...source,...baseFiles]);
  fs.writeFileSync(`${directory}/source-snapshot.json`,JSON.stringify(sourceFiles,null,2)+'\n');
  const evidence=[logPath,`${directory}/source-snapshot.json`].map(p=>({profile:'E-BUILD',path:p,sha256:sha(fs.readFileSync(p))}));
  const record=`${directory}/result.json`;
  const result={schemaVersion:1,id,task:spec.task,status:exitCode===0?'PASS':'FAIL',startedAt,endedAt,exitCode,inputSha256,outputSha256:fingerprint(spec.outputs),sourceSnapshotSha256:sha(JSON.stringify(sourceFiles)),lockfileSha256:fs.existsSync('pnpm-lock.yaml')?sha(fs.readFileSync('pnpm-lock.yaml')):null,command:{binary:node,args:spec.args,environment:spec.environment||{}},evidence,regressionOf:previous?.status==='FAIL'?[previous.record]:[]};
  fs.writeFileSync(record,JSON.stringify(result,null,2)+'\n');
  progress.update(state=> {state.commands[id]={...result,record};const task=state.tasks.find(t=>t.id===spec.task);if(!task.evidence.includes(record))task.evidence.push(record);if(exitCode!==0)task.blockedReason=`${id}失败，原始日志：${logPath}`;});
  console.log(`${result.status} ${id}: exitCode=${exitCode} ${record}`);
  if(exitCode!==0){console.log(tail);process.exitCode=1;}
  return result;
}
module.exports={run,snapshot,fingerprint,sha};
if(require.main===module)run(process.argv[2]||'expo-check').catch(error=>{console.error(error);process.exitCode=1;});
