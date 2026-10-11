const fs=require('node:fs');
const source=fs.readdirSync('resource/acceptance/scenarios').filter(f=>f.endsWith('.md')).map(f=>fs.readFileSync('resource/acceptance/scenarios/'+f,'utf8')).join('\n');
for(const id of process.argv.slice(2)){
const pos=source.indexOf(`### ${id}`),next=source.indexOf('\n### AC',pos+8);
console.log(pos<0?`${id} section not found`:source.slice(pos,next<0?undefined:next));
}
