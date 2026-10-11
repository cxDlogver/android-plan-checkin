$ErrorActionPreference='Stop'
Get-Process -Name node,java,qemu-system-x86_64 -ErrorAction SilentlyContinue | Select-Object Id,ProcessName,CPU,@{Name='MemoryMiB';Expression={[math]::Round($_.WorkingSet64/1MB)}} | Format-Table -AutoSize
Get-NetTCPConnection -LocalPort 8081,8097,8098,4723 -State Listen -ErrorAction SilentlyContinue | Select-Object LocalPort,OwningProcess | Format-Table -AutoSize
