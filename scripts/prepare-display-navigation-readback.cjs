const fs=require('node:fs'),file='scripts/bdd-ui-display.cjs';
let source=fs.readFileSync(file,'utf8');
const before="['shell','cmd','overlay','lookup','android','android:integer/config_navBarInteractionMode']";
if(!source.includes(before))throw new Error('Expected original Android navigation readback absent');
fs.writeFileSync(file,source.replace(before,"['shell','settings','get','secure','navigation_mode']"));
console.log('Android 10 navigation readback uses the real secure setting plus enabled overlay evidence.');
