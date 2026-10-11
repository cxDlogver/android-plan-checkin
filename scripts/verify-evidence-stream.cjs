const fs=require('node:fs'),crypto=require('node:crypto'),{spawn}=require('node:child_process');
const report=JSON.parse(fs.readFileSync('resource/progress/code-delivery.json','utf8')),items=[...report.evidence,...report.code.files],failures=[];
const sha=bytes=>crypto.createHash('sha256').update(bytes).digest('hex');
async function verifyIndex(){
 const child=spawn('git',['cat-file','--batch'],{windowsHide:true,stdio:['pipe','pipe','pipe']});let index=0,header=Buffer.alloc(0),remaining=null,hash=null,separator=false,error=null,stderr='';
 child.stderr.on('data',chunk=>{stderr=(stderr+chunk.toString()).slice(-2000);});
 child.stdout.on('data',chunk=>{if(error)return;try{let offset=0;while(offset<chunk.length){
  if(separator){if(chunk[offset++]!==10)throw new Error('Invalid Git object separator');separator=false;index++;continue;}
  if(remaining!==null){const length=Math.min(remaining,chunk.length-offset);hash.update(chunk.subarray(offset,offset+length));offset+=length;remaining-=length;if(remaining===0){if(hash.digest('hex')!==items[index].sha256)failures.push({path:items[index].path,scope:'git-index'});remaining=null;separator=true;}continue;}
  const end=chunk.indexOf(10,offset);if(end<0){header=Buffer.concat([header,chunk.subarray(offset)]);break;}
  const line=Buffer.concat([header,chunk.subarray(offset,end)]).toString('utf8');header=Buffer.alloc(0);offset=end+1;
  const match=line.match(/^(?:[0-9a-f]{40}|[0-9a-f]{64}) blob (\d+)$/);if(!items[index])throw new Error('Unexpected extra Git object');
  if(!match){failures.push({path:items[index++].path,scope:'git-index',detail:line});continue;}
  remaining=Number(match[1]);hash=crypto.createHash('sha256');if(remaining===0){if(hash.digest('hex')!==items[index].sha256)failures.push({path:items[index].path,scope:'git-index'});remaining=null;separator=true;}
 }}catch(e){error=e;child.kill();}});
 child.stdin.on('error',e=>{error??=e;});
 const closed=new Promise((resolve,reject)=>{child.once('error',reject);child.once('close',code=>{if(error)reject(error);else if(code!==0)reject(new Error('Unable to stream staged Git blobs: '+stderr));else if(index!==items.length||header.length||remaining!==null||separator)reject(new Error('Incomplete staged Git stream'));else resolve();});});
 child.stdin.end(items.map(item=>`:${item.path.replaceAll('\\','/')}\n`).join(''));await closed;
}
async function main(){for(const item of items)if(!fs.existsSync(item.path)||sha(fs.readFileSync(item.path))!==item.sha256)failures.push({path:item.path,scope:'workspace'});if(process.argv.includes('--index'))await verifyIndex();if(failures.length){console.error(JSON.stringify(failures));process.exitCode=1;}else console.log(`PASS evidence integrity: ${report.evidence.length} evidence + ${report.code.files.length} source files${process.argv.includes('--index')?' in streamed staged Git blobs':''}`);}
main().catch(e=>{console.error(e.stack);process.exitCode=1;});
