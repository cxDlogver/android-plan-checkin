param([ValidateSet('29','36')][string]$Api = '36', [switch]$KeepAppium, [string]$ToolRoot = 'D:\xiang\CX_application\1_Configuration_Files\Android-AI')
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'Use-AndroidAI.ps1') -ToolRoot $ToolRoot
$taskSerial = if ($Api -eq '29') { 'emulator-5560' } else { 'emulator-5562' }
$taskDevices = @(& adb.exe devices)
if ($taskDevices | Where-Object { $_ -match "^$taskSerial\s" }) {
    $taskAvdName = @(& adb.exe -s $taskSerial emu avd name)
    if ("plancheckin_api$Api" -notin $taskAvdName) { throw '指定端口的设备不属于本项目，已停止。' }
    & adb.exe -s $taskSerial emu kill
    if ($LASTEXITCODE -ne 0) { throw '模拟器关闭失败。' }
}
if (-not $KeepAppium) {
    $taskListener = Get-NetTCPConnection -LocalPort 4723 -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($taskListener) {
        $taskServer = Get-CimInstance Win32_Process -Filter "ProcessId=$($taskListener.OwningProcess)"
        $taskNode = Join-Path $ToolRoot 'node-v24.21.0-win-x64\node.exe'
        $taskMain = Join-Path $ToolRoot 'appium\node_modules\appium\build\lib\main.js'
        if ($taskServer.ExecutablePath -ne $taskNode -or -not $taskServer.CommandLine.Contains($taskMain)) { throw '端口服务不属于本项目，已保留。' }
        Stop-Process -Id $taskServer.ProcessId
    }
}
$taskResult = [ordered]@{checkedAt=(Get-Date).ToUniversalTime().ToString('o');api=[int]$Api;serial=$taskSerial;stopRequested=$true;appiumRetained=[bool]$KeepAppium}
$taskResult | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $ToolRoot 'logs\last-stop.json') -Encoding utf8
$taskRuntimePath = Join-Path $ToolRoot 'logs\runtime-state.json'
if (Test-Path -LiteralPath $taskRuntimePath) {
    $taskRuntime = Get-Content -LiteralPath $taskRuntimePath -Raw | ConvertFrom-Json
    if ($taskRuntime.api -eq [int]$Api) {
        $taskRuntime.backgroundState = 'STOP_REQUESTED'
        $taskRuntime.environmentReady = $false
        $taskRuntime | ConvertTo-Json | Set-Content -LiteralPath $taskRuntimePath -Encoding utf8
    }
}
$taskResult | ConvertTo-Json
