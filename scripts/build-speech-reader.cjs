const fs=require('node:fs'),path=require('node:path'),{spawnSync}=require('node:child_process'),{env,toolRoot,javaRoot}=require('./task-env.cjs'),{createRun}=require('./evidence-run.cjs'),{snapshot,sha}=require('./p1.cjs');
const sdk=path.join(toolRoot,'sdk'),tools=path.join(sdk,'build-tools/36.0.0'),androidJar=path.join(sdk,'platforms/android-36/android.jar'),source='tests/tools/speech-reader',directory='.cache/speech-reader',run=createRun('speech-reader-tool-build',{source:snapshot([source,'scripts/build-speech-reader.cjs']),androidJarSha256:sha(fs.readFileSync(androidJar))},['IP27']);
if(run){let error=null;try{
 for(const name of ['classes','dex'])fs.mkdirSync(`${directory}/${name}`,{recursive:true});
 const java=path.join(javaRoot,'bin/java.exe');
 function execute(binary,args){const r=spawnSync(binary,args,{env,windowsHide:true,encoding:'utf8',timeout:120000});fs.appendFileSync(`${run.directory}/build.log`,`${path.basename(binary)} exit=${r.status}\n${r.stdout||''}${r.stderr||''}\n`);if(r.status!==0)throw new Error(`${path.basename(binary)} failed, see build.log`);}
 execute(path.join(javaRoot,'bin/javac.exe'),['-encoding','UTF-8','-source','17','-target','17','-classpath',androidJar,'-d',`${directory}/classes`,`${source}/ReaderService.java`]);
 const classes=fs.readdirSync(`${directory}/classes/com/xiang/verification/reader`).filter(f=>f.endsWith('.class')).map(f=>`${directory}/classes/com/xiang/verification/reader/${f}`);
 execute(java,['-cp',path.join(tools,'lib/d8.jar'),'com.android.tools.r8.D8','--min-api','29','--lib',androidJar,'--output',`${directory}/dex`,...classes]);
 execute(path.join(tools,'aapt2.exe'),['compile','--dir',`${source}/res`,'-o',`${directory}/resources.zip`]);
 execute(path.join(tools,'aapt2.exe'),['link','-I',androidJar,'--manifest',`${source}/AndroidManifest.xml`,'-o',`${directory}/base.apk`,`${directory}/resources.zip`]);
 execute(path.join(javaRoot,'bin/jar.exe'),['uf',`${directory}/base.apk`,'-C',`${directory}/dex`,'classes.dex']);
 execute(path.join(tools,'zipalign.exe'),['-f','4',`${directory}/base.apk`,`${directory}/aligned.apk`]);
 execute(java,['-jar',path.join(tools,'lib/apksigner.jar'),'sign','--ks','android/app/debug.keystore','--ks-key-alias','androiddebugkey','--ks-pass','pass:android','--key-pass','pass:android','--out',`${directory}/reader.apk`,`${directory}/aligned.apk`]);
 execute(java,['-jar',path.join(tools,'lib/apksigner.jar'),'verify',`${directory}/reader.apk`]);
 const digest=sha(fs.readFileSync(`${directory}/reader.apk`)),apk=`.artifacts/tools/speech-reader/${digest.slice(0,16)}.apk`;fs.mkdirSync(path.dirname(apk),{recursive:true});fs.copyFileSync(`${directory}/reader.apk`,apk);run.write('tool-apk.json',{apk,sha256:digest,package:'com.xiang.verification.reader',scope:'Actual TalkBack caller PCM capture tool; isolated from product APK and database.',signing:'Existing Android development test key; formal signing identity is not used.'});run.check('tool-APK-created',true,fs.existsSync(apk));
}catch(e){error=e;}run.finish(error,['Tool compilation and signature verification only; speech and TalkBack acceptance require actual device requests and audio evidence.']);}
