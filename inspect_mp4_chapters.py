"""Inspect MP4 for chapter metadata that DaVinci Resolve might read."""
import struct
import sys
from pathlib import Path

def read_box(data, offset, end):
    """Yield (offset, size, type, content_start) for each box."""
    while offset + 8 <= end:
        size, atype = struct.unpack(">I4s", data[offset:offset+8])
        atype = atype.decode("latin-1")
        if size == 0:
            size = end - offset
        elif size == 1 and offset + 16 <= end:
            size = struct.unpack(">Q", data[offset+8:offset+16])[0]
        content_start = offset + 8
        if atype == "meta":
            content_start += 4  # fullbox version+flags
        yield (offset, size, atype, content_start)
        offset += size

def main():
    path = Path(__file__).parent / "20260225-113306-F-Alakazam-line-postgame.mp4"
    if len(sys.argv) > 1:
        path = Path(sys.argv[1])
    data = path.read_bytes()

    # 1) Search for 'chapter' in raw file
    print("=== Search for 'chapter' / 'Chapter' in file ===\n")
    for needle in [b"chapter", b"Chapter", b"CHAPTER"]:
        idx = 0
        while True:
            i = data.find(needle, idx)
            if i == -1:
                break
            start = max(0, i - 16)
            end = min(len(data), i + len(needle) + 24)
            ctx = data[start:end]
            print(f"  offset {i}: ... {ctx!r} ...")
            idx = i + 1

    # 2) Find moov and then udta (user data) - chapters often in moov/udta
    print("\n=== moov/udta structure (top-level user data) ===\n")
    i = 0
    moov_start = None
    while i < min(len(data), 10 * 1024 * 1024):
        if i + 8 > len(data):
            break
        size, atype = struct.unpack(">I4s", data[i:i+8])
        atype = atype.decode("latin-1")
        if atype == "moov":
            moov_start = i
            break
        if size < 8:
            break
        if size == 1 and i + 16 <= len(data):
            size = struct.unpack(">Q", data[i+8:i+16])[0]
        i += size

    if moov_start is not None:
        moov_size = struct.unpack(">I", data[moov_start:moov_start+4])[0]
        if moov_size == 1:
            moov_size = struct.unpack(">Q", data[moov_start+8:moov_start+16])[0]
        moov_end = moov_start + moov_size
        for off, sz, typ, cstart in read_box(data, moov_start + 8, moov_end):
            if typ == "udta":
                print(f"  udta at offset {off}, size={sz}")
                for o2, s2, t2, c2 in read_box(data, cstart, off + sz):
                    print(f"    {t2} size={s2}")
                    if t2 == "meta":
                        # meta content: version+flags already skipped in c2
                        for o3, s3, t3, c3 in read_box(data, c2, off + sz):
                            if o3 >= cstart + (sz - 8):
                                break
                            print(f"      {t3} size={s3}")
                            if t3 == "ilst":
                                # item list - could contain chapter keys
                                ilst_end = o3 + s3
                                pos = c3
                                while pos + 8 <= ilst_end:
                                    try:
                                        size, atype = struct.unpack(">I4s", data[pos:pos+8])
                                        atype = atype.decode("latin-1")
                                        print(f"        item: {atype} size={size}")
                                        pos += size
                                    except Exception:
                                        break
                    if t2 == "chpl":
                        print(f"    CHPL (chapters) size={s2}")

    # 3) Scan entire file for any 'chpl' with relaxed size
    print("\n=== All 'chpl' occurrences (any size) ===\n")
    idx = 0
    while True:
        i = data.find(b"chpl", idx)
        if i == -1:
            break
        if i >= 4:
            size = struct.unpack(">I", data[i-4:i])[0]
            print(f"  chpl at type offset {i}, preceding size field = {size}")
        idx = i + 1

    # 4) List tracks: look for text or metadata track (chapters as text track)
    print("\n=== Track handler types (look for text/meta) ===\n")
    if moov_start is not None:
        pos = moov_start + 8
        while pos < moov_end - 8:
            size, atype = struct.unpack(">I4s", data[pos:pos+8])
            atype = atype.decode("latin-1")
            if atype == "trak":
                # find mdia/hdlr in this trak
                trak_end = pos + size
                p = pos + 8
                while p < trak_end - 8:
                    s, t = struct.unpack(">I4s", data[p:p+8])
                    t = t.decode("latin-1")
                    if t == "mdia":
                        # in mdia, find hdlr
                        mdia_end = p + s
                        q = p + 8
                        while q < mdia_end - 24:
                            sq, tq = struct.unpack(">I4s", data[q:q+8])
                            tq = tq.decode("latin-1")
                            if tq == "hdlr":
                                # hdlr: version(1)+flags(3)+pre_defined(4)+handler_type(4)+...
                                handler_type = data[q+16:q+20].decode("latin-1")
                                name_start = q + 32  # skip to name (null-terminated)
                                name_end = data.find(b"\x00", name_start, min(name_start + 256, mdia_end))
                                name = data[name_start:name_end].decode("utf-8", errors="replace")
                                print(f"  trak: handler_type={handler_type!r} name={name!r}")
                                break
                            q += sq if sq >= 8 else 8
                        break
                    p += s if s >= 8 else 8
            pos += size if size >= 8 else 8

    print("\nDone.")

if __name__ == "__main__":
    main()
