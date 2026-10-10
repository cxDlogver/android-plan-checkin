const {spawnSync}=require('node:child_process');
const fs=require('node:fs');
const result=spawnSync('powershell.exe',['-NoProfile','-Command',"Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'node.exe' -and ($_.CommandLine -like '*scripts/p1.cjs*' -or $_.CommandLine -like '*pnpm.cjs*') } | Select-Object ProcessId,ParentProcessId,CommandLine | ConvertTo-Json -Compress"],{encoding:'utf8',windowsHide:true});
console.log(result.stdout||result.stderr);
const pkg=JSON.parse(fs.readFileSync('package.json','utf8'));
console.log(JSON.stringify({missing:Object.keys({...pkg.dependencies,...pkg.devDependencies}).filter(name=>!fs.existsSync(`node_modules/${name}/package.json`)),lockfile:fs.existsSync('pnpm-lock.yaml'),modules:fs.existsSync('node_modules/.modules.yaml')},null,2));
