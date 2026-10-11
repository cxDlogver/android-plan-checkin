const fs=require('node:fs'),path=require('node:path'),{spawn,execFileSync}=require('node:child_process'),{env}=require('./task-env.cjs'),{createRun}=require('./evidence-run.cjs'),{sha}=require('./p1.cjs');
const root=path.resolve('.cache/talkback'),commit=execFileSync('git',['-C',root,'rev-parse','HEAD'],{encoding:'utf8',windowsHide:true}).trim();
const changed=[];
for(const file of ['shared.gradle','braille/brltty/build.gradle','braille/translate/build.gradle']){
  const original=execFileSync('git',['-C',root,'show',`HEAD:${file}`],{encoding:'utf8',windowsHide:true});
  let adjusted=original.replace('"armeabi-v7a", "arm64-v8a"','"x86_64"').replace('21.4.7075529','27.1.12297006');
  if(file==='shared.gradle')adjusted=adjusted.replace('compileOptions {','compileOptions {\n        coreLibraryDesugaringEnabled true').replace('dependencies {','dependencies {\n    coreLibraryDesugaring "com.android.tools:desugar_jdk_libs:2.1.5"');
  fs.writeFileSync(path.join(root,file),adjusted);changed.push({path:file,originalSha256:sha(original),adjustedSha256:sha(adjusted),adjustment:'Use installed NDK 27 and emulator ABI; enable core library desugaring for Java APIs missing on API29. No screen-reader semantic code changes.'});
}
fs.writeFileSync(path.join(root,'local.properties'),'sdk.dir=D:/xiang/CX_application/1_Configuration_Files/Android-AI/sdk\n');
const run=createRun('talkback-tool-build',{officialRepository:'https://github.com/google/talkback',commit,changed},['IP27']);if(!run)process.exit(0);
run.write('tool-provenance.json',{repository:'https://github.com/google/talkback',commit,changed,desugaring:{version:'2.1.5',guide:'https://developer.android.com/studio/write/java8-support',supportedApis:'https://developer.android.com/studio/write/java11-default-support-table',trigger:'Actual API29 NoSuchMethodError for Collectors.toUnmodifiableSet in TalkBackForBrailleImeImpl.'},scope:'Verification tool only; excluded from product and delivery sources.'});
const gradle=path.resolve('.cache/gradle/wrapper/dists/gradle-9.3.1-bin/23ovyewtku6u96viwx3xl3oks/gradle-9.3.1/bin/gradle.bat');
const logPath=`${run.directory}/commands.log`,log=fs.createWriteStream(logPath);let tail='';
const child=spawn('cmd.exe',['/d','/c',gradle,'assemblePhoneDebug','--no-daemon','--max-workers=2','-Dorg.gradle.jvmargs=-Xmx2048m'],{cwd:root,env,windowsHide:true,stdio:['ignore','pipe','pipe']});
console.log(`RUN TalkBack official source ${commit}: ${logPath}`);
for(const output of [child.stdout,child.stderr])output.on('data',chunk=>{log.write(chunk);tail=(tail+chunk).slice(-2400);});
child.on('close',code=>{log.end(()=>{let error=null;try{run.check('tool-build-exit-code',0,code);}catch(e){error=new Error(`TalkBack build exit ${code}: ${tail}`);}run.finish(error);});});
child.on('error',error=>{log.end(()=>run.finish(error));});
