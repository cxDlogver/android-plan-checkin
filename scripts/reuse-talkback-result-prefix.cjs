const fs=require('node:fs'),path=require('node:path'),{sha}=require('./p1.cjs'),{attr}=require('./bdd-ui-session.cjs'),{bounds}=require('./ui-tree-observation.cjs');
module.exports=async run=>{
 const record=run.previousRecord;if(!record)return null;
 const old=JSON.parse(fs.readFileSync(record,'utf8')),folder=path.dirname(record);
  const failed=old.assertions.find(a=>/^focus-(15|18)-natural-next\.visual-order$/.test(a.id)&&a.status==='FAIL');if(!failed)return null;const nextStep=Number(failed.id.match(/^focus-(\d+)/)[1]),group=nextStep===15?'do':'avoid';
 for(const e of old.evidence)if(sha(fs.readFileSync(e.path))!==e.sha256)throw new Error('Completed TalkBack prefix evidence changed');
 const original=JSON.parse(fs.readFileSync(path.join(folder,'inputs.json'),'utf8')),current=JSON.parse(fs.readFileSync(path.join(run.directory,'inputs.json'),'utf8'));
 if(JSON.stringify(original.source)!==JSON.stringify(current.source))throw new Error('Product changed after completed TalkBack prefix');
 const order=JSON.parse(fs.readFileSync(path.join(folder,'actual-focus-and-speech-order.json'),'utf8'));
  if(order.at(-1).step!==nextStep-1||order.at(-1).id!=='record.result.success')throw new Error('Unexpected TalkBack continuation prefix');
  const xml=fs.readFileSync(path.join(folder,`focus-${nextStep}-natural-next.xml`),'utf8'),previous=bounds(attr(xml,'record.result.success','bounds')),target=bounds(attr(xml,'record.result.failure','bounds'));
  const observed=JSON.parse(fs.readFileSync(path.join(folder,`focus-${nextStep}-natural-next-spoken-observations.json`),'utf8'));
  if(attr(xml,'record.result.failure','a11y-focused')!=='true'||!observed.some(m=>!m.stopped&&m.text.includes(group==='do'?'未完成':'发生了目标行为')&&m.pcmBytes>0&&m.offeredBytes===m.pcmBytes&&m.callerPackages.includes('com.android.talkback')))throw new Error('The previously executed focus transition was not completed');
 run.assertions.push(...old.assertions.filter(a=>a.status==='PASS'));
  run.write('reused-result-prefix.json',{record,sha256:sha(fs.readFileSync(record)),previous,target,reason:'The real swipe, focus and PCM already passed. Compare both controls in the original same-frame XML. Adjacent buttons may have different heights and centered tops; rightward order in overlapping vertical bands remains the visual reading order. Resume only the previously unexecuted skip traversal.'});
  run.check(`focus-${nextStep}-natural-next.visual-order`,true,require('./visual-reading-order.cjs')(previous,target));
  order.push({step:nextStep,id:'record.result.failure',bounds:attr(xml,'record.result.failure','bounds'),spoken:observed.filter(m=>!m.stopped).map(m=>m.text),action:'reused actual TalkBack swipe-right traversal'});
  return {order,group};
};
