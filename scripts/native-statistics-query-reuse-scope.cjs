const fs=require('node:fs'),path=require('node:path'),{sha}=require('./p1.cjs');
module.exports=function(item){
 const file=item.r.evidence.find(e=>e.path.endsWith('source-snapshot.json')),inputs=JSON.parse(fs.readFileSync(path.join(path.dirname(item.record),'inputs.json'))),sources=file?JSON.parse(fs.readFileSync(file.path)):inputs.source||inputs.production,proof=[];
 for(const file of ['src/domain/rules.ts','src/domain/model.ts','src/domain/date.ts','src/application/projections.ts']){
  const expected=sources?.find(s=>s.path===file);if(!expected)throw new Error('Native query omitted source '+file);
  const current=fs.readFileSync(file,'utf8'),recovered=sha(current)===expected.sha256?{body:current,revision:'current identical'}:require('./recover-native-original-source.cjs')(file,expected.sha256);
  const normalize=s=>file==='src/domain/rules.ts'?s.replace('    if(plan.created_on>snapshot.today)continue;\n',''):s;
  if(sha(normalize(recovered.body))!==sha(normalize(current)))throw new Error('Statistics query algorithm changed '+file);
  proof.push({file,origin:recovered.revision,originalSha256:expected.sha256,currentSha256:sha(current),relevantOriginalSha256:sha(normalize(recovered.body)),relevantCurrentSha256:sha(normalize(current))});
 }
 return {proof,scope:'These AC113/AC114 When steps are direct detail/statistics queries. Their original currentSnapshot inputs, real native facts and query outputs are retained. The complete projection/model/date source and complete rules source excluding only the unrelated Today guard match recorded SHA. Fixture-writing and record preparation commands are Given, not a claim of unchanged full service.ts or executor.ts. No query, statistic calculation or Given command was rerun.'};
};
