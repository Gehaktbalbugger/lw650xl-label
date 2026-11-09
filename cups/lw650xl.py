#!/usr/bin/env python3
"""lw650xl - CUPS filter: CUPS raster -> TSPL for the LW650XL PRO (Aimo 650).

Filter chain (installed via install.sh):
  application/pdf -> cgpdftoraster (system) -> lw650xl (this filter)
  lw650xl emits application/vnd.cups-raw, which the CUPS socket backend
  sends to the printer at port 9100.

Input raster: Apple cgpdftoraster "RaS3" format (decoded empirically):
  - magic bytes 33 53 61 52 ("3SaR" as stored)
  - page header is exactly 1800 bytes
  - u32 @0x118 = horizontal DPI, u32 @0x11C = vertical DPI
  - u32 @0x178 = pixel width W, u32 @0x17C = pixel height H
  - pixel data: W*H bytes directly after the header, 8-bit gray,
    0 = black (print), 255 = white, rows UNPADDED (W bytes each)

Output: TSPL, matching what the vendor app (Labellife) sends to this
printer. All of this was verified on the physical printer:

  - BITMAP mode 0 = UNCOMPRESSED. Mode 3 (LZO) is silently swallowed by
    this firmware; mode 4 is the vendor's internal LZO variant. Mode 0
    works and needs no compression library.
  - BITMAP syntax is "BITMAP x,y,width,height,mode," with the binary
    payload immediately after the comma: no length field, no CRLF.
  - Bit 1 = WHITE, bit 0 = printed (black) dot. Rows are packed MSB-first
    and padded to a byte boundary.
  - The bitmap is mapped 1:1 onto the 300 dpi print head (1280 dots wide,
    ~108 mm). A 57 mm label only covers the left part of the head.
  - The label's top edge sits TOP_OFFSET_DOTS below the bitmap origin and
    its left edge is LEFT_MARGIN_DOTS left of bitmap x=0 (measured with a
    ruler print: printed window = x 2..638, y 60..430).
  - "SIZE" is the label PITCH (label + gap/liner), not the label height:
    the vendor app uses SIZE 57 mm,38.6 mm with GAP 3 mm for the AM11354
    57x32 mm label. Telling the printer a shorter pitch makes it drift.
"""
import struct
import sys

# ---------------------------------------------------- printer geometry ----
HEAD_DOTS = 1280          # 300 dpi head, 1280 dots ~= 108 mm
TOP_OFFSET_DOTS = 60      # label top edge below bitmap origin (5.1 mm)
LEFT_MARGIN_DOTS = 24     # 2 mm of the label lies left of bitmap x=0
RIGHT_SAFETY_DOTS = 9     # keep clear of the right label edge
BOTTOM_SAFETY_DOTS = 8    # keep clear of the bottom label edge
DOTS_PER_MM = 300.0 / 25.4

# Media with a known label pitch (SIZE height). The page size comes from
# the PPD; the pitch is what the printer needs to feed correctly.
MEDIA = {
    "LW_57x32": {"pitch": 38.6, "gap": 3.0},   # AM11354 57 x 32 mm
}
DEFAULT_MEDIA = "LW_57x32"


# ---------------------------------------------------------------- raster ---
def read_raster(input_bytes):
    """Yield (dpi_x, dpi_y, width_px, height_px, gray_bytes) per page."""
    pos, n = 0, len(input_bytes)
    MAGIC = b"3SaR"
    while pos < n:
        if pos + 1800 > n:
            return  # trailing partial block (e.g. trailing padding bytes)
        hdr = input_bytes[pos:pos + 1800]
        if hdr[:4] != MAGIC:
            raise ValueError(
                f"bad raster magic at offset {pos}: {hdr[:4]!r} "
                "(expected RaS3 from cgpdftoraster)")
        dpi_x, dpi_y = struct.unpack("<II", hdr[0x118:0x120])
        w, h = struct.unpack("<II", hdr[0x178:0x180])
        if not (0 < w <= 20000 and 0 < h <= 20000):
            raise ValueError(f"implausible page size {w}x{h} @ {pos}")
        data_start, data_len = pos + 1800, w * h
        if data_start + data_len > n:
            raise ValueError(
                f"truncated raster page: need {data_len} bytes at {data_start}, "
                f"have {n - data_start}")
        yield dpi_x, dpi_y, w, h, input_bytes[data_start:data_start + data_len]
        pos = data_start + data_len


# -------------------------------------------------------------- geometry ---
def content_box(w_mm, h_mm):
    """Printable area in bitmap dots: (x, y, width, height)."""
    cw = int(round(w_mm * DOTS_PER_MM)) - LEFT_MARGIN_DOTS - RIGHT_SAFETY_DOTS
    ch = int(round(h_mm * DOTS_PER_MM)) - BOTTOM_SAFETY_DOTS
    cw = max(1, min(cw, HEAD_DOTS))
    ch = max(1, ch)
    return 0, TOP_OFFSET_DOTS, cw, ch


def scale_to_box(gray, w, h, box_w, box_h):
    """Area-average downscale of 8-bit gray to box_w x box_h.

    Returns a bytearray with 1 = dark pixel. Averaging (instead of nearest
    neighbour) keeps thin text from disappearing when a large page is
    shrunk onto a small label.
    """
    dark = bytearray(box_w * box_h)
    if w == box_w and h == box_h:
        for i, g in enumerate(gray):
            if g <= 127:
                dark[i] = 1
        return dark

    xr = []
    for tx in range(box_w):
        x0 = tx * w // box_w
        x1 = max(x0 + 1, (tx + 1) * w // box_w)
        xr.append((x0, x1))

    for ty in range(box_h):
        y0 = ty * h // box_h
        y1 = max(y0 + 1, (ty + 1) * h // box_h)
        rows = gray[y0 * w:y1 * w]
        out = ty * box_w
        for tx, (x0, x1) in enumerate(xr):
            total = 0
            count = 0
            for r in range(0, len(rows), w):
                total += sum(rows[r + x0:r + x1])
                count += x1 - x0
            if total * 2 <= count * 255:      # average <= 127.5 -> dark
                dark[out + tx] = 1
    return dark


def pack_canvas(dark, box_w, box_h, ox, oy, target_h):
    """Compose the dark pixels into a white 1-bpp canvas (bit 1 = white).

    The printer anchors the bitmap at its BOTTOM edge, so the bitmap must
    always be padded to the full feed height (target_h). A shorter bitmap
    shifts the whole image upwards.
    """
    canvas_h = max(oy + box_h, target_h)
    bpr = (HEAD_DOTS + 7) // 8
    out = bytearray(b"\xff" * (bpr * canvas_h))
    for y in range(box_h):
        base = bpr * (oy + y)
        row = dark[y * box_w:(y + 1) * box_w]
        for x in range(box_w):
            if row[x]:
                px = ox + x
                out[base + (px >> 3)] &= ~(0x80 >> (px & 7))
    return bpr, canvas_h, bytes(out)


# ------------------------------------------------------------------ TSPL ---
def num(v):
    return f"{v:g}"


def parse_options(s):
    opts = {}
    for tok in (s or "").split():
        k, _, v = tok.partition("=")
        opts[k] = v
    return opts


def media_geometry(opts, w_mm, h_mm):
    """(label_w_mm, label_h_mm, pitch_mm, gap_mm) for this job.

    The media name (e.g. "LW_57x32") is authoritative: it describes the
    label that is physically loaded. The raster page size is only a
    fallback when the media is unknown.
    """
    name = opts.get("media", "")
    spec = MEDIA.get(name)
    size_w, size_h = w_mm, h_mm
    if name.startswith("LW_"):
        try:
            a, _, b = name[3:].partition("x")
            size_w, size_h = float(a), float(b)
        except ValueError:
            pass
    pitch = float(opts.get("lw-pitch", spec["pitch"] if spec else size_h))
    gap = float(opts.get("lw-gap", spec["gap"] if spec else 3.0))
    return size_w, size_h, pitch, gap


def convert(input_bytes, opts=None):
    """Full raster -> TSPL payload conversion."""
    opts = opts or {}
    density = int(opts.get("lw-density", 15))
    speed = int(opts.get("lw-speed", 1))

    out = bytearray(b"\r\n")  # clear any stale partial line at the printer
    pages = 0
    for dpi_x, dpi_y, w, h, gray in read_raster(input_bytes):
        w_mm = w * 25.4 / dpi_x
        h_mm = h * 25.4 / dpi_y
        size_w, size_h, pitch, gap = media_geometry(opts, w_mm, h_mm)
        ox, oy, cw, ch = content_box(size_w, size_h)
        dark = scale_to_box(gray, w, h, cw, ch)
        # The vendor app sends 444 rows for a 38.6 mm pitch (456 dots), i.e.
        # 12 dots of padding that end up in the gap. Match that exactly.
        target_h = int(round(pitch * DOTS_PER_MM)) - 12
        bpr, canvas_h, bits = pack_canvas(dark, cw, ch, ox, oy, target_h)

        if pages == 0:
            out += (f"DENSITY {density}\r\n"
                    f"SPEED {speed}\r\n"
                    "REFERENCE 0,0\r\n"
                    "OFFSET 0 mm\r\n"
                    f"SIZE {num(size_w)} mm,{num(pitch)} mm\r\n"
                    f"GAP {num(gap)} mm,0 mm\r\n"
                    "DIRECTION 0,0\r\n"
                    "CLS\r\n").encode("ascii")
        else:
            out += b"CLS\r\n"
        pages += 1
        # Mode 0 (uncompressed), no length field, no CRLF before the data.
        out += (f"BITMAP 0,0,{bpr},{canvas_h},0,").encode("ascii")
        out += bits
        out += b"\r\nPRINT 1,1\r\n"
    if not out.strip():
        raise ValueError("no raster pages found in input")
    return bytes(out)


def main(argv):
    if len(argv) < 6:
        sys.stderr.write(
            "Usage: filter job-id user title copies options [file]\n"
            "(stdin is read when no file argument is given)\n")
        return 1
    opts = parse_options(argv[5])
    if len(argv) > 6:
        with open(argv[6], "rb") as f:
            data = f.read()
    else:
        data = sys.stdin.buffer.read()
    try:
        payload = convert(data, opts)
    except Exception as e:
        sys.stderr.write(f"lw650xl: {e}\n")
        return 1
    sys.stdout.buffer.write(payload)
    sys.stdout.buffer.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
