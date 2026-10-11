const {runCases}=require('./bdd-ui-session.cjs');
async function main(){const api=process.argv[2]||'29',config=api==='29'?'M3':'M7';await runCases(api,require('./bdd-ui-lifecycle.cjs').definitions,['AC060/due_past','AC048/default'],config);await runCases(api,require('./bdd-ui-lifecycle-recovery.cjs').definitions,['AC052/ordinary_complete','AC052/ordinary_failed'],config);}
main().catch(e=>{console.error(e.stack);process.exitCode=1;});
