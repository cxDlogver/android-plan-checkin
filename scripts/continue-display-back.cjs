const fs=require('node:fs'),file='scripts/bdd-ui-display.cjs';let s=fs.readFileSync(file,'utf8');
const old="const p=await require('./reuse-display-given.cjs')(t,t.run)||await t.create";
const replacement="const resumed=await require('./reuse-display-back-prefix.cjs')(t);const p=resumed?.planId||await require('./reuse-display-given.cjs')(t,t.run)||await t.create";
if(!s.includes(old))throw new Error('Expected display Given boundary');s=s.replace(old,replacement);
s=s.replace("const before=await t.capture('before-keyboard-facts');await t.device.clickVisible('record.note');","const before=resumed?.before||await t.capture('before-keyboard-facts');if(!resumed){await t.device.clickVisible('record.note');");
s=s.replace("t.check('AC093.A2.first-back-keeps-form',true,true);await t.click('record.actualCompletedOn');","t.check('AC093.A2.first-back-keeps-form',true,true);}await t.device.seek('record.actualCompletedOn');await t.click('record.actualCompletedOn');");
fs.writeFileSync(file,s);
