#!/usr/bin/env python3
"""XP3 packer for KiriKiri (krkr2/krkrz) archives.

Produces a raw (uncompressed) XP3 that is byte-compatible with what krkr2's
reader expects (verified against the game's own data.xp3 + our extractor).

Layout:
  [0..10]   mark 'XP3\\r\\n \\n\\x1a\\x8bg\\x01'
  [11..18]  I64LE index_ofs (offset of index block from archive start)
  [19 .. ]  file data segments (raw, contiguous)
  [index_ofs ..] index block: flag(0x00 raw,no-continue) + I64LE idx_size + idx

Index = sequence of 'File' chunks; each File payload = info+segm+adlr chunks.
"""
import struct, os, sys, zlib

MARK = bytes([0x58, 0x50, 0x33, 0x0d, 0x0a, 0x20, 0x0a, 0x1a, 0x8b, 0x67, 0x01])
HEADER_SIZE = 11 + 8


def _chunk(tag, payload):
    return tag + struct.pack('<q', len(payload)) + payload


def build_xp3(files, out_path):
    """files: list of (arc_name, local_path). arc_name uses '/' separators and is
    the path INSIDE the archive (bare name for root-level entries)."""
    data = bytearray()
    entries = []  # (name, org_size, start_offset, content)
    for arc_name, local_path in files:
        with open(local_path, 'rb') as fh:
            content = fh.read()
        start = len(data) + HEADER_SIZE
        entries.append((arc_name, len(content), start, content))
        data += content

    idx = bytearray()
    for arc_name, org_size, start, content in entries:
        name_u16 = arc_name.encode('utf-16-le')
        nlen = len(name_u16) // 2
        info_payload = struct.pack('<iqqh', 0, org_size, org_size, nlen) + name_u16
        segm_payload = struct.pack('<iqqq', 0, start, org_size, org_size)
        hval = zlib.crc32(content) & 0xffffffff
        adlr_payload = struct.pack('<I', hval)
        file_payload = (_chunk(b'info', info_payload)
                        + _chunk(b'segm', segm_payload)
                        + _chunk(b'adlr', adlr_payload))
        idx += _chunk(b'File', file_payload)

    index_ofs = HEADER_SIZE + len(data)
    final = bytearray()
    final += MARK
    final += struct.pack('<q', index_ofs)
    final += bytes(data)
    assert len(final) == index_ofs, (len(final), index_ofs)
    final += bytes([0x00]) + struct.pack('<q', len(idx)) + bytes(idx)

    with open(out_path, 'wb') as fh:
        fh.write(bytes(final))
    return entries


if __name__ == '__main__':
    # usage: xp3_pack.py out.xp3 "arcname=localpath" "arcname=localpath" ...
    out = sys.argv[1]
    files = []
    for spec in sys.argv[2:]:
        arc, lp = spec.split('=', 1)
        files.append((arc, lp))
    ents = build_xp3(files, out)
    print(f"wrote {out}: {len(ents)} files, total {os.path.getsize(out)} bytes")
