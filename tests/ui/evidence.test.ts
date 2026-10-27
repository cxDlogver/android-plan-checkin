import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {validateObservation} from './oracle';
test('evidence records require provenance, environment, resolved inputs and actual observations',()=>{
 const record={uiVersion:'test-fixture-version',documentId:'test-document',nodeIds:['test-node'],environment:{viewport:{width:393,height:852},fontScale:1,insets:{top:24,bottom:24},keyboard:null},inputs:{name:'独立契约夹具'},screenshot:'fixture-only.png',differences:[],status:'passed',actual:{observed:true}};
 assert.equal(validateObservation(record),true);for(const key of ['uiVersion','documentId','nodeIds','environment','inputs','screenshot','differences','status']){const invalid:any={...record};delete invalid[key];assert.throws(()=>validateObservation(invalid));}
 assert.throws(()=>validateObservation({...record,status:'not_run',passed:true}));assert.throws(()=>validateObservation({...record,actual:null}));assert.throws(()=>validateObservation({...record,nodeIds:[]}));assert.throws(()=>validateObservation({...record,documentId:''}));
 assert.equal(validateObservation({...record,status:'not_run',actual:null}),true);
 if(process.env.UI_EVIDENCE_DIR)fs.writeFileSync(path.join(process.env.UI_EVIDENCE_DIR,'evidence-contract-tests.json'),JSON.stringify({sampleKind:'contract test data, not a captured UI',validInput:record,missingFields:['uiVersion','documentId','nodeIds','environment','inputs','screenshot','differences','status'],invalidOverrides:[{status:'not_run',passed:true},{actual:null},{nodeIds:[]},{documentId:''}],validNotRunInput:{...record,status:'not_run',actual:null},rejectedMissingFields:8,rejectedUnobservedPass:true,passed:true}));
});
