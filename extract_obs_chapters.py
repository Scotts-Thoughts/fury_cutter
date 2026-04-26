"""
Extract chapter markers from an MP4 that uses OBS's "OBS Chapter Handler" metadata track.
DaVinci Resolve (and OBS) store chapters as a metadata track, not the Apple chpl atom.
"""
import struct
import sys
from pathlib import Path
from typing import Optional


def read_box(data, offset, end):
    """Yield (offset, size, type, content_start) for each box."""
    while offset + 8 <= end:
        size, atype = struct.unpack(">I4s", data[offset : offset + 8])
        atype = atype.decode("latin-1")
        if size == 0:
            size = end - offset
        elif size == 1 and offset + 16 <= end:
            size = struct.unpack(">Q", data[offset + 8 : offset + 16])[0]
        content_start = offset + 8
        yield (offset, size, atype, content_start)
        offset += size


def find_box(data, start, end, want_type):
    """Find first box of type want_type between start and end."""
    for off, size, typ, cstart in read_box(data, start, end):
        if typ == want_type:
            return off, size, cstart
    return None


def find_boxes(data, start, end, want_type):
    """Find all boxes of type want_type between start and end."""
    for off, size, typ, cstart in read_box(data, start, end):
        if typ == want_type:
            yield off, size, cstart


def get_timescale_and_duration_from_mdhd(data, mdhd_start, mdhd_size):
    """Parse mdhd fullbox; return (timescale, duration)."""
    content = mdhd_start + 8  # after size+type
    if content + 4 > mdhd_start + mdhd_size:
        return None
    version = data[content]
    content += 4  # version + flags
    if version == 0:
        # creation_time(4), modification_time(4), timescale(4), duration(4)
        if content + 16 > mdhd_start + mdhd_size:
            return None
        content += 8  # skip creation_time, modification_time
        timescale = struct.unpack(">I", data[content : content + 4])[0]
        duration = struct.unpack(">I", data[content + 4 : content + 8])[0]
    else:
        # version 1: creation_time(8), modification_time(8), timescale(4), duration(8)
        if content + 28 > mdhd_start + mdhd_size:
            return None
        content += 16  # skip creation_time, modification_time
        timescale = struct.unpack(">I", data[content : content + 4])[0]
        duration = struct.unpack(">Q", data[content + 4 : content + 12])[0]
    return (timescale, duration)


def parse_stts(data, stts_start, stts_size):
    """Return list of (sample_count, delta) from stts."""
    content = stts_start + 8 + 4  # size+type + version+flags
    entry_count = struct.unpack(">I", data[content : content + 4])[0]
    content += 4
    entries = []
    for _ in range(entry_count):
        if content + 8 > stts_start + stts_size:
            break
        count, delta = struct.unpack(">II", data[content : content + 8])
        entries.append((count, delta))
        content += 8
    return entries


def parse_stsc(data, stsc_start, stsc_size):
    """Return list of (first_chunk, samples_per_chunk, sample_desc_index)."""
    content = stsc_start + 8 + 4
    entry_count = struct.unpack(">I", data[content : content + 4])[0]
    content += 4
    entries = []
    for _ in range(entry_count):
        if content + 12 > stsc_start + stsc_size:
            break
        first, count, id = struct.unpack(">III", data[content : content + 12])
        entries.append((first, count, id))
        content += 12
    return entries


def parse_stsz(data, stsz_start, stsz_size):
    """Return list of sample sizes, or None if uniform."""
    content = stsz_start + 8 + 4  # version+flags
    sample_size = struct.unpack(">I", data[content : content + 4])[0]
    sample_count = struct.unpack(">I", data[content + 4 : content + 8])[0]
    content += 8
    if sample_size != 0:
        return ([sample_size] * sample_count,)
    sizes = []
    for _ in range(sample_count):
        if content + 4 > stsz_start + stsz_size:
            break
        sizes.append(struct.unpack(">I", data[content : content + 4])[0])
        content += 4
    return sizes


def parse_stco(data, stco_start, stco_size):
    """Return list of chunk offsets (32-bit)."""
    content = stco_start + 8 + 4
    entry_count = struct.unpack(">I", data[content : content + 4])[0]
    content += 4
    offsets = []
    for _ in range(entry_count):
        if content + 4 > stco_start + stco_size:
            break
        offsets.append(struct.unpack(">I", data[content : content + 4])[0])
        content += 4
    return offsets


def parse_co64(data, stco_start, stco_size):
    """Return list of chunk offsets (64-bit)."""
    content = stco_start + 8 + 4
    entry_count = struct.unpack(">I", data[content : content + 4])[0]
    content += 4
    offsets = []
    for _ in range(entry_count):
        if content + 8 > stco_start + stco_size:
            break
        offsets.append(struct.unpack(">Q", data[content : content + 8])[0])
        content += 8
    return offsets


def get_obs_chapters(path: Path) -> Optional[list[tuple[float, str]]]:
    """
    Load OBS chapter markers from an MP4 file.
    Returns list of (time_sec, chapter_name) or None if no OBS Chapter Handler track.
    """
    if not path.exists():
        return None
    try:
        data = path.read_bytes()
    except Exception:
        return None

    marker = b"OBS Chapter Handler"
    idx = data.find(marker)
    if idx == -1:
        return None

    hdlr_type_pos = data.rfind(b"hdlr", 0, idx)
    if hdlr_type_pos == -1:
        return None
    hdlr_start = hdlr_type_pos - 4
    hdlr_size = struct.unpack(">I", data[hdlr_start : hdlr_start + 4])[0]
    if hdlr_size == 1:
        hdlr_size = struct.unpack(">Q", data[hdlr_start + 8 : hdlr_start + 16])[0]
    trak_end = hdlr_start + hdlr_size

    pos = hdlr_start - 1
    trak_start = -1
    while pos >= 0:
        found = data.rfind(b"trak", 0, pos + 1)
        if found == -1:
            break
        trak_start = found - 4
        trak_size = struct.unpack(">I", data[trak_start : trak_start + 4])[0]
        if trak_size == 1 and trak_start + 16 <= len(data):
            trak_size = struct.unpack(">Q", data[trak_start + 8 : trak_start + 16])[0]
        trak_end = trak_start + trak_size
        if trak_start <= hdlr_start < trak_end:
            break
        pos = trak_start - 1
    if trak_start < 0 or not (trak_start <= hdlr_start < trak_end):
        return None

    mdia = find_box(data, trak_start + 8, trak_end, "mdia")
    if not mdia:
        return None
    mdia_off, mdia_size, mdia_c = mdia
    mdia_end = mdia_off + mdia_size
    mdhd = find_box(data, mdia_c, mdia_end, "mdhd")
    if not mdhd:
        return None
    mdhd_off, mdhd_size, _ = mdhd
    ts_dur = get_timescale_and_duration_from_mdhd(data, mdhd_off, mdhd_size)
    if not ts_dur:
        return None
    timescale, _duration = ts_dur

    minf = find_box(data, mdia_c, mdia_end, "minf")
    if not minf:
        return None
    minf_off, minf_size, minf_c = minf
    stbl = find_box(data, minf_c, minf_off + minf_size, "stbl")
    if not stbl:
        return None
    stbl_off, stbl_size, stbl_c = stbl
    stbl_end = stbl_off + stbl_size

    stts = find_box(data, stbl_c, stbl_end, "stts")
    stsc = find_box(data, stbl_c, stbl_end, "stsc")
    stsz = find_box(data, stbl_c, stbl_end, "stsz")
    stco = find_box(data, stbl_c, stbl_end, "stco")
    co64 = find_box(data, stbl_c, stbl_end, "co64")
    if not stts or not stsc or not stsz or not (stco or co64):
        return None

    stts_off, stts_sz, _ = stts
    stsc_off, stsc_sz, _ = stsc
    stsz_off, stsz_sz, _ = stsz

    stts_entries = parse_stts(data, stts_off, stts_sz)
    stsc_entries = parse_stsc(data, stsc_off, stsc_sz)
    sample_sizes = parse_stsz(data, stsz_off, stsz_sz)
    if stco:
        chunk_offsets = parse_stco(data, stco[0], stco[1])
    else:
        chunk_offsets = parse_co64(data, co64[0], co64[1])

    sample_count = len(sample_sizes)

    def samples_per_chunk(chunk_one_based):
        n = 1
        for first, count, _ in stsc_entries:
            if chunk_one_based >= first:
                n = count
        return n

    sample_offsets = []
    pos = 0
    for chunk_idx in range(len(chunk_offsets)):
        chunk_offset = chunk_offsets[chunk_idx]
        n = samples_per_chunk(chunk_idx + 1)
        for _ in range(n):
            if pos >= sample_count:
                break
            sample_offsets.append(chunk_offset)
            chunk_offset += sample_sizes[pos]
            pos += 1
    while len(sample_offsets) < sample_count and sample_sizes:
        prev = sample_offsets[-1] if sample_offsets else 0
        idx = len(sample_offsets)
        sample_offsets.append(prev + (sample_sizes[idx - 1] if idx > 0 else 0))

    t = 0
    sample_times = []
    for count, delta in stts_entries:
        for _ in range(count):
            sample_times.append(t)
            t += delta
    while len(sample_times) < sample_count:
        sample_times.append(sample_times[-1] + (stts_entries[-1][1] if stts_entries else 0))

    chapters = []
    for i in range(sample_count):
        offset = sample_offsets[i] if i < len(sample_offsets) else 0
        size = sample_sizes[i] if i < len(sample_sizes) else 0
        time_ticks = sample_times[i] if i < len(sample_times) else 0
        time_sec = time_ticks / timescale
        if offset + size <= len(data):
            raw = data[offset : offset + size]
            end = raw.find(b"\x00\x00\x00\x0c")
            if end == -1:
                end = raw.find(b"\x00")
            if end == -1:
                end = len(raw)
            part = raw[:end]
            # Chapter samples are length-prefixed: 2-byte big-endian length + UTF-8 text.
            text = None
            if len(part) >= 2:
                length = struct.unpack(">H", part[:2])[0]
                if 1 <= length <= len(part) - 2:
                    try:
                        candidate = part[2 : 2 + length].decode("utf-8")
                    except UnicodeDecodeError:
                        candidate = None
                    if candidate is not None and candidate.isprintable():
                        text = candidate
            if text is None:
                text = part.decode("utf-8", errors="replace").strip("\x00")
                if not text.isprintable() and len(text) >= 1 and ord(text[0]) < 0x20:
                    text = text[1:]
            chapters.append((time_sec, text))
        else:
            chapters.append((time_sec, "<unknown>"))
    return chapters


def main():
    path = Path(__file__).parent / "20260225-113306-F-Alakazam-line-postgame.mp4"
    if len(sys.argv) > 1:
        path = Path(sys.argv[1])
    if not path.exists():
        print(f"File not found: {path}", file=sys.stderr)
        sys.exit(1)
    chapters = get_obs_chapters(path)
    if not chapters:
        print("No 'OBS Chapter Handler' track found in this file.", file=sys.stderr)
        sys.exit(1)
    print(f"Chapters (OBS Chapter Handler track):\n")
    for time_sec, text in chapters:
        print(f"  {time_sec:.3f}s  {text!r}")
    print(f"\nTotal: {len(chapters)} chapter(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
