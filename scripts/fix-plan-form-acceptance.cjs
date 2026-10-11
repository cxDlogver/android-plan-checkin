const fs=require('node:fs'),assert=require('node:assert/strict');
const path='src/features/plan-form.tsx';let text=fs.readFileSync(path,'utf8');
for(const [before,after] of [
  ['onChange={value=>change(setType,value as PlanType)}','onChange={value=>void changeType(value as PlanType)}'],
  ["<Body>{mask?'已选择执行星期':'默认不选，请至少选择一个星期。'}</Body>","<Body>{mask===127?'每日':mask?['一','二','三','四','五','六','日'].filter((_,i)=>!!(mask&(1<<i))).map(day=>`周${day}`).join('、'):'默认不选，请至少选择一个星期。'}</Body>"],
  ['disabled={busy} testID="plan.save"','disabled={busy||(type===\'fixed\'&&mask===0)} testID="plan.save"'],
  ['testID="plan.startsOn" onChange','testID="plan.startsOn" error={fields.startsOn} onChange'],
  ['testID="plan.endOn" onChange','testID="plan.endOn" error={fields.endOn||fields[\'changes.endOn\']} onChange'],
  ['testID="plan.dueOn" onChange','testID="plan.dueOn" error={fields.dueOn||fields[\'changes.dueOn\']} onChange'],
]){assert.equal(text.split(before).length,2,before);text=text.replace(before,after);}
fs.writeFileSync(path,text);
