#!/usr/bin/env python3
"""XP3 archive extractor for KiriKiri (krkr2/krkrz) data.xp3 files.

Format (per krkr2 src/core/base/XP3Archive.cpp):
  [0..10]   mark: 'X','P','3',0x0d,0x0a,' ',0x0a,0x1a,0x8b,0x67,0x01
            (or MZ-prefixed exe with mark at 16-byte aligned offset)
  [11..18]  I64LE index_ofs   (offset of index from archive start)
  @index_ofs:
    1 byte  index_flag: low3 = encode method (0=raw,1=zlib), bit7 = continue
    raw : I64LE r_index_size, then index data
    zlib: I64LE compressed_size, I64LE r_index_size, then zlib stream
  index data = sequence of chunks: [4s name][I64LE size][payload]
    'File' chunk payload contains sub-chunks (scanned in order):
      'info': I32 flags, I64 OrgSize, I64 ArcSize, I16 namelen, UTF-16LE name
      'segm': N x 28-byte records: I32 flags, I64 Start, I64 OrgSize, I64 ArcSize
              (flags low3: 0=raw,1=zlib; Start relative to archive start)
      'aldr': I32 FileHash
"""
import struct, sys, os, zlib

MARK = bytes([0x58,0x50,0x33,0x0d,0x0a,0x20,0x0a,0x1a,0x8b,0x67,0x01])

def i64(b, o): return struct.unpack_from('<q', b, o)[0]
def i32(b, o): return struct.unpack_from('<i', b, o)[0]
def i16(b, o): return struct.unpack_from('<h', b, o)[0]

def find_chunk(data, name, start, size):
    """Mirror of tTVPXP3Archive::FindChunk. Returns (payload_start, payload_size) or None."""
    pos = 0
    p = start
    while pos < size:
        found = data[p:p+4] == name
        p += 4
        r_size = i64(data, p); p += 8
        if found:
            return p, r_size
        p += r_size
        pos += r_size + 12
    return None

class Xp3Archive:
    def __init__(self, path):
        self.path = path
        with open(path, 'rb') as f:
            self.data = f.read()
        d = self.data
        if d[:2] == b'MZ':
            raise NotImplementedError("MZ-prefixed archive not supported here")
        assert d[:11] == MARK, "bad XP3 mark"
        self.base = 0
        self.files = []   # list of dicts: name, org_size, arc_size, hash, segments
        # index is a CHAIN: I64LE ofs at 'pos' -> block {flag, sizes, data} ->
        # next I64LE immediately after the block's data (while CONTINUE bit set)
        pos = 11
        while True:
            index_ofs = i64(d, pos); pos += 8
            flag = d[index_ofs]
            p = index_ofs + 1
            method = flag & 7
            if method == 1:
                csize = i64(d, p); p += 8
                rsize = i64(d, p); p += 8
                idx = zlib.decompress(d[p:p+csize])
                assert len(idx) == rsize
                pos_after = p + csize
            elif method == 0:
                rsize = i64(d, p); p += 8
                idx = d[p:p+rsize]
                pos_after = p + rsize
            else:
                raise ValueError("bad index flag")
            self._parse_index(idx)
            if not (flag & 0x80):
                break
            pos = pos_after

    def _parse_index(self, idx):
        ch_start, ch_size = 0, len(idx)
        while True:
            r = find_chunk(idx, b'File', ch_start, ch_size)
            if not r: break
            fstart, fsize = r
            # info
            r = find_chunk(idx, b'info', fstart, fsize)
            assert r, "no info chunk"
            istart, isize = r
            flags = i32(idx, istart)
            org_size = i64(idx, istart+4)
            arc_size = i64(idx, istart+12)
            nlen = i16(idx, istart+20)
            name = idx[istart+22:istart+22+nlen*2].decode('utf-16-le')
            # segm
            r = find_chunk(idx, b'segm', fstart, fsize)
            assert r, "no segm chunk"
            sstart, ssize = r
            nseg = ssize // 28
            segs = []
            for i in range(nseg):
                o = sstart + i*28
                sflags = i32(idx, o)
                s_start = i64(idx, o+4)
                s_org = i64(idx, o+12)
                s_arc = i64(idx, o+20)
                segs.append((sflags & 7, s_start, s_org, s_arc))
            # aldr
            r = find_chunk(idx, b'adlr', fstart, fsize)
            assert r, "no aldr chunk"
            astart, asize = r
            h = i32(idx, astart)
            self.files.append(dict(name=name, org_size=org_size, arc_size=arc_size,
                                   hash=h, flags=flags, segments=segs))
            ch_start = fstart + fsize
            ch_size = len(idx) - ch_start

    def extract_file(self, f):
        out = bytearray()
        for method, start, org, arc in f['segments']:
            chunk = self.data[start:start+arc]
            if len(chunk) < arc:
                raise ValueError("segment truncated")
            if method == 1:
                out += zlib.decompress(chunk)
            else:
                out += chunk
        assert len(out) == f['org_size'], (f['name'], len(out), f['org_size'])
        return bytes(out)

def extract_all(xp3_path, out_dir):
    arc = Xp3Archive(xp3_path)
    os.makedirs(out_dir, exist_ok=True)
    manifest = []
    for f in arc.files:
        data = arc.extract_file(f)
        rel = f['name'].replace('/', os.sep)
        # guard against path traversal / absolute names
        if os.path.isabs(rel) or '..' in rel.split(os.sep):
            print("SKIP (unsafe name):", f['name']); continue
        dest = os.path.join(out_dir, rel)
        try:
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with open(dest, 'wb') as fh:
                fh.write(data)
        except OSError as e:
            print(f"SKIP ({e}): {f['name'][:60]!r}...")
            continue
        manifest.append((f['name'], f['org_size'], f['arc_size']))
    return arc, manifest

if __name__ == '__main__':
    src = sys.argv[1] if len(sys.argv) > 1 else r'C:\Users\User\Desktop\Games\tenshi_chijo\game\data.xp3'
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(src), 'extracted')
    arc, manifest = extract_all(src, out)
    print(f"== {src}: {len(manifest)} files ==")
    for name, org, arcz in sorted(manifest):
        print(f"{org:>12}  {arcz:>12}  {name}")
