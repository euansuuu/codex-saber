[CmdletBinding()]
param([string]$CodexDirectory, [switch]$Upgrade)

$ErrorActionPreference = 'Stop'
if (-not $CodexDirectory) {
    $CodexDirectory = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $env:USERPROFILE '.codex' }
}
$pluginRoot = Split-Path -Parent $PSScriptRoot
$sourceDirectory = Join-Path $pluginRoot 'pets/saber-knight'
$manifestPath = Join-Path $sourceDirectory 'pet.json'
$manifest = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
if ($manifest.spriteVersionNumber -ne 1 -or $manifest.spritesheetPath -ne 'spritesheet.png') {
    throw 'The packaged pet manifest is not the supported Saber v1 format.'
}
Add-Type -AssemblyName System.Drawing
$sheet = [System.Drawing.Bitmap]::new((Join-Path $sourceDirectory $manifest.spritesheetPath))
try {
    if ($sheet.Width -ne 1536 -or $sheet.Height -ne 1872 -or
        -not ($sheet.PixelFormat.ToString().Contains('Argb'))) {
        throw 'The Saber sheet must be a 1536 x 1872 PNG with an alpha channel.'
    }
} finally { $sheet.Dispose() }

$targetDirectory = [IO.Path]::GetFullPath((Join-Path $CodexDirectory 'pets/saber-knight'))
if (Test-Path -LiteralPath $targetDirectory) {
    if ((Get-Item -LiteralPath $targetDirectory).Attributes -band [IO.FileAttributes]::ReparsePoint) {
        throw 'The destination is a link. Choose a regular Codex directory.'
    }
}
$files = @('spritesheet.png', 'pet.json')
$changedFiles = @()
foreach ($file in $files) {
    $target = Join-Path $targetDirectory $file
    if (Test-Path -LiteralPath $target) {
        $item = Get-Item -LiteralPath $target
        if ($item.PSIsContainer -or ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
            throw "The destination file is not a regular file: $target"
        }
        $hasher = [Security.Cryptography.SHA256]::Create()
        try {
            $existingHash = [Convert]::ToBase64String($hasher.ComputeHash([IO.File]::ReadAllBytes($target)))
            $packagedHash = [Convert]::ToBase64String($hasher.ComputeHash([IO.File]::ReadAllBytes((Join-Path $sourceDirectory $file))))
        } finally { $hasher.Dispose() }
        if ($existingHash -ne $packagedHash) {
            $changedFiles += $file
        }
    }
}
if ($changedFiles.Count -gt 0) {
    if (-not $Upgrade) {
        throw "Existing Saber files differ. Use -Upgrade to back up and replace: $targetDirectory"
    }
    $backupName = [DateTime]::UtcNow.ToString('yyyyMMdd-HHmmss-fff') + '-' + [Guid]::NewGuid().ToString('N').Substring(0, 8)
    $backupDirectory = Join-Path $CodexDirectory "pets-backups/saber-knight/$backupName"
    New-Item -ItemType Directory -Path $backupDirectory -Force | Out-Null
    foreach ($file in $files) {
        $existing = Join-Path $targetDirectory $file
        if (Test-Path -LiteralPath $existing) {
            Copy-Item -LiteralPath $existing -Destination (Join-Path $backupDirectory $file)
        }
    }
    Write-Output "Previous Saber files backed up: $backupDirectory"
}
New-Item -ItemType Directory -Path $targetDirectory -Force | Out-Null
foreach ($file in $files) {
    $target = Join-Path $targetDirectory $file
    if ($file -in $changedFiles -or -not (Test-Path -LiteralPath $target)) {
        Copy-Item -LiteralPath (Join-Path $sourceDirectory $file) -Destination $target -Force
    }
}
Write-Output "Pet installed: $targetDirectory"
Write-Output 'In Codex: Settings > Pets > Refresh > Saber. Use /pet to show it.'
$statePath = Join-Path $CodexDirectory '.codex-global-state.json'
if (Test-Path -LiteralPath $statePath) {
    try {
        $state = Get-Content -LiteralPath $statePath -Raw -Encoding UTF8 | ConvertFrom-Json
        $migrations = $state.'electron-persisted-atom-state'.'migrated-cloud-pet-ids-v1'
        $cloudCopy = $migrations.PSObject.Properties | Where-Object { $_.Value.'custom:saber-knight' -like 'pet_*' }
        if ($cloudCopy) {
            Write-Output 'Saber has a migrated cloud copy. Refresh does not replace cloud artwork.'
            Write-Output 'Ask $saber-companion:saber-setup to sync the active Saber artwork while preserving its pet ID.'
        }
    } catch {
        Write-Warning 'Local files are installed, but cloud-migration status could not be read. Check the active Saber in Pets.'
    }
}
