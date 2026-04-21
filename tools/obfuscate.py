#!/usr/bin/env python3
"""
Lightweight "hard to read" minifier for Enforce Script (DayZ).

Scope is intentionally conservative because DayZ's Enforce Script parser
is fragile with multi-line expressions and macro-style constructs:

    * Strip single-line comments (// ...) outside string literals.
    * Strip block comments (/* ... */) outside string literals.
    * Strip blank lines and trailing whitespace.
    * Drop leading indentation on every line.

That's it. Whitespace *inside* expressions is left alone. The resulting
file is single-column, comment-free, and hard to skim by eye, but every
statement that was on its own line in the source is still on its own
line in the output. This keeps the Enforce parser happy even with
multi-line string concatenation and `foreach` pitfalls.

The obfuscator never renames identifiers. Enforce Script resolves
classes, methods, RPCs and CfgPatches entries by name across translation
units, so any blind renamer would brick the mod. Treat this pass as
cosmetic deterrence, not security - DayZ scripts always load as plain
text inside the Bohemia script VM.

Usage:
    python3 tools/obfuscate.py <source_dir> <output_dir>
"""

import os
import re
import shutil
import sys


OBFUSCATE_EXTS = {".c", ".layout"}

RE_BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)


def _strip_line_comments(src: str) -> str:
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
            # Skip to end-of-line but keep the newline.
            while i < n and src[i] != "\n":
                i += 1
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def _strip_block_comments(src: str) -> str:
    """Remove /* ... */ comments while respecting string literals."""
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
        if ch == "/" and nxt == "*":
            j = src.find("*/", i + 2)
            if j == -1:
                # Unterminated, leave the rest as-is (shouldn't happen).
                out.append(src[i:])
                break
            i = j + 2
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def obfuscate_source(src: str) -> str:
    src = _strip_block_comments(src)
    src = _strip_line_comments(src)
    lines = []
    for line in src.split("\n"):
        # Drop leading whitespace so the output is flush to the left column.
        # Trailing whitespace is also stripped. Empty lines disappear.
        stripped = line.rstrip()
        stripped = stripped.lstrip()
        if stripped:
            lines.append(stripped)
    return "\n".join(lines) + "\n"


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
                    data = f.read()
                with open(dst_path, "w", encoding="utf-8", newline="\n") as f:
                    f.write(obfuscate_source(data))
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
