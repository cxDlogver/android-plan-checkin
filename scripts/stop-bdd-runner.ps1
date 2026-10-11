param([Parameter(Mandatory=$true)][ValidateSet('bdd-ui-records.cjs')][string]$Script)
$ErrorActionPreference='Stop'
$matches=@(Get-CimInstance Win32_Process -Filter "Name='node.exe'" | Where-Object { $_.CommandLine.Contains($Script) })
if ($matches.Count -ne 1) { throw "Expected exactly one project runner; found $($matches.Count)" }
Stop-Process -Id $matches[0].ProcessId
Write-Output "Stopped only the failed project runner PID $($matches[0].ProcessId)"
