const fs=require('node:fs'),file='scripts/recover-newline-name.cjs';const text=fs.readFileSync(file,'utf8').replace("xml.includes('请检查输入内容')","xml.includes('请检查')");fs.writeFileSync(file,text);
