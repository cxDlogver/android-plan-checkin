<#
.SYNOPSIS
复用固定签名配置，自动递增版本并构建正式 APK。
.EXAMPLE
.\scripts\android-ai\Build-ReleaseApk.ps1
#>
[CmdletBinding()]
param(
    [string]$VersionCode,
    [string]$VersionName,
    [string]$ToolRoot = 'D:\xiang\CX_application\1_Configuration_Files\Android-AI'
)

$ErrorActionPreference = 'Stop'
$releaseProjectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
$releaseConfigPath = Join-Path $releaseProjectRoot 'config\release.json'

function Invoke-ReleaseCommand {
    param([string]$FilePath, [string[]]$CommandArguments, [string]$Description)
    Write-Host "`n==> $Description"
    # PS5.1 的原生 stderr 可能只是警告，以进程退出码判断成功与否。
    $releasePreviousErrorAction = $ErrorActionPreference
    $releaseExitCode = $null
    try {
        $ErrorActionPreference = 'Continue'
        & $FilePath @CommandArguments
        $releaseExitCode = $LASTEXITCODE
    } finally { $ErrorActionPreference = $releasePreviousErrorAction }
    if ($null -eq $releaseExitCode -or $releaseExitCode -ne 0) {
        throw "$Description 失败（退出码：$releaseExitCode），已停止打包，版本号未递增。"
    }
}

function Unprotect-ReleasePassword {
    param([string]$EncryptedValue)
    $releaseBytes = [Security.Cryptography.ProtectedData]::Unprotect(
        [Convert]::FromBase64String($EncryptedValue), $null,
        [Security.Cryptography.DataProtectionScope]::CurrentUser
    )
    try { return [Text.Encoding]::UTF8.GetString($releaseBytes) }
    finally { [Array]::Clear($releaseBytes, 0, $releaseBytes.Length) }
}

$releaseEnvironmentNames = @(
    'APP_VARIANT', 'PLANCHECKIN_VERSION_CODE', 'PLANCHECKIN_VERSION_NAME',
    'PLANCHECKIN_KEYSTORE', 'PLANCHECKIN_KEY_ALIAS',
    'PLANCHECKIN_STORE_PASSWORD', 'PLANCHECKIN_KEY_PASSWORD', 'CI',
    'GRADLE_USER_HOME', 'JAVA_TOOL_OPTIONS', 'npm_config_proxy', 'npm_config_https_proxy', 'NODE_ENV'
)
$releaseOriginalEnvironment = @{}
foreach ($releaseName in $releaseEnvironmentNames) {
    $releaseOriginalEnvironment[$releaseName] = [Environment]::GetEnvironmentVariable($releaseName, 'Process')
}
$releaseLock = $null
$releaseLocationPushed = $false
$releasePendingApk = $null
$releasePendingConfig = $releaseConfigPath + '.pending'

try {
    $releaseArtifacts = Join-Path $releaseProjectRoot '.artifacts'
    New-Item -ItemType Directory -Path $releaseArtifacts -Force | Out-Null
    try {
        $releaseLock = [IO.File]::Open((Join-Path $releaseArtifacts 'release-build.lock'), [IO.FileMode]::OpenOrCreate, [IO.FileAccess]::ReadWrite, [IO.FileShare]::None)
    } catch { throw '已有打包任务占用发布锁，请等它结束后再执行。' }
    $releaseConfig = Get-Content -LiteralPath $releaseConfigPath -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($releaseConfig.schemaVersion -ne 1) { throw '不支持的 config/release.json 格式。' }
    $releaseLastBuild = $releaseConfig.lastSuccessfulBuild
    $releaseLastCode = 0
    if ($null -ne $releaseLastBuild) {
        $releaseLastCode = [long]$releaseLastBuild.versionCode
        if ($releaseLastCode -lt 1 -or $releaseLastCode -gt 2100000000) { throw '已保存的发布版本号无效。' }
    }
    if ([string]::IsNullOrWhiteSpace($VersionCode)) { $VersionCode = ([long]$releaseLastCode + 1).ToString() }
    $releaseNumericCode = [long]0
    if (-not [long]::TryParse($VersionCode, [ref]$releaseNumericCode) -or $releaseNumericCode -le $releaseLastCode -or $releaseNumericCode -gt 2100000000) {
        throw "VersionCode 必须大于上次成功版本 $releaseLastCode，且不超过 2100000000。"
    }
    if ([string]::IsNullOrWhiteSpace($VersionName)) {
        $VersionName = '1.0.0'
        if ($null -ne $releaseLastBuild) {
            if ($releaseLastBuild.versionName -notmatch '^(\d+)\.(\d+)\.(\d+)(?:-[A-Za-z0-9.-]+)?$') { throw '已保存的展示版本格式错误。' }
            $VersionName = '{0}.{1}.{2}' -f $Matches[1], $Matches[2], ([long]$Matches[3] + 1)
        }
    }
    if ($VersionName -notmatch '^\d+\.\d+\.\d+(?:-[A-Za-z0-9.-]+)?$') { throw 'VersionName 请使用 1.0.0 或 1.0.1-beta.1 等格式。' }

    $releaseSigningPath = Join-Path $releaseConfig.signingDirectory 'credentials.dpapi.json'
    if (-not (Test-Path -LiteralPath $releaseSigningPath -PathType Leaf)) { throw "找不到固定签名配置：$releaseSigningPath" }
    $releaseSigning = Get-Content -LiteralPath $releaseSigningPath -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($releaseSigning.schemaVersion -ne 1 -or [string]::IsNullOrWhiteSpace($releaseSigning.alias) -or [string]::IsNullOrWhiteSpace($releaseSigning.storePassword) -or [string]::IsNullOrWhiteSpace($releaseSigning.keyPassword)) { throw '固定签名配置不完整。' }
    if (-not [IO.Path]::IsPathRooted($releaseSigning.keyPath) -or -not (Test-Path -LiteralPath $releaseSigning.keyPath -PathType Leaf)) { throw '固定签名配置中的 keystore 文件不存在。' }
    $releaseKeystore = (Resolve-Path -LiteralPath $releaseSigning.keyPath).ProviderPath
    if ($releaseKeystore.StartsWith($releaseProjectRoot + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) { throw '签名密钥必须位于项目目录之外。' }
    $releaseOutputApk = [IO.Path]::GetFullPath((Join-Path $releaseProjectRoot $releaseConfig.apkPath))
    if (-not $releaseOutputApk.StartsWith($releaseProjectRoot + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase) -or [IO.Path]::GetExtension($releaseOutputApk) -ne '.apk') { throw 'APK 输出路径必须位于本项目内且以 .apk 结尾。' }
    if ($releaseConfig.signerSha256 -notmatch '^[0-9a-fA-F]{64}$') { throw '发布配置中的签名证书摘要无效。' }

    Push-Location -LiteralPath $releaseProjectRoot
    $releaseLocationPushed = $true
    . (Join-Path $PSScriptRoot 'Use-AndroidAI.ps1') -ToolRoot $ToolRoot
    $env:GRADLE_USER_HOME = $releaseConfig.gradleUserHome
    if ([string]::IsNullOrWhiteSpace($env:GRADLE_USER_HOME) -or -not [IO.Path]::IsPathRooted($env:GRADLE_USER_HOME)) { throw 'Gradle 缓存必须配置为固定绝对路径。' }
    $releaseProxyValue = $env:npm_config_https_proxy
    if ([string]::IsNullOrWhiteSpace($releaseProxyValue)) { $releaseProxyValue = $env:HTTPS_PROXY }
    if ([string]::IsNullOrWhiteSpace($releaseProxyValue)) {
        $releaseInternetSettings = Get-ItemProperty -LiteralPath 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' -ErrorAction SilentlyContinue
        if ($releaseInternetSettings.ProxyEnable -eq 1) {
            $releaseProxyServer = [string]$releaseInternetSettings.ProxyServer
            if ($releaseProxyServer -match '(?:^|;)https=([^;]+)') { $releaseProxyServer = $Matches[1] }
            elseif ($releaseProxyServer -match '(?:^|;)http=([^;]+)') { $releaseProxyServer = $Matches[1] }
            if ($releaseProxyServer -match '^[\w.-]+:\d+$') { $releaseProxyValue = 'http://' + $releaseProxyServer }
        }
    }
    if (-not [string]::IsNullOrWhiteSpace($releaseProxyValue)) {
        $releaseProxyUri = [Uri]$releaseProxyValue
        if (-not $releaseProxyUri.IsAbsoluteUri -or $releaseProxyUri.Scheme -notin @('http', 'https') -or $releaseProxyUri.UserInfo) { throw '构建代理必须使用不含账号密码的 HTTP/HTTPS 代理地址。' }
        $env:npm_config_proxy = $releaseProxyValue
        $env:npm_config_https_proxy = $releaseProxyValue
        $releaseProxyJvmOptions = '-Dhttps.proxyHost={0} -Dhttps.proxyPort={1} -Dhttp.proxyHost={0} -Dhttp.proxyPort={1} -Dhttp.nonProxyHosts=localhost|127.*' -f $releaseProxyUri.Host, $releaseProxyUri.Port
        $env:JAVA_TOOL_OPTIONS = ($env:JAVA_TOOL_OPTIONS + ' ' + $releaseProxyJvmOptions).Trim()
        Write-Host ('复用网络代理：{0}:{1}' -f $releaseProxyUri.Host, $releaseProxyUri.Port)
    }
    $releasePnpm = (Get-Command 'pnpm.cmd' -ErrorAction Stop).Source
    $releaseBuildTools = Join-Path $env:ANDROID_HOME 'build-tools\36.0.0'
    $releaseAapt = Join-Path $releaseBuildTools 'aapt2.exe'
    $releaseSigner = Join-Path $releaseBuildTools 'apksigner.bat'
    foreach ($releaseTool in @($releaseAapt, $releaseSigner)) {
        if (-not (Test-Path -LiteralPath $releaseTool -PathType Leaf)) { throw "缺少构建工具：$releaseTool" }
    }
    Add-Type -AssemblyName System.Security
    try {
        $env:PLANCHECKIN_STORE_PASSWORD = Unprotect-ReleasePassword $releaseSigning.storePassword
        $env:PLANCHECKIN_KEY_PASSWORD = Unprotect-ReleasePassword $releaseSigning.keyPassword
    } catch { throw '无法解密固定签名配置，请使用创建该配置的 Windows 用户运行。' }
    $env:PLANCHECKIN_KEYSTORE = $releaseKeystore
    $env:PLANCHECKIN_KEY_ALIAS = $releaseSigning.alias
    $env:APP_VARIANT = 'production'
    $env:PLANCHECKIN_VERSION_CODE = $releaseNumericCode.ToString()
    $env:PLANCHECKIN_VERSION_NAME = $VersionName
    $env:CI = '1'

    Write-Host "本次版本：$VersionName（versionCode $releaseNumericCode）"
    Write-Host "固定签名：$releaseKeystore"
    Invoke-ReleaseCommand -FilePath $releasePnpm -CommandArguments @('install', '--frozen-lockfile') -Description '安装项目依赖'
    Invoke-ReleaseCommand -FilePath $releasePnpm -CommandArguments @('typecheck') -Description '类型检查'
    Invoke-ReleaseCommand -FilePath $releasePnpm -CommandArguments @('exec', 'expo', 'prebuild', '--platform', 'android', '--no-install', '--no-clean') -Description '同步正式版原生配置'
    Push-Location -LiteralPath (Join-Path $releaseProjectRoot 'android')
    try {
        $env:NODE_ENV = 'production'
        $releaseGradle = Join-Path (Get-Location).Path 'gradlew.bat'
        if (-not (Test-Path -LiteralPath $releaseGradle -PathType Leaf)) { throw '未找到 Gradle wrapper。' }
        Invoke-ReleaseCommand -FilePath $releaseGradle -CommandArguments @(':app:assembleRelease', '--no-daemon', '--no-parallel', '--max-workers=1', '--console=plain') -Description '构建正式 APK'
    } finally { Pop-Location }

    $releaseApk = Join-Path $releaseProjectRoot 'android\app\build\outputs\apk\release\app-release.apk'
    if (-not (Test-Path -LiteralPath $releaseApk -PathType Leaf)) { throw '构建结束，但未找到 app-release.apk。' }
    $releaseBadging = (Invoke-ReleaseCommand -FilePath $releaseAapt -CommandArguments @('dump', 'badging', $releaseApk) -Description '核对 APK 包名与版本') -join "`n"
    $releasePackage = [regex]::Match($releaseBadging, "(?m)^package: name='([^']+)' versionCode='(\d+)' versionName='([^']+)'")
    if (-not $releasePackage.Success -or $releasePackage.Groups[1].Value -ne 'com.xiang.plancheckin' -or $releasePackage.Groups[2].Value -ne $releaseNumericCode.ToString() -or $releasePackage.Groups[3].Value -cne $VersionName) { throw 'APK 包名或版本不一致，未更新发布记录。' }
    $releaseCertificate = (Invoke-ReleaseCommand -FilePath $releaseSigner -CommandArguments @('verify', '--print-certs', $releaseApk) -Description '验证 APK 固定签名') -join "`n"
    $releaseSignerMatch = [regex]::Match($releaseCertificate, 'Signer #1 certificate SHA-256 digest: ([0-9a-fA-F]{64})')
    if (-not $releaseSignerMatch.Success -or $releaseSignerMatch.Groups[1].Value -ne $releaseConfig.signerSha256) { throw 'APK 签名与固定发布签名不一致，未更新发布记录。' }

    New-Item -ItemType Directory -Path (Split-Path -Parent $releaseOutputApk) -Force | Out-Null
    $releasePendingApk = $releaseOutputApk + '.pending'
    Copy-Item -LiteralPath $releaseApk -Destination $releasePendingApk -Force
    $releaseHash = (Get-FileHash -LiteralPath $releasePendingApk -Algorithm SHA256).Hash
    if (Test-Path -LiteralPath $releaseOutputApk) { [IO.File]::Replace($releasePendingApk, $releaseOutputApk, [System.Management.Automation.Language.NullString]::Value) }
    else { [IO.File]::Move($releasePendingApk, $releaseOutputApk) }
    $releaseConfig.lastSuccessfulBuild = [ordered]@{
        versionCode = $releaseNumericCode
        versionName = $VersionName
        apkSha256 = $releaseHash
        builtAt = (Get-Date).ToUniversalTime().ToString('o')
    }
    [IO.File]::WriteAllText($releasePendingConfig, ($releaseConfig | ConvertTo-Json -Depth 6) + [Environment]::NewLine, [Text.UTF8Encoding]::new($false))
    [IO.File]::Replace($releasePendingConfig, $releaseConfigPath, [System.Management.Automation.Language.NullString]::Value)
    Write-Host "`n打包成功：$VersionName（versionCode $releaseNumericCode）"
    Write-Host "APK：$releaseOutputApk"
    Write-Host "SHA256：$releaseHash"
    Write-Output $releaseOutputApk
} finally {
    foreach ($releaseName in $releaseEnvironmentNames) {
        if ($null -eq $releaseOriginalEnvironment[$releaseName]) {
            [Environment]::SetEnvironmentVariable($releaseName, [System.Management.Automation.Language.NullString]::Value, 'Process')
        } else {
            [Environment]::SetEnvironmentVariable($releaseName, $releaseOriginalEnvironment[$releaseName], 'Process')
        }
    }
    if ($releaseLocationPushed) { Pop-Location }
    if ($null -ne $releaseLock) {
        try {
            foreach ($releaseTemporaryPath in @($releasePendingApk, $releasePendingConfig)) {
                if ($releaseTemporaryPath -and (Test-Path -LiteralPath $releaseTemporaryPath)) { Remove-Item -LiteralPath $releaseTemporaryPath -Force }
            }
        } finally { $releaseLock.Dispose() }
    }
}
