'use strict';const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),assert=require('node:assert/strict');const root=path.resolve(__dirname,'../..'),read=f=>JSON.parse(fs.readFileSync(f,'utf8')),relative=f=>path.relative(root,f).replaceAll('\\','/'),ref=f=>({path:relative(f),sha256:crypto.createHash('sha256').update(fs.readFileSync(f)).digest('hex')}),write=(f,v)=>fs.writeFileSync(f,JSON.stringify(v,null,2)+'\n',{flag:'wx'});
function settledFixtureSeeking(adapter){
 const device=adapter.device,original=device.seek,observations=[];
 device.seek=async function(testID,...args){
  const startedAt=new Date().toISOString();await original.call(this,testID,...args);let last=null,stable=0;const samples=[];
  for(let attempt=0;attempt<40;attempt++){
   const source=await this.source(),tag=source.split('>').find(t=>t.includes('resource-id="'+testID+'"'))||'',match=tag.match(/bounds="\[(-?\d+),(-?\d+)\]\[(-?\d+),(-?\d+)\]"/),bounds=match?.slice(1).map(Number);
   const visible=bounds&&bounds[2]>bounds[0]&&bounds[3]>bounds[1]&&!tag.includes('displayed="false"')&&!tag.includes('enabled="false"'),key=visible?JSON.stringify(bounds):null;
   stable=key&&key===last?stable+1:key?1:0;last=key;samples.push({at:new Date().toISOString(),bounds:bounds??null,visible:Boolean(visible),stable});
   if(stable>=4){const element=await this.id(testID);observations.push({testID,startedAt,samples,element});return element;}
   await new Promise(resolve=>setTimeout(resolve,150));
  }
  observations.push({testID,startedAt,samples,blocked:true});throw Error('Fixture control did not settle at visible native bounds: '+testID);
 };
 return()=>{device.seek=original;write(path.join(adapter.directory,'responsive-matrix-navigation.json'),{minimumConsecutiveStableVisibleSamples:4,sampleIntervalMs:150,operation:'Readiness only; original native click and independent product assertions remain in force.',observations});};
}
function requiredScopeRecord(record,model){
 const cases=new Map(model.cases.map(c=>[c.id,c])),latest=new Map();
 for(const attempt of record.attempts){assert.equal(attempt.run.visits.length,1);latest.set(attempt.run.visits[0].visitIndex,attempt);}
 const selected=[],audit=[];
 record.sequence.forEach((caseId,visitIndex)=>{if(cases.get(caseId).kind!=='primary')return;const attempt=latest.get(visitIndex),visit=attempt?.run.visits[0];assert.ok(attempt?.closedAt&&visit?.outcome==='passed'&&[null,0].includes(attempt.run.exitCode)&&visit.checks.length&&visit.checks.every(c=>c.status==='passed'),'Scope requires the latest closed passed primary visit '+visitIndex);selected.push(attempt);audit.push({visitIndex,caseId,runId:attempt.run.id});});
 const ids=new Set(selected.map(a=>a.run.id)),historical=record.attempts.filter(a=>cases.get(record.sequence[a.run.visits[0].visitIndex]).kind==='primary');
 return {record:{...record,attempts:selected},audit:{requiredPrimaryVisits:selected.length,historicalPrimaryAttempts:historical.length,selected:audit,excludedHistoricalPrimaryAttemptIds:historical.filter(a=>!ids.has(a.run.id)).map(a=>a.run.id),selectionRule:'Latest closed passed attempt for each required visitIndex in the unchanged sequence; failures and prior attempts remain in the canonical record.'}};
}

function completeFixtureObservations(adapter,root){
 const original=adapter.observe,manifest=read(path.join(root,'plan/ui-spec/manifest.json')),documents=new Map(manifest.documents.filter(d=>d.kind==='screen').map(d=>{const doc=read(path.join(root,'plan/ui-spec',d.file));return [doc.id,doc];})),pending=[];
 const flatten=n=>[n,...n.children.flatMap(flatten)];
 adapter.observe=async function(name,options={}){
  const deadline=Date.now()+15000;
  for(let attempt=0;;attempt++){
   const shot=await original.call(this,name,options),frame=shot.report,document=documents.get(frame.documentId);assert.ok(document,'Known native document before layout readiness');
   const missing=frame.environment.viewport.width>=768?[]:flatten(document.tree).filter(n=>n.ownership==='application').filter(n=>!frame.measurements[n.id]?.box||!frame.measurements[n.id]?.props).map(n=>n.id);
   if(!missing.length)return shot;
   const item={name,attempt,nonce:frame.nonce,navigationSerial:frame.navigationSerial,documentId:frame.documentId,missing};
   if(options.save!==false){item.preserved=[];for(const ext of ['.json','.xml','.png']){const from=path.join(this.directory,name+ext),to=path.join(this.directory,name+'.layout-pending-'+attempt+ext);fs.renameSync(from,to);item.preserved.push(ref(to));}}else item.rawReport=frame;
   pending.push(item);if(Date.now()>=deadline)throw Error('Actual native layout measurements did not become complete: '+missing.join(','));
   await new Promise(resolve=>setTimeout(resolve,150));
  }
 };
 return()=>{adapter.observe=original;write(path.join(adapter.directory,'responsive-matrix-layout-readiness.json'),{scope:'Presence of actual measurement records and applied props only; independent geometry and content assertions are unchanged.',pendingObservations:pending});};
}
async function prepareFixtureProfile(adapter,seed,expected,journal){
 const device=adapter.device,deadline=Date.now()+60000,samples=[],recoveries=[];let last=null,stable=0;
 while(Date.now()<deadline){
  let source=await device.source();
  if(!source.includes('resource-id="ui-review.command"')){
   const prefix='profile-'+expected.width+'x'+expected.height+'-font-'+expected.fontScale+'-recovery-'+recoveries.length,before=await adapter.capture(prefix+'-before');
   const bootstrap=expected.width>=768?{width:393,height:expected.height}:null;if(bootstrap)device.adb(['shell','wm','size',bootstrap.width*3+'x'+bootstrap.height*3]);let nativeSource='';const entryAttempts=[];for(let entryAttempt=0;entryAttempt<4;entryAttempt++){device.deepLink(adapter.scheme+':///native');const entryDeadline=Date.now()+4000;do{nativeSource=await device.source();if(nativeSource.includes('resource-id="native.ui-review"')||nativeSource.includes('resource-id="ui-review.command"'))break;await new Promise(r=>setTimeout(r,200));}while(Date.now()<entryDeadline);entryAttempts.push({at:new Date().toISOString(),nativeEntryVisible:nativeSource.includes('resource-id="native.ui-review"'),reviewVisible:nativeSource.includes('resource-id="ui-review.command"')});if(entryAttempts.at(-1).nativeEntryVisible||entryAttempts.at(-1).reviewVisible)break;}assert.ok(nativeSource.includes('resource-id="native.ui-review"')||nativeSource.includes('resource-id="ui-review.command"'),'Authorized native entry must become ready after configuration');if(!nativeSource.includes('resource-id="ui-review.command"'))await device.clickVisible('native.ui-review');await device.waitSource(x=>x.includes('resource-id="ui-review.command"'),20000);await adapter.restart(seed);if(bootstrap){device.adb(['shell','wm','size',expected.width*3+'x'+expected.height*3]);await device.waitSource(x=>x.includes('resource-id="ui-review.command"')&&x.includes('resource-id="ui.unsupported"'),20000);}const after=await adapter.observe(prefix+'-after');
   recoveries.push({bootstrap,entryAttempts,requestedProfile:expected,before:ref(before.tree),beforeScreenshot:ref(before.screenshot),after:ref(path.join(adapter.directory,prefix+'-after.json')),observation:'Re-entered the authorized isolated review host during profile preparation; system font scale was not changed.'});last=null;stable=0;source=await device.source();
  }
  let shot;
  try{shot=await adapter.observe('profile-readiness',{save:false});}
  catch(error){const actual=await device.source();if(!actual.includes('resource-id="ui-review.capture"')&&/could not be located|no such element/i.test(error.message)){samples.push({at:new Date().toISOString(),hostLost:true,error:error.message});last=null;stable=0;continue;}throw error;}
  const frame=shot.report,actual={width:frame.environment.viewport.width,height:frame.environment.viewport.height,fontScale:frame.environment.fontScale},matches=Math.abs(actual.width-expected.width)<.01&&Math.abs(actual.height-expected.height)<.01&&Math.abs(actual.fontScale-expected.fontScale)<.0001,key=JSON.stringify({actual,runId:frame.context.runId,navigationSerial:frame.navigationSerial,windowId:source.match(/window-id="([^"]+)"/)?.[1]});
  stable=matches?(key===last?stable+1:1):0;last=key;samples.push({at:new Date().toISOString(),actual,matched:matches,stable});
  if(stable>=4){const identity=device.identity();assert.ok(Math.abs(Number(identity.fontScale)-expected.fontScale)<.0001,'Actual SDK font scale must remain the requested value');journal.push({expected,actual,identity,samples,recoveries,ready:true});return;}
  await new Promise(resolve=>setTimeout(resolve,200));
 }
 journal.push({expected,samples,recoveries,ready:false});throw Error('Actual isolated host did not settle at requested viewport/font profile');
}
async function prepareKeyboardTarget(adapter,testID,journal){
 const device=adapter.device,record={testID,samples:[],gestures:[],ready:false};journal.push(record);let stable=0,last=null;const deadline=Date.now()+20000;
 try{
  while(Date.now()<deadline){const sdkShown=/mInputShown=true\b/.test(device.adb(['shell','dumpsys','input_method'])),shot=await adapter.observe('keyboard-layout-preparation',{save:false}),frame=shot.report,node=frame.measurements[testID],keyboard=frame.environment.keyboard,ready=Boolean(sdkShown&&keyboard&&node?.box),key=ready?JSON.stringify({keyboard,viewport:frame.environment.viewport,target:node.box,roots:Object.values(frame.measurements).filter(n=>n.parentId===null).map(n=>n.box)}):null;stable=key&&key===last?stable+1:key?1:0;last=key;record.samples.push({at:new Date().toISOString(),sdkShown,keyboard,stable});if(stable>=2)break;await new Promise(r=>setTimeout(r,150));}
  assert.ok(stable>=2,'Actual SDK and published keyboard geometry must settle before visibility assertions');
  for(let attempt=0;attempt<40;attempt++){
   const frame=(await adapter.observe('keyboard-target-preparation',{save:false})).report,source=await device.source(),tag=source.split('>').find(t=>t.includes('resource-id="'+testID+'"'))||'',match=tag.match(/bounds="\[(-?\d+),(-?\d+)\]\[(-?\d+),(-?\d+)\]"/),b=match?.slice(1).map(Number),scale=frame.environment.pixelRatio,kb=frame.environment.keyboard,node=frame.measurements[testID];if(!kb||!node?.box){record.samples.push({at:new Date().toISOString(),stage:'target-layout',keyboard:kb??null,targetMeasured:Boolean(node?.box),sdkShown:/mInputShown=true\b/.test(device.adb(['shell','dumpsys','input_method']))});if(Date.now()>=deadline)throw Error('Actual keyboard target metadata did not stay ready');await new Promise(r=>setTimeout(r,150));continue;}const full=node.box.height*scale,top=frame.environment.insets.top*scale,bottom=kb.screenY*scale;assert.ok(Number.isFinite(full)&&full>0&&full<=bottom-top+1,'Target full height must fit the actual visible keyboard viewport');
   if(!b||b[2]<=b[0]||b[3]<=b[1]){await device.seek(testID);continue;}
   if(b[1]>=top-1&&b[3]<=bottom+1&&b[3]-b[1]>=full-1){assert.ok(/mInputShown=true\b/.test(device.adb(['shell','dumpsys','input_method'])),'Real IME must remain open');Object.assign(record,{ready:true,bounds:b,nativeFullHeightPx:full,keyboard:kb,pixelRatio:scale,viewport:frame.environment.viewport});return;}
   const clipped=Math.max(0,full-(b[3]-b[1])),direction=b[1]<top-1||(clipped>1&&b[1]<=top+1)?'up':'down',deficit=Math.max(clipped,direction==='up'?top-b[1]:b[3]-bottom),percent=Math.max(.12,Math.min(.35,(Math.max(1,deficit)+6)/Math.max(1,(bottom-top)*.7))),changed=await device.scroll(direction,percent,true);record.gestures.push({direction,percent,beforeBounds:b,nativeFullHeightPx:full,keyboardTopPx:bottom,changed});
  }
  throw Error('Keyboard target could not be scrolled fully above the actual IME: '+testID);
 }catch(error){record.blocked=error.message;throw error;}
}

function assertFullKeyboardProof(frame,xml,testID,expectedBounds){
 const tag=xml.split('>').find(t=>t.includes('resource-id="'+testID+'"'))||'',match=tag.match(/bounds="\[(-?\d+),(-?\d+)\]\[(-?\d+),(-?\d+)\]"/),bounds=match?.slice(1).map(Number),e=frame.environment,full=frame.measurements[testID]?.box.height*e.pixelRatio;
 assert.ok(e.keyboard&&bounds&&Number.isFinite(full)&&full>0,'Actual IME, measured target and native rectangle required');assert.ok(bounds[1]>=e.insets.top*e.pixelRatio-1&&bounds[3]<=e.keyboard.screenY*e.pixelRatio+1&&bounds[3]-bounds[1]>=full-1,'Complete target must remain above actual IME');if(expectedBounds)assert.deepEqual(bounds,expectedBounds,'Summary rectangle is the actual native rectangle');return {testID,bounds,nativeFullHeightPx:full,keyboard:e.keyboard,passed:true};
}

module.exports={settledFixtureSeeking,requiredScopeRecord,completeFixtureObservations,prepareFixtureProfile,prepareKeyboardTarget,assertFullKeyboardProof};
