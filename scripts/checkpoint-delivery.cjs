const {spawnSync}=require('node:child_process'),{env}=require('./task-env.cjs');
const title=process.argv.slice(2).join(' ').replaceAll('_',' ');if(!title)throw new Error('Checkpoint title required');
function run(command,args){const r=spawnSync(command,args,{env,windowsHide:true,stdio:'inherit',timeout:240000});if(r.status!==0)throw new Error(command+' failed: '+r.status);}
run(process.execPath,['scripts/update-bdd-coverage.cjs']);
run(process.execPath,['scripts/finalize-delivery.cjs']);
run('git',['add','.']);
run(process.execPath,['scripts/verify-evidence-stream.cjs','--index']);
const change=spawnSync('git',['diff','--cached','--quiet'],{env,windowsHide:true});
if(change.status===1)run('git',['-c','gc.auto=0','commit','--quiet','-m',title]);else if(change.status!==0)throw new Error('Cannot inspect staged checkpoint');
run('git',['push','origin','main']);
console.log('Public checkpoint synchronized.');
