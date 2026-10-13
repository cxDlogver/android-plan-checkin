const fs=require('node:fs'),path=require('node:path'),state=require('./progress.cjs').read();
for(const key of process.argv.slice(2)){
 const item=state.commands[key],file=path.join(path.dirname(item.record),'appium.log'),lines=fs.readFileSync(file,'utf8').split(/\r?\n/).map(s=>s.replace(/\\"/g,'"'));
 const indices=lines.flatMap((s,i)=>s.includes('[HTTP] -->')&&s.includes('press_keycode')?[i]:[]);
 console.log(key);
 for(const i of indices.slice(-4)){
  const last=lines.slice(Math.max(0,i-50),i).filter(s=>s.includes('<hierarchy')||s.includes('<android.widget.')).at(-1);
  console.log(lines[i]);console.log(JSON.stringify({precedingSourceAt:last?.slice(0,26),keyboardView:!!last?.includes('keyboard_view'),dateModal:!!last?.includes('date-picker.'),focusedInputs:[...(last||'').matchAll(/<[^>]*focused="true"[^>]*>/g)].map(m=>m[0].slice(0,500))}));
 }
}
