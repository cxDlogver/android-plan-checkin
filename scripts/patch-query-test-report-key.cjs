const fs=require('node:fs'),f='scripts/close-core-calendar-pages.cjs';fs.writeFileSync(f,fs.readFileSync(f,'utf8').replace("'query-acceptance-tests'","'query-tests'"));
