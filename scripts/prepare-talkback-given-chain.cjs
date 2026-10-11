const fs=require('node:fs'),file='scripts/bdd-ui-talkback.cjs';let source=fs.readFileSync(file,'utf8');
const start=source.indexOf('let reused=false;if(run.previousRecord)'),end=source.indexOf('if(!reused){',start);
if(start<0||end<0)throw new Error('TalkBack reuse block missing');
source=source.slice(0,start)+"const originalGiven=await require('./reuse-talkback-given.cjs')(t,run);let reused=!!originalGiven;if(originalGiven)({fixed,avoid,weekly,once}=originalGiven);"+source.slice(end);
fs.writeFileSync(file,source);console.log('TalkBack original Given chain reuse is prepared.');
