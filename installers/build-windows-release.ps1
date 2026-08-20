[CmdletBinding()]
param([string]$OutputDirectory = (Join-Path $PSScriptRoot "..\dist"))

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repositoryRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$bundleRoot = Join-Path $OutputDirectory "ExcaliFlow-Setup"
$archive = Join-Path $OutputDirectory "ExcaliFlow-Setup-windows.zip"
$content = @("VERSION", "SKILL.md", "THIRD_PARTY_LICENSES.md", "agents", "assets", "scripts", "src", "tests")

if (Test-Path -LiteralPath $bundleRoot) {
    throw "Refusing to overwrite existing bundle directory: $bundleRoot. Choose an empty -OutputDirectory or remove that exact generated directory yourself."
}
if (Test-Path -LiteralPath $archive) {
    throw "Refusing to overwrite existing archive: $archive. Choose an empty -OutputDirectory or remove that exact generated archive yourself."
}
New-Item -ItemType Directory -Path $bundleRoot -Force | Out-Null
foreach ($name in $content) {
    Copy-Item -LiteralPath (Join-Path $repositoryRoot $name) -Destination (Join-Path $bundleRoot $name) -Recurse -Force
}
foreach ($name in @("ExcaliFlow-Setup.cmd", "ExcaliFlow-Setup.ps1", "host-targets.json")) {
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot $name) -Destination (Join-Path $bundleRoot $name) -Force
}
Compress-Archive -LiteralPath $bundleRoot -DestinationPath $archive -Force
Write-Output "Windows release bundle created: $archive"
