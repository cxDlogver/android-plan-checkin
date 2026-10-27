import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {resolveText,resolvePercent} from '../../src/ui/bindings';
import {spec,flatten,expectedText} from './oracle';
test('all dynamic fields use both independent typed input groups and reject missing inputs',()=>{
 let fields=0;
 for(const doc of spec().documents)for(const node of flatten(doc.tree))if(node.content?.binding){for(const group of [0,1]){const values:Record<string,string|number>={};for(const [key,parameter]of Object.entries(node.content.binding.parameters)as [string,{type:string}][]){values[key]=parameter.type==='integer'?(group?23:17):parameter.type==='number'?(group?.81:.37):parameter.type==='date'?(group?'2027-02-14':'2025-11-03'):parameter.type==='datetime'?(group?'2027-02-14T16:48:00Z':'2025-11-03T11:35:00Z'):parameter.type==='time'?(group?'16:48':'11:35'):(group?'动态乙 ':'动态甲 ')+key;}assert.equal(resolveText(node.content,values),expectedText(node.content,values));for(const key of Object.keys(values)){const missing={...values};delete missing[key];assert.throws(()=>resolveText(node.content,missing));}fields++;}}
 assert.ok(fields>100);
 if(process.env.UI_EVIDENCE_DIR)fs.writeFileSync(path.join(process.env.UI_EVIDENCE_DIR,'bindings-tests.json'),JSON.stringify({groups:2,bindingsChecked:fields,passed:true}));
});
test('proportional fills preserve 0, half, full and reject invalid proportional inputs',()=>{
 let count=0;for(const doc of spec().documents)for(const node of flatten(doc.tree)){const sizing=node.sizing.width;if(!sizing.binding)continue;for(const ratio of [0,.5,1])assert.equal(resolvePercent(sizing,{[sizing.binding.path]:ratio}),ratio);for(const ratio of [-.01,1.01,NaN,'0.5'])assert.throws(()=>resolvePercent(sizing,{[sizing.binding.path]:ratio}));count++;}assert.ok(count>0);
});
