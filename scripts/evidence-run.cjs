const fs=require('node:fs');
const assert=require('node:assert/strict');
const {sha}=require('./p1.cjs');
const progress=require('./progress.cjs');
function createRun(name,inputs,implementationIds=[],metadata={}){
  const inputSha256=sha(JSON.stringify(inputs)),previous=progress.read().commands[name];
  if(previous?.status==='PASS'&&previous.inputSha256===inputSha256&&fs.existsSync(previous.record)){
    const saved=JSON.parse(fs.readFileSync(previous.record,'utf8'));
    if(saved.status==='PASS'&&saved.assertions.every(item=>item.status==='PASS')&&saved.evidence.every(file=>fs.existsSync(file.path)&&sha(fs.readFileSync(file.path))===file.sha256)){
      console.log(`SKIP ${name}: unchanged PASS evidence ${previous.record}`);return null;
    }
  }
  const startedAt=new Date().toISOString(),runId=startedAt.replace(/[:.]/g,'-'),directory=`resource/acceptance/runs/${runId}/${name}`,assertions=[];
  fs.mkdirSync(directory,{recursive:true});
  const write=(file,data)=>fs.writeFileSync(`${directory}/${file}`,typeof data==='string'?data:JSON.stringify(data,null,2)+'\n');
  write('inputs.json',inputs);
  progress.update(state=>{state.commands[name]={status:'IN_PROGRESS',inputSha256,record:null};state.next=`继续未完成验收；${name} 正在执行，已通过且输入相同的功能复用原报告。`;});
  return {directory,write,assertions,previousRecord:previous?.record||null,
    check(id,expected,actual){const status=JSON.stringify(expected)===JSON.stringify(actual)?'PASS':'FAIL';assertions.push({id,expected,actual,status});write('assertions.json',assertions);assert.equal(status,'PASS',id);},
    finish(error=null,limitations=[]){
      if(error)assertions.push({id:'execution',expected:'successful scoped verification',actual:error.message,status:'FAIL'});
      const status=error||assertions.some(item=>item.status==='FAIL')?'FAIL':'PASS';
      const evidence=fs.readdirSync(directory).filter(file=>!['result.json','assertions.json','evidence-manifest.json'].includes(file)).map(file=>({...(metadata.caseId?{profile:file.endsWith('.png')||file.endsWith('.xml')||file==='appium.log'?'E-UI':/facts|query|given.*command|receipt|capture/i.test(file)?'E-DATA':'E-NATIVE'}:{}),path:`${directory}/${file}`,sha256:sha(fs.readFileSync(`${directory}/${file}`))}));
      const result={...metadata,runId,status,startedAt,endedAt:new Date().toISOString(),inputSha256,previousRecord:previous?.record||null,scope:name,implementationIds,assertions,evidence,limitations};
      write('assertions.json',assertions);write('result.json',result);
      write('evidence-manifest.json',[...evidence,...['assertions.json','result.json'].map(file=>({path:`${directory}/${file}`,sha256:sha(fs.readFileSync(`${directory}/${file}`))}))]);
      progress.update(state=>{state.commands[name]={status,inputSha256,record:`${directory}/result.json`};for(const id of implementationIds){const task=state.tasks.find(task=>task.id===id);if(task.status!=='DONE')task.status='IN_PROGRESS';task.evidence.push(`${directory}/result.json`);}});
      console.log(`${status} ${name}: ${directory}/result.json`);if(error)process.exitCode=1;return result;
    }
  };
}
module.exports={createRun};
