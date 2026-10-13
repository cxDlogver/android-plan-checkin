const {spawnSync}=require('node:child_process'),{env}=require('./task-env.cjs'),{passed}=require('./run-bdd-matrix.cjs'),{DeviceDriver}=require('./device-driver.cjs');
const failures=[];function run(script,args){new DeviceDriver('36','.cache/final-api36-gap-identity').identity();const r=spawnSync(process.execPath,['scripts/'+script,...args],{env,windowsHide:true,stdio:'inherit'});if(r.status){failures.push(script+' '+args.join(' '));new DeviceDriver('36','.cache/final-api36-gap-identity').identity();}}
for(const config of ['M5','M6','M8'])run('run-bdd-uncompleted.cjs',[config,'display']);
if(!passed('AC085-default-M6'))run('bdd-list-observation-continuation.cjs',['M6']);
if(!passed('AC055-shared-future-resume-interval-M7'))run('bdd-lifecycle-query-gap.cjs',['36','AC055']);
for(const config of ['M7','M8'])if(!passed(`AC094-default-${config}`))run('bdd-ui-talkback.cjs',['36',config]);
if(failures.length){console.error('Retained incomplete scopes: '+failures.join('; '));process.exitCode=1;}else console.log('Remaining API36 device scopes completed; raw visual review and formal APK are independent.');
