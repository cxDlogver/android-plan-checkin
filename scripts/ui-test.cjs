#!/usr/bin/env node
'use strict';
const fs=require('node:fs'),path=require('node:path'),os=require('node:os'),crypto=require('node:crypto'),{spawnSync}=require('node:child_process');
const root=path.resolve(__dirname,'..'),args=process.argv.slice(2),mode=args.shift(),directory=path.resolve(process.env.UI_EVIDENCE_DIR||'plan/code-execution/evidence/'+new Date().toISOString().replace(/[:.]/g,'-'));
if(!directory.startsWith(root+path.sep))throw Error('Evidence directory must stay in the workspace');
fs.mkdirSync(directory,{recursive:true});const startedAt=new Date().toISOString();
const plan=JSON.parse(fs.readFileSync(path.join(root,'plan/task-planning/task-plan.json'),'utf8')),taskIds=(process.env.UI_TASK_IDS||plan.tasks.map(t=>t.id).join(',')).split(','),taskMap=new Map(plan.tasks.map(t=>[t.id,t]));
function declaredFiles(id,seen=new Set()){if(seen.has(id))return [];seen.add(id);const t=taskMap.get(id);if(!t)throw Error('Unknown task '+id);return [...t.files.map(f=>path.resolve(root,'plan/task-planning',f.path)),...t.dependsOn.flatMap(dep=>declaredFiles(dep,seen))];}
const sources=[...new Set(taskIds.flatMap(id=>declaredFiles(id)).concat([__filename,path.join(root,'pnpm-lock.yaml'),path.join(root,'tsconfig.json')]))];
const fontDirectory=path.join(root,'assets/fonts/generated');if(fs.existsSync(fontDirectory)){sources.push(...fs.readdirSync(fontDirectory).map(name=>path.join(fontDirectory,name)),path.join(root,'plan/code-execution/scripts/font-instances.py'),path.join(root,'plan/code-execution/scripts/compile-ui.cjs'),path.join(root,'plan/code-execution/scripts/metro-native.cjs'));}
const acceptanceDirectory=path.join(root,'plan/code-execution/scripts');sources.push(...fs.readdirSync(acceptanceDirectory).filter(name=>/\.(?:cjs|py)$/.test(name)).map(name=>path.join(acceptanceDirectory,name)));
const files=[...new Set(sources)].map(file=>({path:path.relative(root,file).replaceAll('\\','/'),sha256:crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex')}));
const scriptFile=taskIds.at(-1)==='P01'?__filename:path.join(acceptanceDirectory,'accept-'+taskIds.at(-1).toLowerCase()+'.cjs');
const script={path:path.relative(root,scriptFile).replaceAll('\\','/'),sha256:crypto.createHash('sha256').update(fs.readFileSync(scriptFile)).digest('hex')},authoredAt=fs.statSync(scriptFile).mtime.toISOString();
const bundledPython=path.join(os.homedir(),'.cache/codex-runtimes/codex-primary-runtime/dependencies/python',process.platform==='win32'?'python.exe':'bin/python3');
const python=process.env.CODE_EXECUTION_PYTHON||(fs.existsSync(bundledPython)?bundledPython:'python');
const executionDirectory=path.join(root,'plan/code-execution'),batchId=path.basename(directory);
if(!/^[A-Za-z0-9_.-]{1,160}$/.test(batchId))throw Error('Evidence directory needs a safe batch name');
const pending=fs.readdirSync(executionDirectory).filter(name=>/^execution\.batch\..*\.pending\.json$/.test(name));
if(pending.length)throw Error('Resolve unclosed acceptance batches before launching another: '+pending.join(', '));
fs.writeFileSync(path.join(executionDirectory,'execution.batch.'+batchId+'.pending.json'),JSON.stringify({runId:batchId,taskIds,command:process.argv,evidencePath:path.relative(root,directory).replaceAll('\\','/'),startedAt},null,2)+'\n',{flag:'wx'});
function compile(){const result=spawnSync(process.execPath,[require.resolve('typescript/bin/tsc'),'-p','tsconfig.ui-tests.json'],{cwd:root,encoding:'utf8',windowsHide:true});fs.writeFileSync(path.join(directory,'compile.txt'),result.stdout+result.stderr);if(result.status!==0)throw Error('UI test compilation failed: '+result.stdout+result.stderr);}
process.env.UI_EVIDENCE_DIR=directory;
(async()=>{
 if(taskIds.some(id=>id!=='P01')){compile();await require('../plan/code-execution/scripts/accept-task.cjs')({root,directory,mode,args,taskIds});return;}

 if(mode==='unit'){
  const types=spawnSync(process.execPath,[require.resolve('typescript/bin/tsc'),'--noEmit'],{cwd:root,encoding:'utf8',windowsHide:true});fs.writeFileSync(path.join(directory,'typecheck.txt'),types.stdout+types.stderr);fs.writeFileSync(path.join(directory,'typecheck-assertions.json'),JSON.stringify({assertions:[{target:'task:P01:0',label:'Application typecheck',expected:0,actual:types.status,verdict:types.status===0?'passed':'failed'}]},null,2));if(types.status!==0)throw Error('Application typecheck failed: '+types.stdout+types.stderr);
  compile();const file=path.join(root,'tests/ui/harness.test.cjs');if(!fs.existsSync(file))throw Error('Acceptance assertions are not implemented yet');
  const run=spawnSync(process.execPath,['--test',file],{cwd:root,env:{...process.env,UI_EVIDENCE_DIR:directory},encoding:'utf8',windowsHide:true});fs.writeFileSync(path.join(directory,'unit.txt'),run.stdout+run.stderr);process.stdout.write(run.stdout+run.stderr);if(run.status!==0)process.exitCode=1;return;
 }
 if(mode==='integration'&&args.includes('--smoke')){
  const {NativeAdapter}=require('../tests/ui/native-adapter.cjs'),adapter=new NativeAdapter(directory);try{const identity=await adapter.open();fs.writeFileSync(path.join(directory,'identity.json'),JSON.stringify(identity,null,2));const actual=await adapter.controlsSmoke();process.env.UI_EXPORT_ASSERTIONS='1';require('../tests/ui/harness.test.cjs').assertNativeSmoke(actual);console.log('Real native controls smoke passed');}finally{await adapter.close();}return;
 }
 throw Error('Acceptance mode is not implemented: '+mode+' '+args.join(' '));
})().catch(error=>{fs.writeFileSync(path.join(directory,'failure.txt'),error.stack||error.message);console.error(error.message);process.exitCode=1;}).finally(()=>{
 fs.writeFileSync(path.join(directory,'run.json'),JSON.stringify({command:process.argv,cwd:root,startedAt,finishedAt:new Date().toISOString(),exitCode:process.exitCode||0,taskIds,files,script,authoredAt},null,2)+'\n');
 const localOnly=args.includes('--local-task')||args.includes('--local-only');
 const closed=spawnSync(process.execPath,[path.join(acceptanceDirectory,'register-results.cjs'),path.relative(root,directory),path.basename(directory),python,...(localOnly?['--local-only']:[])],{cwd:root,stdio:'inherit',windowsHide:true});
 if(closed.error){console.error('Batch status registration failed: '+closed.error.message);process.exitCode=1;}
 else if(closed.status!==0){console.error('Batch did not close; keep evidence and resolve registration before continuing.');process.exitCode=1;}
});
