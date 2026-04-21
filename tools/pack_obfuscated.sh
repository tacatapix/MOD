#!/usr/bin/env bash
# Produce the obfuscated + signed build:
#   dist/@PackFazupix_KOTH_Obfuscated/
#     mod.cpp
#     addons/PackFazupix_KOTH.pbo
#     addons/PackFazupix_KOTH.pbo.<keyname>.bisign
#     keys/<keyname>.bikey
#
# Requires armake2 in $PATH (cargo install --git \
#   https://github.com/KoffeinFlummi/armake2 armake2).

set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
KEYNAME="${1:-Private}"

STAGE_RAW="$ROOT/dist/staging/PackFazupix_KOTH"
STAGE_OBF="$ROOT/dist/staging_obf/PackFazupix_KOTH"
OUT="$ROOT/dist/@PackFazupix_KOTH_Obfuscated"
KEYDIR="$ROOT/dist/keys"

command -v armake2 >/dev/null || {
    echo "armake2 not found in PATH. Install with:"
    echo "  cargo install --git https://github.com/KoffeinFlummi/armake2 armake2"
    exit 1
}

# 1) Refresh the raw staging (for reproducibility).
rm -rf "$STAGE_RAW"
mkdir -p "$STAGE_RAW"
cp "$ROOT/config.cpp"     "$STAGE_RAW/"
cp -r "$ROOT/Scripts"      "$STAGE_RAW/"
cp -r "$ROOT/GUI"          "$STAGE_RAW/"
printf 'PackFazupix_KOTH' > "$STAGE_RAW/\$PBOPREFIX\$"

# 2) Obfuscate into the obf staging.
python3 "$HERE/obfuscate.py" "$STAGE_RAW" "$STAGE_OBF"
cp "$STAGE_RAW/\$PBOPREFIX\$" "$STAGE_OBF/\$PBOPREFIX\$"

# 3) Generate the keypair (once per keyname) and the output mod layout.
mkdir -p "$KEYDIR"
if [ ! -f "$KEYDIR/$KEYNAME.biprivatekey" ]; then
    ( cd "$KEYDIR" && armake2 keygen -v "$KEYNAME" )
fi

rm -rf "$OUT"
mkdir -p "$OUT/addons" "$OUT/keys"
cp "$ROOT/mod.cpp"              "$OUT/"
cp "$KEYDIR/$KEYNAME.bikey"     "$OUT/keys/"

# 4) Pack + sign.
armake2 pack -f "$STAGE_OBF" "$OUT/addons/PackFazupix_KOTH.pbo"
armake2 sign -f "$KEYDIR/$KEYNAME.biprivatekey" "$OUT/addons/PackFazupix_KOTH.pbo"

# 5) Verify the signature matches the public key.
armake2 verify "$KEYDIR/$KEYNAME.bikey" "$OUT/addons/PackFazupix_KOTH.pbo" \
    "$OUT/addons/PackFazupix_KOTH.pbo.$KEYNAME.bisign"

echo
echo "ok: $OUT"
echo "    addons/PackFazupix_KOTH.pbo"
echo "    addons/PackFazupix_KOTH.pbo.$KEYNAME.bisign"
echo "    keys/$KEYNAME.bikey"
echo
echo "Private key lives at $KEYDIR/$KEYNAME.biprivatekey - keep it secret!"
