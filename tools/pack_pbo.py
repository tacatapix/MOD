#!/usr/bin/env python3
"""
Minimal PBO packer for DayZ script-only mods.

Usage:
    python3 tools/pack_pbo.py <source_dir> <output.pbo>

The source_dir is the directory whose CONTENTS become the PBO. Filenames
inside the PBO are encoded with Windows-style backslashes. A `$PBOPREFIX$`
file inside source_dir provides the PBO prefix (overrides the default).

This packer produces an UNCOMPRESSED, UNSIGNED PBO. It's fine for loading
on a DayZ server (the server doesn't require signed PBOs for locally
controlled mods). For signed distribution (client mods delivered via
Workshop or DSA-key'd servers) use the official DayZ Tools AddonBuilder
or Mikero's pboProject instead - see tools/pack_windows.ps1.

Caveats:
    * Does NOT binarise config.cpp -> config.bin. DayZ will parse the
      plain-text config.cpp at load time just fine.
    * Does NOT compress. Script-only mods are small, so this is a wash.
    * Does NOT sign. The PBO has no .bisign - DSA-key-protected servers
      will reject it; run `DSCreateKey` + `DSSignFile` if you need signing.
"""

import hashlib
import os
import struct
import sys
import time

# MIME / packing-method constants (see BI PBO spec)
MIME_UNCOMPRESSED = 0x00000000
MIME_PROPERTIES   = 0x56657273  # 'Vers'

# Files that must never end up in the PBO.
SKIP_NAMES = {"$PBOPREFIX$", ".DS_Store", "Thumbs.db"}
SKIP_EXTS  = {".pbo", ".bisign", ".log", ".bak", ".tmp", ".orig"}


def write_header_entry(out, filename, mime, orig_size, timestamp, size):
    # out is a bytearray; bytearray uses .extend(), not .write().
    out.extend(filename.encode("ascii") + b"\x00")
    out.extend(struct.pack("<IIIII", mime, orig_size, 0, timestamp, size))


def collect_files(source_dir):
    """Walk source_dir and yield (relative_windows_path, absolute_disk_path)."""
    source_dir = os.path.abspath(source_dir)
    for root, dirs, files in os.walk(source_dir):
        dirs.sort()
        for name in sorted(files):
            if name in SKIP_NAMES:
                continue
            lower = name.lower()
            if any(lower.endswith(ext) for ext in SKIP_EXTS):
                continue
            abs_path = os.path.join(root, name)
            rel_path = os.path.relpath(abs_path, source_dir)
            # PBO uses Windows-style backslashes.
            rel_path = rel_path.replace(os.sep, "\\").replace("/", "\\")
            yield rel_path, abs_path


def read_prefix(source_dir, default):
    path = os.path.join(source_dir, "$PBOPREFIX$")
    if os.path.exists(path):
        with open(path, "rb") as f:
            return f.read().decode("utf-8").strip()
    return default


def pack(source_dir, output_path):
    source_dir  = os.path.abspath(source_dir)
    output_path = os.path.abspath(output_path)
    prefix      = read_prefix(source_dir, os.path.basename(source_dir))

    files = list(collect_files(source_dir))
    now   = int(time.time())
    body  = bytearray()

    # Properties header.
    write_header_entry(body, "", MIME_PROPERTIES, 0, 0, 0)
    body.extend(b"prefix\x00" + prefix.encode("ascii") + b"\x00")
    body.append(0x00)  # end of properties

    # Per-file headers (uncompressed).
    file_blobs = []
    for rel, abs_path in files:
        with open(abs_path, "rb") as f:
            blob = f.read()
        write_header_entry(body, rel, MIME_UNCOMPRESSED, len(blob), now, len(blob))
        file_blobs.append(blob)

    # Terminator header.
    write_header_entry(body, "", 0, 0, 0, 0)

    # File data in the same order as the headers above.
    for blob in file_blobs:
        body.extend(blob)

    # Checksum: 0x00 then SHA-1 of the preceding body (including the 0x00 byte).
    body.append(0x00)
    digest = hashlib.sha1(bytes(body)).digest()
    body.extend(digest)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(body)

    total = sum(len(b) for b in file_blobs)
    print(f"packed {len(files)} file(s), {total} byte(s) of payload")
    print(f"prefix: {prefix}")
    print(f"wrote:  {output_path} ({len(body)} bytes)")


def main(argv):
    if len(argv) != 3:
        print(__doc__, file=sys.stderr)
        return 2
    pack(argv[1], argv[2])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
