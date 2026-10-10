const fs=require('node:fs'),crypto=require('node:crypto');
const {spawnSync}=require('node:child_process');
const report=JSON.parse(fs.readFileSync('resource/progress/code-delivery.json','utf8'));
const sha=bytes=>crypto.createHash('sha256').update(bytes).digest('hex');
const failures=[];
const items=[...report.evidence,...report.code.files];
let staged,offset=0;
if(process.argv.includes('--index')){
  const result=spawnSync('git',['cat-file','--batch'],{input:items.map(item=>`:${item.path.replaceAll('\\','/')}\n`).join(''),windowsHide:true,maxBuffer:256*1024*1024});
  if(result.status!==0)throw new Error(`Unable to read staged Git blobs: ${result.stderr?.toString()||result.error?.message}`);staged=result.stdout;
}
for(const item of items){
  if(!fs.existsSync(item.path)||sha(fs.readFileSync(item.path))!==item.sha256)failures.push({path:item.path,scope:'workspace'});
  if(staged){
    const end=staged.indexOf(10,offset);if(end<0)throw new Error('Incomplete Git batch header');
    const header=staged.subarray(offset,end).toString('utf8'),match=header.match(/^(?:[0-9a-f]{40}|[0-9a-f]{64}) blob (\d+)$/);offset=end+1;
    if(!match){failures.push({path:item.path,scope:'git-index',detail:header});continue;}
    const size=Number(match[1]),blob=staged.subarray(offset,offset+size);if(blob.length!==size||staged[offset+size]!==10)throw new Error('Incomplete Git batch object');offset+=size+1;
    if(sha(blob)!==item.sha256)failures.push({path:item.path,scope:'git-index'});
  }
}
if(staged&&offset!==staged.length)throw new Error('Unexpected trailing Git batch output');
if(failures.length){console.error(JSON.stringify(failures));process.exitCode=1;}
else console.log(`PASS evidence integrity: ${report.evidence.length} evidence + ${report.code.files.length} source files${process.argv.includes('--index')?' in staged Git blobs':''}`);
