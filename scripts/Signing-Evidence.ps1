param([string]$SigningDirectory = (Join-Path $env:USERPROFILE '.android-plan-checkin-signing'), [string]$JavaRoot = 'D:\xiang\CX_application\1_Configuration_Files\JAVA\jdk-17.0.1')
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Security
$taskConfig = Get-Content -LiteralPath (Join-Path $SigningDirectory 'credentials.dpapi.json') -Raw | ConvertFrom-Json
$taskCertificatePath = Join-Path $PSScriptRoot '..\resource\progress\release-certificate.der'
$env:PLANCHECKIN_STORE_PASSWORD = [Text.Encoding]::UTF8.GetString([Security.Cryptography.ProtectedData]::Unprotect([Convert]::FromBase64String($taskConfig.storePassword), $null, [Security.Cryptography.DataProtectionScope]::CurrentUser))
try {
    & (Join-Path $JavaRoot 'bin\keytool.exe') -exportcert -keystore $taskConfig.keyPath -storepass:env PLANCHECKIN_STORE_PASSWORD -alias $taskConfig.alias -file $taskCertificatePath
    if ($LASTEXITCODE -ne 0) { throw 'Cannot export public release certificate.' }
} finally { Remove-Item Env:PLANCHECKIN_STORE_PASSWORD -ErrorAction SilentlyContinue }
$taskCert = New-Object Security.Cryptography.X509Certificates.X509Certificate2($taskCertificatePath)
$taskAcl = Get-Acl -LiteralPath $SigningDirectory
$taskResult = [ordered]@{
    status='PASS'; recordedAt=(Get-Date).ToUniversalTime().ToString('o'); keyOutsideRepository=$true
    signingDirectory=$SigningDirectory; certificateFile='resource/progress/release-certificate.der'
    certificateSha256=(Get-FileHash -LiteralPath $taskCertificatePath -Algorithm SHA256).Hash.ToLowerInvariant()
    subject=$taskCert.Subject; validFrom=$taskCert.NotBefore.ToUniversalTime().ToString('o'); validTo=$taskCert.NotAfter.ToUniversalTime().ToString('o')
    privateKeyDelivered=$false; credentialsProtection='Windows DPAPI CurrentUser'
    directoryOwner=$taskAcl.Owner; inheritedAccessBlocked=$taskAcl.AreAccessRulesProtected
    access=@($taskAcl.Access | Select-Object IdentityReference,FileSystemRights,AccessControlType,IsInherited)
}
if (-not $taskAcl.AreAccessRulesProtected -or $taskAcl.Access.Count -ne 1 -or $taskAcl.Access[0].IdentityReference.Translate([Security.Principal.SecurityIdentifier]).Value -ne [Security.Principal.WindowsIdentity]::GetCurrent().User.Value) { $taskResult.status='FAIL' }
$taskResult | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $PSScriptRoot '..\resource\progress\release-signing.json') -Encoding UTF8
Write-Output ('Signing security ' + $taskResult.status + '; public certificate SHA-256: ' + $taskResult.certificateSha256)
if ($taskResult.status -ne 'PASS') { exit 1 }
