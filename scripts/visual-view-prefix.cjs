const fs=require('node:fs'),path=require('node:path'),ts=require('typescript'),{sha}=require('./p1.cjs');
const metalFunctions={today:['Body','Button','Choice','Metal','Tag','Page','MetaLine','SettingsButton'],create:['Body','Button','Choice','Field','DateField','Page','MetaLine'],record:['Body','Button','Choice','Field','DateField','Metal','Page'],detail:['Body','Button','Metal','Notice','Page','MetaLine'],calendar:['Body','Button','Metal','StatusFilter','Page','MetaLine','CalendarTodayButton']};
const features={today:'today',create:'plan-form',record:'record-form',detail:'plan-detail',calendar:'calendar'};
function declarations(body,names){const ast=ts.createSourceFile('source.tsx',body,ts.ScriptTarget.Latest,true,ts.ScriptKind.TSX);return names.map(name=>{const s=ast.statements.find(n=>n.name?.text===name||ts.isVariableStatement(n)&&n.declarationList.declarations.some(d=>d.name.getText(ast)===name));if(!s)throw Error('Missing exact presentation declaration '+name);return s.getText(ast);}).join('\n');}
module.exports=(run,previous,original)=>{
 const retained=new Map();if(!previous?.record)return retained;const r=JSON.parse(fs.readFileSync(previous.record));
 if(r.status!=='PASS'&&r.assertions.some(a=>a.status==='FAIL'&&a.id!=='execution'))return retained;
 const input=JSON.parse(fs.readFileSync(path.join(path.dirname(previous.record),'inputs.json')));if(input.originalSha256!==original.sha256)return retained;
 for(const e of r.evidence)if(sha(fs.readFileSync(e.path))!==e.sha256)throw Error('Changed retained visual evidence');
 function old(file){const expected=input.source.find(s=>s.path===file);if(!expected)throw Error('Missing original visual source');const current=fs.readFileSync(file,'utf8');if(sha(current)===expected.sha256)return current;for(const suffix of ['.after-first','.before']){const stored='resource/progress/visual-alignment/'+file.replaceAll('/','__')+suffix;if(fs.existsSync(stored)){const body=fs.readFileSync(stored,'utf8');if(sha(body)===expected.sha256)return body;}}throw Error('Cannot recover exact visual source '+file);}
 for(const name of ['today','create-top','create-weekdays','create-footer','create-save','record','record-save','detail','calendar']){
  const group=name.split('-')[0],file=`src/features/${features[group]}.tsx`;let same;
  try{same=sha(old(file))===sha(fs.readFileSync(file));const names=[...metalFunctions[group],'colors','styles'];same&&=declarations(old('src/ui/metal.tsx'),names)===declarations(fs.readFileSync('src/ui/metal.tsx','utf8'),names);
   if(['today','calendar'].includes(group))same&&=old('src/features/shared.tsx')===fs.readFileSync('src/features/shared.tsx','utf8');
   if(group==='record')same&&=declarations(old('src/features/shared.tsx'),['resultText','resultLabel','resultColor'])===declarations(fs.readFileSync('src/features/shared.tsx','utf8'),['resultText','resultLabel','resultColor']);
  }catch{same=false;}if(!same)continue;
  let imageRecord=previous.record;let png=r.evidence.find(e=>new RegExp('/\\d+-'+name+'\\.png$').test(e.path)),xml=png&&r.evidence.find(e=>e.path===png.path.replace(/\.png$/,'.xml'));
  if(!png){const linked=r.evidence.find(e=>e.path.endsWith('/actual-to-Pen-alignment.json'));const view=linked&&JSON.parse(fs.readFileSync(linked.path)).views.find(v=>v.name===name);const prefix=view?.retained;if(prefix){if(sha(fs.readFileSync(prefix.record))!==prefix.reportSha256)throw Error('Changed visual prefix report');const manifest=JSON.parse(fs.readFileSync(prefix.record)).evidence;for(const e of [prefix.png,prefix.xml]){if(!manifest.some(m=>m.path===e.path&&m.sha256===e.sha256)||sha(fs.readFileSync(e.path))!==e.sha256)throw Error('Changed retained original image');}png=prefix.png;xml=prefix.xml;imageRecord=prefix.record;}}
  if(!png||!xml)continue;
  const assertions=r.assertions.filter(a=>a.id.startsWith(name+'.'));if(assertions.some(a=>a.status!=='PASS'))continue;
  retained.set(name,{record:imageRecord,reportSha256:sha(fs.readFileSync(imageRecord)),sourceReuseRecord:previous.record,sourceReuseReportSha256:sha(fs.readFileSync(previous.record)),png,xml,assertions,scope:'Exact original component source recovered; the render declarations used by this view are byte identical. Retain this already observed viewport and its passing geometry, without re-navigation or capture.'});
 }
 if(retained.size)run.write('retained-unchanged-visual-views.json',Object.fromEntries(retained));return retained;
};
