const fs=require('node:fs'),state=require('./progress.cjs').read();
for(const key of process.argv.slice(2)){const c=state.commands[key];if(!c){console.log(key,'missing');continue;}let directory;
  if(c.record)directory=c.record.replace(/\/result.json$/,'');else{const dirs=fs.readdirSync('resource/acceptance/runs').reverse();directory=dirs.map(d=>`resource/acceptance/runs/${d}/${key}`).find(d=>fs.existsSync(d));}
  const file=c.logPath||directory&&`${directory}/commands.log`;console.log(key,c.status,file);if(file&&fs.existsSync(file)){const data=fs.readFileSync(file,'utf8');console.log(data.slice(-4000));}
}
