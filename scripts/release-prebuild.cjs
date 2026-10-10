const fs=require('node:fs');
const {spawn}=require('node:child_process');
const {createHash}=require('node:crypto');
const {node,env}=require('./task-env.cjs');
const progress=require('./progress.cjs');
const directory=`resource/acceptance/runs/${new Date().toISOString().replace(/[:.]/g,'-')}/release-prebuild`;
fs.mkdirSync(directory,{recursive:true});
const stream=fs.createWriteStream(`${directory}/commands.log`);
const child=spawn(node,['node_modules/expo/bin/cli','prebuild','--platform','android','--no-install'],{env:{...env,APP_VARIANT:'production'},windowsHide:true,stdio:['ignore','pipe','pipe']});
for(const output of [child.stdout,child.stderr])output.on('data',chunk=>stream.write(chunk));
child.on('error',error=>stream.write(error.message));
child.on('close',async exitCode=>{
  await new Promise(resolve=>stream.end(resolve));
  const files=['commands.log'];
  for(const file of ['android/app/build.gradle','android/gradle.properties','android/app/src/main/AndroidManifest.xml','android/app/src/main/res/xml/backup_rules.xml','android/app/src/main/res/xml/data_extraction_rules.xml'])if(fs.existsSync(file)){const target=`${directory}/${file.replaceAll('/','_')}`;fs.copyFileSync(file,target);files.push(target.slice(directory.length+1));}
  const result={status:exitCode===0?'PASS':'FAIL',exitCode,endedAt:new Date().toISOString(),variant:'production',evidence:files.map(file=>({path:`${directory}/${file}`,sha256:createHash('sha256').update(fs.readFileSync(`${directory}/${file}`)).digest('hex')}))};
  fs.writeFileSync(`${directory}/result.json`,JSON.stringify(result,null,2)+'\n');
  progress.update(state=>{state.commands['release-prebuild']={...result,record:`${directory}/result.json`};state.tasks.find(task=>task.id==='IP03').evidence.push(`${directory}/result.json`);});
  console.log(`${result.status}: ${directory}/result.json`);process.exitCode=exitCode===0?0:1;
});
