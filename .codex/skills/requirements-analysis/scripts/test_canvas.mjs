import vm from 'node:vm';
import fs from 'node:fs';
import {pathToFileURL} from 'node:url';

export function verifyCanvasReview(html){
 const data=JSON.parse(html.match(/<script id="data" type="application\/json">([\s\S]*?)<\/script>/)[1]);
 const program=html.match(/<script>([\s\S]*?)<\/script>/)[1];
 const registry=new Map(),contexts=new Map(),issues=[];
 const check=(truth,message)=>{if(!truth)issues.push(message);};
 class Context{
  constructor(){this.calls=[];}
  measureText(text){return {width:Array.from(text).length*8};}
 }
 for(const name of ['setTransform','clearRect','save','translate','scale','beginPath','moveTo','lineTo','quadraticCurveTo','closePath','fill','stroke','bezierCurveTo','fillText','fillRect','strokeRect','restore'])Context.prototype[name]=function(...args){this.calls.push([name,...args]);if(this.calls.length>10000)this.calls.splice(0,5000);};
 class Element{
  constructor(tag,id=''){this.tagName=tag;this.id=id;this.children=[];this.attrs={};this.style={setProperty(k,v){this[k]=v;}};this.value='';this.hidden=false;this._text='';this.width=0;this.height=0;}
  append(...items){this.children.push(...items);}
  replaceChildren(...items){this.children=items;this._text='';}
  set textContent(v){this._text=String(v);this.children=[];}
  get textContent(){return this._text+this.children.map(c=>c.textContent).join('');}
  setAttribute(k,v){this.attrs[k]=String(v);}
  getAttribute(k){return this.attrs[k];}
  getBoundingClientRect(){return {left:0,top:0,width:this.id==='minimap'?210:1440,height:this.id==='header'?120:this.id==='minimap'?120:780};}
  getContext(){if(!contexts.has(this))contexts.set(this,new Context());return contexts.get(this);}
  setPointerCapture(){} releasePointerCapture(){}
 }
 for(const match of html.matchAll(/id="([^"]+)"/g))registry.set(match[1],new Element('div',match[1]));
 registry.get('data').textContent=JSON.stringify(data);
 registry.get('details').hidden=true;registry.get('tooltip').hidden=true;
 const document={getElementById:id=>registry.get(id),createElement:tag=>new Element(tag),documentElement:new Element('html')};
 const window={innerWidth:1440,innerHeight:900,devicePixelRatio:2,addEventListener(){}};
 const context=vm.createContext({document,window,requestAnimationFrame:callback=>callback()});
 new vm.Script(program).runInContext(context);
 const run=source=>vm.runInContext(source,context),graph=registry.get('graph');
 const initial=run('JSON.stringify([D.states,D.transitions,D.requirements,D.starts])');
 check(run('graph().nodes.length')===data.states.length,'state graph node coverage');
 check(run('geometries.length')===data.transitions.length,'state graph edge coverage');
 check(graph.width===2880&&graph.height===1560,'device pixel ratio / viewport sizing');
 check(run('graph().starts.length')===data.starts.length,'all real starts retained');
 let stateClicks=0;
 for(const state of data.states){
  run('selectState('+JSON.stringify(state.id)+')');
  check(registry.get('detail-kind').textContent==='状态','state click kind');
  check(registry.get('detail-title').textContent===state.title,'state click target');
  const info=run('routeFor('+JSON.stringify(state.id)+')');
  if(info){let end=info.start;for(const id of info.route){const edge=data.transitions.find(e=>e.id===id);check(edge.from===end,'route continuity');end=edge.to;}check(end===state.id,'route stops at current state');}
  check(run('geometries.length')===data.transitions.length,'selection must not prune graph');stateClicks++;
 }
 let transitionClicks=0;
 for(const edge of data.transitions){
  run('selectTransition('+JSON.stringify(edge.id)+')');
  check(registry.get('detail-kind').textContent.includes('原子需求'),'arrow opens atomic requirement');
  check(registry.get('detail-title').textContent===run('human('+JSON.stringify(edge.event)+')'),'arrow opens correct event');
  check(!registry.get('detail-body').textContent.includes('从真实起点到当前状态'),'arrow detail must not mix state route');
  const w=data.transitionValidation?.transitions?.[edge.id];
  if(w){check(registry.get('detail-body').textContent.includes('本条迁移的可执行路径'),'per-edge witness displayed');if(['finite_domain_passed','no_guard_constraints'].includes(w.status))check(registry.get('detail-body').textContent.includes('应用功能尚未验收'),'model feasibility not product acceptance');}
  transitionClicks++;
 }
 const start=data.starts[0];
 run('centerNode('+JSON.stringify(start)+')');
 const point=run('(()=>{const p=position('+JSON.stringify(start)+'),v=views[mode];return {x:(p.x+p.w/2)*v.scale+v.x,y:(p.y+p.h/2)*v.scale+v.y};})()');
 const ev=(x,y)=>({button:0,pointerId:1,clientX:x,clientY:y,preventDefault(){}});
 graph.onpointerdown(ev(point.x,point.y));graph.onpointerup(ev(point.x,point.y));
 check(run('selected.kind')==='state'&&run('selected.id')===start,'canvas node hit dispatch');
 const xBefore=run('position('+JSON.stringify(start)+').x');
 graph.onpointerdown(ev(point.x,point.y));graph.onpointermove(ev(point.x+70,point.y+25));graph.onpointerup(ev(point.x+70,point.y+25));
 check(run('position('+JSON.stringify(start)+').x')>xBefore,'node dragging');
 check(run('geometries.length')===data.transitions.length,'node drag keeps edges');
 const beforeWorld=run('world(500,300)');run('zoomAt(1.4,500,300)');const afterWorld=run('world(500,300)');
 check(Math.abs(beforeWorld.x-afterWorld.x)<1e-8&&Math.abs(beforeWorld.y-afterWorld.y)<1e-8,'zoom retains pointer anchor');
 const blank=run('(()=>{for(let x=3;x<viewport.w;x+=130)for(let y=3;y<viewport.h;y+=90)if(!hitTest(x,y))return {x,y};return null;})()');
 if(blank){const old=run('views[mode].x');graph.onpointerdown(ev(blank.x,blank.y));graph.onpointermove(ev(blank.x+35,blank.y+30));graph.onpointerup(ev(blank.x+35,blank.y+30));check(run('views[mode].x')===old+35,'background dragging pans');}else check(false,'no blank area for pan test');
 registry.get('fit').onclick();check(Number.isFinite(run('views[mode].scale')),'fit has finite scale');
 let arrowHit=false;
 for(const shape of run('geometries')){for(const point of shape.sample){const v=run('views[mode]'),x=point.x*v.scale+v.x,y=point.y*v.scale+v.y;const hit=run('hitTest('+x+','+y+')');if(hit?.kind==='edge'){graph.onpointerdown(ev(x,y));graph.onpointerup(ev(x,y));check(run('selected.kind')==='transition'&&run('selected.id')===hit.id,'canvas arrow hit dispatch');arrowHit=true;break;}}if(arrowHit)break;}
 check(arrowHit||data.transitions.length===0,'at least one arrow can be hit');
 run("switchMode('requirement')");
 check(run('graph().nodes.length')===data.requirements.length,'all requirement nodes in coverage support');
 check(run('geometries.length')===data.requirementGraph.edges.length,'only route-used edges');
 const pairUses=new Map();let visits=0;for(const route of data.requirementGraph.traversal.routes){let state=route.entryStateId;check(data.starts.includes(state),'coverage route real start');for(const id of route.transitionIds){const t=data.transitions.find(t=>t.id===id);check(t.from===state,'coverage route must not teleport');state=t.to;visits++;}route.requirementIds.slice(1).forEach((id,i)=>{const key=JSON.stringify([route.requirementIds[i],id]);pairUses.set(key,(pairUses.get(key)||0)+1);});}check(visits===data.requirementGraph.traversal.totalVisits,'coverage total visits');check(pairUses.size===data.requirementGraph.edges.length,'only used continuation pairs retained');for(const edge of data.requirementGraph.edges)check(pairUses.get(JSON.stringify([edge.from,edge.to]))===edge.usageCount,'continuation multiplicity');
 run('validationDetail()');check(registry.get('detail-body').textContent.includes('需求模型'),'model acceptance entry');if(data.transitionValidation?.caseCounts)check(registry.get('detail-body').textContent.includes('已声明分支可执行'),'case validation summary');
 run('coverageDetail()');check(registry.get('detail-body').textContent.includes(String(visits)),'coverage visits visible');if(data.requirementGraph.traversal.routes.some(r=>r.contextCheck.status==='conflict'))check(registry.get('detail-body').textContent.includes('条件冲突'),'context conflict visible');
 if(data.requirementGraph.traversal.optimality==='not_proven')check(registry.get('detail-body').textContent.includes('没有证明全局最短'),'heuristic must not claim optimum');
 check(registry.get('root-legend').textContent==='入口需求','requirement entries are distinct from business state starts');
 if(data.requirements.length)run('selectRequirement('+JSON.stringify(data.requirements[0].id)+')');
 for(const id of data.requirementGraph.reduction.uncoveredRequirementIds){run('selectRequirement('+JSON.stringify(id)+')');check(registry.get('detail-status').textContent.includes('未覆盖'),'unreachable requirement clearly marked');}

 if(data.requirementGraph.edges.length){run('selectEdge('+JSON.stringify(data.requirementGraph.edges[0].id)+')');check(registry.get('detail-kind').textContent.includes('业务衔接'),'requirement arrow is relation, not invented requirement');}
 const rootSelect=registry.get('root-choice');
 check(rootSelect.children.length===data.starts.length+1,'root selector only documented starts plus all');
 for(const root of data.starts){rootSelect.value=root;rootSelect.onchange();check(run('rootChoice')===root,'switch documented root');}
 for(const id of data.requirementGraph.reduction.uncoveredRequirementIds){run('selectRequirement('+JSON.stringify(id)+')');for(const root of data.starts){rootSelect.value=root;rootSelect.onchange();check(registry.get('detail-status').textContent.includes('未覆盖'),'root switch preserves uncovered detail');}}

 check(run('JSON.stringify([D.states,D.transitions,D.requirements,D.starts])')===initial,'view interactions must not mutate requirements');
 check(!issues.length,'synthetic canvas checks completed');
 return {scope:'Synthetic Canvas/DOM logic, not a real browser or visual acceptance',states:data.states.length,transitions:data.transitions.length,requirements:data.requirements.length,continuationEdges:data.requirementGraph.edges.length,roots:data.starts.length,stateClicks,transitionClicks,dragPanZoom:'exercised',problems:issues,browserObserved:false,semanticDigest:data.semanticDigest};
}
if(typeof process!=='undefined'&&process.argv[1]&&import.meta.url===pathToFileURL(process.argv[1]).href){const result=verifyCanvasReview(fs.readFileSync(process.argv[2],'utf8'));console.log(JSON.stringify(result,null,2));if(result.problems.length)process.exitCode=1;}
