const fs=require('node:fs'),path=require('node:path'),{sha,snapshot}=require('./p1.cjs'),{take,read,references}=require('./acceptance-evidence.cjs'),{runCases}=require('./bdd-ui-session.cjs');
const observer=take('API36-stopped-interruption-readback'),state=read(observer,'actual-interrupted-command-state.json'),native=read(observer,'actual-interrupted-private-database-facts.json'),prefix=read(observer,'original-prefix.json'),original=JSON.parse(fs.readFileSync(prefix.directory+'/result.json'));
for(const e of original.evidence)if(sha(fs.readFileSync(e.path))!==e.sha256)throw new Error('Interrupted prefix evidence changed');
const inputs=JSON.parse(fs.readFileSync(prefix.directory+'/inputs.json'));
for(const f of snapshot(['app','src/features','src/ui','src/state','src/domain','src/application','src/infrastructure/database','src/verification']))if(inputs.source.find(o=>o.path===f.path)?.sha256!==f.sha256)throw new Error('Product changed after original Save');
if(state.records.length!==1||state.receipts.filter(r=>r.kind==='SubmitCycleRecord').length!==1)throw new Error('No exact committed Save to recover');
runCases('36',{AC105:{default:async t=>{
 t.run.assertions.push(...prefix.assertions.filter(a=>a.status==='PASS'));
 t.run.write('committed-save-reuse-scope.json',{dependencies:references([observer]),originalReport:prefix.directory+'/result.json',originalReportSha256:sha(fs.readFileSync(prefix.directory+'/result.json')),scope:'The original native Save committed before execution interruption. Restore its exact native after-facts as Given and perform only remaining readback; do not submit any new record.'});
 await t.client.call('factsFixture',{facts:native.facts,confirm:'RESET_ISOLATED_DEV_FACTS'});await t.clock(new Date(prefix.before.asOfMs).toISOString());
 const after=await t.capture('after-facts'),r=after.facts.cycle_records.filter(r=>r.plan_id===state.planId);t.check('AC105.A1.exact-committed-record',state.records,r);t.check('AC105.A1.empty-note-valid','',r[0].note);t.check('AC105.original-submit-receipt',state.receipts.filter(r=>r.kind==='SubmitCycleRecord'),after.facts.command_receipts.filter(r=>r.plan_id===state.planId&&r.kind==='SubmitCycleRecord'));
 await t.nav('/records/[recordId]',{planId:state.planId,recordId:r[0].id});t.check('AC105.empty-note-readback','',await t.property('record.note','text'));await t.frame('committed-empty-note-readback');
}}},['AC105/default'],'M7').catch(e=>{console.error(e.stack);process.exitCode=1;});
