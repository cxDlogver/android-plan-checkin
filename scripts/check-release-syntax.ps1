$ErrorActionPreference = 'Stop'
$taskTokens = $null
$taskErrors = $null
[Management.Automation.Language.Parser]::ParseFile((Join-Path $PSScriptRoot 'Release-PlanCheckin.ps1'), [ref]$taskTokens, [ref]$taskErrors) | Out-Null
$taskResult = [ordered]@{ checkedAt=(Get-Date).ToUniversalTime().ToString('o'); scope='Release-PlanCheckin.ps1 parse only, no signing operation'; status= $(if ($taskErrors.Count) {'FAIL'} else {'PASS'}); errors=@($taskErrors | ForEach-Object { $_.Message }) }
$taskResult | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $PSScriptRoot '..\resource\progress\release-script-syntax.json') -Encoding UTF8
$taskResult | ConvertTo-Json -Depth 4
if ($taskErrors.Count) { exit 1 }
