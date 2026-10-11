const {spawn}=require('node:child_process'),fs=require('node:fs'),{env}=require('./task-env.cjs'),{passed}=require('./run-bdd-matrix.cjs');
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
function child(script,args=[]){return new Promise((resolve,reject)=>{const p=spawn(process.execPath,['scripts/'+script,...args],{env,windowsHide:true,stdio:'inherit'});p.on('error',reject);p.on('exit',code=>resolve(code));});}
async function main(){
 while(require('./progress.cjs').read().commands['AC094-default-M1']?.status==='IN_PROGRESS')await sleep(5000);
 console.log('M1 TalkBack is closed. Begin only uncompleted M4 cases.');
 await child('run-bdd-matrix.cjs',['M4']);
 await child('run-bdd-uncompleted.cjs',['M4','display']);
 const raw=require('./progress.cjs').read().commands['AC092-default-M4'];
 if(raw?.status==='FAIL'){const r=JSON.parse(fs.readFileSync(raw.record,'utf8'));if(r.assertions.find(a=>a.status==='FAIL')?.id==='AC092.A2.uniform-six-row-heights')await child('bdd-calendar-clipped-geometry-continuation.cjs',['M4']);}
 if(!passed('AC094-default-M4'))await child('bdd-ui-talkback.cjs',['29','M4']);
 await child('update-bdd-coverage.cjs');
 console.log('M4 execution closed; raw display requires separate actual image review.');
}
main().catch(e=>{console.error(e.stack);process.exitCode=1;});
