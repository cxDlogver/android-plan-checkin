const fs=require('node:fs'),path=require('node:path'),{sha}=require('./p1.cjs');
module.exports=async(t,run)=>{
 let record=run.previousRecord;
 while(record){const old=JSON.parse(fs.readFileSync(record,'utf8')),folder=path.dirname(record),capture=path.join(folder,'failure-native-facts.json'),given=fs.readdirSync(folder).find(f=>f.endsWith('-given-create.json'));
 if(given&&fs.existsSync(capture)){for(const e of old.evidence)if(sha(fs.readFileSync(e.path))!==e.sha256)throw new Error('Display Given evidence changed');const data=JSON.parse(fs.readFileSync(capture,'utf8')),facts=data.snapshot?.facts||data.facts,payload=JSON.parse(fs.readFileSync(path.join(folder,given),'utf8')).envelope.payload;if(facts?.plans.some(p=>p.id===payload.planId)){await t.client.call('factsFixture',{facts,confirm:'RESET_ISOLATED_DEV_FACTS'});run.write('original-display-Given-reuse.json',{record,sha256:sha(fs.readFileSync(record)),planId:payload.planId,reason:'Restore the already created isolated plan; no create or record submit repeated.'});return payload.planId;}}
 record=old.previousRecord;
 }
 return null;
};
