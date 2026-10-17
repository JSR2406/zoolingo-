# Remaining archive steps (run ONLY after the deepseek-harness robocopy completes).
# Moves zoolingo-local (+.vercel), frontend + app.log -> _strays, removes empty temp_uploads,
# then prints final state of the workspace root.

$ErrorActionPreference = 'Continue'
# derive workspace root from this script's own location (ASCII-only; avoids codepage issues)
$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$arc  = 'E:\coding\Default Project Archive'

if (Test-Path "$root\deepseek-harness") {
    Write-Output 'ABORT: deepseek-harness source still present - previous move not finished.'
    exit 1
}

# 1) zoolingo-local (2.5 GB)
robocopy "$root\zoolingo-local" "$arc\zoolingo-local" /E /MOVE /NFL /NDL /NJH /MT:16 /R:2 /W:2
if ($LASTEXITCODE -gt 7) { Write-Output "zoolingo robocopy failed: $LASTEXITCODE"; exit 1 } else { Write-Output 'zoolingo-local MOVE OK' }

# 2) .vercel (zoolingo deploy link) travels with zoolingo
if (Test-Path "$root\.vercel") {
    Move-Item "$root\.vercel" "$arc\zoolingo-local\.vercel" -Force
    Write-Output '.vercel moved into archived zoolingo-local'
}

# 3) strays
New-Item -ItemType Directory -Force "$arc\_strays" | Out-Null
if (Test-Path "$root\frontend") { Move-Item "$root\frontend" "$arc\_strays\frontend" -Force; Write-Output 'frontend -> _strays OK' }
if (Test-Path "$root\app.log")  { Move-Item "$root\app.log"  "$arc\_strays\app.log"  -Force; Write-Output 'app.log -> _strays OK' }

# 4) empty temp dir
if (Test-Path "$root\temp_uploads") { Remove-Item "$root\temp_uploads" -Force; Write-Output 'temp_uploads removed (was empty)' }

# 5) verification
Write-Output '--- workspace root after cleanup ---'
Get-ChildItem $root -Force | Select-Object Name | ForEach-Object { $_.Name }
Write-Output '--- archive tree ---'
Get-ChildItem $arc -Force | Select-Object Name | ForEach-Object { $_.Name }
