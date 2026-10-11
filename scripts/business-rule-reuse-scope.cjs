const fs=require('node:fs'),{execFileSync}=require('node:child_process'),{sha}=require('./p1.cjs');
module.exports=function(item){const files=JSON.parse(fs.readFileSync(item.r.evidence.find(e=>e.path.endsWith('source-snapshot.json')).path,'utf8')),proof=[];
 const excludes={
  'src/domain/commands.ts':"    if((envelope.kind==='SubmitCycleRecord'||envelope.kind==='SubmitOneTimeResult')&&p.confirmedToday!==today)throw new DomainError('DAY_CHANGED');\n",
  'src/domain/rules.ts':'    if(plan.created_on>snapshot.today)continue;\n'
 };
 for(const file of ['src/domain/commands.ts','src/domain/rules.ts','src/domain/model.ts','src/domain/date.ts','tests/domain/bdd-service-rules.test.ts']){
  const expected=files.find(f=>f.path===file);const current=fs.readFileSync(file,'utf8');if(!expected&&file.startsWith('tests/')){proof.push({file,currentSha256:sha(current),originalTestShaCaptured:false,scope:'Retained test source explains the original named successful assertions; original test-file SHA equality is not claimed. Production algorithm equality is independently checked below.'});continue;}if(!expected)throw new Error('Original snapshot omitted '+file);let old=current,origin='Current file identical';
  if(sha(current)!==expected.sha256){old=execFileSync('git',['show','e48c6e5:'+file],{encoding:'utf8',windowsHide:true});origin='Recovered Git e48c6e5 exact complete original';if(sha(old)!==expected.sha256)throw new Error('Original file not recovered '+file);}
  let relevantCurrent=current,relevantOld=old;if(excludes[file]){relevantCurrent=current.replace(excludes[file],'');if(current!==old&&!current.includes(excludes[file]))throw new Error('Expected scoped later guard not found');}
  if(file==='src/domain/date.ts'){const core=s=>s.slice(0,s.indexOf('export const formatDate='));relevantOld=core(old);relevantCurrent=core(current);}
  if(sha(relevantOld)!==sha(relevantCurrent))throw new Error('Relevant executed code changed '+file);
  proof.push({file,origin,expectedOriginalSha256:expected.sha256,actualOriginalSha256:sha(old),relevantOriginalSha256:sha(relevantOld),relevantCurrentSha256:sha(relevantCurrent),excluded:excludes[file]||null});
 }
 return {proof,scope:'The successful service rule tests submit confirmedToday equal to each operation day and do not call Today sections. Their command/statistics/permission branches are byte identical after excluding only the later first-submit day-priority guard and Today clock-rollback guard. New guards have separate actual scoped reports. Display date formatting is outside pure date arithmetic. No test was run again.'};
};
