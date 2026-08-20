[CmdletBinding()]
param(
    [string]$OutputDirectory = (Join-Path $PSScriptRoot "..\dist"),
    [string]$PfxPath,
    [string]$PfxPassword,
    [string]$TimestampUrl,
    [switch]$RequireSignature,
    [switch]$KeepStage
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Find-SignTool {
    $configured = $env:SIGNTOOL_PATH
    if ($configured -and (Test-Path -LiteralPath $configured -PathType Leaf)) {
        return $configured
    }
    $sdkRoot = "C:\Program Files (x86)\Windows Kits\10\bin"
    if (Test-Path -LiteralPath $sdkRoot -PathType Container) {
        $tool = Get-ChildItem -LiteralPath $sdkRoot -Filter "signtool.exe" -Recurse -ErrorAction SilentlyContinue |
            Where-Object { $_.FullName -match "\\x64\\signtool\.exe$" } |
            Sort-Object FullName -Descending |
            Select-Object -First 1
        if ($tool) { return $tool.FullName }
    }
    throw "SignTool was not found. Install the Windows SDK or set SIGNTOOL_PATH."
}

function Sign-Installer {
    param([Parameter(Mandatory = $true)][string]$Installer)
    if ([string]::IsNullOrWhiteSpace($PfxPath)) {
        if ($RequireSignature) { throw "A signed installer is required, but -PfxPath was not provided." }
        Write-Warning "Created an unsigned local EXE. It must not be uploaded as a signed release asset."
        return
    }
    if (-not (Test-Path -LiteralPath $PfxPath -PathType Leaf)) { throw "Signing certificate does not exist: $PfxPath" }
    if ([string]::IsNullOrWhiteSpace($TimestampUrl)) { throw "Signing requires -TimestampUrl for an RFC 3161 timestamp." }
    $signTool = Find-SignTool
    $arguments = @("sign", "/fd", "SHA256", "/f", $PfxPath)
    if (-not [string]::IsNullOrEmpty($PfxPassword)) { $arguments += @("/p", $PfxPassword) }
    $arguments += @("/tr", $TimestampUrl, "/td", "SHA256", "/d", "ExcaliFlow Studio", $Installer)
    & $signTool @arguments
    if ($LASTEXITCODE -ne 0) { throw "SignTool failed to sign the Windows installer." }
    & $signTool verify "/pa" "/all" $Installer
    if ($LASTEXITCODE -ne 0) { throw "SignTool verification failed for the Windows installer." }
}

$repositoryRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$iexpress = Join-Path $env:WINDIR "System32\iexpress.exe"
if (-not (Test-Path -LiteralPath $iexpress -PathType Leaf)) { throw "IExpress is not available on this Windows computer." }
$output = [System.IO.Path]::GetFullPath($OutputDirectory)
$zipOutput = Join-Path $output "ExcaliFlow-Setup-windows.zip"
$exeOutput = Join-Path $output "ExcaliFlow-Setup-windows.exe"
if (Test-Path -LiteralPath $zipOutput) { throw "Refusing to overwrite existing archive: $zipOutput" }
if (Test-Path -LiteralPath $exeOutput) { throw "Refusing to overwrite existing installer: $exeOutput" }

$stage = Join-Path ([System.IO.Path]::GetTempPath()) ("ExcaliFlow-IExpress-" + [guid]::NewGuid().ToString("N"))
try {
    New-Item -ItemType Directory -Path $stage | Out-Null
    & (Join-Path $PSScriptRoot "build-windows-release.ps1") -OutputDirectory $stage
    New-Item -ItemType Directory -Path $output -Force | Out-Null
    Copy-Item -LiteralPath (Join-Path $stage "ExcaliFlow-Setup-windows.zip") -Destination $zipOutput

    $package = Join-Path $stage "iexpress-files"
    New-Item -ItemType Directory -Path $package | Out-Null
    Copy-Item -LiteralPath $zipOutput -Destination (Join-Path $package "ExcaliFlow-Setup-windows.zip")
    @'
@echo off
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0start-installer.ps1"
exit /b %ERRORLEVEL%
'@ | Set-Content -LiteralPath (Join-Path $package "start-installer.cmd") -Encoding ascii
    @'
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$destination = Join-Path ([System.IO.Path]::GetTempPath()) ("ExcaliFlow-Setup-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $destination | Out-Null
Expand-Archive -LiteralPath (Join-Path $PSScriptRoot "ExcaliFlow-Setup-windows.zip") -DestinationPath $destination
& (Join-Path $destination "ExcaliFlow-Setup\ExcaliFlow-Setup.cmd")
exit $LASTEXITCODE
'@ | Set-Content -LiteralPath (Join-Path $package "start-installer.ps1") -Encoding utf8
    $sed = @"
[Version]
Class=IEXPRESS
SEDVersion=3

[Options]
PackagePurpose=InstallApp
ShowInstallProgramWindow=0
HideExtractAnimation=1
UseLongFileName=1
InsideCompressed=0
CAB_FixedSize=0
CAB_ResvCodeSigning=0
RebootMode=N
InstallPrompt=%InstallPrompt%
DisplayLicense=%DisplayLicense%
FinishMessage=%FinishMessage%
TargetName=%TargetName%
FriendlyName=%FriendlyName%
AppLaunched=%AppLaunched%
PostInstallCmd=%PostInstallCmd%
AdminQuietInstCmd=%AdminQuietInstCmd%
UserQuietInstCmd=%UserQuietInstCmd%
SourceFiles=SourceFiles

[Strings]
InstallPrompt=
DisplayLicense=
FinishMessage=
TargetName=$exeOutput
FriendlyName=ExcaliFlow Studio Setup
AppLaunched=start-installer.cmd
PostInstallCmd=<None>
AdminQuietInstCmd=
UserQuietInstCmd=
FILE0="ExcaliFlow-Setup-windows.zip"
FILE1="start-installer.cmd"
FILE2="start-installer.ps1"

[SourceFiles]
SourceFiles0=$package\

[SourceFiles0]
%FILE0%=
%FILE1%=
%FILE2%=
"@
    $sedPath = Join-Path $stage "ExcaliFlow-Setup.sed"
    Set-Content -LiteralPath $sedPath -Value $sed -Encoding ascii
    $iexpressProcess = Start-Process -FilePath $iexpress -ArgumentList @("/N", $sedPath) -Wait -PassThru
    if ($iexpressProcess.ExitCode -ne 0 -or -not (Test-Path -LiteralPath $exeOutput -PathType Leaf)) { throw "IExpress failed to create the Windows installer (exit $($iexpressProcess.ExitCode); SED $sedPath)." }
    Sign-Installer -Installer $exeOutput
    Write-Output "Windows EXE installer created: $exeOutput"
} finally {
    if ($KeepStage) {
        Write-Warning "Kept IExpress staging directory for diagnosis: $stage"
    } elseif (Test-Path -LiteralPath $stage) {
        Remove-Item -LiteralPath $stage -Recurse -Force
    }
}
