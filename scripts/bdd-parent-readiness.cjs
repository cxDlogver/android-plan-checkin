const fs=require('node:fs'),catalog=require('../resource/acceptance/追踪目录.json'),state=require('./progress.cjs').read();
const requested=new Set(process.argv.slice(2)),coverage=JSON.parse(fs.readFileSync('resource/progress/bdd-coverage.json','utf8'));
for(const scenario of catalog.scenarios){if(requested.size&&!requested.has(scenario.id)||state.acceptance[scenario.id]?.status==='PASS')continue;
 const item=coverage.cases.find(c=>c.caseId===scenario.id),configs=scenario.core?Array.from({length:8},(_,i)=>'M'+(i+1)):['VISUAL','A11Y'].includes(scenario.layer)?Array.from({length:8},(_,i)=>'M'+(i+1)):['M3','M7'],rows=scenario.examples?.slice(1).map(r=>r[0])||['default'];
 if(!/UI|NATIVE|DOMAIN|VISUAL|A11Y/.test(scenario.layer))continue;
 const missing=configs.flatMap(config=>rows.filter(row=>!item.passingInstances.some(p=>p.configId===config&&p.rowId===row)).map(row=>row+'/'+config));
 const companions=Object.entries(state.commands).filter(([key,c])=>key.startsWith(scenario.id+'-')&&c.status==='PASS'&&!item.passingInstances.some(i=>i.record===c.record)).map(([key])=>key);
 console.log(JSON.stringify({caseId:scenario.id,layer:scenario.layer,core:scenario.core,passing:item.passingInstances.length,missingCount:missing.length,missing:missing.slice(0,12),companionCount:companions.length,scopeNote:'Readiness inventory only. Native parameter aliases, DOMAIN coverage, full clause semantics and evidence profiles still require explicit review before parent PASS.'}));
}
