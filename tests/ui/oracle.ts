import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
export const specificationRoot=path.resolve('plan/ui-spec');
export const readJSON=(file:string):any=>JSON.parse(fs.readFileSync(file,'utf8'));
export const sha256=(file:string)=>crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
export const spec=()=>{const manifest=readJSON(path.join(specificationRoot,'manifest.json'));return {manifest,library:readJSON(path.join(specificationRoot,'library.json')),rules:readJSON(path.join(specificationRoot,'rules.json')),documents:manifest.documents.map((d:any)=>readJSON(path.join(specificationRoot,d.file)))};};
export function flatten(node:any):any[]{return [node,...(node.children||[]).flatMap(flatten)];}
export function parameter(value:unknown,type:string,format:string):string{
  if(type==='integer'||type==='number'){if(typeof value!=='number'||!Number.isFinite(value)||type==='integer'&&!Number.isInteger(value))throw Error('Invalid numeric test input');return format==='0%'?Math.round(value*100)+'%':String(value);}
  if(type==='string'){if(typeof value!=='string')throw Error('Invalid string test input');return value;}
  if(typeof value!=='string')throw Error('Missing date/time test input');
  if(type==='time'){if(!/^\d{2}:\d{2}$/.test(value))throw Error('Invalid time');return value;}
  const dt=new Date(value.length===10?value+'T00:00:00Z':value);if(!Number.isFinite(dt.getTime()))throw Error('Invalid date');
  const options:Intl.DateTimeFormatOptions={timeZone:'UTC',month:'numeric',day:'numeric'};
  if(format.includes('yyyy'))options.year='numeric';if(format.includes('EEEE'))options.weekday='long';
  if(format==='yyyy年M月')delete options.day;
  const parts=new Intl.DateTimeFormat('zh-CN',options).formatToParts(dt);
  const get=(k:string)=>parts.find(p=>p.type===k)?.value||'';
  let text=(options.year?get('year')+'年':'')+get('month')+'月'+(options.day?get('day')+'日':'');
  if(options.weekday)text+=' '+get('weekday');
  if(format.includes('HH:mm'))text+=' '+dt.toISOString().slice(11,16);
  return text;
}
export function expectedText(content:any,inputs:Record<string,unknown>):string{
  if(!content.binding)return content.value;
  return content.binding.template.replace(/\{\{([^}]+)\}\}/g,(_:string,key:string)=>{if(!Object.hasOwn(inputs,key))throw Error('Missing required input: '+key);const p=content.binding.parameters[key];return parameter(inputs[key],p.type,p.format);});
}
export function validateObservation(record:any){
  for(const key of ['uiVersion','documentId','nodeIds','environment','inputs','screenshot','differences','status'])if(record[key]===undefined||record[key]===null)throw Error('Missing '+key);
  if(!Array.isArray(record.nodeIds)||!record.nodeIds.length||!record.uiVersion||!record.documentId)throw Error('Invalid identity');
  if(record.status==='not_run'&&(record.actual!==undefined&&record.actual!==null||record.passed===true))throw Error('Unexecuted record claims observation');
  if(record.status==='passed'&&(!record.actual||!record.screenshot))throw Error('Passed without actual evidence');
  return true;
}

export interface MeasuredBox {x:number;y:number;width:number;height:number}
export interface GeometryFinding {nodeId:string;rule:string;expected:unknown;actual:unknown;passed:boolean}
export function expectedRatio(size:any,inputs:Record<string,unknown>):number{
 const value=size.binding?inputs[size.binding.path]:size.value;
 if(typeof value!=='number'||!Number.isFinite(value)||value<0||value>1)throw Error('Invalid proportional input');
 return value;
}
/** Validate source constraints against independently observed native boxes.
 * Intrinsic content sizes are observed inputs; fixed values, flow positions,
 * track widths, min/max and ratios are derived from the source contract.
 */
export function geometryConstraints(tree:any,boxes:Record<string,MeasuredBox>,inputs:Record<string,unknown>,pixelRatio=1,environment?:{viewport?:{width:number;height:number};insets?:{top:number;bottom:number};bottomManagedElsewhere?:boolean}):GeometryFinding[]{
 const findings:GeometryFinding[]=[],epsilon=1/pixelRatio;
 const equal=(nodeId:string,rule:string,expected:number,actual:number)=>findings.push({nodeId,rule,expected,actual,passed:Math.abs(expected-actual)<=epsilon});
 const bound=(nodeId:string,rule:string,expected:number,actual:number,lower:boolean)=>findings.push({nodeId,rule,expected,actual,passed:lower?actual+epsilon>=expected:actual-epsilon<=expected});
 function visit(n:any,parent?:any){
  if(n.ownership==='platform'){const edge=n.extensions?.environmentRegion?.edge,box=boxes[n.id];if(edge&&environment?.insets){if(!box)findings.push({nodeId:n.id,rule:'host region present',expected:true,actual:false,passed:false});else equal(n.id,'host '+edge,edge==='bottom'&&environment.bottomManagedElsewhere?0:environment.insets[edge as 'top'|'bottom'],box.height);}return;}
  const box=boxes[n.id];if(!box){findings.push({nodeId:n.id,rule:'present',expected:true,actual:false,passed:false});return;}
  for(const axis of ['width','height'] as const){
   const size=n.sizing?.[axis];if(!size)continue;
   if(size.mode==='viewport'&&environment?.viewport)equal(n.id,axis+' viewport',environment.viewport[axis],box[axis]);
   if(size.mode==='fill'&&parent&&parent.layout?.type==='flex'){const main=parent.layout.direction==='row'?'width':'height';if(axis!==main){const p=boxes[parent.id],padding=parent.layout.padding||[0,0,0,0];if(p){let extent=p[axis]-(axis==='width'?padding[1]+padding[3]:padding[0]+padding[2]);if(size.max!==null)extent=Math.min(extent,size.max);if(size.min!==null)extent=Math.max(extent,size.min);equal(n.id,axis+' cross fill',extent,box[axis]);}}}
   if(size.mode==='fixed')equal(n.id,axis+' fixed',size.value,box[axis]);
   if(size.min!==null&&size.min!==undefined)bound(n.id,axis+' min',size.min,box[axis],true);
   if(size.max!==null&&size.max!==undefined)bound(n.id,axis+' max',size.max,box[axis],false);
   if(size.mode==='percent'&&parent){const p=boxes[parent.id],padding=parent.layout?.padding||[0,0,0,0];if(p){const available=p[axis]-(axis==='width'?padding[1]+padding[3]:padding[0]+padding[2]);equal(n.id,axis+' ratio',available*expectedRatio(size,inputs),box[axis]);}}
  }
  const children=(n.children||[]).filter((c:any)=>boxes[c.id]&&(c.ownership!=='platform'||!!c.extensions?.environmentRegion)),layout=n.layout;
  if(layout&&children.length){
   const [top,right,bottom,left]=layout.padding,contentWidth=box.width-left-right,contentHeight=box.height-top-bottom;
   if(layout.type==='grid'){
    const tracks=layout.columns,widths=tracks.map((t:any)=>t.mode==='fixed'?t.value:0),remaining=contentWidth-layout.columnGap*(tracks.length-1)-widths.reduce((a:number,b:number)=>a+b,0),weight=tracks.reduce((a:number,t:any)=>a+(t.mode==='fraction'?t.value:0),0);
    tracks.forEach((t:any,i:number)=>{if(t.mode==='fraction')widths[i]=remaining*t.value/weight;});let y=top;
    for(let row=0;row<Math.ceil(children.length/tracks.length);row++){let x=left;const cells=children.slice(row*tracks.length,(row+1)*tracks.length),height=Math.max(...cells.map((c:any)=>boxes[c.id]!.height));cells.forEach((c:any,col:number)=>{const actual=boxes[c.id]!;equal(c.id,'grid x',x,actual.x);equal(c.id,'grid y',y,actual.y);equal(c.id,'grid track width',widths[col],actual.width);x+=widths[col]+layout.columnGap;});y+=height+layout.rowGap;}
   }else if(layout.type==='flex'&&layout.wrap==='nowrap'){
    const row=layout.direction==='row',main=row?'width':'height',cross=row?'height':'width',origin=row?left:top,extent=row?contentWidth:contentHeight,crossExtent=row?contentHeight:contentWidth,crossOrigin=row?top:left;
    const occupied=children.reduce((sum:number,c:any)=>sum+boxes[c.id]![main],0),free=extent-occupied-layout.gap*(children.length-1);
    let cursor=origin+(layout.justify==='center'?free/2:layout.justify==='end'?free:0),gap=layout.gap;
    if(layout.justify==='space-between'&&children.length>1)gap+=free/(children.length-1);
    for(const c of children){const actual=boxes[c.id]!;equal(c.id,'flow '+(row?'x':'y'),cursor,row?actual.x:actual.y);cursor+=actual[main]+gap;const aligned=c.placement?.alignSelf||layout.align;if(aligned==='start'||aligned==='center'||aligned==='end'){const expected=crossOrigin+(aligned==='center'?(crossExtent-actual[cross])/2:aligned==='end'?crossExtent-actual[cross]:0);equal(c.id,'cross '+(row?'y':'x'),expected,row?actual.y:actual.x);}}
    const flexible=children.filter((c:any)=>['fraction','fill'].includes(c.sizing?.[main]?.mode)),nonFlexible=children.filter((c:any)=>!flexible.includes(c)).reduce((sum:number,c:any)=>sum+boxes[c.id]![main],0),weight=(c:any)=>c.sizing[main].mode==='fraction'?c.sizing[main].value:1,weights=flexible.reduce((sum:number,c:any)=>sum+weight(c),0);for(const c of flexible){let expected=(extent-nonFlexible-layout.gap*(children.length-1))*weight(c)/weights;const d=c.sizing[main];if(d.max!==null)expected=Math.min(expected,d.max);if(d.min!==null)expected=Math.max(expected,d.min);equal(c.id,'flex '+main,expected,boxes[c.id]![main]);}
   }
  }
  for(const child of n.children||[])visit(child,n);
 }
 visit(tree);return findings;
}
export function gradientEndpoints(style:any,width:number,height:number,layer=0){
 const geometry=style.extensions?.fillGeometry?.find((g:any)=>g.layer===layer);if(!geometry)return null;
 const radians=geometry.rotationCCW*Math.PI/180,cx=geometry.center[0]*width,cy=geometry.center[1]*height,dx=-Math.sin(radians)*width*geometry.size[1],dy=-Math.cos(radians)*height*geometry.size[1];
 return {x1:cx-dx/2,y1:cy-dy/2,x2:cx+dx/2,y2:cy+dy/2};
}
