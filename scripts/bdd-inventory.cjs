const fs=require('node:fs');
const state=JSON.parse(fs.readFileSync('resource/progress/state.json','utf8'));
const catalog=JSON.parse(fs.readFileSync('resource/acceptance/追踪目录.json','utf8'));
console.log('Tasks:',state.tasks.map(t=>`${t.id}:${t.status}`).join(' '));
for(const file of fs.readdirSync('resource/acceptance/scenarios')){
  const text=fs.readFileSync(`resource/acceptance/scenarios/${file}`,'utf8');
  for(const match of text.matchAll(/### (AC\d+)｜([^\r\n]+)/g)){
    const end=text.indexOf('\n### AC',match.index+1),section=text.slice(match.index,end<0?undefined:end);
    const current=state.acceptance[match[1]]?.status||'NOT_RUN';
    if(process.argv.includes('--pending')&&current==='PASS')continue;
    console.log(`${match[1]} ${current} ${match[2]} | ${section.match(/层级：([^\r\n]+)/)?.[1]}`);
  }
}
