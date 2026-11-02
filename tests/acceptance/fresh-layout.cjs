'use strict';
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const ready=require('./fixture-readiness.cjs');
module.exports=async options=>{
 const {root,directory,adapter,seed}=options,profiles=[],targets=[];
 try{
  const primaryFrames={prepareProfile:profile=>ready.prepareFixtureProfile(adapter,seed,profile,profiles),prepareKeyboardTarget:id=>ready.prepareKeyboardTarget(adapter,id,targets)};
  const result=await require('./browse-matrix.cjs')({...options,primaryFrames});
  const comparisons=result.keyboards.map(k=>{const inspect=(file,id,bounds)=>ready.assertFullKeyboardProof(JSON.parse(fs.readFileSync(path.join(directory,file))),fs.readFileSync(path.join(directory,file.replace(/\.json$/,'.xml')),'utf8'),id,bounds);return {row:k.row,documentId:k.documentId,focus:inspect(k.focus,k.inputId,k.inputBounds),save:inspect(k.save,k.saveId,k.saveBounds)};});assert.equal(comparisons.length,81);fs.writeFileSync(path.join(directory,'responsive-full-keyboard-visibility.json'),JSON.stringify({combinations:81,fullyVisibleFocus:81,fullyVisibleSave:81,results:comparisons},null,2)+'\n');
  require('./supplementary.cjs').baseline(adapter);await ready.prepareFixtureProfile(adapter,seed,{width:393,height:852,fontScale:1},profiles);await adapter.restart(seed);return result;
 }finally{fs.writeFileSync(path.join(directory,'responsive-matrix-profile-readiness.json'),JSON.stringify({profiles},null,2)+'\n');fs.writeFileSync(path.join(directory,'responsive-keyboard-target-readiness.json'),JSON.stringify({targets},null,2)+'\n');}
};
