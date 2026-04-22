<#
.SYNOPSIS
Pack @PackFazupix_KOTH using the official DayZ Tools AddonBuilder.

.DESCRIPTION
Assumes DayZ Tools is installed via Steam at its default path
(%STEAMAPPS%\common\DayZ Tools\Bin\AddonBuilder\AddonBuilder.exe).

Produces a properly-binarised, signed-ready PBO. Use this for
production / Workshop distribution. For local testing on a dev server
the Python packer (tools/pack_linux.sh) is enough.

.EXAMPLE
    pwsh tools/pack_windows.ps1
#>

$ErrorActionPreference = "Stop"

$root       = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
$stage      = Join-Path $root "dist\staging\PackFazupix_KOTH"
$out        = Join-Path $root "dist\@PackFazupix_KOTH"
$addonsOut  = Join-Path $out   "addons"

# Refresh staging.
if (Test-Path $stage) { Remove-Item -Recurse -Force $stage }
New-Item -ItemType Directory -Force -Path $stage    | Out-Null
Copy-Item (Join-Path $root "config.cpp") $stage
Copy-Item -Recurse (Join-Path $root "Scripts") $stage
Copy-Item -Recurse (Join-Path $root "GUI")     $stage
Set-Content -NoNewline -Path (Join-Path $stage '$PBOPREFIX$') -Value 'PackFazupix_KOTH'

New-Item -ItemType Directory -Force -Path $addonsOut | Out-Null
Copy-Item (Join-Path $root "mod.cpp") $out -Force

# Locate AddonBuilder.
$candidates = @(
    "$env:ProgramFiles (x86)\Steam\steamapps\common\DayZ Tools\Bin\AddonBuilder\AddonBuilder.exe",
    "$env:ProgramFiles\Steam\steamapps\common\DayZ Tools\Bin\AddonBuilder\AddonBuilder.exe"
)
$builder = $candidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $builder) {
    throw "AddonBuilder.exe not found. Install DayZ Tools via Steam or edit this script with the correct path."
}

& $builder $stage $addonsOut -clear -packonly
if ($LASTEXITCODE -ne 0) { throw "AddonBuilder failed: $LASTEXITCODE" }

Write-Host "ok: $addonsOut"
