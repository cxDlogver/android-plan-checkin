$ErrorActionPreference='Stop'
$taskBindings = @(Get-NetTCPConnection -State Listen -LocalPort 4723,8097,8098 | Select-Object LocalAddress,LocalPort,OwningProcess)
if ($taskBindings.Count -lt 3 -or @($taskBindings | Where-Object LocalAddress -ne '127.0.0.1').Count -gt 0) { throw 'Validation listeners must bind only to IPv4 loopback.' }
$taskRecord = [ordered]@{ checkedAt=(Get-Date).ToUniversalTime().ToString('o'); status='PASS'; bindings=$taskBindings; scope='current task Appium and development verification bridge only' }
$taskRecord | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath 'resource/progress/validation-listeners.json' -Encoding utf8
$taskRecord | ConvertTo-Json -Depth 5
