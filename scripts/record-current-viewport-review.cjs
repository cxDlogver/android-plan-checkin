const {take,read,references}=require('./acceptance-evidence.cjs'),{createRun}=require('./evidence-run.cjs');
const [config,row]=process.argv.slice(2);
if(!['M2/three_button','M4/gesture','M6/three_button','M8/gesture'].includes(config+'/'+row))throw Error('Only the two actually inspected current IME images are authorized in this review');
const item=take(`AC093-${row}-${config}-viewport-continuation`),image=item.r.evidence.find(e=>e.path.endsWith('/2-keyboard-open-save-reachable.png'));
if(!image)throw Error('Missing inspected current image');
const run=createRun(`AC093-${row}-${config}-current-viewport-reviewed`,{dependencies:references([item]),image},['IP27'],{caseId:'AC093',configId:config,rowId:row,phase:'VISUAL_REVIEW'});
if(run){run.write('current-viewport-review.json',{reviewer:'Codex actual image inspection',image,geometry:read(item,'complete-keyboard-and-save-bounds.json'),observation:'The full current Save rectangle and complete 确认保存 caption are visible above the actual keyboard. The native gesture pill or three-button bar is visible. The original accepted Back and retained-draft observations are linked by the companion; this review claims current Save viewport only.',noRepeatedBusinessExecution:true});run.check('actual-inspected-full-save',true,item.r.assertions.some(a=>a.id==='AC093.A2.actual-complete-unclipped-save'&&a.actual===true));run.finish();}
