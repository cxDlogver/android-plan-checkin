'use strict';
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),{spawnSync}=require('node:child_process');
const root=path.resolve(__dirname,'../../..'),relative=process.argv[2],id=process.argv[3],python=process.argv[4],directory=path.resolve(root,relative);if(!/^[A-Za-z0-9_.-]{1,160}$/.test(id||'')||!python||!directory.startsWith(root+path.sep))throw Error('Expected workspace run directory, safe unique run id and Python executable');
const pending=path.join(root,'plan/code-execution','execution.batch.'+id+'.pending.json');
if(!fs.existsSync(pending))fs.writeFileSync(pending,JSON.stringify({runId:id,evidencePath:relative,command:process.argv},null,2)+'\n',{flag:'wx'});
const read=p=>JSON.parse(fs.readFileSync(p)),ref=p=>({path:path.relative(root,p).replaceAll('\\','/'),sha256:crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex')});
const meta=read(path.join(directory,'run.json')),result=read(path.join(directory,'results.json')),context=read(path.join(directory,'context.json')),script=path.join(__dirname,'accept-p08.cjs');
const evidence=items=>items.map(({file,form,description})=>({...ref(path.resolve(directory,file)),form,description}));
for(const visit of result.visits)for(const check of visit.checks)check.evidence=evidence(check.evidence);for(const task of result.taskResults)task.evidence=evidence(task.evidence);
const file=path.join(root,'plan/code-execution/execution.json'),gate=path.join(root,'plan/skill/code-execution/scripts/execution.py'),candidate=path.join(directory,'registration-run.json');
const run={id,taskIds:meta.taskIds,script:meta.script||ref(script),authoredAt:meta.authoredAt||fs.statSync(script).mtime.toISOString(),command:meta.command,cwd:'.',startedAt:meta.startedAt,finishedAt:meta.finishedAt,exitCode:meta.exitCode,environment:context.environment,files:meta.files,context:ref(path.join(directory,'context.json')),visits:result.visits,taskResults:result.taskResults};
fs.writeFileSync(candidate,JSON.stringify(run,null,2)+'\n');
const child=spawnSync(python,['-B',gate,'submit',file,'--workspace',root,'--run',path.relative(root,candidate),...(process.argv.includes('--local-only')?['--local-only']:[])],{cwd:root,encoding:'utf8',windowsHide:true,maxBuffer:16*1024*1024});
if(child.error)throw child.error;
let closure;try{closure=JSON.parse(child.stdout);}catch{throw Error(child.stdout+'\n'+child.stderr);}
// An interrupted or rejected submission retains its input for explicit recovery.
if(closure.recorded&&closure.checked)fs.rmSync(candidate,{force:true});
console.log(JSON.stringify(closure));
process.exitCode=child.status===0?0:1;
