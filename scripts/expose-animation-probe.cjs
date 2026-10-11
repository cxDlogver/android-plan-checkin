const fs=require('node:fs'),assert=require('node:assert/strict');
const file='src/verification/development.tsx',source=fs.readFileSync(file,'utf8');
const before='<Animated.View style={[{width:30,height:30,backgroundColor:',after='<Animated.View accessible testID="native.animation.square" accessibilityLabel="原生动画方块" style={[{width:30,height:30,backgroundColor:';
if(source.includes(after)){console.log('SKIP animation probe already exposed');process.exit(0);}
assert.equal(source.split(before).length,2);fs.writeFileSync(file,source.replace(before,after));
console.log('Exposed the development animation view to the native accessibility bounds probe.');
