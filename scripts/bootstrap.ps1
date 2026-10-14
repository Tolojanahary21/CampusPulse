[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$projectRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$environmentFiles = @(
    @{ Source = '.env.example'; Destination = '.env' },
    @{ Source = 'backend/.env.example'; Destination = 'backend/.env' },
    @{ Source = 'frontend/.env.example'; Destination = 'frontend/.env.local' }
)

foreach ($environmentFile in $environmentFiles) {
    $sourcePath = Join-Path $projectRoot $environmentFile.Source
    $destinationPath = Join-Path $projectRoot $environmentFile.Destination
    if (-not (Test-Path -LiteralPath $sourcePath -PathType Leaf)) {
        throw "Exemple manquant : $($environmentFile.Source)"
    }
    if (Test-Path -LiteralPath $destinationPath) {
        Write-Host "Conservé : $($environmentFile.Destination)"
    } else {
        # Pas de -Force : une configuration existante ne doit jamais être écrasée.
        Copy-Item -LiteralPath $sourcePath -Destination $destinationPath -ErrorAction Stop
        Write-Host "Créé : $($environmentFile.Destination)"
    }
}

Write-Host 'Configurer backend/.env (SECRET_KEY et SMTP), puis suivre README.md.'
Write-Host 'Les fichiers existants sont conservés ; aucun contenu de configuration affiché.'
