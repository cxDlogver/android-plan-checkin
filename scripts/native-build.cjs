const fs=require('node:fs');
const path=require('node:path');
const {spawn}=require('node:child_process');
const {createHash}=require('node:crypto');
const {env,node,toolRoot}=require('./task-env.cjs');
const progress=require('./progress.cjs');
const action=process.argv[2]||'debug';
if(!['sdk','debug','release','environment'].includes(action))throw new Error('Unsupported build action');
if(action==='release'){
  const source=fs.readFileSync('android/app/build.gradle','utf8');
  if(!/applicationId ['"]com\.xiang\.plancheckin['"]/.test(source)||!source.includes('signingConfig signingConfigs.release'))throw new Error('Generate production native configuration with external release signing first.');
  for(const key of ['PLANCHECKIN_KEYSTORE','PLANCHECKIN_STORE_PASSWORD','PLANCHECKIN_KEY_ALIAS','PLANCHECKIN_KEY_PASSWORD'])if(!env[key])throw new Error('Required release signing environment is missing.');
  if(env.PLANCHECKIN_VERSION_CODE&&!source.includes(`versionCode ${env.PLANCHECKIN_VERSION_CODE}`))throw new Error('Generate native configuration for the requested versionCode before building.');
}
const startedAt=new Date().toISOString();
const directory=`resource/acceptance/runs/${startedAt.replace(/[:.]/g,'-')}/native-build/${action}`;
const hash=file=>createHash('sha256').update(fs.readFileSync(file)).digest('hex');
const sources=[];
function scan(directory){if(!fs.existsSync(directory))return;for(const item of fs.readdirSync(directory,{withFileTypes:true})){const file=`${directory}/${item.name}`;if(item.isDirectory())scan(file);else sources.push({path:file,sha256:hash(file)});}}
for(const root of ['app','src','plugins','assets','scripts','android/app/src'])scan(root);
for(const file of ['package.json','pnpm-lock.yaml','app.config.ts','metro.config.cjs','tsconfig.json','android/gradle.properties','android/gradle/wrapper/gradle-wrapper.properties','android/app/build.gradle','android/build.gradle','android/settings.gradle'])if(fs.existsSync(file))sources.push({path:file,sha256:hash(file)});
sources.sort((a,b)=>a.path.localeCompare(b.path));
const inputs=action==='debug'?sources.filter(file=>/^(android\/|package\.json$|pnpm-lock\.yaml$|plugins\/)/.test(file.path)):sources.filter(file=>!file.path.startsWith('scripts/')&&!(action==='release'&&/^src\/verification\/(development\.tsx|runtime-development\.ts|fixtures\.ts|bridge[^/]*)$/.test(file.path)));
const inputSha256=createHash('sha256').update(JSON.stringify({cacheVersion:2,action,architectures:process.env.PLANCHECKIN_ARCHITECTURES||null,inputs})).digest('hex');
const previous=progress.read().commands[`native-${action}`];
if(previous?.status==='PASS'&&previous.inputSha256===inputSha256&&fs.existsSync(previous.record)&&[...previous.evidence,...previous.artifacts].every(file=>fs.existsSync(file.path)&&hash(file.path)===file.sha256)){
  console.log(`SKIP native-${action}: input and evidence unchanged; ${previous.record}`);process.exit(0);
}
fs.mkdirSync(directory,{recursive:true});
fs.writeFileSync(`${directory}/source-snapshot.json`,JSON.stringify({startedAt,inputSha256,inputs,sources},null,2)+'\n');
const output=fs.createWriteStream(`${directory}/commands.log`);
let command,args,cwd=process.cwd();
const buildEnv={...env,CMAKE_BUILD_PARALLEL_LEVEL:'1'};
let nativeReuseTasks=[];
if(action==='release'&&process.env.PLANCHECKIN_REUSE_NATIVE_FROM)nativeReuseTasks=require('./native-reuse.cjs').validateNativeReuse(process.env.PLANCHECKIN_REUSE_NATIVE_FROM,sources,directory);
if(env.npm_config_https_proxy){const proxy=new URL(env.npm_config_https_proxy);buildEnv.JAVA_TOOL_OPTIONS=`-Dhttps.proxyHost=${proxy.hostname} -Dhttps.proxyPort=${proxy.port} -Dhttp.proxyHost=${proxy.hostname} -Dhttp.proxyPort=${proxy.port} -Dhttp.nonProxyHosts=localhost|127.*`;}
if(action==='sdk'){
  command='cmd.exe';args=['/d','/s','/c',`${toolRoot}/sdk/cmdline-tools/22.0/bin/sdkmanager.bat --sdk_root=${toolRoot}/sdk ndk;27.1.12297006 cmake;3.22.1`];
}else{
   const architectures=process.env.PLANCHECKIN_ARCHITECTURES||(action==='debug'?'x86_64':'arm64-v8a,x86_64');
   if(!/^(arm64-v8a|x86_64)(,(arm64-v8a|x86_64))*$/.test(architectures))throw new Error('Unsupported architecture');
    command='cmd.exe';cwd=path.resolve('android');args=['/d','/s','/c',`gradlew.bat ${action==='environment'?'help --init-script ../scripts/gradle-evidence.init.gradle':action==='debug'?`:app:assembleDebug -PreactNativeArchitectures=${architectures}`:`:app:assembleRelease -PreactNativeArchitectures=${architectures}`} ${nativeReuseTasks.map(task=>`-x ${task}`).join(' ')} --no-daemon --no-parallel --max-workers=1 --console=plain`];
}
output.write(`${new Date().toISOString()}\n${command} ${args.join(' ')}\n`);
progress.update(s=>{const t=s.tasks.find(t=>t.id==='IP03');t.status='IN_PROGRESS';t.blockedReason=null;t.startedAt??=startedAt;s.next='接续原生构建缓存；生成APK后执行尚未运行的Android原生模块与设备验收。';s.commands[`native-${action}`]={status:'RUNNING',startedAt,inputSha256,record:null,logPath:`${directory}/commands.log`};});
console.log(`RUN native-${action}: ${directory}/commands.log`);
const child=spawn(command,args,{cwd,env:buildEnv,windowsHide:true,stdio:['ignore','pipe','pipe']});
let tail='';for(const stream of [child.stdout,child.stderr])stream.on('data',chunk=>{output.write(chunk);tail=(tail+chunk).slice(-6000);});
child.on('error',error=>{output.write(error.stack);console.error(error.message);});
child.on('close',async exitCode=>{
  output.write(`\n${new Date().toISOString()} exitCode=${exitCode}\n`);await new Promise(resolve=>output.end(resolve));
  const artifacts=[];
  if(exitCode===0&&['debug','release'].includes(action)){
    const folder=`android/app/build/outputs/apk/${action}`;
    if(fs.existsSync(folder))for(const name of fs.readdirSync(folder).filter(name=>name.endsWith('.apk'))){const file=`${folder}/${name}`,digest=hash(file),target=`.artifacts/apk/${action}/${digest.slice(0,16)}.apk`;fs.mkdirSync(path.dirname(target),{recursive:true});fs.copyFileSync(file,target);artifacts.push({path:target,originalPath:file,sha256:digest,bytes:fs.statSync(target).size});}
    if(!artifacts.length)exitCode=1;
  }
  const evidence=['commands.log','source-snapshot.json'].map(name=>({path:`${directory}/${name}`,sha256:hash(`${directory}/${name}`)}));
  if(nativeReuseTasks.length)evidence.push({path:`${directory}/native-reuse.json`,sha256:hash(`${directory}/native-reuse.json`)});
  let toolchain=null;
  if(exitCode===0&&action==='environment'){
    const line=fs.readFileSync(`${directory}/commands.log`,'utf8').split(/\r?\n/).find(line=>line.startsWith('PLANCHECKIN_ENVIRONMENT='));
    if(!line)exitCode=1;else{toolchain=JSON.parse(line.slice('PLANCHECKIN_ENVIRONMENT='.length));fs.writeFileSync(`${directory}/toolchain.json`,JSON.stringify(toolchain,null,2)+'\n');evidence.push({path:`${directory}/toolchain.json`,sha256:hash(`${directory}/toolchain.json`)});}
  }
  const result={status:exitCode===0?'PASS':'FAIL',exitCode,action,startedAt,endedAt:new Date().toISOString(),inputSha256,sourceSnapshot:`${directory}/source-snapshot.json`,previousRecord:previous?.record||null,nodeVersion:process.version,log:`${directory}/commands.log`,toolchain,artifacts,evidence,limitations:action==='debug'?['开发包x86_64构建；不能作为正式签名/离线release通过']:[]};
  fs.writeFileSync(`${directory}/result.json`,JSON.stringify(result,null,2)+'\n');
  progress.update(s=>{s.commands[`native-${action}`]={...result,record:`${directory}/result.json`};s.tasks.find(t=>t.id==='IP03').evidence.push(`${directory}/result.json`);});
  console.log(`${result.status} native-${action}: ${directory}/result.json`);if(exitCode!==0)console.log(tail);process.exitCode=exitCode===0?0:1;
});
