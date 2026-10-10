const fs=require('node:fs');
const path=require('node:path');
const {spawn}=require('node:child_process');
const {env,node,toolRoot}=require('./task-env.cjs');
const progress=require('./progress.cjs');
const action=process.argv[2]||'debug';
if(!['sdk','debug','release','environment'].includes(action))throw new Error('Unsupported build action');
if(action==='release'){
  const source=fs.readFileSync('android/app/build.gradle','utf8');
  if(!/applicationId ['"]com\.xiang\.plancheckin['"]/.test(source)||!source.includes('signingConfig signingConfigs.release'))throw new Error('Generate production native configuration with external release signing first.');
  for(const key of ['PLANCHECKIN_KEYSTORE','PLANCHECKIN_STORE_PASSWORD','PLANCHECKIN_KEY_ALIAS','PLANCHECKIN_KEY_PASSWORD'])if(!env[key])throw new Error('Required release signing environment is missing.');
}
const directory=`resource/acceptance/runs/${new Date().toISOString().replace(/[:.]/g,'-')}/native-build/${action}`;
fs.mkdirSync(directory,{recursive:true});
const output=fs.createWriteStream(`${directory}/commands.log`);
let command,args,cwd=process.cwd();
const buildEnv={...env,CMAKE_BUILD_PARALLEL_LEVEL:'1'};
if(env.npm_config_https_proxy){const proxy=new URL(env.npm_config_https_proxy);buildEnv.JAVA_TOOL_OPTIONS=`-Dhttps.proxyHost=${proxy.hostname} -Dhttps.proxyPort=${proxy.port} -Dhttp.proxyHost=${proxy.hostname} -Dhttp.proxyPort=${proxy.port} -Dhttp.nonProxyHosts=localhost|127.*`;}
if(action==='sdk'){
  command='cmd.exe';args=['/d','/s','/c',`${toolRoot}/sdk/cmdline-tools/22.0/bin/sdkmanager.bat --sdk_root=${toolRoot}/sdk ndk;27.1.12297006 cmake;3.22.1`];
}else{
   const architectures=process.env.PLANCHECKIN_ARCHITECTURES||(action==='debug'?'x86_64':'arm64-v8a,x86_64');
   if(!/^(arm64-v8a|x86_64)(,(arm64-v8a|x86_64))*$/.test(architectures))throw new Error('Unsupported architecture');
   command='cmd.exe';cwd=path.resolve('android');args=['/d','/s','/c',`gradlew.bat ${action==='environment'?'buildEnvironment':action==='debug'?`assembleDebug -PreactNativeArchitectures=${architectures}`:`assembleRelease -PreactNativeArchitectures=${architectures}`} --no-daemon --no-parallel --max-workers=1 --console=plain`];
}
output.write(`${new Date().toISOString()}\n${command} ${args.join(' ')}\n`);
progress.update(s=>{const t=s.tasks.find(t=>t.id==='IP03');t.status='IN_PROGRESS';t.startedAt??=new Date().toISOString();s.commands[`native-${action}`]={status:'RUNNING',record:null,logPath:`${directory}/commands.log`};});
console.log(`RUN native-${action}: ${directory}/commands.log`);
const child=spawn(command,args,{cwd,env:buildEnv,windowsHide:true,stdio:['ignore','pipe','pipe']});
let tail='';for(const stream of [child.stdout,child.stderr])stream.on('data',chunk=>{output.write(chunk);tail=(tail+chunk).slice(-6000);});
child.on('error',error=>{output.write(error.stack);console.error(error.message);});
child.on('close',async exitCode=>{
  output.write(`\n${new Date().toISOString()} exitCode=${exitCode}\n`);await new Promise(resolve=>output.end(resolve));
  const result={status:exitCode===0?'PASS':'FAIL',exitCode,action,endedAt:new Date().toISOString(),log:`${directory}/commands.log`,limitations:action==='debug'?['开发包x86_64构建；不能作为正式签名/离线release通过']:[]};
  fs.writeFileSync(`${directory}/result.json`,JSON.stringify(result,null,2)+'\n');
  progress.update(s=>{s.commands[`native-${action}`]={...result,record:`${directory}/result.json`};s.tasks.find(t=>t.id==='IP03').evidence.push(`${directory}/result.json`);});
  console.log(`${result.status} native-${action}: ${directory}/result.json`);if(exitCode!==0)console.log(tail);process.exitCode=exitCode===0?0:1;
});
