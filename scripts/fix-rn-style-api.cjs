const fs=require('node:fs');
for(const file of ['src/ui/metal.tsx','scripts/complete-ui-gaps.cjs']){
  const before=fs.readFileSync(file,'utf8');
  if(!before.includes('StyleSheet.absoluteFillObject'))throw new Error(`Missing expected legacy style API in ${file}`);
  fs.writeFileSync(file,before.replace('StyleSheet.absoluteFillObject','StyleSheet.absoluteFill'));
}
