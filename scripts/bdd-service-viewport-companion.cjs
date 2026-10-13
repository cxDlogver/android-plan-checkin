const {runCases}=require('./bdd-ui-session.cjs'),{take,read,references}=require('./acceptance-evidence.cjs');
const api=process.argv[2]||'36',selected=process.argv.slice(3),definitions={};
for(const ac of ['AC053','AC054']){if(selected.length&&!selected.includes(ac))continue;const original=take(`${ac}-default-api${api}`);definitions[ac]={'shared-native-service-viewport':async t=>{
 const before=read(original,'given-facts.json').snapshot,after=read(original,ac==='AC053'?'first-reconcile.json':'after-rejected-command.json').snapshot;
 const archive=after.facts.lifecycle_events.find(e=>e.kind==='archive'&&!before.facts.lifecycle_events.some(old=>old.id===e.id));if(!archive)throw new Error('Original independent archive observation missing');const planId=archive.plan_id;
 t.run.write('original-native-When-reused.json',{dependencies:references([original]),assertions:original.r.assertions,scope:'The original native reconcile/old-submit When is already accepted. Restore its before and committed after snapshots solely as viewport Given. Actual product screenshots and native after readback complete E-UI; they are not claimed to be screenshots captured during the earlier native command.'});
 await t.client.call('factsFixture',{facts:before.facts,confirm:'RESET_ISOLATED_DEV_FACTS'});await t.clock(new Date(before.asOfMs).toISOString());await t.nav('/plans/[planId]',{planId});await t.device.seek('plan.archive');await t.frame('accepted-before-facts-actual-product-view');
 await t.client.call('factsFixture',{facts:after.facts,confirm:'RESET_ISOLATED_DEV_FACTS'});await t.clock(new Date(after.asOfMs).toISOString());await t.nav('/plans/[planId]',{planId});await t.textPresent(ac+'.E3.archived-product-text','归档');await t.device.seek('plan.delete');await t.frame('accepted-after-facts-actual-product-view');
 const state=await t.capture('actual-presented-after-facts');t.check(ac+'.E3.accepted-after-facts-preserved',after.facts,state.facts);t.check(ac+'.E3.no-resume-control',false,(await t.device.source()).includes('plan.resume'));
 if(ac==='AC053'){await t.nav('/plans/[planId]/calendar',{planId});await t.click('calendar.date.2026-10-09');await t.frame('natural-last-day-actual-calendar');}
}};}
runCases(api,definitions,[],api==='29'?'M3':'M7').catch(e=>{console.error(e.stack);process.exitCode=1;});
