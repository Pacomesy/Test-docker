# Construit l'image, exporte docker save, génère docker-compose.offline.yml + manifeste pour la cible hors ligne.
# Usage (depuis n'importe quel répertoire) :
#   .\scripts\pack-offline.ps1 -OutDir C:\dist\horloge-offline
#   .\scripts\pack-offline.ps1 -ImageName horloge-meteo -Tag 1.2.0 -OutDir .\offline-pack -Zip
param(
    [string] $ImageName = "horloge-meteo",
    [string] $Tag = "1.2.0",
    [Parameter(Mandatory = $true)]
    [string] $OutDir,
    [switch] $Zip
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$Template = Join-Path $PSScriptRoot "docker-compose.offline.template.yml"
$OfflineImage = "${ImageName}:${Tag}"
$SafeTag = ($Tag -creplace '[^\w\.\-]', '_')
$TarName = "${ImageName}_${SafeTag}.tar"
$AbsOut = $OutDir
if (-not [System.IO.Path]::IsPathRooted($AbsOut)) {
    $AbsOut = Join-Path (Get-Location).Path $OutDir
}
$AbsOut = [System.IO.Path]::GetFullPath($AbsOut)
$Utf8NoBom = New-Object System.Text.UTF8Encoding $false

if (-not (Test-Path -LiteralPath $Template)) {
    Write-Error "Template introuvable : $Template"
}

New-Item -ItemType Directory -Path $AbsOut -Force | Out-Null

Write-Host "Build $OfflineImage (APP_VERSION=$Tag) ..."
Push-Location $RepoRoot
try {
    docker build --build-arg "APP_VERSION=$Tag" -t $OfflineImage .
}
finally {
    Pop-Location
}

$TarPath = Join-Path $AbsOut $TarName
Write-Host "Export docker save -> $TarPath"
docker save -o $TarPath $OfflineImage

$ManifestPath = Join-Path $AbsOut "pack-manifest.env"
$manifestLines = @(
    "OFFLINE_IMAGE=$OfflineImage",
    "OFFLINE_TAR=$TarName"
)
[System.IO.File]::WriteAllLines($ManifestPath, $manifestLines, $Utf8NoBom)

$ComposeOut = Join-Path $AbsOut "docker-compose.offline.yml"
$composeBody = (Get-Content -LiteralPath $Template -Raw) -replace '__OFFLINE_IMAGE__', $OfflineImage
[System.IO.File]::WriteAllText($ComposeOut, $composeBody, $Utf8NoBom)

$DocSrc = Join-Path $RepoRoot "OFFLINE_DEPLOY.md"
if (Test-Path -LiteralPath $DocSrc) {
    Copy-Item -LiteralPath $DocSrc -Destination (Join-Path $AbsOut "OFFLINE_DEPLOY.md") -Force
}

Copy-Item -LiteralPath (Join-Path $PSScriptRoot "load-and-run-offline.sh") -Destination $AbsOut -Force
Copy-Item -LiteralPath (Join-Path $PSScriptRoot "load-and-run-offline.ps1") -Destination $AbsOut -Force

Write-Host "Pack prêt : $AbsOut"
if ($Zip) {
    $ZipPath = "$AbsOut.zip"
    if (Test-Path -LiteralPath $ZipPath) {
        Remove-Item -LiteralPath $ZipPath -Force
    }
    Compress-Archive -Path (Join-Path $AbsOut "*") -DestinationPath $ZipPath
    Write-Host "Archive ZIP : $ZipPath"
}
