// Synthetic DOM/Canvas checks: no real-browser or product acceptance claim.
import fs from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';
export function verifyReview(file,sourceFile){
 const html=fs.readFileSync(file,'utf8'),blocks=[...html.matchAll(/<script([^>]*)>([\s\S]*?)<\/script>/g)];
 const data=blocks.find(x=>x[1].includes('id="data"'))[2],testData=blocks.find(x=>x[1].includes('id="test-data"'))[2];
 const source=JSON.parse(data),payload=JSON.parse(testData),elements=new Map(),frames=[];
 class Element{
  constructor(id=''){this.id=id;this.value='';this.hidden=false;this.children=[];this.attrs={};this.style={setProperty(){}};this._text='';this.width=1280;this.height=720;}
  get textContent(){return this._text+this.children.map(c=>c.textContent??String(c)).join('');}set textContent(v){this._text=String(v);this.children=[];}
  append(...items){this.children.push(...items);}appendChild(e){this.append(e);}replaceChildren(...items){this.children=items;this._text='';}
  setAttribute(k,v){this.attrs[k]=v;}addEventListener(k,f){this['on'+k]=f;}setPointerCapture(){}releasePointerCapture(){}
  getBoundingClientRect(){return {left:0,top:0,width:1280,height:this.id==='header'?130:720};}
  getContext(){return new Proxy({measureText:t=>({width:[...t].length*8})},{get:(o,k)=>k in o?o[k]:(()=>{}),set:(o,k,v)=>(o[k]=v,true)});}
 }
 const get=id=>{if(!elements.has(id))elements.set(id,new Element(id));return elements.get(id)};get('data').textContent=data;get('test-data').textContent=testData;
 const document={getElementById:get,createElement:()=>new Element(),documentElement:new Element()};
 const sandbox=vm.createContext({document,window:{devicePixelRatio:1,innerWidth:1280,innerHeight:850,addEventListener(){}},requestAnimationFrame:f=>frames.push(f),console});
 const run=s=>vm.runInContext(s,sandbox,{timeout:30000});
 for(const block of blocks.filter(b=>!b[1].includes('application/json')))run(block[2]);
 const flush=()=>{while(frames.length)frames.shift()();};flush();const checks=[];
 assert.equal(run('testMode'),true);assert.equal(get('test-mode').attrs['aria-pressed'],'true');checks.push('默认测试图，保留三个视图入口');
 if(sourceFile){const sourceHtml=fs.readFileSync(sourceFile,'utf8');const src=[...sourceHtml.matchAll(/<script([^>]*)>([\s\S]*?)<\/script>/g)];assert.equal(data,src.find(x=>x[1].includes('id="data"'))[2]);assert.equal(blocks.find(x=>!x[1].includes('application/json'))[2],src.find(x=>!x[1].includes('application/json'))[2]);checks.push('完整复用上游数据与原绘图脚本');}
 assert.equal(run('graph().nodes.length'),source.requirementGraph.nodes.length);assert.equal(run('graph().edges.length'),source.requirementGraph.edges.length);
 assert.equal(run('new Set(graph().edges.map(e=>JSON.stringify([e.from,e.to]))).size'),source.requirementGraph.edges.length);
 assert.equal(run('JSON.stringify(graph().starts)'),JSON.stringify(source.requirementStarts));checks.push('节点、唯一有向边和入口一一对应');
 const positions=run('JSON.stringify(graph().positions)');run("switchMode('requirement')");flush();assert.equal(run('JSON.stringify(graph().positions)'),positions);assert.equal(get('requirement-mode').attrs['aria-pressed'],'true');run("switchMode('test')");flush();assert.equal(run('JSON.stringify(graph().positions)'),positions);checks.push('测试图与需求图复用同一布局');
 run("switchMode('state')");flush();assert.equal(run('graph().nodes.length'),source.states.length);assert.equal(run('graph().edges.length'),source.transitions.length);run('selectState(D.starts[0])');flush();assert.ok(get('detail-body').textContent.includes('从真实起点到当前状态'));checks.push('原完整状态图和状态详情保留');
 run("switchMode('test');selectRequirement(D.requirementStarts[0])");flush();const text=get('detail-body').textContent;
 for(const label of ['准备条件','测试步骤','功能预期','视觉预期','CSS 设计值','验收结论与证据','实际：待记录','证据：待采集','完整链路'])assert.ok(text.includes(label),label);
 assert.ok(!text.includes('"transitionId"'));checks.push('测试详情含步骤、功能、UI/CSS、链路、结果及证据槽');
 run('selectEdge(graph().edges[0].id)');flush();assert.ok(get('detail-body').textContent.includes('后项条件'));assert.ok(get('detail-body').textContent.includes('所属需求路线'));checks.push('箭头展示前后测试、条件和路线步次');
 if(source.requirementGraph.traversal.routes.some(r=>r.contextCheck.status==='conflict')){run('coverageDetail()');assert.ok(get('detail-body').textContent.includes('条件冲突'));assert.ok(get('detail-body').textContent.includes('没有重新计算路线'));checks.push('继承结构路线并显式暴露条件冲突');}
 const node=run('({...position(graph().starts[0]),id:graph().starts[0],view:{...views[mode]}})'),v=node.view,cv=get('graph');const x=v.x+(node.x+20)*v.scale,y=v.y+(node.y+20)*v.scale;
 cv.onpointerdown({button:0,clientX:x,clientY:y,pointerId:1});cv.onpointermove({clientX:x+30,clientY:y});cv.onpointerup({clientX:x+30,clientY:y,pointerId:1});flush();assert.equal(run('position(graph().starts[0]).x'),node.x+30/v.scale);checks.push('节点拖拽');
 const oldScale=run('views[mode].scale');cv.onwheel({clientX:20,clientY:20,deltaY:100,preventDefault(){}});flush();assert.ok(run('views[mode].scale')<oldScale);checks.push('Canvas缩放');
 const oldX=run('views[mode].x');cv.onpointerdown({button:0,clientX:-99999,clientY:-99999,pointerId:2});cv.onpointermove({clientX:-99979,clientY:-99999});cv.onpointerup({clientX:-99979,clientY:-99999,pointerId:2});flush();assert.equal(run('views[mode].x'),oldX+20);checks.push('Canvas平移');
 const second=run('graph().starts[0]');get('search').value=payload.plan.cases.find(c=>c.requirementId===second).title;get('search').oninput();assert.ok(get('target').children.length>1);get('target').value=second;get('target').onchange();flush();assert.ok(get('detail-kind').textContent.includes('测试项'));checks.push('中文定位进入测试详情');
 const beforeResults=JSON.stringify(payload.plan.cases.map(c=>c.result));assert.equal(run('JSON.stringify(P.cases.map(c=>c.result))'),beforeResults);checks.push('只读交互不改变实测结论');
 assert.ok(!testData.includes('</script'));assert.ok(!html.includes('https://cdn'));checks.push('离线嵌入与脚本转义');
 return {status:'PASS',kind:'synthetic_dom_canvas',checks,realBrowser:'NOT_TESTED',productAcceptance:'NOT_RUN'};
}
if(process.argv[1]?.endsWith('test_review.mjs'))console.log(JSON.stringify(verifyReview(process.argv[2],process.argv[3]),null,2));
