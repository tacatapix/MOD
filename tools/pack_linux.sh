#!/usr/bin/env bash
# Pack the mod into dist/@PackFazupix_KOTH/addons/PackFazupix_KOTH.pbo using the
# Python packer. Produces an unsigned, uncompressed PBO. Good for testing;
# for signed production builds use tools/pack_windows.ps1 which drives the
# official DayZ Tools AddonBuilder.

set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
STAGE="$ROOT/dist/staging/PackFazupix_KOTH"
OUTDIR="$ROOT/dist/@PackFazupix_KOTH"
OUTPBO="$OUTDIR/addons/PackFazupix_KOTH.pbo"

# Refresh staging from live sources.
rm -rf "$STAGE"
mkdir -p "$STAGE"
cp "$ROOT/config.cpp" "$STAGE/"
cp -r "$ROOT/Scripts"  "$STAGE/"
cp -r "$ROOT/GUI"      "$STAGE/"
printf 'PackFazupix_KOTH' > "$STAGE/\$PBOPREFIX\$"

# Mod folder layout.
mkdir -p "$OUTDIR/addons" "$OUTDIR/keys"
cp "$ROOT/mod.cpp" "$OUTDIR/"

python3 "$HERE/pack_pbo.py" "$STAGE" "$OUTPBO"
echo "ok: $OUTPBO"
