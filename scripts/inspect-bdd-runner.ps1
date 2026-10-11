param([switch]$Stop)
$ErrorActionPreference='Stop'
$runners=@(Get-CimInstance Win32_Process -Filter "name='node.exe'" | Where-Object { $_.CommandLine -match 'scripts[/\\]run-bdd-matrix.cjs M1' })
if($Stop){if($runners.Count -ne 1){throw "Expected one scoped M1 runner"};Stop-Process -Id $runners[0].ProcessId;Write-Output "Stopped scoped M1 runner $($runners[0].ProcessId) for harness repair"}else{$runners | Select-Object ProcessId,CommandLine | Format-List}
