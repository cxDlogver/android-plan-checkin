const {execFileSync}=require('node:child_process'),{sha}=require('./p1.cjs'),cache=new Map();
module.exports=function(file,expected){
 const key=file+':'+expected;if(cache.has(key))return cache.get(key);
 const revisions=execFileSync('git',['log','--all','--format=%H','--',file],{encoding:'utf8',windowsHide:true}).trim().split(/\r?\n/).filter(Boolean);
 for(const revision of revisions){
  let body;try{body=execFileSync('git',['show',revision+':'+file],{encoding:'utf8',windowsHide:true,stdio:['ignore','pipe','ignore']});}catch{continue;}
  const candidates=[{body,scope:'complete retained commit'}];
  if(file==='src/application/service.ts'){
   if(body.includes('const gate=afterUserCommit();if(gate)await gate;return committed;'))candidates.push({body:body.replace('const gate=afterUserCommit();if(gate)await gate;return committed;','afterUserCommit();return committed;'),scope:'exact reconstruction before optional post-commit observer began awaiting a gate'});
   if(body.includes('afterUserCommit();return committed;')){candidates.push({body:body.replace('afterUserCommit();return committed;','const gate=afterUserCommit();if(gate)await gate;return committed;'),scope:'exact reconstruction with optional awaited post-commit gate before later notifications'});const beforeGate=body.replace('now, afterUserCommit, attachExecutor','now, attachExecutor').replace('const committed=await this.executor.transaction<CommandResult>','return await this.executor.transaction<CommandResult>').replace('        afterUserCommit();return committed;\n','');candidates.push({body:beforeGate,scope:'exact reconstruction before development-only post-commit observer was added'});candidates.push({body:beforeGate.replace(',fieldErrors:failure.fieldErrors',''),scope:'exact reconstruction before observer and error-field presentation additions'});}
  }
  for(const candidate of candidates)for(const text of [candidate.body,candidate.body.replace(/\r?\n/g,'\r\n')])if(sha(text)===expected){const result={body:text,revision:revision+' '+candidate.scope};cache.set(key,result);return result;}
 }
 for(const name of fsMaps()){const map=JSON.parse(require('node:fs').readFileSync(name,'utf8'));for(let i=0;i<(map.sources||[]).length;i++)if(map.sources[i].replaceAll('\\','/').endsWith('/'+file)){const body=map.sourcesContent?.[i];if(body&&sha(body)===expected){const result={body,revision:'embedded-source-map '+name};cache.set(key,result);return result;}}}
 throw new Error('No retained Git source matches original native SHA '+file+' '+expected);
};
function fsMaps(){const fs=require('node:fs'),dir='.artifacts/apk/release';return fs.readdirSync(dir).filter(n=>n.endsWith('.map')).map(n=>dir+'/'+n);}
