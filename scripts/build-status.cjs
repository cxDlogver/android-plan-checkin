const fs=require('node:fs');
const state=require('./progress.cjs').read();
for(const id of ['native-debug','native-release']){
  const command=state.commands[id];if(!command)continue;
  const file=command.log||command.logPath;
  const log=file&&fs.existsSync(file)?fs.readFileSync(file,'utf8'):'';
  const apk=`android/app/build/outputs/apk/${id==='native-release'?'release':'debug'}/app-${id==='native-release'?'release':'debug'}.apk`;
  console.log(JSON.stringify({id,status:command.status,apkPresent:fs.existsSync(apk),bundleTask:log.split(/\r?\n/).filter(line=>line.startsWith('> Task :app:createBundleReleaseJsAndAssets')),appAssemble:log.split(/\r?\n/).filter(line=>/^> Task :app:assemble/.test(line)),lastSteps:command.status==='RUNNING'?log.split(/\r?\n/).filter(line=>/^(> Task |BUILD |FAILURE:|\* What went wrong:|Execution failed|.*OutOfMemoryError|.*native memory allocation|.*Could not resolve)/.test(line)).slice(-8):[],lastOutput:command.status==='RUNNING'?log.slice(-1600):null}));
}
