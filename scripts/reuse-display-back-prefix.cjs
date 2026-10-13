const fs=require('node:fs'),path=require('node:path'),{sha,snapshot}=require('./p1.cjs');
module.exports=async t=>{
 let record=t.run.previousRecord;
 const required=['AC093.A2.actual-keyboard-shown','AC093.A2.save-reachable-and-enabled','AC093.A2.save-above-actual-keyboard','AC093.A2.complete-save-hit-area','AC093.A2.first-back-closes-keyboard','AC093.A2.first-back-keeps-form'];
 while(record){const r=JSON.parse(fs.readFileSync(record,'utf8')),dir=path.dirname(record);
  if(fs.existsSync(path.join(dir,'before-keyboard-facts.json'))&&required.every(id=>r.assertions.some(a=>a.id===id&&a.status==='PASS'))){
   for(const e of r.evidence)if(sha(fs.readFileSync(e.path))!==e.sha256)throw new Error('Original display prefix evidence changed');
   const inputs=JSON.parse(fs.readFileSync(path.join(dir,'inputs.json'),'utf8')),current=snapshot(['app','src/features','src/ui','src/state','src/domain','src/application','src/infrastructure/database','src/verification']);
   if(current.some(f=>inputs.source.find(o=>o.path===f.path)?.sha256!==f.sha256))throw new Error('Product changed after original Back prefix');
   const saved=JSON.parse(fs.readFileSync(path.join(dir,'before-keyboard-facts.json'),'utf8')).snapshot;
   const p=saved.facts.plans.find(p=>p.type==='one_time');if(!p)throw new Error('Original display plan missing');
   await t.client.call('factsFixture',{facts:saved.facts,confirm:'RESET_ISOLATED_DEV_FACTS'});
   t.run.assertions.push(...r.assertions.filter(a=>a.status==='PASS'&&a.id!=='AC093.A3.native-navigation-mode'));
   t.run.write('reused-successful-keyboard-and-first-back.json',{record,sha256:sha(fs.readFileSync(record)),required,reason:'The actual keyboard, complete Save hit area and first Back already passed. Restore the unsaved draft as Given and execute only the remaining modal/discard Back actions.'});
   return {planId:p.id,before:saved,modalPassed:r.assertions.some(a=>a.id==='AC093.A2.modal-back-keeps-form'&&a.status==='PASS')};
  }
  record=r.previousRecord;
 }
 return null;
};
