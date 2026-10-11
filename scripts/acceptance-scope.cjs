const catalog=require('../resource/acceptance/追踪目录.json');for(const id of process.argv.slice(2)){const s=catalog.scenarios.find(s=>s.id===id);console.log(JSON.stringify(s,null,2));}
