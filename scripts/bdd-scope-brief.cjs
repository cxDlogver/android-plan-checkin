const fs=require('node:fs'),path=require('node:path'),catalog=require('../resource/acceptance/追踪目录.json'),state=require('./progress.cjs').read();
for(const id of process.argv.slice(2)){
 const s=catalog.scenarios.find(s=>s.id===id);if(!s)throw new Error(id);
 const file=fs.readdirSync('resource/acceptance/scenarios').map(f=>'resource/acceptance/scenarios/'+f).find(f=>fs.readFileSync(f,'utf8').includes('### '+id+'｜'));
 const body=fs.readFileSync(file,'utf8'),section=body.slice(body.indexOf('### '+id+'｜')).split(/\r?\n### /)[0];
 console.log(id+' '+s.title+' '+s.layer+' '+(s.core?'8-config':'base-config'));
 console.log(section.split(/\r?\n/).filter(l=>l.includes(id+'.A')||l.includes(id+'.E')).join('\n'));
 for(const [key,c]of Object.entries(state.commands)){
  if(!key.startsWith(id+'-')||!c.record||c.status!=='PASS'||key.includes('full-acceptance'))continue;
  const r=JSON.parse(fs.readFileSync(c.record));console.log(JSON.stringify({key,record:c.record,assertions:r.assertions.filter(a=>!a.id.startsWith('Given')&&!a.id.startsWith('step-')).map(a=>a.id),files:r.evidence.map(e=>path.basename(e.path)).filter(f=>!/^step-|\.png$|appium\.log|device\.json|fixture/.test(f))}));
 }
}
