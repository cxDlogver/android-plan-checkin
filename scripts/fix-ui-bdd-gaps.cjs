const fs=require('node:fs'),assert=require('node:assert/strict');
function edit(file,pairs){let text=fs.readFileSync(file,'utf8');for(const [before,after]of pairs){assert.equal(text.split(before).length,2,`${file}: ${before}`);text=text.replace(before,after);}fs.writeFileSync(file,text);}
edit('src/features/record-form.tsx',[
  ['const change=(callback:()=>void)=>{callback();','const change=(callback:()=>void)=>{if(busy)return;callback();'],
  ['<Choice value={result} onChange','<Choice disabled={busy} value={result} onChange'],
  ['editable={right.allowed}','editable={right.allowed&&!busy}'],
  ['testID="record.actualCompletedOn" onChange','testID="record.actualCompletedOn" disabled={busy} onChange'],
  ['disabled={busy} testID="record.save"','disabled={busy||!result} testID="record.save"'],
]);
edit('src/features/plan-form.tsx',[
  ['=>{setter(value);setDirty(true);','=>{if(busy)return;setter(value);setDirty(true);'],
  ['<Field label="名称" value','<Field editable={!busy} label="名称" value'],
  ['<Field label="说明（可选）" value','<Field editable={!busy} label="说明（可选）" value'],
  ['<Choice value={type}','<Choice disabled={busy} value={type}'],
  ['<Choice value={direction}','<Choice disabled={busy} value={direction}'],
  ['testID={`plan.weekday.${index+1}`}','disabled={busy} testID={`plan.weekday.${index+1}`}'],
  ['testID="plan.weekday.everyday"','disabled={busy} testID="plan.weekday.everyday"'],
  ['<Field label="每周目标天数（1–7）"','<Field editable={!busy} label="每周目标天数（1–7）"'],
  ['<DateField label="开始日期"','<DateField disabled={busy} label="开始日期"'],
  ['<DateField label="结束日期（可不设置）"','<DateField disabled={busy} label="结束日期（可不设置）"'],
  ['<DateField label="截止日期"','<DateField disabled={busy} label="截止日期"'],
]);
