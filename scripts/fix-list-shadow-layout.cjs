const fs=require('node:fs'),assert=require('node:assert/strict'),{sha}=require('./p1.cjs');
const changes=[];
function edit(file,before,after){const content=fs.readFileSync(file,'utf8');if(content.includes(after))return;assert.equal(content.split(before).length,2,file);const updated=content.replace(before,after);fs.writeFileSync(file,updated);changes.push({file,beforeSha256:sha(content),afterSha256:sha(updated)});}
edit('src/ui/metal.tsx',"!scroll&&{flex:1,paddingHorizontal:20}","!scroll&&{flex:1}");
for(const file of ['src/features/plans.tsx','src/features/calendar.tsx','src/features/plan-detail.tsx'])edit(file,'<FlatList data=','<FlatList contentContainerStyle={{paddingHorizontal:20,paddingTop:8,paddingBottom:8}} data=');
edit('src/features/today.tsx','<SectionList sections=','<SectionList contentContainerStyle={{paddingHorizontal:20,paddingTop:8,paddingBottom:8}} sections=');
edit('src/features/plans.tsx','<Choice value={filter}','<View style={{paddingHorizontal:20}}><Choice value={filter}');
edit('src/features/plans.tsx',"label:'归档'}]}/><FlatList","label:'归档'}]}/></View><FlatList");
if(changes.length)fs.writeFileSync('resource/progress/list-shadow-fix.json',JSON.stringify({recordedAt:new Date().toISOString(),status:'AWAITING_NATIVE_REVIEW',problem:'Lists clipped outer shadows because horizontal page padding narrowed the scroll viewport; API29 native stack also overrode status-bar icon appearance.',changes,scope:'Four list content containers retain the same 20dp horizontal inset, with 8dp breathing space inside their full-width scroll viewport; native stack explicitly requests dark status-bar icons.',businessLogicChanged:false},null,2)+'\n');
console.log(`Updated ${changes.length} layout source entries.`);
