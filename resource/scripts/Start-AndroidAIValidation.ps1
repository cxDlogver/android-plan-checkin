param(
    [ValidateSet('29','36')][string]$Api = '36',
    [switch]$VerifyControl,
    [string]$ToolRoot = 'D:\xiang\CX_application\1_Configuration_Files\Android-AI'
)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'Use-AndroidAI.ps1') -ToolRoot $ToolRoot
$taskSerial = if ($Api -eq '29') { 'emulator-5560' } else { 'emulator-5562' }
$taskOtherSerial = if ($Api -eq '29') { 'emulator-5562' } else { 'emulator-5560' }
$taskInitialDevices = @(& adb.exe devices)
if ($taskInitialDevices | Where-Object { $_ -match "^$taskOtherSerial\s" }) {
    throw '另一套验收AVD正在运行，请先关闭它，再切换API。'
}
$taskAddress = 'http://127.0.0.1:4723'
$taskNode = Join-Path $ToolRoot 'node-v24.21.0-win-x64\node.exe'
$taskMain = Join-Path $ToolRoot 'appium\node_modules\appium\build\lib\main.js'
$taskListener = Get-NetTCPConnection -LocalPort 4723 -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
if ($taskListener) {
    $taskServer = Get-CimInstance Win32_Process -Filter "ProcessId=$($taskListener.OwningProcess)"
    if ($taskServer.ExecutablePath -ne $taskNode -or -not $taskServer.CommandLine.Contains($taskMain)) {
        throw '4723端口不属于本项目Appium，请先确认该服务。'
    }
    $taskServerId = $taskServer.ProcessId
} else {
    $taskService = & (Join-Path $PSScriptRoot 'Start-AndroidAIService.ps1') -ToolRoot $ToolRoot
    $taskServerId = $taskService.ProcessId
}
$taskDeadline = (Get-Date).AddSeconds(60)
do {
    try { $taskHealth = Invoke-RestMethod -Uri "$taskAddress/status" -TimeoutSec 2 }
    catch { $taskHealth = $null }
    if ($taskHealth.value.ready) { break }
    Start-Sleep -Seconds 1
} while ((Get-Date) -lt $taskDeadline)
if (-not $taskHealth.value.ready) { throw "Appium未就绪，查看$ToolRoot\logs\appium-4723.log" }
$taskExpectedVersion = (Get-Content -LiteralPath (Join-Path $ToolRoot 'appium\node_modules\appium\package.json') -Raw | ConvertFrom-Json).version
if ($taskHealth.value.build.version -ne $taskExpectedVersion) { throw 'Appium服务版本与本地安装不一致。' }
$taskDevices = @(& adb.exe devices)
if (-not ($taskDevices | Where-Object { $_ -match "^$taskSerial\s" })) {
    & (Join-Path $PSScriptRoot 'Start-AndroidAIEmulator.ps1') -Api $Api -ToolRoot $ToolRoot | Out-Host
}
& (Join-Path $PSScriptRoot 'Wait-AndroidAIReady.ps1') -Api $Api -ToolRoot $ToolRoot | Out-Host
$taskControl = 'NOT_REQUESTED'
if ($VerifyControl) {
    & $taskNode (Join-Path $PSScriptRoot 'Check-AndroidAIAutomation.cjs') $Api
    if ($LASTEXITCODE -ne 0) { throw "API$Api自动化控制检查失败，查看$ToolRoot\logs\automation-api$Api.json" }
    $taskControl = 'PASS'
}
$taskRuntime = [ordered]@{
    checkedAt = (Get-Date).ToUniversalTime().ToString('o')
    appiumProcessId = $taskServerId; appiumAddress = $taskAddress
    avd = "plancheckin_api$Api"; serial = $taskSerial; api = [int]$Api
    deviceTimeZone = ((& adb.exe -s $taskSerial shell getprop persist.sys.timezone) -join '').Trim()
    environmentReady = $true; nativeControl = $taskControl
    productAcceptance = 'NOT_RUN'; backgroundState = 'RUNNING'
}
$taskRuntime | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $ToolRoot 'logs\runtime-state.json') -Encoding utf8
$taskRuntime | ConvertTo-Json
