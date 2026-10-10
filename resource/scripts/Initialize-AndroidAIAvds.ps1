param([string]$ToolRoot = 'D:\xiang\CX_application\1_Configuration_Files\Android-AI')
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'Use-AndroidAI.ps1') -ToolRoot $ToolRoot
$taskAvdManager = Join-Path $env:ANDROID_HOME 'cmdline-tools\22.0\bin\avdmanager.bat'
foreach ($taskApi in @('29','36')) {
    $taskName = "plancheckin_api$taskApi"
    $taskTarget = Join-Path $env:ANDROID_AVD_HOME "$taskName.avd"
    if (Test-Path -LiteralPath $taskTarget) {
        Write-Output "已有AVD，保留原配置：$taskName"
        continue
    }
    'no' | & $taskAvdManager create avd -n $taskName -k "system-images;android-$taskApi;default;x86_64" -d pixel_5 -p $taskTarget
    if ($LASTEXITCODE -ne 0) { throw "AVD创建失败：$taskName" }
    $taskConfig = Join-Path $taskTarget 'config.ini'
    $taskValues = [ordered]@{
        'hw.cpu.ncore'='4'; 'hw.ramSize'='4096'; 'disk.dataPartition.size'='2G'
        'hw.lcd.width'='1080'; 'hw.lcd.height'='2340'; 'hw.lcd.density'='440'
        'hw.gpu.enabled'='yes'; 'hw.gpu.mode'='host'; 'hw.keyboard'='yes'
        'fastboot.forceColdBoot'='yes'; 'fastboot.forceFastBoot'='no'
        'showDeviceFrame'='no'
    }
    $taskLines = @(Get-Content -LiteralPath $taskConfig | Where-Object {
        $taskKey = ($_ -split '=',2)[0].Trim()
        -not $taskValues.Contains($taskKey)
    })
    foreach ($taskEntry in $taskValues.GetEnumerator()) { $taskLines += "$($taskEntry.Key)=$($taskEntry.Value)" }
    [System.IO.File]::WriteAllLines($taskConfig,$taskLines,[System.Text.UTF8Encoding]::new($false))
    Write-Output "AVD已创建：$taskName，4核/4GiB/393dp，数据分区2GiB"
}
