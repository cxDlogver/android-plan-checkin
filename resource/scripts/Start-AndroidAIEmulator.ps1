param([ValidateSet('29','36')][string]$Api = '36', [switch]$Visible, [string]$ToolRoot = 'D:\xiang\CX_application\1_Configuration_Files\Android-AI')
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'Use-AndroidAI.ps1') -ToolRoot $ToolRoot
$taskEmulator = Join-Path $env:ANDROID_HOME 'emulator\emulator.exe'
if (-not (Test-Path -LiteralPath $taskEmulator)) { throw 'Emulator尚未安装；先完成SDK配置' }
$taskName = "plancheckin_api$Api"
$taskPort = if ($Api -eq '29') { 5560 } else { 5562 }
if (Get-NetTCPConnection -LocalPort $taskPort -State Listen -ErrorAction SilentlyContinue) { throw "模拟器端口$taskPort已占用；请先确认现有设备" }
$taskAvds = @(& $taskEmulator -list-avds)
if ($taskName -notin $taskAvds) { throw "AVD尚未创建：$taskName" }
$taskArguments = @('-avd',$taskName,'-port',[string]$taskPort,'-memory','4096','-cores','4','-no-snapshot','-no-boot-anim','-no-metrics','-timezone','Asia/Shanghai','-gpu','host')
if (-not $Visible) { $taskArguments += '-no-window' }
$taskStdout = Join-Path $ToolRoot "logs\emulator-api$Api.stdout.log"
$taskStderr = Join-Path $ToolRoot "logs\emulator-api$Api.stderr.log"
if ($Visible) { $taskProcess = Start-Process -FilePath $taskEmulator -ArgumentList $taskArguments -RedirectStandardOutput $taskStdout -RedirectStandardError $taskStderr -PassThru }
else { $taskProcess = Start-Process -FilePath $taskEmulator -ArgumentList $taskArguments -WindowStyle Hidden -RedirectStandardOutput $taskStdout -RedirectStandardError $taskStderr -PassThru }
[PSCustomObject]@{ ProcessId=$taskProcess.Id; Avd=$taskName; Serial="emulator-$taskPort"; Visible=[bool]$Visible; BootStatus='WAIT_FOR_ADB' }
