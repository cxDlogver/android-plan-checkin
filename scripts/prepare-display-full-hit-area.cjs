const fs=require('node:fs'),file='scripts/bdd-ui-display.cjs';let text=fs.readFileSync(file,'utf8');
for(const [from,to]of [
["await new Promise(r=>setTimeout(r,750));t.run.write('actual-enabled-navigation-overlay.log'","await new Promise(r=>setTimeout(r,750));await t.restart();await t.device.request(t.device.endpoint('appium/settings'),'POST',{settings:{enableMultiWindows:true}});t.run.write('actual-enabled-navigation-overlay.log'"],
["const p=await t.create('one_time','2026-10-09',{dueOn:'2026-10-10'});","const p=await require('./reuse-display-given.cjs')(t,t.run)||await t.create('one_time','2026-10-09',{dueOn:'2026-10-10'});"],
["await t.device.seek('record.save');const xml=await t.frame('keyboard-open-save-reachable')","await t.device.revealButton('record.save');const xml=await t.frame('keyboard-open-save-reachable')"],
["t.check('AC093.A2.save-above-actual-keyboard',true,Number.isFinite(top)&&saveBounds.bottom<=top+1);","t.check('AC093.A2.save-above-actual-keyboard',true,Number.isFinite(top)&&saveBounds.bottom<=top+1);t.check('AC093.A2.complete-save-hit-area',true,saveBounds.height/metrics(t.device.identity()).scale>=48);"],
]){if(!text.includes(from))throw new Error('Expected display harness anchor missing');text=text.replace(from,to);}
fs.writeFileSync(file,text);console.log('Display observations now require the entire 48 dp save hit area and restart after native navigation configuration changes.');
