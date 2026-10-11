const fs=require('node:fs');
const speechFile='scripts/talkback-speech-evidence.cjs';let s=fs.readFileSync(speechFile,'utf8');
const from="d.adb(['shell','input','touchscreen','swipe',String(x),String(y),String(x+1),String(y),'1000']);";
if(!s.includes(from))throw new Error('Previous uncompleted focus injection anchor missing');
s=s.replace(from,"await hardwareTap(d,x,y,300);").replace("action:'native one-finger exploration with 1000 ms contact and 1 px movement; actual TalkBack focus and speech'","action:'project emulator kernel touch-screen contact via event mouse; actual TalkBack focus and delivered speech'");
s=s.replace('module.exports={setup,',`async function hardwareTap(d,x,y,hold=60){d.adb(['emu','event','mouse',String(x),String(y),'0','1']);await sleep(hold);d.adb(['emu','event','mouse',String(x),String(y),'0','0']);}
async function hardwareSwipe(d,x1,y1,x2,y2){d.adb(['emu','event','mouse',String(x1),String(y1),'0','1']);for(let i=1;i<=4;i++){await sleep(25);d.adb(['emu','event','mouse',String(Math.round(x1+(x2-x1)*i/4)),String(Math.round(y1+(y2-y1)*i/4)),'0','1']);}d.adb(['emu','event','mouse',String(x2),String(y2),'0','0']);}
module.exports={hardwareTap,hardwareSwipe,setup,`);
fs.writeFileSync(speechFile,s);
const f='scripts/bdd-ui-talkback.cjs';let t=fs.readFileSync(f,'utf8');
t=t.replace("d.adb(['shell','input','tap',String(point.x),String(point.y)]);await speech.sleep(80);d.adb(['shell','input','tap',String(point.x),String(point.y)]);","await speech.hardwareTap(d,point.x,point.y);await speech.sleep(80);await speech.hardwareTap(d,point.x,point.y);");
t=t.replace("d.adb(['shell','input','swipe','220','900','820','900','200']);","await speech.hardwareSwipe(d,220,900,820,900);");
fs.writeFileSync(f,t);console.log('Use emulator kernel touch-screen events for TalkBack exploration and gestures; ordinary injected adb input had bypassed actual accessibility focus.');
