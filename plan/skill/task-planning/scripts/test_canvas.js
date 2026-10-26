#!/usr/bin/env node
"use strict";
const fs=require("node:fs"),vm=require("node:vm"),assert=require("node:assert/strict");
const html=fs.readFileSync(process.argv[2],"utf8");
const embedded=html.match(/<script id="model" type="application\/json">([\s\S]*?)<\/script>/)[1];
const artifactModel=JSON.parse(embedded),atomicView=Array.isArray(artifactModel.cases),script=[...html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)].at(-1)[1];
const elements=new Map(),paint=[];
function element(id){
  if(!elements.has(id)){
    const attrs=new Map(),classes=new Set();if(id==='toggleSidebar')attrs.set('aria-expanded','true');
    elements.set(id,{id,innerHTML:"",textContent:"",hidden:false,dataset:{},listeners:{},firstChild:{textContent:""},value:'',
      addEventListener(n,f){this.listeners[n]=f;},getBoundingClientRect(){return {width:900,height:600,left:0,top:0};},setPointerCapture(){},focus(){},parentElement:{},
      setAttribute(n,v){attrs.set(n,v);},getAttribute(n){return attrs.get(n);},classList:{toggle(n,v){if(v)classes.add(n);else classes.delete(n);},contains(n){return classes.has(n);}}});
  }return elements.get(id);
}
element('model').textContent=embedded;
for(const id of ['stateModel','atomicModel','taskPlan'])element(id).textContent=html.match(new RegExp('<script id="'+id+'" type="application/json">([\\s\\S]*?)</script>'))[1];
const ctx=new Proxy({measureText(t){return {width:[...String(t)].length*7};},clearRect(){paint.length=0;},fillText(t){paint.push({text:t,color:this.fillStyle});}},{get:(t,k)=>k in t?t[k]:()=>{}});
element('graph').getContext=()=>ctx;
const sandbox={document:{getElementById:element,querySelector:selector=>element(selector),title:''},window:{devicePixelRatio:1},ResizeObserver:class{constructor(f){this.f=f;}observe(){this.f();}}};
vm.createContext(sandbox);const evaluate=s=>vm.runInContext(s,sandbox,{timeout:15000});evaluate(script);
const read=s=>JSON.parse(JSON.stringify(evaluate(s))),q=JSON.stringify,close=(a,b,message)=>assert.ok(Math.abs(a-b)<1e-7,message);

// The sidebar switch belongs to the rail outside the replaceable detail content.
const railIndex=html.indexOf('class="sidebar-toggle-rail"'),toggleIndex=html.indexOf('id="toggleSidebar"'),detailIndex=html.indexOf('<aside id="detail"');
assert.ok(railIndex>html.indexOf('</section>')&&toggleIndex>railIndex&&toggleIndex<detailIndex,'Sidebar edge switch survives hiding or replacing detail');
assert.ok(!html.slice(html.indexOf('class="toolbar"'),html.indexOf('class="canvas-area"')).includes('toggleSidebar'),'Sidebar control is next to detail');
const model=read('model'),original=read('model'),originalArtifact=read('artifact'),originalStates=read('stateModel'),positions=()=>read('allNodeBoxes.map(n=>({id:n.id,x:n.x,y:n.y}))'),view=()=>read('({scale,offsetX,offsetY})');
assert.equal(evaluate('focusId'),'','Full graph is the default');
assert.equal(evaluate('nodeBoxes.length'),model.states.length);
assert.ok(!html.includes('id="entityList"'),'No bottom selection list');
assert.ok(!elements.has('entityList'),'No hidden list dependency');
if(!model.states.length){
  assert.equal(evaluate('edgePaths.length'),0);assert.ok(element('detail').innerHTML.includes('全局约束'));
  element('toggleSidebar').onclick();assert.equal(element('detail').hidden,true);element('toggleSidebar').onclick();assert.equal(element('detail').hidden,false);
  evaluate('zoom(1.2);resetLayout();showOverview()');assert.deepEqual(read('artifact'),originalArtifact);assert.deepEqual(read('stateModel'),originalStates);
  console.log('Canvas simulation passed: empty graph, global constraints, sidebar and unchanged source models. Browser rendering is checked separately.');process.exit(0);
}
// Independent shortest-path oracle: cycles, shortcuts and multiple roots remain minimum-hop columns.
const hops=new Map(),queue=[];for(const s of model.states)if(s.isInitial){hops.set(s.id,0);queue.push(s.id);}
for(let i=0;i<queue.length;i++)for(const e of model.transitions.filter(e=>e.from===queue[i]))if(!hops.has(e.to)){hops.set(e.to,hops.get(queue[i])+1);queue.push(e.to);}
const boxes=read('allNodeBoxes');for(const n of boxes){assert.equal(n.x,35+(hops.get(n.id)||0)*500,'Shortest-hop column: '+n.id);if(model.states.find(s=>s.id===n.id).isInitial)assert.equal(n.x,35,'Initial state in first column');}
const visual=model.states.find(s=>artifactModel.cases.find(c=>c.id===s.id)?.kind==='primary')||model.states[0];
evaluate('selectState('+q(visual.id)+')');for(const title of ['到达路径','前置条件','当前操作','预期结果','验收方式与证据','当前验收状态'])assert.ok(element('detail').innerHTML.includes(title),'Readable case section '+title);
const target=model.states.find(s=>s.id!==visual.id)||visual,edge=model.transitions[0];
const beforePositions=positions(),beforeView=view(),beforePaths=read('edgePaths');
evaluate('(()=>{const n=nodeBoxes.find(n=>n.id==='+q(target.id)+');selectAt((n.x+n.w/2)*scale+offsetX,(n.y+n.h/2)*scale+offsetY);})()');
assert.ok(element('detail').innerHTML.includes(target.title),'Canvas state selection');assert.equal(evaluate('focusId'),target.id,'Click focuses state');
let expectedNodes,expectedEdges;
if(atomicView){
  const sequence=artifactModel.coverage.sequence,end=sequence.indexOf(target.id);let start=0;for(let i=end;i>=0;i--)if(model.states.find(s=>s.id===sequence[i]).isInitial){start=i;break;}
  const prefix=sequence.slice(start,end+1),pairs=new Set(prefix.slice(1).map((value,i)=>JSON.stringify([prefix[i],value])));
  expectedNodes=[...new Set(prefix)].sort();expectedEdges=artifactModel.edges.filter(e=>pairs.has(JSON.stringify([e.from,e.to]))).map(e=>e.id).sort();
  assert.ok(element('detail').innerHTML.includes('到达路径'));assert.ok(!element('detail').innerHTML.includes('迁移直接来源'));
}else{expectedNodes=[...new Set([target.id,...model.transitions.filter(e=>e.from===target.id||e.to===target.id).flatMap(e=>[e.from,e.to])])].sort();expectedEdges=model.transitions.filter(e=>e.from===target.id||e.to===target.id).map(e=>e.id).sort();}
assert.deepEqual(read('visibleStates.map(s=>s.id).sort()'),expectedNodes,'Correct focus path or neighborhood');
assert.deepEqual(read('visibleEdges.map(e=>e.id).sort()'),expectedEdges,'Only selected arrival path edges or incident state edges visible');
assert.deepEqual(positions(),beforePositions,'Focus keeps all node positions');assert.deepEqual(view(),beforeView,'Focus keeps viewport');
for(const path of read('edgePaths'))assert.deepEqual(path,beforePaths.find(e=>e.id===path.id),'Focus keeps curve and label: '+path.id);
evaluate('(()=>{const n=nodeBoxes.find(n=>n.id==='+q(target.id)+');selectAt((n.x+n.w/2)*scale+offsetX,(n.y+n.h/2)*scale+offsetY);})()');
assert.equal(evaluate('focusId'),'','Second click restores full graph');assert.deepEqual(positions(),beforePositions);assert.deepEqual(view(),beforeView);
// Drag through the actual pointer listeners; coordinates are screen pixels.
function send(type,x,y){element('graph').listeners[type]({clientX:x,clientY:y,pointerId:1,button:0});}
function screen(p){const v=view();return {x:p.x*v.scale+v.offsetX,y:p.y*v.scale+v.offsetY};}
const nodeBefore=read('allNodeBoxes.find(n=>n.id==='+q(target.id)+')'),nodePoint=screen({x:nodeBefore.x+nodeBefore.w/2,y:nodeBefore.y+nodeBefore.h/2}),dragScale=view().scale;
send('pointerdown',nodePoint.x,nodePoint.y);send('pointermove',nodePoint.x+31,nodePoint.y+19);send('pointerup',nodePoint.x+31,nodePoint.y+19);
const nodeAfter=read('allNodeBoxes.find(n=>n.id==='+q(target.id)+')');close(nodeAfter.x-nodeBefore.x,31/dragScale,'Node horizontal drag');close(nodeAfter.y-nodeBefore.y,19/dragScale,'Node vertical drag');assert.equal(evaluate('focusId'),'','Node drag does not toggle focus');assert.deepEqual(view(),beforeView,'Node drag does not pan');
const draggedPositions=positions();evaluate('focusGraph('+q(target.id)+');focusGraph("")');assert.deepEqual(positions(),draggedPositions,'Manual positions survive focus and restore');
if(edge){
evaluate('resetLayout();selectEdge('+q(edge.id)+')');const edgeBefore=read('edgePaths.find(e=>e.id==='+q(edge.id)+')'),edgePoint=screen({x:edgeBefore.label.x+edgeBefore.label.w/2,y:edgeBefore.label.y+edgeBefore.label.h/2}),edgeScale=view().scale;
send('pointerdown',edgePoint.x,edgePoint.y);send('pointermove',edgePoint.x+35,edgePoint.y+27);send('pointerup',edgePoint.x+35,edgePoint.y+27);
const edgeAfter=read('edgePaths.find(e=>e.id==='+q(edge.id)+')');assert.deepEqual(edgeAfter.points[0],edgeBefore.points[0],'Dragged edge retains source attachment');assert.deepEqual(edgeAfter.points.at(-1),edgeBefore.points.at(-1),'Dragged edge retains target attachment');close(edgeAfter.points[20].x-edgeBefore.points[20].x,.75*35/edgeScale,'Curve bends horizontally');close(edgeAfter.points[20].y-edgeBefore.points[20].y,.75*27/edgeScale,'Curve bends vertically');
assert.equal(evaluate('selected.id'),edge.id);assert.equal(paint.at(-1).text,edgeAfter.text,'Selected edge label is painted above nodes and other edges');assert.equal(paint.at(-1).color,'#145a9f','Top edge is selected');
// Selected edge wins the hit test even where its route crosses a node.
const savedRoute=read('edgePaths.find(e=>e.id==='+q(edge.id)+').points');
evaluate('(()=>{const n=nodeBoxes[0],e=edgePaths.find(e=>e.id==='+q(edge.id)+');e.points=[{x:n.x+n.w/2,y:n.y+n.h/2},{x:n.x+n.w/2+1,y:n.y+n.h/2}];})()');
const overlap=read('({x:nodeBoxes[0].x+nodeBoxes[0].w/2,y:nodeBoxes[0].y+nodeBoxes[0].h/2})'),overlapScreen=screen(overlap);
assert.equal(evaluate('hitTest('+overlapScreen.x+','+overlapScreen.y+').id'),edge.id,'Selected top layer also wins pointer hit');evaluate('edgePaths.find(e=>e.id==='+q(edge.id)+').points='+q(savedRoute)+';draw()');
for(const t of [(artifactModel.edges.find(e=>e.id===edge.id).kind==='restart'?'重新准备入口':'前项终态与后项前提一致')])assert.ok(element('detail').innerHTML.includes(t),t);
assert.equal(element('detail').innerHTML.includes('事后分支条件'),!!edge.condition);assert.equal(element('detail').innerHTML.includes('分支结果样例'),!!edge.condition);
}
const beforeFold=positions(),foldView=view(),foldDetail=element('detail').innerHTML;
for(let cycle=0;cycle<3;cycle++){
  element('toggleSidebar').onclick();assert.equal(element('detail').hidden,true);assert.equal(element('toggleSidebar').getAttribute('aria-expanded'),'false');assert.equal(element('layout').classList.contains('sidebar-collapsed'),true);
  assert.equal(element('sidebarToggleText').textContent,'展开详情');assert.equal(element('sidebarToggleIcon').textContent,'‹');assert.equal(element('toggleSidebar').getAttribute('aria-label'),'展开详情侧栏');
  // The control reads actual visibility, so stale ARIA metadata cannot break the next click.
  element('toggleSidebar').setAttribute('aria-expanded','true');element('toggleSidebar').onclick();assert.equal(element('detail').hidden,false);assert.equal(element('toggleSidebar').getAttribute('aria-expanded'),'true');assert.equal(element('layout').classList.contains('sidebar-collapsed'),false);
  assert.equal(element('sidebarToggleText').textContent,'收起详情');assert.equal(element('sidebarToggleIcon').textContent,'›');assert.equal(element('detail').innerHTML,foldDetail,'Sidebar retains content');
}
element('toggleSidebar').onclick();evaluate('selectState('+q(target.id)+')');assert.equal(element('detail').hidden,true,'Selecting a state keeps sidebar collapsed');const hiddenSelection=element('detail').innerHTML;element('toggleSidebar').onclick();assert.equal(element('detail').innerHTML,hiddenSelection,'Expand reveals latest selected state');
assert.deepEqual(positions(),beforeFold);assert.deepEqual(view(),foldView);
// Blank-space drag pans rather than moving an entity.
const panView=view(),panNodes=positions();send('pointerdown',-10000,-10000);send('pointermove',-9975,-9985);send('pointerup',-9975,-9985);close(view().offsetX-panView.offsetX,25,'Background pan X');close(view().offsetY-panView.offsetY,15,'Background pan Y');assert.deepEqual(positions(),panNodes);
element('graph').listeners.keydown({key:'ArrowRight',shiftKey:false,preventDefault(){}});assert.equal(evaluate('selected.type'),'state');element('graph').listeners.keydown({key:'Enter',preventDefault(){}});assert.ok(evaluate('focusId'));element('graph').listeners.keydown({key:'Escape',preventDefault(){}});assert.equal(evaluate('focusId'),'');
evaluate('resetLayout();showOverview()');assert.deepEqual(read('model'),original,'View interactions never modify model');assert.deepEqual(read('artifact'),originalArtifact,'Artifact unchanged');assert.deepEqual(read('stateModel'),originalStates,'Source state graph unchanged');assert.equal(evaluate('edgeAdjustments.size'),0,'Reset clears curve adjustments');assert.deepEqual(positions(),beforePositions,'Reset restores default columns');assert.ok(element('detail').innerHTML.includes('全局约束'));
if(atomicView){
  const originalAtomic=JSON.parse(element('atomicModel').textContent),originalPlan=JSON.parse(element('taskPlan').textContent);
  const titles=['到达路径','前置条件','当前操作','预期结果','验收方式与证据','当前验收状态'];
  const forbidden=['直接来源','structurePath','nodeIds','bindingMap','controlNodeId','ctx.','record-response','not_run','dataProfileId','原截图','相关任务','字段契约'];
  for(const c of artifactModel.cases){const r=originalAtomic.requirements.find(r=>r.id===c.requirementId),t=r?originalStates.transitions.find(t=>t.id===r.transitionId):null;evaluate('selectState('+q(c.id)+')');const content=element('detail').innerHTML;for(const label of [...titles,'视觉验收','功能验收','未执行'])assert.ok(content.includes(label),'Case detail '+c.id+' '+label);assert.equal(content.includes('本次结果分支'),!!t?.condition,'Actual branch only: '+c.id);for(const word of forbidden)assert.ok(!content.includes(word),'No technical/source leakage '+c.id+' '+word);if(t){assert.ok(content.includes(originalStates.states.find(s=>s.id===t.from).title));assert.ok(content.includes(originalStates.states.find(s=>s.id===t.to).title));}
    const target=c.kind==='primary'?originalStates.states.find(s=>s.id===c.expected.stateId):null,expectedImages=[...new Set((target?.source||[]).filter(r=>r.kind==='ui').map(r=>r.screenshotPath))];
    const images=[...content.matchAll(/<img\b[^>]*src="([^"]+)"/g)].map(m=>m[1].replaceAll('&amp;','&'));
    assert.equal(images.length,expectedImages.length,'Only target UI images, deduplicated: '+c.id);
    for(let index=0;index<images.length;index++){const path=require('node:path'),actualFile=path.resolve(path.dirname(process.argv[2]),decodeURIComponent(images[index])),expectedFile=path.resolve(path.dirname(process.argv[2]),path.dirname(artifactModel.stateGraph.path),expectedImages[index]);assert.equal(actualFile,expectedFile,'Image resolved relative to bound state graph');assert.ok(fs.statSync(actualFile).isFile(),'Expected image exists');}
    if(images.length){const expectedStart=content.indexOf('<h3>预期结果</h3>'),evidenceStart=content.indexOf('<h3>验收方式与证据</h3>');assert.ok(content.indexOf('<img')>expectedStart&&content.lastIndexOf('<img')<evidenceStart,'UI image belongs to expected result');assert.ok(content.includes('预期 UI 参考图'));assert.ok(content.includes('不代表已采集到实际验收证据'));assert.ok(content.includes('查看完整尺寸'));}else assert.ok(!content.includes('预期 UI 图'),'No unrelated or placeholder UI image');
    assert.ok(!content.slice(content.indexOf('<h3>当前验收状态</h3>')).includes('<img'),'Reference is not actual execution evidence');
    for(const [name,g]of Object.entries(c.acceptance)){assert.ok(content.includes((name==='visual'?'视觉验收':'功能验收')+' · '+(g.applicable?'需要验收':'不适用')));for(const check of g.checks){assert.ok(content.includes(evaluate('typeNames['+q(check.testType)+']')));assert.ok(content.includes(evaluate('environmentNames['+q(check.environment)+']')));for(const proof of check.evidence)assert.ok(content.includes(evaluate('evidenceNames['+q(proof.form)+']')),'Readable evidence form');}}}
  for(const e of artifactModel.edges){evaluate('selectEdge('+q(e.id)+')');const content=element('detail').innerHTML;assert.ok(content.includes(e.kind==='restart'?'重新准备入口':'前项终态与后项前提一致'));for(const word of forbidden)assert.ok(!content.includes(word),'No edge metadata leakage');if(e.kind==='handoff')assert.ok(content.includes(originalStates.states.find(s=>s.id===e.viaStateId).title));}
  assert.equal(evaluate('expectedUIHTML(null)'), '');assert.equal(evaluate('expectedUIHTML({title:"无界面结果",source:[]})'),'');
  for(const raw of ['','https://example.com/image.png','file:///C:/image.png','//server/image.png','/absolute.png'])assert.equal(evaluate('expectedImagePath('+q(raw)+')'),null,'No external/absolute image paths');
  const visualState=originalStates.states.find(s=>s.source.some(r=>r.kind==='ui'));
  if(visualState){const ref=visualState.source.find(r=>r.kind==='ui'),input={title:'重复图片',source:[ref,ref]};const dedup=evaluate('expectedUIHTML('+q(input)+')');assert.equal((dedup.match(/<img\b/g)||[]).length,1,'Duplicate UI references render once');}
  assert.deepEqual(read('typeNames'),{script:'脚本验收',browser:'浏览器验收'},'Exactly two readable acceptance types');
  // Preconditions follow the selected occurrence, including its actual predecessor.
  for(let index=0;index<artifactModel.coverage.sequence.length;index++){const id=artifactModel.coverage.sequence[index],c=artifactModel.cases.find(c=>c.id===id),previous=index?artifactModel.coverage.sequence[index-1]:null,edge=previous?artifactModel.edges.find(e=>e.from===previous&&e.to===id):null;evaluate('selectedArrivalIndex='+index+';selectState('+q(id)+')');const content=element('detail').innerHTML;if(c.kind!=='primary')assert.ok(content.includes('独立准备本项检查'));else if(edge?.kind==='handoff'){assert.ok(content.includes('上一用例'));assert.ok(content.includes(artifactModel.cases.find(c=>c.id===previous).operation.label));assert.ok(content.includes(originalStates.states.find(s=>s.id===c.given.stateId).title));}else assert.ok(content.includes(index?'重新进入起点':'从起点开始'));}
  const repeated=artifactModel.cases.find(r=>artifactModel.coverage.sequence.filter(value=>value===r.id).length>1);
  if(repeated){const indices=artifactModel.coverage.sequence.flatMap((value,index)=>value===repeated.id?[index]:[]),beforeSwitch=positions(),switchView=view();evaluate('focusGraph('+q(repeated.id)+');selectState('+q(repeated.id)+')');element('arrivalOccurrence').onchange({target:{value:String(indices.at(-1))}});assert.equal(evaluate('selectedArrivalIndex'),indices.at(-1));assert.deepEqual(positions(),beforeSwitch);assert.deepEqual(view(),switchView);assert.equal(read('arrivalPath('+q(repeated.id)+').ids').at(-1),repeated.id);evaluate('focusGraph("")');}
  // Execution projection is read-only UI data, including partial/stale outcomes.
  const first=artifactModel.cases[0],savedExecution=read('artifact.cases[0].execution');
  for(const [status,label] of [['passed','通过'],['failed','未通过'],['partial','部分完成'],['blocked','暂不能执行'],['stale','证据已失效']]){
    const record={status,actual:'已取得本次实际观察。',evidence:[{form:'assertion-report',path:'../code-execution/evidence/result.json'}],checks:[{aspect:'visual',checkIndex:0,status,actual:'实际观察可读。',evidence:[{form:'assertion-report',path:'../code-execution/evidence/result.json'}]}]};
    evaluate('artifact.cases[0].execution='+q(record)+';selectState('+q(first.id)+')');
    assert.ok(element('detail').innerHTML.includes(label));assert.ok(element('detail').innerHTML.includes('实际观察可读。'));
    assert.ok(element('detail').innerHTML.includes('../code-execution/evidence/result.json'));
    evaluate('showOverview()');assert.ok(element('detail').innerHTML.includes(label+' 1 项'));
  }
  for(const path of ['https://example.com/x','file:///C:/x','/absolute','\\server\\x'])assert.ok(!evaluate('evidenceLink('+q({form:'assertion-report',path})+')').includes('<a'),'Evidence link rejects external paths');
  evaluate('artifact.cases[0].execution='+q(savedExecution));
  evaluate('showOverview()');assert.deepEqual(read('artifact'),originalArtifact);assert.deepEqual(read('stateModel'),originalStates);
}
assert.deepEqual(read('taskPlan'),JSON.parse(element('taskPlan').textContent));assert.deepEqual(read('atomicModel'),JSON.parse(element('atomicModel').textContent));
for(const p of ['需求澄清','检查结果','范围与门禁'])assert.ok(!element('detail').innerHTML.includes(p),'No process panel: '+p);
for(const p of ['clauses','clarifications','operations','gates','semanticReviews'])assert.ok(!(p in model),'No process field: '+p);
console.log('Test Case Canvas simulation passed: readable six-part sidebar, two acceptance types, expected target UI figures, aspect/evidence labels, actual predecessor for every visit, no source/variable leakage, shortest-hop columns, full-graph default, focus visibility and position stability, node/edge dragging, selected-edge top layer, sidebar toggle, keyboard selection and unchanged model. Browser rendering is checked separately.');
