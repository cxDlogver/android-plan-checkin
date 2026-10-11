const fs=require('node:fs'),assert=require('node:assert/strict');
const file='src/features/record-form.tsx';let text=fs.readFileSync(file,'utf8');
for(const [before,after]of [
  ["import { formatInstant }", "import { date, formatInstant }"],
  ['[error,setError]=useState<string|null>(null);','[error,setError]=useState<string|null>(null),[fields,setFields]=useState<Record<string,string>>({});'],
  ['frozen.current=null;setError(null);};','frozen.current=null;setError(null);setFields({});};'],
  ['if(!plan||busy)return;if(!result)','if(!plan||busy)return;setFields({});if(!result)'],
  ['else{setError(saved.code);if','else{setError(saved.code);setFields(saved.fieldErrors||{});if'],
  ['testID="record.note"/>','testID="record.note" error={fields.note}/>'],
  ['testID="record.actualCompletedOn" disabled={busy}', 'testID="record.actualCompletedOn" disabled={busy} error={fields.actualCompletedOn||fields.date||(error===\'DATE_INELIGIBLE\'?\'实际完成日期必须在创建日到今天之间。\':error===\'VALIDATION_FAILED\'&&!on?\'请选择实际完成日期。\':undefined)}'],
  ['title={on<snapshot.today?\'进入补记确认\':\'重新确认当前业务日\'}', 'title={reconfirmOn<snapshot.today?\'进入补记确认\':\'重新确认当前业务日\'}'],
  ['重新确认 ${on} ${on<snapshot.today?', '重新确认 ${reconfirmOn} ${reconfirmOn<snapshot.today?'],
  ['confirmedToday.current=snapshot.today;revisions.current={plan:plan.revision,record:undefined};', 'setOn(reconfirmOn);confirmedToday.current=snapshot.today;revisions.current={plan:plan.revision,record:undefined};'],
  ['<Field label="文字备注（可选）"', '{completionPreview&&<Body strong>{completionPreview}</Body>}<Field label="文字备注（可选）"'],
]){assert.equal(text.split(before).length,2,before);text=text.replace(before,after);}
const target='  return <Page title={record?';assert.equal(text.split(target).length,2);
text=text.replace(target,`  const reconfirmOn=plan.type==='one_time'&&result!=='completed'?snapshot.today:on;
  let completionPreview:string|undefined;
  if(plan.type==='one_time'&&result==='completed'&&!record&&referencedDue){
    try{date(on,snapshot.zone);if(on>=plan.created_on&&on<=snapshot.today)completionPreview=on<=JSON.parse(referencedDue.value_json).dueOn?'按时完成':'迟完成';}catch{}
  }
  return <Page title={record?`);
fs.writeFileSync(file,text);
const metal='src/ui/metal.tsx';text=fs.readFileSync(metal,'utf8');
const before='<View style={styles.overlay}><ScrollView style={{maxHeight:\'95%\'}} contentContainerStyle={styles.dialog}';
assert.equal(text.split(before).length,2);
text=text.replace(before,"<View style={[styles.overlay,{padding:4}]}><ScrollView style={{maxHeight:'95%'}} contentContainerStyle={[styles.dialog,{padding:4}]}");fs.writeFileSync(metal,text);
