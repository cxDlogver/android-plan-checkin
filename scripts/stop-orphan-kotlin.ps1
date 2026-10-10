$ErrorActionPreference = 'Stop'
$workspace = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$processes = Get-CimInstance Win32_Process -Filter "Name='java.exe'"
$stopped = @()
foreach ($process in $processes) {
  if ($process.CommandLine -and $process.CommandLine.Contains("$workspace\.cache\gradle\") -and $process.CommandLine.Contains('org.jetbrains.kotlin.daemon.KotlinCompileDaemon') -and -not (Get-Process -Id $process.ParentProcessId -ErrorAction SilentlyContinue)) {
    Stop-Process -Id $process.ProcessId
    $stopped += $process.ProcessId
  }
}
$system = Get-CimInstance Win32_OperatingSystem
$evidence = @{ checkedAt=(Get-Date).ToUniversalTime().ToString('o'); stoppedTaskOrphans=$stopped; freePhysicalKiB=$system.FreePhysicalMemory; freeVirtualKiB=$system.FreeVirtualMemory; reason='Failed task Gradle parent exited; only this workspace Kotlin daemon selected' }
$evidence | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $workspace 'resource/progress/native-memory-recovery.json') -Encoding UTF8
$evidence | ConvertTo-Json
