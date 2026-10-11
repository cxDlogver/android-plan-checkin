const fs=require('node:fs'),assert=require('node:assert/strict');
const file='src/ui/metal.tsx';let text=fs.readFileSync(file,'utf8');
const before="style={{fontSize:12,color:error?colors.failure:colors.muted}}>{error||''}";
assert.equal(text.split(before).length,2);
text=text.replace(before,"accessibilityRole={error?'alert':undefined} accessibilityLiveRegion={error?'polite':undefined} style={{fontSize:12,color:error?colors.failure:colors.muted}}>{error||''}");
const target='<Modal visible={open} transparent';assert.equal(text.split(target).length,2);
text=text.replace(target,'{error&&<Body accessibilityRole="alert" accessibilityLiveRegion="polite" style={{color:colors.failure}}>{error}</Body>}<Modal visible={open} transparent');
fs.writeFileSync(file,text);
