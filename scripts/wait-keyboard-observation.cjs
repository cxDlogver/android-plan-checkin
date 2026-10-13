const {nodes,bounds}=require('./ui-tree-observation.cjs');
module.exports=async function(t,shown){
 if(t.device.api!=='36')return t.device.request(t.device.endpoint('appium/device/is_keyboard_shown'));
 const deadline=Date.now()+(shown?15000:5000),observations=[];let source,raw;
 do{raw=t.device.adb(['shell','dumpsys','input_method']);const requested=/mInputShown=true\b/.test(raw);source=await t.device.source();const keyboards=nodes(source).filter(n=>/com\.(?:android|google\.android)\.inputmethod/.test(n.attributes.package||'')&&n.attributes['resource-id']?.endsWith('/keyboard_view')).map(n=>bounds(n.attributes.bounds)).filter(b=>b&&b.height>=200&&b.width>0);observations.push({at:new Date().toISOString(),requested,inputViewShown:/mIsInputViewShown=true\b/.test(raw),actualKeyboardBounds:keyboards});
  if(shown?requested&&keyboards.length:!requested){t.run.write((shown?'before':'after')+'-actual-IME-state.json',{observations,actualShown:shown,scope:'Native API36 request flag plus actual keyboard_view hierarchy bounds for showing; poll the native request flag after Back instead of sampling it before the asynchronous hide completes.'});t.run.write((shown?'before':'after')+'-actual-IME-dumpsys.log',raw);return shown;}await new Promise(r=>setTimeout(r,300));
 }while(Date.now()<deadline);
 t.run.write('unsettled-IME-observations.json',{shown,observations});t.run.write('unsettled-IME-dumpsys.log',raw);await t.frame('unsettled-IME-real-product');throw new Error(shown?'Native IME has no actual rendered keyboard_view; do not treat request flags as a visible keyboard.':'Native IME did not settle hidden after Back.');
};
