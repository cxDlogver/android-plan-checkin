const {runCases}=require('./bdd-ui-session.cjs');
const api=process.argv[2],config=api==='29'?'M3':'M7';
const presets={
 storage:[['records',['AC043/archive_fail']],['crash',[]]],
 lifecycle:[['lifecycle',[]]],
 calendar:[['calendar',[]]],
 statistics:[['statistics',[]],['week-statistics',[]]],
 pages:[['pages',[]]],
};
async function main(){const scopes=presets[process.argv[3]];if(!scopes)throw new Error('Expected storage, lifecycle, calendar, statistics or pages');for(const [module,selected]of scopes){console.log(`Continue API${api} BDD scope ${module}; explicitly selected ${selected.join(',')||'previously unexecuted parameters'}`);await runCases(api,require(`./bdd-ui-${module}.cjs`).definitions,selected,config);}}
main().catch(e=>{console.error(e.stack);process.exitCode=1;});
