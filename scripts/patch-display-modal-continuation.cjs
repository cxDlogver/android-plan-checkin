const fs=require('node:fs'),file='scripts/bdd-ui-display.cjs';let s=fs.readFileSync(file,'utf8');
const start="await t.device.seek('record.actualCompletedOn',true);await t.click('record.actualCompletedOn');";
const end="t.check('AC093.A2.modal-back-keeps-form',true,true);await t.device.back();";
if(!s.includes(start)||!s.includes(end))throw new Error('Exact retained modal boundary missing');
s=s.replace(start,"if(!resumed?.modalPassed){"+start).replace(end,"t.check('AC093.A2.modal-back-keeps-form',true,true);await require('./settle-after-native-modal.cjs')(t);}await t.device.back();");
fs.writeFileSync(file,s);
