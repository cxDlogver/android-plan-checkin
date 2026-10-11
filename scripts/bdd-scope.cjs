const fs=require('node:fs');
for(const id of process.argv.slice(2))for(const file of fs.readdirSync('resource/acceptance/scenarios')){
  const text=fs.readFileSync(`resource/acceptance/scenarios/${file}`,'utf8'),start=text.indexOf(`### ${id}｜`);if(start<0)continue;
  const end=text.indexOf('\n### AC',start+1),section=text.slice(start,end<0?undefined:end);
  console.log(section.split(/\r?\n/).filter(line=>/^### |^层级：|^\*\*场景|^\*\*操作|^\*\*结果|^    \||^- \[ \] AC\d+\.A/.test(line)).join('\n'));
}
