const fs=require('node:fs'),path=require('node:path'),{sha,snapshot}=require('./p1.cjs');
module.exports=async function(t,result){
 let record=t.run.previousRecord;const ids=['AC024.A1.selection','AC024.A1.date','AC024.A1.direction'];
 while(record){const original=JSON.parse(fs.readFileSync(record)),directory=path.dirname(record);
  if(ids.every(id=>original.assertions.some(a=>a.id===id&&a.status==='PASS'))&&fs.existsSync(path.join(directory,'before-facts.json'))){
   for(const e of original.evidence)if(sha(fs.readFileSync(e.path))!==e.sha256)throw new Error('Original prefix evidence changed');
   const inputs=JSON.parse(fs.readFileSync(path.join(directory,'inputs.json'))),current=snapshot(['app','src/features','src/ui','src/state','src/domain','src/application','src/infrastructure/database','src/verification']);
   if(current.some(f=>inputs.source.find(o=>o.path===f.path)?.sha256!==f.sha256))throw new Error('Product changed after original preselection');
   const before=JSON.parse(fs.readFileSync(path.join(directory,'before-facts.json'))).snapshot,created=original.evidence.find(e=>/given-create\.json$/.test(e.path)),planId=JSON.parse(fs.readFileSync(created.path)).envelope.payload.planId;
   await t.client.call('factsFixture',{facts:before.facts,confirm:'RESET_ISOLATED_DEV_FACTS'});await t.clock(new Date(before.asOfMs).toISOString());
   t.run.assertions.push(...original.assertions.filter(a=>a.status==='PASS'));t.run.write('reused-preselected-prefix.json',{record,sha256:sha(fs.readFileSync(record)),required:ids,reason:'Keep the accepted actual Today-button preselection, date and direction observations. Restore the original unsaved draft as Given and execute only the remaining discard/no-write/readback steps.'});
   t.run.write('before-facts.json',{snapshot:before});await t.nav('/records/new',{planId,businessOn:before.today,result});return {planId,before};
  }record=original.previousRecord;
 }return null;
};
