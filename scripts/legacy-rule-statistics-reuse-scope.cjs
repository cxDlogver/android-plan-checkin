const fs=require('node:fs'),{execFileSync}=require('node:child_process'),{sha}=require('./p1.cjs');
module.exports=function(item){
 const original=JSON.parse(fs.readFileSync(item.r.evidence.find(e=>e.path.endsWith('source-snapshot.json')).path)),proof=[];
 for(const file of ['src/domain/rules.ts','src/domain/model.ts','src/domain/date.ts']){
  const expected=original.find(f=>f.path===file);if(!expected)throw new Error('Original rule snapshot omitted '+file);
  const current=fs.readFileSync(file,'utf8');let old=current,origin='Complete source identical';
  if(sha(current)!==expected.sha256){old=execFileSync('git',['show','93110d6:'+file],{encoding:'utf8',windowsHide:true});origin='Git 93110d6 complete original source SHA verified';}
  if(sha(old)!==expected.sha256)throw new Error('Original rule source not recovered '+file);
  const scoped=s=>file==='src/domain/rules.ts'?s.replace('    if(plan.created_on>snapshot.today)continue;\n',''):file==='src/domain/date.ts'?s.slice(0,s.indexOf('export const formatDate=')<0?undefined:s.indexOf('export const formatDate=')):s;
  if(sha(scoped(old))!==sha(scoped(current)))throw new Error('Independent pure rule branch changed '+file);
  proof.push({file,origin,originalSha256:expected.sha256,currentSha256:sha(current),relevantOriginalSha256:sha(scoped(old)),relevantCurrentSha256:sha(scoped(current))});
 }
 return {proof,scope:'Reuse only the independently successful pure permission, lifecycle interval/status, calendar marker and fixed/weekly statistics observations from the original Node log. Rules differ solely in the later Today future-created guard; date display formatting is excluded from arithmetic. The original full commands.ts body is unavailable and is not claimed unchanged. Actual current command/transaction behavior is separately proven by each retained API 29 and API 36 native manifest. No accepted Node test or native business command is executed again.'};
};
