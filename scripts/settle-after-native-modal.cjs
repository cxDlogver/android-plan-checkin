module.exports=async t=>{
 await new Promise(r=>setTimeout(r,1000));
 const before=t.device.adb(['shell','dumpsys','input_method']);
 t.run.write('post-modal-before-discard-IME.log',before);
 // A modal may restore focus to the note input. Observe that new IME before
 // testing navigation away from the form; the original first Back is separate.
 if(t.device.api==='36'&&/mInputShown=true\b/.test(before)){
  await t.device.hideKeyboard();
  t.run.write('post-modal-restored-IME-dismissal.json',{beforeShown:true,afterShown:await require('./wait-keyboard-observation.cjs')(t,false),scope:'Dismiss only an IME restored after the date modal. This is not a repeat of the accepted initial keyboard Back.'});
 }
};
