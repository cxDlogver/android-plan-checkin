param([int]$Port = 4723, [string]$ToolRoot = 'D:\xiang\CX_application\1_Configuration_Files\Android-AI')
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'Use-AndroidAI.ps1') -ToolRoot $ToolRoot
if ($Port -lt 1024 -or $Port -gt 65535) { throw 'Port必须为1024–65535' }
if (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue) { throw "端口$Port已被占用；请先确认现有服务" }
$taskNode = Join-Path $ToolRoot 'node-v24.21.0-win-x64\node.exe'
$taskMain = Join-Path $ToolRoot 'appium\node_modules\appium\build\lib\main.js'
if (-not (Test-Path -LiteralPath $taskMain)) { throw 'Appium尚未安装' }
$taskLog = Join-Path $ToolRoot "logs\appium-$Port.log"
$taskArguments = @('"' + $taskMain + '"','--address','127.0.0.1','--port',[string]$Port,'--log','"' + $taskLog + '"','--log-timestamp')
$taskProcess = Start-Process -FilePath $taskNode -ArgumentList $taskArguments -WindowStyle Hidden -RedirectStandardOutput (Join-Path $ToolRoot "logs\appium-$Port.stdout.log") -RedirectStandardError (Join-Path $ToolRoot "logs\appium-$Port.stderr.log") -PassThru
[PSCustomObject]@{ ProcessId=$taskProcess.Id; Address="http://127.0.0.1:$Port"; Log=$taskLog; Status='WAIT_FOR_STATUS_READY' }
