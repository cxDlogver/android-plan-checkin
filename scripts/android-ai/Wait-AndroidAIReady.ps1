param([ValidateSet('29','36')][string]$Api = '36', [int]$TimeoutSeconds = 300, [string]$ToolRoot = 'D:\xiang\CX_application\1_Configuration_Files\Android-AI')
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'Use-AndroidAI.ps1') -ToolRoot $ToolRoot
if ($TimeoutSeconds -lt 1 -or $TimeoutSeconds -gt 600) { throw '启动等待时间必须为1–600秒' }
$taskSerial = if ($Api -eq '29') { 'emulator-5560' } else { 'emulator-5562' }
$taskAdb = Join-Path $env:ANDROID_HOME 'platform-tools\adb.exe'
if (-not (Test-Path -LiteralPath $taskAdb)) { throw "ADB不存在：$taskAdb" }
function Get-AndroidBootStatus {
    $taskProbeInfo = New-Object System.Diagnostics.ProcessStartInfo
    $taskProbeInfo.FileName = $taskAdb
    $taskProbeInfo.Arguments = "-s $taskSerial shell getprop sys.boot_completed"
    $taskProbeInfo.UseShellExecute = $false
    $taskProbeInfo.CreateNoWindow = $true
    $taskProbeInfo.RedirectStandardOutput = $true
    $taskProbeInfo.RedirectStandardError = $true
    $taskProbe = New-Object System.Diagnostics.Process
    $taskProbe.StartInfo = $taskProbeInfo
    try {
        [void]$taskProbe.Start()
        $taskProbeOutput = $taskProbe.StandardOutput.ReadToEndAsync()
        $taskProbeError = $taskProbe.StandardError.ReadToEndAsync()
        if (-not $taskProbe.WaitForExit(5000)) {
            $taskProbe.Kill()
            $taskProbe.WaitForExit()
            return ''
        }
        $taskProbeText = $taskProbeOutput.GetAwaiter().GetResult()
        [void]$taskProbeError.GetAwaiter().GetResult()
        if ($taskProbe.ExitCode -eq 0) { return $taskProbeText.Trim() }
        return ''
    } finally { $taskProbe.Dispose() }
}
$taskStarted = Get-Date
do {
    $taskBoot = Get-AndroidBootStatus
    if ($taskBoot.Trim() -eq '1') { break }
    Start-Sleep -Seconds 3
} while (((Get-Date) - $taskStarted).TotalSeconds -lt $TimeoutSeconds)
if ($taskBoot.Trim() -ne '1') { throw "$taskSerial 启动超时，查看工具目录logs/emulator-api$Api.*.log" }
$taskAvd = @(& adb.exe -s $taskSerial emu avd name)
if ("plancheckin_api$Api" -notin $taskAvd) { throw '端口上的AVD不属于本项目' }
$taskSdk = ((& adb.exe -s $taskSerial shell getprop ro.build.version.sdk) -join '').Trim()
if ($taskSdk -ne $Api) { throw "API不符：预期$Api，实际$taskSdk" }
$taskReport = [ordered]@{
    checkedAt = (Get-Date).ToUniversalTime().ToString('o')
    avd = "plancheckin_api$Api"; serial = $taskSerial; api = [int]$taskSdk
    bootCompleted = 1; adbState = ((& adb.exe -s $taskSerial get-state) -join '').Trim()
    size = ((& adb.exe -s $taskSerial shell wm size) -join '').Trim()
    density = ((& adb.exe -s $taskSerial shell wm density) -join '').Trim()
    fontScale = ((& adb.exe -s $taskSerial shell settings get system font_scale) -join '').Trim()
    deviceTimeZone = ((& adb.exe -s $taskSerial shell getprop persist.sys.timezone) -join '').Trim()
    configuredCores = 4; configuredRamMiB = 4096; verification = 'PASS'
}
$taskReport | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $ToolRoot "logs\boot-api$Api.json") -Encoding utf8
$taskReport | ConvertTo-Json
