#!/usr/bin/env python3
"""
Lightweight obfuscator / minifier for Enforce Script (DayZ).

What it does:
    * Strips line comments (//...)
    * Strips block comments (/* ... */)
    * Collapses blank lines and trims trailing whitespace
    * Removes leading indentation (keeps one leading space inside
      multi-token lines)
    * Replaces multiple spaces/tabs with a single space outside of
      string literals
    * Preserves every identifier (class names, method names, RPC names)
      so the mod's public surface is unchanged and CfgPatches / RestApi /
      client<->server RPCs keep working.

What it does NOT do:
    * Does not rename identifiers. Enforce Script has no module system —
      classes are resolved by name across translation units (CfgPatches,
      RPC routing, layout lookups, ScriptRPC dispatch), so a blind rename
      will brick the mod. A targeted renamer is possible but is a much
      larger project (requires a real Enforce parser).
    * Does not encrypt strings. Enforce's `string` type is read by the
      engine as UTF-8; any encryption would need runtime decryption in
      script and would hurt performance more than it helps security.
    * Does not binarise anything. Binarisation of `config.cpp` requires
      the Bohemia DayZ Tools on Windows.

Usage:
    python3 tools/obfuscate.py <source_dir> <output_dir>

It walks <source_dir>, obfuscates every `.c` and `.layout` file, and
copies everything else verbatim into <output_dir>.
"""

import os
import re
import shutil
import sys


# Files we actually rewrite. Everything else is copied verbatim.
OBFUSCATE_EXTS = {".c", ".layout"}

# Match // comments that are NOT inside a string. We approximate this by
# eating characters before the `//` on each line in a second pass (see
# strip_line_comments below). A full parser is overkill for a minifier.
RE_BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)
RE_MULTI_BLANK   = re.compile(r"\n\s*\n+")
RE_TRAILING_WS   = re.compile(r"[ \t]+\n")
RE_MULTI_SPACE   = re.compile(r"[ \t]{2,}")


def strip_line_comments(src: str) -> str:
    """Remove // comments while respecting string literals."""
    out = []
    i = 0
    n = len(src)
    in_str = False
    str_ch = ""
    while i < n:
        ch = src[i]
        nxt = src[i + 1] if i + 1 < n else ""
        if in_str:
            out.append(ch)
            if ch == "\\" and i + 1 < n:
                out.append(nxt)
                i += 2
                continue
            if ch == str_ch:
                in_str = False
            i += 1
            continue
        if ch in ('"', "'"):
            in_str = True
            str_ch = ch
            out.append(ch)
            i += 1
            continue
        if ch == "/" and nxt == "/":
            # Skip until end of line but keep the newline.
            while i < n and src[i] != "\n":
                i += 1
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def obfuscate_source(src: str) -> str:
    # Block comments first (greedy-safe because non-greedy DOTALL).
    src = RE_BLOCK_COMMENT.sub("", src)
    src = strip_line_comments(src)
    src = RE_TRAILING_WS.sub("\n", src)
    src = RE_MULTI_BLANK.sub("\n", src)
    # Collapse runs of whitespace *outside* strings. Cheap approximation:
    # only touch leading whitespace on each line plus runs of 2+ spaces
    # that don't sit between a leading `"` and the next `"`.
    lines = []
    for line in src.split("\n"):
        stripped = line.lstrip()
        if stripped:
            # Leave one space so tokens like `return x;` stay readable when
            # concatenated with previous content in an IDE, but we drop the
            # original indentation level.
            lines.append(stripped)
    joined = "\n".join(lines)
    # Now kill leftover double-spaces that aren't inside a string.
    joined = _collapse_spaces_outside_strings(joined)
    # Strip trailing blank lines/newlines.
    return joined.strip() + "\n"


def _collapse_spaces_outside_strings(src: str) -> str:
    out = []
    i = 0
    n = len(src)
    in_str = False
    str_ch = ""
    while i < n:
        ch = src[i]
        nxt = src[i + 1] if i + 1 < n else ""
        if in_str:
            out.append(ch)
            if ch == "\\" and i + 1 < n:
                out.append(nxt)
                i += 2
                continue
            if ch == str_ch:
                in_str = False
            i += 1
            continue
        if ch in ('"', "'"):
            in_str = True
            str_ch = ch
            out.append(ch)
            i += 1
            continue
        if ch in " \t":
            # Collapse runs of spaces/tabs to a single space outside strings.
            out.append(" ")
            while i < n and src[i] in " \t":
                i += 1
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def process_tree(src_dir: str, dst_dir: str) -> None:
    src_dir = os.path.abspath(src_dir)
    dst_dir = os.path.abspath(dst_dir)
    if os.path.exists(dst_dir):
        shutil.rmtree(dst_dir)
    os.makedirs(dst_dir, exist_ok=True)

    touched = kept = 0
    for root, dirs, files in os.walk(src_dir):
        dirs.sort()
        rel = os.path.relpath(root, src_dir)
        out_root = dst_dir if rel == "." else os.path.join(dst_dir, rel)
        os.makedirs(out_root, exist_ok=True)
        for name in sorted(files):
            src_path = os.path.join(root, name)
            dst_path = os.path.join(out_root, name)
            ext = os.path.splitext(name)[1].lower()
            if ext in OBFUSCATE_EXTS:
                with open(src_path, "r", encoding="utf-8") as f:
                    src = f.read()
                with open(dst_path, "w", encoding="utf-8", newline="\n") as f:
                    f.write(obfuscate_source(src))
                touched += 1
            else:
                shutil.copy2(src_path, dst_path)
                kept += 1
    print(f"obfuscated: {touched} file(s); copied verbatim: {kept} file(s)")


def main(argv):
    if len(argv) != 3:
        print(__doc__, file=sys.stderr)
        return 2
    process_tree(argv[1], argv[2])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
