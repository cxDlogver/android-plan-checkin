const fs=require('node:fs'),progress=require('./progress.cjs');
const state=progress.read(),root='resource/acceptance/runs',directories=fs.readdirSync(root).sort().reverse();
for(const [name,command]of Object.entries(state.commands).filter(([,command])=>['IN_PROGRESS','RUNNING'].includes(command.status))){
  const found=directories.find(directory=>fs.existsSync(`${root}/${directory}/${name}`));
  console.log(JSON.stringify({name,status:command.status,record:command.record,files:found?fs.readdirSync(`${root}/${found}/${name}`):[],folder:found?`${root}/${found}/${name}`:null}));
}
