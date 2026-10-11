param(
    [ValidateSet('CreateKey','ImportKey','Prebuild','Build')][string]$Action = 'Build',
    [string]$SigningDirectory = (Join-Path $env:USERPROFILE '.android-plan-checkin-signing'),
    [string]$ExistingKey,
    [string]$Alias = 'plancheckin-release',
    [ValidateRange(1,2100000000)][int]$VersionCode = 2,
    [string]$VersionName = '1.0.0',
    [string]$ReuseNativeFrom,
    [string]$ToolRoot = 'D:\xiang\CX_application\1_Configuration_Files\Android-AI',
    [string]$JavaRoot = 'D:\xiang\CX_application\1_Configuration_Files\JAVA\jdk-17.0.1'
)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Security
$taskWorkspace = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$taskSigningRoot = [IO.Path]::GetFullPath($SigningDirectory)
if ($taskSigningRoot.StartsWith($taskWorkspace + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase) -or $taskSigningRoot -eq $taskWorkspace) { throw 'Signing material must stay outside this repository.' }
$taskCredentials = Join-Path $taskSigningRoot 'credentials.dpapi.json'
$taskNode = Join-Path $ToolRoot 'node-v24.21.0-win-x64\node.exe'
function Protect-Password([string]$Value) {
    [Convert]::ToBase64String([Security.Cryptography.ProtectedData]::Protect([Text.Encoding]::UTF8.GetBytes($Value), $null, [Security.Cryptography.DataProtectionScope]::CurrentUser))
}
function Unprotect-Password([string]$Value) {
    [Text.Encoding]::UTF8.GetString([Security.Cryptography.ProtectedData]::Unprotect([Convert]::FromBase64String($Value), $null, [Security.Cryptography.DataProtectionScope]::CurrentUser))
}
function Read-Password([string]$Prompt) {
    $taskSecure = Read-Host $Prompt -AsSecureString
    $taskPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($taskSecure)
    try { [Runtime.InteropServices.Marshal]::PtrToStringBSTR($taskPointer) } finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($taskPointer) }
}
if ($Action -in @('CreateKey','ImportKey')) {
    if (Test-Path -LiteralPath $taskCredentials) { throw 'A signing configuration already exists. It will not be overwritten.' }
    New-Item -ItemType Directory -Path $taskSigningRoot -Force | Out-Null
    $taskIdentity = [Security.Principal.WindowsIdentity]::GetCurrent().User
    $taskAcl = New-Object Security.AccessControl.DirectorySecurity
    $taskAcl.SetOwner($taskIdentity)
    $taskAcl.SetAccessRuleProtection($true, $false)
    $taskRule = New-Object Security.AccessControl.FileSystemAccessRule($taskIdentity, 'FullControl', 'ContainerInherit,ObjectInherit', 'None', 'Allow')
    $taskAcl.AddAccessRule($taskRule)
    Set-Acl -LiteralPath $taskSigningRoot -AclObject $taskAcl
    if ($Action -eq 'CreateKey') {
        $taskKey = Join-Path $taskSigningRoot 'release.p12'
        if (Test-Path -LiteralPath $taskKey) { throw 'The key file already exists. It will not be replaced.' }
        $taskRandom = New-Object byte[] 48
        $taskRng = [Security.Cryptography.RandomNumberGenerator]::Create()
        try { $taskRng.GetBytes($taskRandom) } finally { $taskRng.Dispose() }
        $taskStorePassword = [Convert]::ToBase64String($taskRandom)
        $taskKeyPassword = $taskStorePassword
        $env:PLANCHECKIN_STORE_PASSWORD = $taskStorePassword
        $env:PLANCHECKIN_KEY_PASSWORD = $taskKeyPassword
        try {
            & (Join-Path $JavaRoot 'bin\keytool.exe') -genkeypair -keystore $taskKey -storetype PKCS12 -alias $Alias -keyalg RSA -keysize 4096 -validity 10000 -dname 'CN=PlanCheckin,OU=Android,O=PlanCheckin' -storepass:env PLANCHECKIN_STORE_PASSWORD -keypass:env PLANCHECKIN_KEY_PASSWORD
            if ($LASTEXITCODE -ne 0) { throw 'Key generation failed.' }
        } finally { Remove-Item Env:PLANCHECKIN_STORE_PASSWORD, Env:PLANCHECKIN_KEY_PASSWORD -ErrorAction SilentlyContinue }
    } else {
        if (-not $ExistingKey -or -not (Test-Path -LiteralPath $ExistingKey -PathType Leaf)) { throw 'Provide the existing signing key path.' }
        $taskKey = [IO.Path]::GetFullPath($ExistingKey)
        if ($taskKey.StartsWith($taskWorkspace + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) { throw 'The existing key must be outside this repository.' }
        $taskStorePassword = Read-Password 'Keystore password (hidden)'
        $taskKeyPassword = Read-Password 'Key password (hidden)'
    }
    [ordered]@{ schemaVersion=1; keyPath=$taskKey; alias=$Alias; storePassword=(Protect-Password $taskStorePassword); keyPassword=(Protect-Password $taskKeyPassword); createdAt=(Get-Date).ToUniversalTime().ToString('o') } | ConvertTo-Json | Set-Content -LiteralPath $taskCredentials -Encoding UTF8
    Write-Output ('Signing material saved outside Git: ' + $taskSigningRoot)
    Write-Output 'Back up this directory securely. DPAPI passwords are tied to this Windows account; use a separate encrypted password backup before moving machines.'
    exit 0
}
if (-not (Test-Path -LiteralPath $taskCredentials -PathType Leaf)) { throw 'Prepare a signing key first with CreateKey or ImportKey.' }
$taskConfig = Get-Content -LiteralPath $taskCredentials -Raw | ConvertFrom-Json
$env:PLANCHECKIN_KEYSTORE = $taskConfig.keyPath
$env:PLANCHECKIN_KEY_ALIAS = $taskConfig.alias
$env:PLANCHECKIN_STORE_PASSWORD = Unprotect-Password $taskConfig.storePassword
$env:PLANCHECKIN_KEY_PASSWORD = Unprotect-Password $taskConfig.keyPassword
$env:APP_VARIANT = 'production'
$env:PLANCHECKIN_VERSION_CODE = [string]$VersionCode
$env:PLANCHECKIN_VERSION_NAME = $VersionName
if ($ReuseNativeFrom) { $env:PLANCHECKIN_REUSE_NATIVE_FROM = $ReuseNativeFrom }
try {
    Push-Location $taskWorkspace
    if ($Action -eq 'Prebuild') { & $taskNode (Join-Path $PSScriptRoot 'release-prebuild.cjs') }
    else { & $taskNode (Join-Path $PSScriptRoot 'native-build.cjs') release }
    if ($LASTEXITCODE -ne 0) { throw 'Release operation failed; inspect the recorded evidence.' }
} finally {
    Pop-Location
    Remove-Item Env:PLANCHECKIN_KEYSTORE,Env:PLANCHECKIN_KEY_ALIAS,Env:PLANCHECKIN_STORE_PASSWORD,Env:PLANCHECKIN_KEY_PASSWORD,Env:APP_VARIANT,Env:PLANCHECKIN_VERSION_CODE,Env:PLANCHECKIN_VERSION_NAME,Env:PLANCHECKIN_REUSE_NATIVE_FROM -ErrorAction SilentlyContinue
}
