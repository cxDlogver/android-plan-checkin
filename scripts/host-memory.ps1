$ErrorActionPreference = 'Stop'
$system = Get-CimInstance Win32_OperatingSystem
$workspace = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$processes = Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'java.exe' -and $_.CommandLine -and $_.CommandLine.Contains($workspace) }
@{ checkedAt = (Get-Date).ToUniversalTime().ToString('o'); memory = ($system | Select-Object FreePhysicalMemory,FreeVirtualMemory,TotalVisibleMemorySize,TotalVirtualMemorySize); processes = @($processes | ForEach-Object { $running=Get-Process -Id $_.ProcessId; @{ processId=$_.ProcessId; parentProcessId=$_.ParentProcessId; cpuSeconds=$running.CPU; workingSet=$running.WorkingSet64; privateMemory=$running.PrivateMemorySize64; commandLine=$_.CommandLine } }) } | ConvertTo-Json -Depth 4
