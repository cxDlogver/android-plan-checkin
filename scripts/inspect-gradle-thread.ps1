param([int]$TaskProcessId)
$ErrorActionPreference='Stop'
$taskWorker=Get-CimInstance Win32_Process -Filter "ProcessId=$TaskProcessId"
$taskWorkspace=(Resolve-Path -LiteralPath '.').Path
if (-not $taskWorker.CommandLine.Contains('org.gradle.launcher.daemon.bootstrap.GradleDaemon') -or -not $taskWorker.CommandLine.Contains("$taskWorkspace\.cache\gradle")) { throw 'Only this task Gradle daemon may be inspected.' }
$taskJcmd='D:\xiang\CX_application\1_Configuration_Files\JAVA\jdk-17.0.1\bin\jcmd.exe'
& $taskJcmd $TaskProcessId Thread.print | Set-Content -LiteralPath '.cache/gradle-thread-dump.txt' -Encoding utf8
Get-Content -LiteralPath '.cache/gradle-thread-dump.txt' | Select-String -Pattern '^"Daemon worker' -Context 0,35
