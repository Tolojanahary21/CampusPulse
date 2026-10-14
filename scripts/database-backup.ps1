[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('Backup', 'Restore')]
    [string]$Action,
    [string]$BackupPath,
    [switch]$RestoreToEmptyTarget
)

$ErrorActionPreference = 'Stop'
$projectRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$originalLocation = Get-Location
$stoppedServices = @()
$operationSucceeded = $false
$postgresTemporaryFile = $null

function Invoke-Docker {
    param([string[]]$DockerArguments)
    & docker @DockerArguments
    if ($LASTEXITCODE -ne 0) {
        throw "Docker a échoué (code $LASTEXITCODE). La procédure est interrompue."
    }
}

try {
    Set-Location -LiteralPath $projectRoot
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        throw 'Docker Compose est requis pour ce script.'
    }
    if ($Action -eq 'Backup') {
        if ($BackupPath) {
            throw 'Backup crée son dossier dans backups/. BackupPath sert uniquement à Restore.'
        }
        $backupRoot = [System.IO.Path]::GetFullPath((Join-Path $projectRoot 'backups'))
        if (-not $backupRoot.StartsWith($projectRoot + [System.IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
            throw 'Le dossier de sauvegarde sort du projet.'
        }
        $backupName = (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssfffZ') + '-' + [guid]::NewGuid().ToString('N').Substring(0, 8)
        $backupDirectory = Join-Path $backupRoot $backupName
        New-Item -ItemType Directory -Path $backupDirectory -ErrorAction Stop | Out-Null
    } else {
        if (-not $RestoreToEmptyTarget) {
            throw 'La restauration nécessite -RestoreToEmptyTarget ; aucune donnée existante ne sera écrasée.'
        }
        if (-not $BackupPath -or -not (Test-Path -LiteralPath $BackupPath -PathType Container)) {
            throw 'Fournir -BackupPath vers un dossier de sauvegarde complet.'
        }
        $backupDirectory = (Resolve-Path -LiteralPath $BackupPath).Path
        $manifest = Get-Content -LiteralPath (Join-Path $backupDirectory 'manifest.json') -Raw | ConvertFrom-Json
        if ($manifest.version -ne 1) { throw 'Version de sauvegarde inconnue.' }
        foreach ($filename in @('database.dump', 'uploads.tar.gz')) {
            $hash = (Get-FileHash -LiteralPath (Join-Path $backupDirectory $filename) -Algorithm SHA256).Hash
            if ($hash -ne $manifest.sha256.$filename) { throw "Empreinte invalide : $filename" }
        }
    }

    $runningServices = @(& docker compose ps --status running --services)
    if ($LASTEXITCODE -ne 0) { throw 'Impossible de vérifier les services Compose.' }
    if ($runningServices -notcontains 'postgres') {
        throw 'Démarrer PostgreSQL avec docker compose up -d postgres avant cette opération.'
    }
    $stoppedServices = @($runningServices | Where-Object { $_ -in @('backend', 'mail-worker') })
    if ($stoppedServices.Count -gt 0) {
        Invoke-Docker -DockerArguments (@('compose', 'stop') + $stoppedServices)
    }

    $scriptMount = $PSScriptRoot + ':/maintenance:ro'
    if ($Action -eq 'Backup') {
        $postgresTemporaryFile = '/tmp/campuspulse-backup.dump'
        Invoke-Docker -DockerArguments @('compose', 'exec', '-T', 'postgres', 'sh', '-c', 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=custom --file=/tmp/campuspulse-backup.dump')
        Invoke-Docker -DockerArguments @('compose', 'cp', 'postgres:/tmp/campuspulse-backup.dump', (Join-Path $backupDirectory 'database.dump'))
        Invoke-Docker -DockerArguments @('compose', 'run', '--rm', '--no-deps', '-v', ($backupDirectory + ':/backup'), '-v', $scriptMount, 'backend', 'python', '/maintenance/storage_archive.py', 'backup')
        $hashes = @{}
        foreach ($filename in @('database.dump', 'uploads.tar.gz')) {
            $hashes[$filename] = (Get-FileHash -LiteralPath (Join-Path $backupDirectory $filename) -Algorithm SHA256).Hash
        }
        @{
            version = 1
            created_at_utc = (Get-Date).ToUniversalTime().ToString('o')
            sha256 = $hashes
        } | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $backupDirectory 'manifest.json') -Encoding UTF8
        Write-Host "Sauvegarde créée : $backupDirectory"
    } else {
        $emptyDatabaseQuery = 'SELECT count(*) FROM information_schema.tables WHERE table_schema = ''public'';'
        $tableCount = @(& docker compose exec -T postgres sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "$1"' sh $emptyDatabaseQuery)
        if ($LASTEXITCODE -ne 0 -or ($tableCount -join '').Trim() -ne '0') {
            throw 'La base cible doit être vide. Utiliser un nouveau projet Compose et ses volumes.'
        }
        Invoke-Docker -DockerArguments @('compose', 'run', '--rm', '--no-deps', '-v', ($backupDirectory + ':/backup:ro'), '-v', $scriptMount, 'backend', 'python', '/maintenance/storage_archive.py', 'verify')
        $postgresTemporaryFile = '/tmp/campuspulse-restore.dump'
        Invoke-Docker -DockerArguments @('compose', 'cp', (Join-Path $backupDirectory 'database.dump'), 'postgres:/tmp/campuspulse-restore.dump')
        Invoke-Docker -DockerArguments @('compose', 'exec', '-T', 'postgres', 'sh', '-c', 'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner --no-privileges --exit-on-error --single-transaction /tmp/campuspulse-restore.dump')
        Invoke-Docker -DockerArguments @('compose', 'run', '--rm', '--no-deps', '-v', ($backupDirectory + ':/backup:ro'), '-v', $scriptMount, 'backend', 'python', '/maintenance/storage_archive.py', 'restore')
        Write-Host 'Base et stockage restaurés. Vérifier les migrations et les parcours avant réouverture.'
    }
    $operationSucceeded = $true
} finally {
    # Une sauvegarde échouée ne doit pas prolonger l’arrêt. Une restauration
    # échouée conserve l’arrêt pour éviter une application partiellement restaurée.
    try {
        if ($postgresTemporaryFile) {
            # Un seul chemin constant dans le conteneur PostgreSQL ; aucune
            # suppression de dossier et aucune entrée utilisateur interpolée.
            & docker compose exec -T postgres rm -f -- $postgresTemporaryFile
            if ($LASTEXITCODE -ne 0) { Write-Warning 'Le fichier temporaire du conteneur reste à nettoyer.' }
        }
        if ($stoppedServices.Count -gt 0 -and ($Action -eq 'Backup' -or $operationSucceeded)) {
            Invoke-Docker -DockerArguments (@('compose', 'start') + $stoppedServices)
        }
    } finally {
        Set-Location -LiteralPath $originalLocation.Path
    }
}
