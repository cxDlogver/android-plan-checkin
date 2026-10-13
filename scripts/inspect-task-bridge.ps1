$ErrorActionPreference='Stop'
Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'node.exe' -and $_.CommandLine -match 'verification-bridge\.cjs' } | Select-Object ProcessId,CommandLine | ConvertTo-Json -Compress
