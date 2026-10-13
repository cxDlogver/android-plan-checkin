const fs=require('node:fs'),file='scripts/bdd-ui-display.cjs';let body=fs.readFileSync(file,'utf8');
for(const [id,shown]of [['AC093.A2.actual-keyboard-shown',true],['AC093.A2.first-back-closes-keyboard',false]]){const old=`t.check('${id}',${shown},await t.device.request(t.device.endpoint('appium/device/is_keyboard_shown')))`,next=`t.check('${id}',${shown},await require('./wait-keyboard-observation.cjs')(t,${shown}))`;if(body.includes(next))continue;if(!body.includes(old))throw new Error('Expected exact keyboard observation '+id);body=body.replace(old,next);}
fs.writeFileSync(file,body);
