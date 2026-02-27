"""
Quick script to inspect MP4 file for chapter metadata (chpl atom and related).
Uses only Python stdlib to parse MP4 atom structure.
"""
import struct
import sys
from pathlib import Path


def read_atoms(f, path="", depth=0):
    """Recursively read MP4 atoms and yield (path, type, size, content_start)."""
    while True:
        header = f.read(8)
        if len(header) < 8:
            break
        size, atype = struct.unpack(">I4s", header)
        atype = atype.decode("latin-1")
        if size == 0:
            size = max(8, 2**31)
        if size == 1:
            ext = f.read(8)
            if len(ext) < 8:
                break
            size = struct.unpack(">Q", ext)[0]
        content_start = f.tell()
        yield (path + "/" + atype, atype, size, content_start)
        if atype in ("moov", "trak", "mdia", "minf", "stbl", "udta", "meta", "ilst", "dinf", "edts"):
            yield from read_atoms(f, path + "/" + atype, depth + 1)
            f.seek(content_start + size - 8)
        else:
            f.seek(content_start + size - 8)


def parse_chpl(f, size):
    """Parse Apple chapter list atom (chpl) content."""
    data = f.read(min(size, 4))
    if len(data) < 4:
        return []
    count_data = f.read(1)
    if not count_data:
        return []
    count = ord(count_data)
    chapters = []
    for _ in range(count):
        entry = f.read(8)
        if len(entry) < 8:
            break
        duration_ms = struct.unpack(">Q", entry)[0]
        name_bytes = []
        while True:
            b = f.read(1)
            if not b or b == b"\x00":
                break
            name_bytes.append(b[0])
        chapters.append((duration_ms, bytes(name_bytes).decode("utf-8", errors="replace")))
    return chapters


def main():
    path = Path(__file__).parent / "20260225-113306-F-Alakazam-line-postgame.mp4"
    if len(sys.argv) > 1:
        path = Path(sys.argv[1])
    if not path.exists():
        print(f"File not found: {path}")
        sys.exit(1)

    print(f"Analyzing: {path}\n")
    print("--- All metadata-related atoms ---")

    with open(path, "rb") as f:
        for atom_path, atype, size, content_start in read_atoms(f):
            if atype in ("udta", "meta", "chpl", "ilst", "nm ") or "meta" in atom_path or "udta" in atom_path:
                print(f"  {atom_path}  type={atype}  size={size}  content_start={content_start}")

    print("\n--- Chapter list (chpl) search ---")
    with open(path, "rb") as f:
        while True:
            header = f.read(8)
            if len(header) < 8:
                break
            size, atype = struct.unpack(">I4s", header)
            atype = atype.decode("latin-1")
            if size == 0:
                break
            if size == 1:
                size = struct.unpack(">Q", f.read(8))[0]
            content_start = f.tell()
            if atype == "chpl":
                print(f"Found 'chpl' atom at offset {content_start - 8}, size={size}")
                chapters = parse_chpl(f, size - 8)
                for i, (dur_ms, name) in enumerate(chapters, 1):
                    sec = dur_ms / 1000.0
                    print(f"  Chapter {i}: {sec:.2f}s - {name!r}")
                f.seek(content_start + size - 8)
                continue
            if atype not in ("moov", "trak", "mdia", "minf", "stbl", "udta", "meta", "ilst", "dinf", "edts"):
                f.seek(content_start + size - 8)
                continue
            f.seek(content_start + size - 8)

    print("\n--- Raw scan for 'chpl' signature ---")
    with open(path, "rb") as f:
        data = f.read()
    idx = 0
    found = False
    while True:
        i = data.find(b"chpl", idx)
        if i == -1:
            break
        atom_start = i - 4
        if atom_start >= 0:
            size = struct.unpack(">I", data[atom_start : atom_start + 4])[0]
            print(f"  'chpl' at byte offset {i} (atom size at {atom_start}, size={size})")
            found = True
        idx = i + 1
    if not found:
        print("  No 'chpl' atom found in file.")

    print("\nDone.")


if __name__ == "__main__":
    main()
