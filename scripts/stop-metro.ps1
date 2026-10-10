param([Parameter(Mandatory=$true)][int]$TaskProcessId)
$ErrorActionPreference='Stop'
$taskProcess=Get-CimInstance Win32_Process -Filter "ProcessId=$TaskProcessId"
if (-not $taskProcess) { Write-Output 'Metro process already exited'; exit 0 }
if (-not $taskProcess.CommandLine.Contains('node_modules/expo/bin/cli') -or -not $taskProcess.CommandLine.Contains('--port 8081') -or -not $taskProcess.CommandLine.Contains('--dev-client')) { throw 'The PID is not the task Metro process.' }
Stop-Process -Id $TaskProcessId
Write-Output 'Stopped task development Metro only'
