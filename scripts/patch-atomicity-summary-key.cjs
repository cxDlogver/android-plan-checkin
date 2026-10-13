const fs=require('node:fs'),f='scripts/close-service-UI-gaps.cjs';fs.writeFileSync(f,fs.readFileSync(f,'utf8').replace("'AC008-atomicity-summary'","'AC008-migration-summary'"));
