#!/usr/bin/env bash
# Build the obfuscated + signed dual-mod distribution:
#
#   dist/@PackFazupix_KOTH/
#       mod.cpp
#       addons/PackFazupix_KOTH.pbo
#       addons/PackFazupix_KOTH.pbo.<key>.bisign
#       keys/<key>.bikey
#
#   dist/@PackFazupix_KOTH_Server/
#       mod.cpp
#       addons/PackFazupix_KOTH_Server.pbo
#       addons/PackFazupix_KOTH_Server.pbo.<key>.bisign
#       keys/<key>.bikey
#
# Requires armake2 in $PATH:
#   cargo install --git https://github.com/KoffeinFlummi/armake2 armake2

set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
KEYNAME="${1:-Private}"

command -v armake2 >/dev/null || {
    echo "armake2 not found in PATH."
    echo "Install with:"
    echo "  cargo install --git https://github.com/KoffeinFlummi/armake2 armake2"
    exit 1
}

STAGE_CLIENT_RAW="$ROOT/dist/staging/PackFazupix_KOTH"
STAGE_CLIENT_OBF="$ROOT/dist/staging_obf/PackFazupix_KOTH"
OUT_CLIENT="$ROOT/dist/@PackFazupix_KOTH"

STAGE_SERVER_RAW="$ROOT/dist/staging/PackFazupix_KOTH_Server"
STAGE_SERVER_OBF="$ROOT/dist/staging_obf/PackFazupix_KOTH_Server"
OUT_SERVER="$ROOT/dist/@PackFazupix_KOTH_Server"

KEYDIR="$ROOT/dist/keys"

# ----------------------------------------------------------------------------
# 1. Stage the main (client+server) mod.
# ----------------------------------------------------------------------------
rm -rf "$STAGE_CLIENT_RAW"
mkdir -p "$STAGE_CLIENT_RAW"
cp    "$ROOT/config.cpp" "$STAGE_CLIENT_RAW/"
cp -r "$ROOT/Scripts"    "$STAGE_CLIENT_RAW/"
cp -r "$ROOT/GUI"        "$STAGE_CLIENT_RAW/"
printf 'PackFazupix_KOTH' > "$STAGE_CLIENT_RAW/\$PBOPREFIX\$"

python3 "$HERE/obfuscate.py" "$STAGE_CLIENT_RAW" "$STAGE_CLIENT_OBF"
cp "$STAGE_CLIENT_RAW/\$PBOPREFIX\$" "$STAGE_CLIENT_OBF/\$PBOPREFIX\$"

# ----------------------------------------------------------------------------
# 2. Stage the server-only mod.
# ----------------------------------------------------------------------------
rm -rf "$STAGE_SERVER_RAW"
mkdir -p "$STAGE_SERVER_RAW"
cp -r "$ROOT/ServerMod/PackFazupix_KOTH_Server/." "$STAGE_SERVER_RAW/"

python3 "$HERE/obfuscate.py" "$STAGE_SERVER_RAW" "$STAGE_SERVER_OBF"
cp "$STAGE_SERVER_RAW/\$PBOPREFIX\$" "$STAGE_SERVER_OBF/\$PBOPREFIX\$"

# ----------------------------------------------------------------------------
# 3. Keypair.
# ----------------------------------------------------------------------------
mkdir -p "$KEYDIR"
if [ ! -f "$KEYDIR/$KEYNAME.biprivatekey" ]; then
    ( cd "$KEYDIR" && armake2 keygen -v "$KEYNAME" )
fi

# ----------------------------------------------------------------------------
# 4. Pack + sign both mods.
# ----------------------------------------------------------------------------
build_mod () {
    local stage="$1" outdir="$2" pboname="$3" modcpp="$4"
    rm -rf "$outdir"
    mkdir -p "$outdir/addons" "$outdir/keys"
    cp "$modcpp"                "$outdir/"
    cp "$KEYDIR/$KEYNAME.bikey" "$outdir/keys/"
    armake2 pack -f "$stage" "$outdir/addons/$pboname.pbo"
    armake2 sign -f "$KEYDIR/$KEYNAME.biprivatekey" "$outdir/addons/$pboname.pbo"
    armake2 verify "$KEYDIR/$KEYNAME.bikey" \
        "$outdir/addons/$pboname.pbo" \
        "$outdir/addons/$pboname.pbo.$KEYNAME.bisign"
    echo "ok: $outdir/addons/$pboname.pbo"
}

build_mod "$STAGE_CLIENT_OBF" "$OUT_CLIENT" "PackFazupix_KOTH" \
    "$ROOT/mod.cpp"
build_mod "$STAGE_SERVER_OBF" "$OUT_SERVER" "PackFazupix_KOTH_Server" \
    "$ROOT/ServerMod/mod.cpp"

echo
echo "==> Distribute to players:    $OUT_CLIENT"
echo "==> Server ONLY (secret):     $OUT_SERVER"
echo "==> Private key (NEVER share): $KEYDIR/$KEYNAME.biprivatekey"
