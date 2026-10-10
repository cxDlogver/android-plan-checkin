param([string]$ToolRoot = 'D:\xiang\CX_application\1_Configuration_Files\Android-AI')
$ErrorActionPreference = 'Stop'
$taskNodeRoot = Join-Path $ToolRoot 'node-v24.21.0-win-x64'
if (-not (Test-Path -LiteralPath (Join-Path $taskNodeRoot 'node.exe'))) { throw "Node24工具目录不存在：$taskNodeRoot" }
$env:JAVA_HOME = 'D:\xiang\CX_application\1_Configuration_Files\JAVA\jdk-17.0.1'
$env:ANDROID_HOME = Join-Path $ToolRoot 'sdk'
$env:ANDROID_SDK_ROOT = $env:ANDROID_HOME
$env:ANDROID_USER_HOME = Join-Path $ToolRoot 'android-user'
$env:ANDROID_AVD_HOME = Join-Path $ToolRoot 'avd'
$env:APPIUM_HOME = Join-Path $ToolRoot 'appium-home'
$env:ANDROID_AI_TOOL_ROOT = $ToolRoot
$env:npm_config_cache = Join-Path $ToolRoot 'npm-cache'
$env:npm_config_registry = 'https://registry.npmjs.org/'
$env:APPIUM_SKIP_CHROMEDRIVER_INSTALL = '1'
$taskPathEntries = @($taskNodeRoot, (Join-Path $ToolRoot 'appium\node_modules\.bin'), (Join-Path $env:JAVA_HOME 'bin'), (Join-Path $env:ANDROID_HOME 'platform-tools'), (Join-Path $env:ANDROID_HOME 'emulator'), (Join-Path $env:ANDROID_HOME 'cmdline-tools\22.0\bin'))
$taskExistingPathEntries = @($env:Path -split ';' | Where-Object { $_ -and $_ -notin $taskPathEntries })
$env:Path = (@($taskPathEntries) + $taskExistingPathEntries | Select-Object -Unique) -join ';'
# 仅改变当前PowerShell及其子进程，避免覆盖其他项目的全局Node。
