const fs=require('node:fs'),file='scripts/talkback-speech-evidence.cjs';let source=fs.readFileSync(file,'utf8');
const original="d.adb(['shell','input','tap',String(x),String(y)]);await captureSpeech";
if(!source.includes(original))throw new Error('Expected original short touch exploration absent');
source=source.replace(original,"d.adb(['shell','input','touchscreen','swipe',String(x),String(y),String(x+1),String(y),'1000']);await captureSpeech").replace('single native touch exploration tap; actual TalkBack focus and speech','native one-finger exploration with 1000 ms contact and 1 px movement; actual TalkBack focus and speech');fs.writeFileSync(file,source);
console.log('Use an actual sustained touch exploration gesture; a zero-duration injected tap produced no accessibility focus.');
