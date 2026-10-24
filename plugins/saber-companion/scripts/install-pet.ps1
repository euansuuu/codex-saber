[CmdletBinding()]
param([string]$CodexDirectory)

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
            throw "Existing Saber files differ. Back up your changes before replacing: $target"
        }
    }
}
New-Item -ItemType Directory -Path $targetDirectory -Force | Out-Null
foreach ($file in $files) {
    $target = Join-Path $targetDirectory $file
    if (-not (Test-Path -LiteralPath $target)) {
        Copy-Item -LiteralPath (Join-Path $sourceDirectory $file) -Destination $target
    }
}
Write-Output "Pet installed: $targetDirectory"
Write-Output 'In Codex: Settings > Pets > Refresh > Saber. Use /pet to show it.'
