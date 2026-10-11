const fs=require('node:fs'),progress=require('./progress.cjs');
const build=progress.read().commands['native-release'];
console.log(JSON.stringify({status:build.status,record:build.record,processId:build.processId,logPath:build.logPath},null,2));
if(build.logPath)console.log(fs.readFileSync(build.logPath,'utf8').slice(-1800));
