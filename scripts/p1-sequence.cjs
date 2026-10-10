const {run}=require('./p1.cjs');
(async()=>{for(const id of process.argv.slice(2)){const result=await run(id);if(result.status!=='PASS')break;}})().catch(error=>{console.error(error);process.exitCode=1;});
