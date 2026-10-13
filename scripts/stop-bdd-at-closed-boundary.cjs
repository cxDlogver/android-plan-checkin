const fs=require('node:fs'),{sha}=require('./p1.cjs');
const identity=JSON.parse(fs.readFileSync('.cache/bdd-reload-identity.json','utf8').replace(/^\uFEFF/,'')),start=Date.now(),pid=identity.childPid;
const timer=setInterval(()=>{try{
 const state=JSON.parse(fs.readFileSync('resource/progress/state.json','utf8')),active=Object.entries(state.commands).filter(([key,c])=>/-M7$/.test(key)&&c.status==='IN_PROGRESS'),closed=Object.entries(state.commands).filter(([key,c])=>/-M7$/.test(key)&&c.record&&['PASS','FAIL'].includes(c.status)).map(([key,c])=>({key,record:c.record,result:JSON.parse(fs.readFileSync(c.record))})).sort((a,b)=>b.result.endedAt.localeCompare(a.result.endedAt))[0];
 if(!active.length&&closed&&Date.parse(closed.result.endedAt)>=start){
  if(!closed.result.evidence.every(e=>fs.existsSync(e.path)&&sha(fs.readFileSync(e.path))===e.sha256))throw new Error('Last closed evidence changed');
  process.kill(pid);clearInterval(timer);const report={...identity,stoppedAt:new Date().toISOString(),lastClosed:{key:closed.key,record:closed.record,sha256:sha(fs.readFileSync(closed.record))},activeCasesAtStop:[],scope:'Only the owned orchestrator was stopped earlier. Its M7 child was stopped after a complete closed scenario, before any next business operation. Existing accepted When evidence is retained. Resume with current corrected harness.'};fs.writeFileSync('resource/progress/API36验收脚本重载.json',JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report));
 }
 if(Date.now()-start>600000)throw new Error('No closed boundary observed; child left running');
}catch(e){if(/Unexpected end|Expected.*JSON|ENOENT/.test(e.message))return;clearInterval(timer);console.error(e.message);process.exitCode=1;}},20);
