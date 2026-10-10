const fs=require('node:fs');
const runs='resource/acceptance/runs',latest=fs.readdirSync(runs).sort().reverse().map(run=>`${runs}/${run}/native-api36/failure.xml`).find(file=>fs.existsSync(file));
const source=fs.readFileSync(latest,'utf8');console.log(source.match(/<[^>]*resource-id="native\.report"[^>]*>/)?.[0]?.slice(0,3000)||'No report node');
