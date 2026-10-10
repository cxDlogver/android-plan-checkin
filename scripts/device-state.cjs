const fs=require('node:fs');
const {decode}=require('./device-driver.cjs');
const api=process.argv[2]||'36',prefix=process.argv[3]||'native-api',runs='resource/acceptance/runs';
const latest=fs.readdirSync(runs).sort().reverse().map(run=>`${runs}/${run}/${prefix}${api}`).find(folder=>fs.existsSync(folder));
if(!latest){console.log('No native device evidence yet.');process.exit(0);}
console.log(latest);
for(const file of fs.readdirSync(latest).filter(file=>file.endsWith('.xml'))){const source=fs.readFileSync(`${latest}/${file}`,'utf8');const nodes=[...source.matchAll(/<[^>]+>/g)].map(match=>match[0]);const items=nodes.map(tag=>({id:tag.match(/resource-id="([^"]*)"/)?.[1],text:decode(tag.match(/text="([^"]*)"/)?.[1]||''),description:decode(tag.match(/content-desc="([^"]*)"/)?.[1]||'')})).filter(item=>item.id||item.text||item.description).map(item=>({...item,text:item.text.slice(0,160),description:item.description.slice(0,160)}));console.log(JSON.stringify({file,items:items.slice(0,45)}));}
