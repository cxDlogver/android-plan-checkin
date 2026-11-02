'use strict';
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
function assertNativeSmoke(actual,directory){
 const report=actual.report,rows=[];
 const check=(label,expected,value)=>{rows.push({label,expected,actual:value,verdict:require('node:util').isDeepStrictEqual(expected,value)?'passed':'failed'});fs.writeFileSync(path.join(directory,'controls-comparisons.json'),JSON.stringify({assertions:rows},null,2)+'\n');assert.deepEqual(value,expected,label);};
 check('disabled click invokes no handler',0,report.calls.filter(c=>c.name==='disabled').length);
 check('enabled click invokes its handler once',1,report.calls.filter(c=>c.name==='enabled').length);
 check('Choice event preserves its selected value','b',report.choice);
 check('Field preserves controlled input','实际控件输入',report.value);
 const disabled=actual.evidence.source.match(/<[^>]*resource-id="ui-test.disabled"[^>]*>/)?.[0];
 check('disabled state is exposed by the actual native node',true,Boolean(disabled?.includes('enabled="false"')));
 check('error text remains present in the actual native tree',true,actual.evidence.source.includes('可观察的错误说明'));
 check('injected real container does not submit during its mount',0,actual.fixtureReport.trace.filter(c=>c.name==='execute').length);
 return rows;
}
module.exports={assertNativeSmoke};
