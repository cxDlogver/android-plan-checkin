const fs=require('node:fs'),file='scripts/device-driver.cjs';let s=fs.readFileSync(file,'utf8');
const old='top=Math.round(rect.y+30),bottom=Math.round(rect.y+rect.height-30)',next='top=Math.round(rect.y+90),bottom=Math.round(rect.y+rect.height-180)';if(!s.includes(old))throw new Error('Expected original observer gutter viewport');s=s.replace(old,next);fs.writeFileSync(file,s);
