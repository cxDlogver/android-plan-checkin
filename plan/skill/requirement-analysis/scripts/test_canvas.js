#!/usr/bin/env node
"use strict";
const fs=require("node:fs"),vm=require("node:vm"),assert=require("node:assert/strict");
const html=fs.readFileSync(process.argv[2],"utf8");
const embedded=html.match(/<script id="model" type="application\/json">([\s\S]*?)<\/script>/)[1];
const model=JSON.parse(embedded),script=[...html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)].at(-1)[1];
const elements=new Map(),paint=[];
function element(id){
  if(!elements.has(id)){
    const attrs=new Map(),classes=new Set();if(id==='toggleSidebar')attrs.set('aria-expanded','true');
    elements.set(id,{id,innerHTML:"",textContent:"",hidden:false,dataset:{},listeners:{},value:'',
      addEventListener(n,f){this.listeners[n]=f;},getBoundingClientRect(){return {width:900,height:600,left:0,top:0};},setPointerCapture(){},focus(){},parentElement:{},
      setAttribute(n,v){attrs.set(n,v);},getAttribute(n){return attrs.get(n);},classList:{toggle(n,v){if(v)classes.add(n);else classes.delete(n);},contains(n){return classes.has(n);}}});
  }return elements.get(id);
}
element('model').textContent=embedded;
const ctx=new Proxy({measureText(t){return {width:[...String(t)].length*7};},clearRect(){paint.length=0;},fillText(t){paint.push({text:t,color:this.fillStyle});}},{get:(t,k)=>k in t?t[k]:()=>{}});
element('graph').getContext=()=>ctx;
const sandbox={document:{getElementById:element,title:''},window:{devicePixelRatio:1},ResizeObserver:class{constructor(f){this.f=f;}observe(){this.f();}}};
vm.createContext(sandbox);const evaluate=s=>vm.runInContext(s,sandbox,{timeout:15000});evaluate(script);
const read=s=>JSON.parse(JSON.stringify(evaluate(s))),q=JSON.stringify,close=(a,b,message)=>assert.ok(Math.abs(a-b)<1e-7,message);

// The sidebar switch belongs to the rail outside the replaceable detail content.
const railIndex=html.indexOf('class="sidebar-toggle-rail"'),toggleIndex=html.indexOf('id="toggleSidebar"'),detailIndex=html.indexOf('<aside id="detail"');
assert.ok(railIndex>html.indexOf('</section>')&&toggleIndex>railIndex&&toggleIndex<detailIndex,'Sidebar edge switch survives hiding or replacing detail');
assert.ok(!html.slice(html.indexOf('class="toolbar"'),html.indexOf('class="canvas-area"')).includes('toggleSidebar'),'Sidebar control is next to detail');
const original=read('model'),positions=()=>read('allNodeBoxes.map(n=>({id:n.id,x:n.x,y:n.y}))'),view=()=>read('({scale,offsetX,offsetY})');
assert.equal(evaluate('focusId'),'','Full graph is the default');
assert.equal(evaluate('nodeBoxes.length'),model.states.length);
assert.ok(!html.includes('id="entityList"'),'No bottom selection list');
assert.ok(!elements.has('entityList'),'No hidden list dependency');
// Independent shortest-path oracle: cycles, shortcuts and multiple roots remain minimum-hop columns.
const hops=new Map(),queue=[];for(const s of model.states)if(s.isInitial){hops.set(s.id,0);queue.push(s.id);}
for(let i=0;i<queue.length;i++)for(const e of model.transitions.filter(e=>e.from===queue[i]))if(!hops.has(e.to)){hops.set(e.to,hops.get(queue[i])+1);queue.push(e.to);}
const boxes=read('allNodeBoxes');for(const n of boxes){assert.equal(n.x,35+(hops.get(n.id)||0)*500,'Shortest-hop column: '+n.id);if(model.states.find(s=>s.id===n.id).isInitial)assert.equal(n.x,35,'Initial state in first column');}
const visual=model.states.find(s=>s.visualFacts.length);assert.ok(visual,'Fixture has visual facts');
evaluate('selectState('+q(visual.id)+')');assert.ok(element('detail').innerHTML.includes(visual.visualFacts[0].statement));assert.ok(element('detail').innerHTML.includes('<img'));assert.ok(element('detail').innerHTML.includes(visual.source.find(s=>s.kind==='ui').structurePath));
const target=model.states.find(s=>s.id!==visual.id)||visual,edge=model.transitions[0];assert.ok(edge,'Fixture has an edge');
const beforePositions=positions(),beforeView=view(),beforePaths=read('edgePaths');
evaluate('(()=>{const n=nodeBoxes.find(n=>n.id==='+q(target.id)+');selectAt((n.x+n.w/2)*scale+offsetX,(n.y+n.h/2)*scale+offsetY);})()');
assert.ok(element('detail').innerHTML.includes(target.statement),'Canvas state selection');assert.equal(evaluate('focusId'),target.id,'Click focuses state');
const expectedNeighbors=[...new Set([target.id,...model.transitions.filter(e=>e.from===target.id||e.to===target.id).flatMap(e=>[e.from,e.to])])].sort();
assert.deepEqual(read('visibleStates.map(s=>s.id).sort()'),expectedNeighbors,'Only direct neighbors visible');
assert.deepEqual(read('visibleEdges.map(e=>e.id).sort()'),model.transitions.filter(e=>e.from===target.id||e.to===target.id).map(e=>e.id).sort(),'Only incident edges visible');
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
evaluate('resetLayout();selectEdge('+q(edge.id)+')');const edgeBefore=read('edgePaths.find(e=>e.id==='+q(edge.id)+')'),edgePoint=screen({x:edgeBefore.label.x+edgeBefore.label.w/2,y:edgeBefore.label.y+edgeBefore.label.h/2}),edgeScale=view().scale;
send('pointerdown',edgePoint.x,edgePoint.y);send('pointermove',edgePoint.x+35,edgePoint.y+27);send('pointerup',edgePoint.x+35,edgePoint.y+27);
const edgeAfter=read('edgePaths.find(e=>e.id==='+q(edge.id)+')');assert.deepEqual(edgeAfter.points[0],edgeBefore.points[0],'Dragged edge retains source attachment');assert.deepEqual(edgeAfter.points.at(-1),edgeBefore.points.at(-1),'Dragged edge retains target attachment');close(edgeAfter.points[20].x-edgeBefore.points[20].x,.75*35/edgeScale,'Curve bends horizontally');close(edgeAfter.points[20].y-edgeBefore.points[20].y,.75*27/edgeScale,'Curve bends vertically');
assert.equal(evaluate('selected.id'),edge.id);assert.equal(paint.at(-1).text,edgeAfter.text,'Selected edge label is painted above nodes and other edges');assert.equal(paint.at(-1).color,'#145a9f','Top edge is selected');
// Selected edge wins the hit test even where its route crosses a node.
evaluate('(()=>{const n=nodeBoxes[0],e=edgePaths.find(e=>e.id==='+q(edge.id)+');e.points=[{x:n.x+n.w/2,y:n.y+n.h/2},{x:n.x+n.w/2+1,y:n.y+n.h/2}];})()');
const overlap=read('({x:nodeBoxes[0].x+nodeBoxes[0].w/2,y:nodeBoxes[0].y+nodeBoxes[0].h/2})'),overlapScreen=screen(overlap);
assert.equal(evaluate('hitTest('+overlapScreen.x+','+overlapScreen.y+').id'),edge.id,'Selected top layer also wins pointer hit');evaluate('draw()');
for(const t of ['GIVEN','WHEN','THEN','直接来源'])assert.ok(element('detail').innerHTML.includes(t),t);
assert.equal(element('detail').innerHTML.includes('事后分支条件'),!!edge.condition);assert.equal(element('detail').innerHTML.includes('分支结果样例'),!!edge.condition);
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
evaluate('resetLayout();showOverview()');assert.deepEqual(read('model'),original,'View interactions never modify model');assert.equal(evaluate('edgeAdjustments.size'),0,'Reset clears curve adjustments');assert.deepEqual(positions(),beforePositions,'Reset restores default columns');assert.ok(element('detail').innerHTML.includes('全局约束'));
for(const p of ['需求澄清','检查结果','范围与门禁'])assert.ok(!element('detail').innerHTML.includes(p),'No process panel: '+p);
for(const p of ['clauses','clarifications','operations','gates','semanticReviews'])assert.ok(!(p in model),'No process field: '+p);
console.log('Canvas simulation passed: shortest-hop columns, full-graph default, focus visibility and position stability, node/edge dragging, selected-edge top layer, sidebar toggle, keyboard selection and unchanged model. Browser rendering is checked separately.');
