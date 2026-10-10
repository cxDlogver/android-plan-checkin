const fs=require('node:fs'),{spawnSync}=require('node:child_process'),path=require('node:path');
const {env,javaRoot}=require('./task-env.cjs');
const result=spawnSync('powershell.exe',['-NoProfile','-ExecutionPolicy','Bypass','-File','scripts/host-memory.ps1'],{encoding:'utf8',windowsHide:true});
if(result.status!==0)throw new Error(result.stderr);
const diagnostic=JSON.parse(result.stdout.replace(/^\uFEFF/,''));
console.log(JSON.stringify({...diagnostic,processes:diagnostic.processes.map(p=>({...p,commandLine:p.commandLine.includes('GradleDaemon')?'owned Gradle daemon':'owned Gradle client'}))},null,2));
const daemon=diagnostic.processes.find(p=>p.commandLine.includes('GradleDaemon'));
if(daemon){const dump=spawnSync(path.join(javaRoot,'bin/jcmd.exe'),[String(daemon.processId),'Thread.print'],{env,encoding:'utf8',windowsHide:true,timeout:20000,maxBuffer:4*1024*1024});fs.writeFileSync('.cache/native-thread-dump.log',(dump.stdout||'')+(dump.stderr||''));console.log(dump.stdout.split(/\r?\n/).filter(line=>/Download|Socket|SSL|Cache|WorkerExecutor|Execution|BuildOperation|^["]Daemon|^["]included/i.test(line)).slice(0,45).join('\n'));}
