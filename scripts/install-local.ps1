[CmdletBinding()]
param([switch]$Upgrade)

$ErrorActionPreference = 'Stop'
$workspaceRoot = Split-Path -Parent $PSScriptRoot
if (-not (Get-Command codex -ErrorAction SilentlyContinue)) {
    throw 'Codex CLI was not found. Install or locate it before running local setup.'
}
& codex plugin marketplace add $workspaceRoot --json
if ($LASTEXITCODE -ne 0) { throw 'Could not register the local Saber marketplace.' }
& codex plugin add 'saber-companion@saber-local' --json
if ($LASTEXITCODE -ne 0) { throw 'Could not install the Saber plugin.' }
& (Join-Path $workspaceRoot 'plugins/saber-companion/scripts/install-pet.ps1') -Upgrade:$Upgrade
Write-Output 'Saber plugin and pet files are installed locally. Start a new chat for the skills.'
