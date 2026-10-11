const fs=require('node:fs'),path=require('node:path'),{sha}=require('./p1.cjs');
module.exports=async(t,run)=>{
 let record=run.previousRecord;const visited=new Set();
 while(record&&!visited.has(record)){
  visited.add(record);const old=JSON.parse(fs.readFileSync(record,'utf8')),folder=path.dirname(record),files=fs.readdirSync(folder).filter(file=>file.endsWith('-given-create.json'));
  if(files.length===4){
   for(const e of old.evidence)if(sha(fs.readFileSync(e.path))!==e.sha256)throw new Error('Original TalkBack Given digest mismatch');
   const creates=files.map(file=>({file,payload:JSON.parse(fs.readFileSync(path.join(folder,file),'utf8')).envelope.payload}));
   const saved=path.join(folder,'failure-native-facts.json');
   const savedCapture=fs.existsSync(saved)?JSON.parse(fs.readFileSync(saved,'utf8')):null;
   const facts=savedCapture?.snapshot?.facts||savedCapture?.facts||null;
   const complete=f=>f&&f.plans.length===4&&creates.every(c=>f.plans.some(p=>p.id===c.payload.planId))&&f.cycle_records.length===3&&f.one_time_results.length===1;
   let existing=await t.capture('original-Given-current-readback');
   if(!complete(existing.facts)&&complete(facts)){await t.client.call('factsFixture',{facts,confirm:'RESET_ISOLATED_DEV_FACTS'});existing=await t.capture('original-Given-restored-readback');}
   if(complete(existing.facts)){run.write('original-Given-command-reuse.json',{record,sha256:sha(fs.readFileSync(record)),creates,restorationSource:complete(facts)?saved:null,reason:'Reuse the original four plan IDs and committed records, restoring their captured isolated fixture when another case replaced it. No create or submit command is repeated.'});return Object.fromEntries([['fixed','语音成功计划'],['avoid','语音失败计划'],['weekly','语音跳过计划'],['once','语音取消计划']].map(([key,name])=>[key,creates.find(c=>c.payload.name===name).payload.planId]));}
  }
  record=old.previousRecord;
 }
 return null;
};
