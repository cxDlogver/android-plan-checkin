const fs=require('node:fs'),assert=require('node:assert/strict');const file='src/ui/metal.tsx';let text=fs.readFileSync(file,'utf8');
const before="edges={['top','left','right']}";assert.equal(text.split(before).length,2);text=text.replace(before,"edges={back?['top','bottom','left','right']:['top','left','right']}");fs.writeFileSync(file,text);
