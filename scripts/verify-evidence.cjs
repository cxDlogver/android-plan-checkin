const fs=require('node:fs'),crypto=require('node:crypto');
const {spawnSync}=require('node:child_process');
const report=JSON.parse(fs.readFileSync('resource/progress/code-delivery.json','utf8'));
const sha=bytes=>crypto.createHash('sha256').update(bytes).digest('hex');
const failures=[];
for(const item of [...report.evidence,...report.code.files]){
  if(!fs.existsSync(item.path)||sha(fs.readFileSync(item.path))!==item.sha256)failures.push({path:item.path,scope:'workspace'});
  if(process.argv.includes('--index')){const blob=spawnSync('git',['show',`:${item.path.replaceAll('\\','/')}`],{windowsHide:true,maxBuffer:20*1024*1024});if(blob.status!==0||sha(blob.stdout)!==item.sha256)failures.push({path:item.path,scope:'git-index'});}
}
if(failures.length){console.error(JSON.stringify(failures));process.exitCode=1;}
else console.log(`PASS evidence integrity: ${report.evidence.length} evidence + ${report.code.files.length} source files${process.argv.includes('--index')?' in staged Git blobs':''}`);
