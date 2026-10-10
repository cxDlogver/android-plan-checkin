const fs=require('node:fs');
const {spawnSync}=require('node:child_process');
const {node}=require('./task-env.cjs');
const files=['scripts/native-build.cjs','scripts/signing-status.cjs','scripts/release-prebuild.cjs','scripts/device-driver.cjs','scripts/device-native.cjs','scripts/metro.cjs'];
const results=files.map(file=>{const result=spawnSync(node,['--check',file],{encoding:'utf8',windowsHide:true});return {file,status:result.status===0?'PASS':'FAIL',exitCode:result.status,output:result.stdout+result.stderr};});
fs.writeFileSync('resource/progress/runner-syntax.json',JSON.stringify({checkedAt:new Date().toISOString(),scope:'new or changed build and device driver scripts only',results},null,2)+'\n');
console.log(JSON.stringify(results));if(results.some(result=>result.status!=='PASS'))process.exitCode=1;
