module.exports=({define,client,randomUUID})=>{
define('AC109','shared-readonly-and-immutable',async t=>{
  const p=await t.create();await t.at('2026-10-09');await t.given();
  for(const [field,value]of [['type','weekly'],['direction','avoid'],['startsOn','2026-10-09'],['timezone','America/New_York']])await t.command('EditPlan',{...await t.ref(p),changes:{[field]:value},ruleConfirmations:[]},'VALIDATION_FAILED');await t.unchanged('AC109.A4.immutable-rejection');
  await t.command('ArchivePlan',{...await t.ref(p),eventId:randomUUID()});await t.given();await t.command('EditPlan',{...await t.ref(p),changes:{name:'不能编辑'},ruleConfirmations:[]},'ARCHIVED');await t.unchanged('AC109.A4.archived-rejection');
});
define('AC104','default',async t=>{
  const p=await t.create('weekly'),r=await t.record(p,'2026-10-09','success','最初');let before=await t.given();
  await t.command('ModifyCycleRecord',{...await t.ref(p),recordId:r,expectedRecordRevision:1,result:'failure',note:'修正'});let after=await t.snap('after-correction');
  t.check('AC104.A1.per-transaction-increment',[2,before.facts.plans.find(x=>x.id===p).revision+1,before.dataRevision+1],[after.facts.cycle_records.find(x=>x.id===r).revision,after.facts.plans.find(x=>x.id===p).revision,after.dataRevision]);
  await t.edit(p,{weeklyTarget:5});await t.edit(p,{weeklyTarget:3});await t.edit(p,{weeklyTarget:4});after=await t.snap('versions');const rules=after.facts.rule_versions.filter(x=>x.plan_id===p&&x.kind==='weekly_target');t.check('AC104.A2.max-includes-cancelled',[1,2,3],rules.map(x=>x.revision));t.check('AC104.A2.same-millisecond',1,new Set(rules.filter(x=>x.revision>1).map(x=>x.created_at_ms)).size);
  before=await t.given();await t.edit(p,{weeklyTarget:4});after=await t.snap('no-op');t.check('AC104.A3.no-op',[before.dataRevision,before.facts.plans.find(x=>x.id===p).revision],[after.dataRevision,after.facts.plans.find(x=>x.id===p).revision]);
  await t.at('2026-10-09');await t.command('RequestPause',{...await t.ref(p),eventId:randomUUID(),confirmedEffectiveOn:'2026-10-10'});const pending=await t.snap('pending-state');await t.at('2026-10-10',0);const reconciled=await t.snap('reconciled');t.check('AC104.A4.independent-reconcile',[pending.dataRevision+1,pending.facts.plans.find(x=>x.id===p).revision+1],[reconciled.dataRevision,reconciled.facts.plans.find(x=>x.id===p).revision]);
});
define('AC102','default',async t=>{
  const p=await t.create();await t.at('2026-10-09');const env=t.envelope('SubmitCycleRecord',{...await t.ref(p),recordId:randomUUID(),businessOn:'2026-10-09',result:'success',note:'',confirmedToday:'2026-10-09',confirmedEntryKind:'ordinary'});await t.send(env);const initial=await t.snap('committed');const receipt=initial.facts.command_receipts.find(r=>r.command_id===env.commandId);t.check('AC102.A1.expiry',env.issuedAtMs+604800000,receipt.expires_at_ms);
  t.ms=receipt.expires_at_ms-1;await client.call('clock',{instant:new Date(t.ms).toISOString()});const replay=await t.send(env);t.check('AC102.A1.last-millisecond',true,replay.replayed);
  t.ms=receipt.expires_at_ms;await client.call('clock',{instant:new Date(t.ms).toISOString()});await t.send(env,'COMMAND_EXPIRED');
  const snapshot=await t.snap(),facts=snapshot.facts;facts.command_receipts=[];const issued=t.ms-604800000;
  for(let i=0;i<201;i++)facts.command_receipts.push({command_id:randomUUID(),plan_id:null,kind:'CreatePlan',payload_digest:'a'.repeat(64),result_code:'OK',object_id:null,issued_at_ms:issued,committed_at_ms:issued,expires_at_ms:t.ms});
  const tombstoneId=randomUUID();facts.command_receipts.push({command_id:tombstoneId,plan_id:null,kind:'PermanentlyDeletePlan',payload_digest:null,result_code:'TARGET_REMOVED',object_id:null,issued_at_ms:t.ms,committed_at_ms:t.ms,expires_at_ms:t.ms+604800000});
  await client.call('factsFixture',{facts,confirm:'RESET_ISOLATED_DEV_FACTS'});const before=await t.given();t.run.write('cleanup-result.json',await client.call('cleanReceipts'));const after=await t.snap('after-cleanup');t.check('AC102.A2.exact-200',[1,1],[after.facts.command_receipts.filter(r=>r.expires_at_ms<=t.ms).length,after.facts.command_receipts.filter(r=>r.command_id===tombstoneId).length]);
  t.check('AC102.A3.revision-and-history',JSON.stringify({...before.facts,command_receipts:[]}),JSON.stringify({...after.facts,command_receipts:[]}));await t.given();await t.send(env,'COMMAND_EXPIRED');await t.unchanged('AC102.A3.expired-cleaned-no-reexecution');
});
};
