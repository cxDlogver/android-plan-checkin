param([Parameter(Mandatory=$true)][int]$TaskProcessId)
$ErrorActionPreference='Stop'
$taskProcess=Get-CimInstance Win32_Process -Filter "ProcessId=$TaskProcessId"
if (-not $taskProcess) { Write-Output 'Project verification bridge already exited'; exit 0 }
if (-not $taskProcess.CommandLine.Contains('verification-bridge.cjs') -or $taskProcess.Name -ne 'node.exe') { throw 'The PID is not the project verification bridge.' }
$listener=Get-NetTCPConnection -LocalPort 8098 -State Listen
if ($listener.OwningProcess -ne $TaskProcessId) { throw 'The project bridge listener belongs to another process.' }
Stop-Process -Id $TaskProcessId
Write-Output 'Stopped project verification bridge only'
