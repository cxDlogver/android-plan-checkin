const {spawnSync}=require('node:child_process'),{node,env}=require('./task-env.cjs'),progress=require('./progress.cjs');
for(const [script,config,key]of [['bdd-visual-alignment.cjs','M5','UI-alignment-M5'],...['M8','M6','M7','M5'].map(config=>['bdd-visual-calendar-geometry.cjs',config,'UI-calendar-geometry-'+config])]){
 if(progress.read().commands[key]?.status==='PASS'){console.log('REUSE '+key);continue;}
 const result=spawnSync(node,['scripts/'+script,config],{env,stdio:'inherit',windowsHide:true});if(result.status!==0){process.exitCode=result.status||1;break;}
}
