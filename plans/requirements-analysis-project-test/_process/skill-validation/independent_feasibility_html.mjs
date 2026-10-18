// Independent synthetic DOM checks. No actual browser/visual acceptance implied.
import fs from 'node:fs';
import vm from 'node:vm';
import path from 'node:path';
import crypto from 'node:crypto';
import {fileURLToPath} from 'node:url';
const here=path.dirname(fileURLToPath(import.meta.url));
const run=path.resolve(here,'../..');
const filename=path.join(run,'review.html');
const html=fs.readFileSync(filename,'utf8');
const data=JSON.parse(html.match(/<script id="data" type="application\/json">([\s\S]*?)<\/script>/)[1]);
const program=html.match(/<script>([\s\S]*?)<\/script>/)[1];
const registry=new Map();
const drawing=new Proxy({measureText:t=>({width:String(t).length*8})},{get:(o,k)=>o[k]||(()=>{})});
class Element{
 constructor(tag,id=''){this.tagName=tag;this.id=id;this.children=[];this.attrs={};this.value='';this.hidden=false;this._text='';this.style={setProperty(){}};}
 append(...items){this.children.push(...items);}
 replaceChildren(...items){this.children=items;this._text='';}
 set textContent(v){this._text=String(v);this.children=[];}
 get textContent(){return this._text+this.children.map(c=>c.textContent).join('');}
 setAttribute(k,v){this.attrs[k]=v;}
 getAttribute(k){return this.attrs[k];}
 getBoundingClientRect(){return {left:0,top:0,width:this.id==='minimap'?210:1440,height:this.id==='header'?120:this.id==='minimap'?120:780};}
 getContext(){return drawing;}
}
for(const m of html.matchAll(/id="([^"]+)"/g))registry.set(m[1],new Element('div',m[1]));
registry.get('data').textContent=JSON.stringify(data);
const document={getElementById:id=>registry.get(id),createElement:tag=>new Element(tag),documentElement:new Element('html')};
const env=vm.createContext({document,window:{innerWidth:1440,innerHeight:900,devicePixelRatio:1,addEventListener(){}},requestAnimationFrame:f=>f()});
vm.runInContext(program,env);
const evaluate=s=>vm.runInContext(s,env);
const descend=(e,out=[])=>{out.push(e);for(const c of e.children)descend(c,out);return out;};
const assert=(value,message)=>{if(!value)throw new Error(message);};
const record={scope:'synthetic DOM only; no browser observed',browserObserved:false,semanticDigest:data.semanticDigest,
 htmlSha256:crypto.createHash('sha256').update(html).digest('hex'),
 transitionDetails:0,caseDetails:0,witnessStepButtons:0,initialConditionsChecked:0,coverageSegments:0,coverageSteps:0,problems:[]};
const body=()=>registry.get('detail-body');
const checkWitness=(host,w,t)=>{
 const steps=host.children.filter(e=>e.tagName==='ol').flatMap(e=>e.children);
 assert(steps.length===w.transitionIds.length,'wrong witness step count '+t.id);
 assert(host.textContent.includes('应用功能尚未验收'),'missing product acceptance boundary');
 const last=steps.at(-1).children.find(c=>c.tagName==='button');
 last.onclick();
 assert(evaluate('selected.id')===t.requirementId,'witness last step button opens a different requirement');
 for(const [key,values] of Object.entries(w.initialContext||{})){
  const d=data.pathContext.domains[key];
  if(values.length<d.values.length){
   assert(host.textContent.includes(d.description+'：'+values.map(v=>d.labels[v]).join('或')),'initial condition hidden or mismatched '+key);
   record.initialConditionsChecked++;
  }
 }
 record.witnessStepButtons+=steps.length;
};
for(const t of data.transitions){
 evaluate('selectTransition('+JSON.stringify(t.id)+')');
 const section=descend(body()).find(e=>e.tagName==='section'&&e.children.some(c=>c.tagName==='h3'&&c.textContent==='本条迁移的可执行路径'));
 assert(section,'missing witness section for '+t.id);
 const w=data.transitionValidation.transitions[t.id];
 if(w.status==='finite_domain_passed'||w.status==='no_guard_constraints'){
  checkWitness(section,w,t);
 }
 const cases=data.transitionValidation.caseResults[t.id];
 const panes=section.children.filter(e=>e.tagName==='details'&&e.children.some(c=>c.tagName==='summary'&&c.textContent.startsWith('条件分支 ')));
 assert(panes.length===(cases.length>1?cases.length:0),'missing declared case detail '+t.id);
 for(const [ci,pane] of panes.entries()){
  const row=cases[ci];
  if(row.status==='finite_domain_passed'||row.status==='no_guard_constraints')checkWitness(pane,row,t);
  for(const [key,values] of Object.entries(data.pathContext.transitionRules[t.id].cases[ci].requires||{})){
   const domain=data.pathContext.domains[key];
   assert(pane.textContent.includes(domain.description+'：'+values.map(v=>domain.labels[v]).join('或')),'case condition label mismatch '+t.id);
  }
  record.caseDetails++;
 }
 record.transitionDetails++;
}
evaluate('coverageDetail()');
const elements=descend(body());
record.coverageSegments=elements.filter(e=>e.tagName==='summary'&&e.textContent.startsWith('展开完整中文路线')).length;
record.coverageSteps=elements.filter(e=>e.tagName==='ol').flatMap(e=>e.children).length;
assert(record.coverageSegments===data.requirementGraph.traversal.routes.length,'coverage segment count');
assert(record.coverageSteps===data.requirementGraph.traversal.totalVisits,'coverage repeated steps missing');
if(data.requirementGraph.traversal.optimality==='not_proven'){
 assert(body().textContent.includes('全局最短未证明'),'heuristic advertised as proven shortest');
 assert(body().textContent.includes(String(data.requirementGraph.traversal.lowerBoundVisits)),'lower bound not visible');
}
assert(body().textContent.includes('不会自动清空或改变业务数据'),'restart data preservation boundary absent');
assert(body().textContent.includes('未证明前一段留下的数据满足下一段'),'cross-segment compatibility boundary absent');
assert(body().textContent.includes('真实数据准备、来源语义和未编码条件仍需审查'),'semantic review boundary absent');
fs.writeFileSync(path.join(here,'independent-feasibility-html.json'),JSON.stringify(record,null,2));
console.log(JSON.stringify(record,null,2));
