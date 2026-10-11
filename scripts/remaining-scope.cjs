const fs = require('node:fs');
const catalog = JSON.parse(fs.readFileSync('resource/acceptance/追踪目录.json','utf8'));
for (const id of process.argv.slice(2)) {
  if (id.startsWith('IP')) {
    const task=catalog.tasks.find(task=>task.id===id);
    console.log(JSON.stringify({...task,acceptance:undefined,exitChecks:task.exitChecks?.length>15?`${task.exitChecks.length} exit checks; see catalog`:task.exitChecks,execution:undefined},null,2));
  } else {
    const directory='resource/acceptance/scenarios';
    for(const name of fs.readdirSync(directory)) {
      const content=fs.readFileSync(`${directory}/${name}`,'utf8');
      const start=content.indexOf(`### ${id}｜`);
      if(start<0) continue;
      const end=content.indexOf('\n### AC',start+1);
      console.log(content.slice(start,end<0?undefined:end));
    }
  }
}
