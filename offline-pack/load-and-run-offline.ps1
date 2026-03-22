# Déploiement hors ligne : charger l'image puis démarrer (dossier du pack = répertoire du script).
# Usage : .\load-and-run-offline.ps1   ou   .\load-and-run-offline.ps1 https
param(
    [string] $Mode = "http"
)

$ErrorActionPreference = "Stop"
$Dir = $PSScriptRoot
$Manifest = Join-Path $Dir "pack-manifest.env"
if (-not (Test-Path -LiteralPath $Manifest)) {
    Write-Error "Fichier manquant : pack-manifest.env (utilisez le dossier produit par pack-offline.ps1)."
}
Get-Content -LiteralPath $Manifest | ForEach-Object {
    if ($_ -match '^\s*([A-Za-z_][A-Za-z0-9_]*)=(.*)$') {
        Set-Item -Path "env:$($Matches[1])" -Value $Matches[2].Trim()
    }
}
if (-not $env:OFFLINE_TAR -or -not $env:OFFLINE_IMAGE) {
    Write-Error "pack-manifest.env doit définir OFFLINE_TAR et OFFLINE_IMAGE."
}
$TarPath = Join-Path $Dir $env:OFFLINE_TAR
if (-not (Test-Path -LiteralPath $TarPath)) {
    Write-Error "Archive introuvable : $TarPath"
}
Write-Host "Chargement de l'image $($env:OFFLINE_IMAGE) ..."
docker load -i $TarPath
$Compose = Join-Path $Dir "docker-compose.offline.yml"
if (-not (Test-Path -LiteralPath $Compose)) {
    Write-Error "Fichier manquant : docker-compose.offline.yml"
}
Push-Location $Dir
try {
    if ($Mode -eq "https") {
        Write-Host "Démarrage HTTPS (profil https, certificats dans .\certs) ..."
        docker compose --profile https -f $Compose up -d app-https
    }
    else {
        Write-Host "Démarrage HTTP sur le port 8000 ..."
        docker compose -f $Compose up -d app
    }
}
finally {
    Pop-Location
}
