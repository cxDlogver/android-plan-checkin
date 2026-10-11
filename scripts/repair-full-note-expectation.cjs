const fs=require('node:fs'),file='scripts/bdd-ui-real-full.cjs';let s=fs.readFileSync(file,'utf8');s=s.replaceAll("'真实空间不足保留输入'","'😀'.repeat(2000)");fs.writeFileSync(file,s);
