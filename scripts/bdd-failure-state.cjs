const fs=require('node:fs'),state=require('./progress.cjs').read();
for(const key of process.argv.slice(2)){const c=state.commands[key];if(!c){console.log(key,'MISSING');continue;}
  const r=JSON.parse(fs.readFileSync(c.record,'utf8')),d=c.record.replace(/\/result.json$/,'');
  console.log(JSON.stringify({key,record:c.record,assertions:r.assertions.map(a=>({id:a.id,status:a.status,actual:a.status==='FAIL'?a.actual:undefined})),files:fs.readdirSync(d)},null,2));
}
