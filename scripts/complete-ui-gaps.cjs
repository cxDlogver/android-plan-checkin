const fs=require('node:fs'),assert=require('node:assert/strict');
function edit(file,pairs){let text=fs.readFileSync(file,'utf8');for(const [before,after]of pairs){assert.equal(text.split(before).length,2,`${file}: ${before}`);text=text.replace(before,after);}fs.writeFileSync(file,text);}
edit('src/ui/metal.tsx',[
  ['onChange,testID}:{options:', 'onChange,testID,disabled=false}:{options:'],
  ['onChange:(value:string)=>void;testID?:string})','onChange:(value:string)=>void;testID?:string;disabled?:boolean})'],
  ['<Button title={option.label} selected=', '<Button disabled={disabled} title={option.label} selected='],
  ['zone,testID,error}:{label:', 'zone,testID,error,disabled=false}:{label:'],
  ['testID?:string;error?:string}){','testID?:string;error?:string;disabled?:boolean}){'],
  ['<Button title={value||\'不设置结束\'} testID={testID}', '<TextInput accessibilityLabel={`${label}，YYYY-MM-DD`} placeholder="YYYY-MM-DD" editable={!disabled} value={value||\'\'} onChangeText={text=>onChange(nullable&&text===\'\'?null:text)} testID={testID?`${testID}.input`:undefined} style={styles.input}/><Button disabled={disabled} title="选择日期" testID={testID}'],
  ["setMonth((value||min||businessToday(Date.now(),zone)).slice(0,7));setOpen(true);", "setMonth((value&&/^\\d{4}-\\d{2}/.test(value)?value:min||businessToday(Date.now(),zone)).slice(0,7));setOpen(true);"],
]);
const metal='src/ui/metal.tsx';fs.appendFileSync(metal,`\nexport function StatusFilter({value,onChange,counts}:{value:string;onChange:(value:string)=>void;counts:{all:number;completed:number;incomplete:number}}){
  const [open,setOpen]=useState(false);
  const options=[{value:'all',label:'全部状态'},{value:'completed',label:'已完成'},{value:'incomplete',label:'未完成'}] as const;
  const current=options.find(option=>option.value===value)!;
  return <View><Button title={current.label+'（'+counts[current.value]+'）'} accessibilityLabel={'状态筛选，'+current.label+'，'+counts[current.value]+'项'} testID="calendar.filter.open" onPress={()=>setOpen(true)}/><Modal transparent visible={open} onRequestClose={()=>setOpen(false)}><View style={styles.overlay}><Pressable accessible={false} testID="calendar.filter.outside" onPress={()=>setOpen(false)} style={StyleSheet.absoluteFill}/><View style={styles.dialog}><Body title>筛选状态</Body>{options.map(option=><Button key={option.value} title={option.label+'（'+counts[option.value]+'）'} selected={value===option.value} testID={'calendar.filter.'+option.value} onPress={()=>{onChange(option.value);setOpen(false);}}/>)}<Button title="关闭筛选" testID="calendar.filter.close" onPress={()=>setOpen(false)}/></View></View></Modal></View>;
}\n`);
edit('src/features/shared.tsx',[
  ["const {snapshot}=useApp();return", "const {snapshot}=useApp(),outcome=snapshot.facts.one_time_results.find(row=>row.plan_id===plan.id),state=status(snapshot.facts,plan.id,snapshot.asOfMs);return"],
  ['{children}<Button title="查看计划"','{state===\'running\'&&plan.type!==\'one_time\'&&plan.starts_on>snapshot.today&&<Body>尚未开始 · {plan.starts_on}</Body>}{outcome&&<Body strong style={{color:resultColor(outcome.outcome)}}>{resultText(plan,outcome.outcome)}</Body>}{children}<Button title="查看计划"'],
]);
edit('src/features/plan-detail.tsx',[
  ['的计划、规则、全部记录与统计，无法恢复。','的计划、规则、${snapshot.facts.cycle_records.filter(r=>r.plan_id===plan.id).length+snapshot.facts.one_time_results.filter(r=>r.plan_id===plan.id).length} 条记录与统计，无法恢复。'],
  ["?'按时完成':'延期完成'", "?'按时完成':'迟完成'"],
]);
