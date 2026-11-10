#!/usr/bin/env python3
"""lw650xl - CUPS filter: CUPS raster -> TSPL for the LW650XL PRO (Aimo 650).

Filter chain (installed via install.sh):
  application/pdf -> cgpdftoraster (system) -> lw650xl (this filter)
  lw650xl emits application/vnd.cups-raw, which the CUPS socket backend
  sends to the printer at port 9100.

Input raster: Apple cgpdftoraster "RaS3" format (decoded empirically):
  - 4-byte sync word 33 53 61 52 ("3SaR" as stored), ONLY before page 1
  - page header is 1796 bytes (so page 1's header ends at file offset 1800)
  - header-relative: u32 @0x114 = horizontal DPI, @0x118 = vertical DPI,
    u32 @0x174 = pixel width W, @0x178 = pixel height H
  - pixel data: W*H bytes directly after the header, 8-bit gray,
    0 = black (print), 255 = white, rows UNPADDED (W bytes each)
  - every next page repeats header + data WITHOUT the sync word; assuming
    1800 bytes per page desynchronises the stream from page 2 onwards

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
import collections
import os
import re
import struct
import sys

# ---------------------------------------------------- printer geometry ----
HEAD_DOTS = 1280          # 300 dpi head, 1280 dots ~= 108 mm
TOP_OFFSET_DOTS = 60      # label top edge below bitmap origin (5.1 mm)
LEFT_MARGIN_DOTS = 24     # 2 mm of the label lies left of bitmap x=0
RIGHT_SAFETY_DOTS = 9     # keep clear of the right label edge
BOTTOM_SAFETY_DOTS = 8    # keep clear of the bottom label edge
DOTS_PER_MM = 300.0 / 25.4

# Defaults, measured on the AM11354 57x32 roll. Rolls that sit differently
# in the printer (a narrow 36 mm roll sits ~1 mm further left, and a tall
# label starts higher because the bitmap is anchored at its bottom) override
# these per size with left= / top= in the PPD's lw-media line.
DEFAULT_LEFT_MM = LEFT_MARGIN_DOTS / DOTS_PER_MM     # ~2.0 mm dead zone
DEFAULT_TOP_MM = TOP_OFFSET_DOTS / DOTS_PER_MM       # ~5.1 mm below origin
DEFAULT_BOTTOM_MM = BOTTOM_SAFETY_DOTS / DOTS_PER_MM  # ~0.7 mm shy of the edge
DEFAULT_RIGHT_MM = RIGHT_SAFETY_DOTS / DOTS_PER_MM     # ~0.8 mm shy of the edge

# Media with a known label pitch (SIZE height). The page size comes from
# the PPD; the pitch is what the printer needs to feed correctly, and
# voffset moves the print down the label (see content_box).
MEDIA = {
    # AM11354 57 x 32 mm, liggend; 2 mm dode zone links, 5,1 mm tot de bovenrand
    "LW_57x32": {"pitch": 38.6, "gap": 3.0, "voffset": 0.34},
    # AM99012 / Dymo S0722400 36 x 89 mm, staand op de rol: smaller en lager
    # 3 mm of the label hangs past the head's left end and cannot be printed,
    # so the right side is trimmed to the same 3 mm to keep the print centred.
    "LW_36x89": {"pitch": 93.0, "gap": 4.0, "left": 3.0, "right": 3.0,
                 "top": -0.5, "bottom": 1.0},
}
DEFAULT_MEDIA = "LW_57x32"

# Sizes added with ./add-size.sh carry their geometry as PPD comments:
#   *% lw-media LW_76x51 pitch=53.5 gap=3 voffset=1
# CUPS keeps PPD comments intact (checked against the installed PPD) and
# hands the PPD to filters through the PPD env var, so the PPD is the single
# place where a size is defined. MEDIA above only stays as a fallback.
GEOMETRY_KEYS = ("pitch", "gap", "gapoff", "voffset", "left", "right", "top",
              "bottom", "rows", "rotate", "sense", "xoffset")
SENSORS = ("sense",)

Geometry = collections.namedtuple(
    "Geometry", "size_w size_h pitch gap gapoff voffset left right top bottom"
                 " rows rotate sense xoffset")

PPD_PATHS = (
    os.environ.get("PPD"),
    "/etc/cups/ppd/LW650XL_Labels.ppd",
)
_LW_MEDIA = re.compile(r"^\*%\s*lw-media\s+(\S+)(.*)$", re.M)


def load_ppd_media(paths=PPD_PATHS):
    """Built-in MEDIA merged with the size lines found in the PPD."""
    media = dict(MEDIA)
    for path in paths:
        if not path or not os.access(path, os.R_OK):
            continue
        try:
            with open(path, "r", errors="replace") as f:
                text = f.read()
        except OSError:
            continue
        for m in _LW_MEDIA.finditer(text):
            spec = {}
            for tok in m.group(2).split():
                key, _, value = tok.partition("=")
                if key not in GEOMETRY_KEYS:
                    continue
                if key in SENSORS:            # words, not numbers
                    spec[key] = value
                    continue
                try:
                    spec[key] = float(value)
                except ValueError:
                    pass
            spec = {k: v for k, v in spec.items() if k in GEOMETRY_KEYS}
            if spec:
                entry = dict(MEDIA.get(m.group(1), {}))
                entry.update(spec)
                media[m.group(1)] = entry
        break
    return media


_TABLE = None


def media_table():
    global _TABLE
    if _TABLE is None:
        _TABLE = load_ppd_media()
    return _TABLE


# ---------------------------------------------------------------- raster ---
# CUPS raster v3 layout (decoded from real cgpdftoraster output):
#   [4-byte sync "3SaR"] [1796-byte page header] [W*H bytes of 8-bit gray]
#   [1796-byte page header] [W*H bytes] ...
# The sync word appears ONLY in front of the first page header; later pages
# have the bare 1796-byte header. Field offsets are header-relative:
#   u32 @0x114 / @0x118 = horizontal / vertical DPI
#   u32 @0x174 / @0x178 = pixel width W / pixel height H
HEADER_BYTES = 1796
MAGIC = b"3SaR"


def read_raster(input_bytes):
    """Yield (dpi_x, dpi_y, width_px, height_px, gray_bytes) per page."""
    pos, n = 0, len(input_bytes)
    if input_bytes[:4] != MAGIC:
        raise ValueError(
            f"bad raster magic at offset 0: {input_bytes[:4]!r} "
            "(expected RaS3 from cgpdftoraster)")
    pos = 4
    while pos < n:
        if input_bytes[pos:pos + 4] == MAGIC:      # some rasters repeat it
            pos += 4
        if pos + HEADER_BYTES > n:
            return  # trailing padding bytes
        hdr = input_bytes[pos:pos + HEADER_BYTES]
        dpi_x, dpi_y = struct.unpack("<II", hdr[0x114:0x11C])
        w, h = struct.unpack("<II", hdr[0x174:0x17C])
        if not (0 < w <= 20000 and 0 < h <= 20000):
            raise ValueError(f"implausible page size {w}x{h} @ {pos}")
        data_start, data_len = pos + HEADER_BYTES, w * h
        if data_start + data_len > n:
            raise ValueError(
                f"truncated raster page: need {data_len} bytes at {data_start}, "
                f"have {n - data_start}")
        yield dpi_x, dpi_y, w, h, input_bytes[data_start:data_start + data_len]
        pos = data_start + data_len


# -------------------------------------------------------------- geometry ---
def canvas_rows(geom):
    """Bitmap height in dots: pinned `rows`, else the pitch minus 12 dots."""
    if geom.rows:
        return int(geom.rows)
    return int(round(geom.pitch * DOTS_PER_MM)) - 12


def print_window(geom, target_h):
    """Printable area in bitmap dots: (x, y, width, height).

    `left` is the dead zone between the label's left edge and bitmap x=0 (the
    head cannot reach it), `top` is where the label starts below the bitmap
    origin and `voffset` nudges the print down the label for centring. The
    height is clamped to the canvas: the printer anchors the bitmap at its
    bottom edge, so growing the window would move the whole print.
    """
    # De kop begint niet altijd op de linker rand van de liner: smalle rollen
    # liggen in dit pad soms 6 mm rechts van x=0. xoffset schuift het hele
    # printvlak daarnaartoe; left blijft de dode zone aan de linkerkant.
    ox = max(0, int(round(geom.xoffset * DOTS_PER_MM)))
    dead = int(round(geom.left * DOTS_PER_MM))
    cw = (int(round(geom.size_w * DOTS_PER_MM)) - dead
          - int(round(geom.right * DOTS_PER_MM)))
    ch = int(round(geom.size_h * DOTS_PER_MM)) - int(round(geom.bottom * DOTS_PER_MM))
    # Rows below zero cannot be printed: the head starts at x/y 0.
    oy = max(0, int(round((geom.top + geom.voffset) * DOTS_PER_MM)))
    cw = max(1, min(cw, HEAD_DOTS - ox))
    ch = max(1, min(ch, target_h - oy))
    return ox, oy, cw, ch


def rotate_cw(gray, w, h):
    """Rotate an 8-bit gray buffer 90 degrees clockwise -> (data, new_w, new_h).

    Word/macOS hands CUPS a PORTRAIT raster (orientation-requested=4 makes
    cgpdftoraster rotate the page) while a shipping label is landscape. The
    rotation direction was checked against the PDF itself: clockwise restores
    the original page.
    """
    out = bytearray(w * h)
    for y in range(h):
        out[h - 1 - y::h] = gray[y * w:(y + 1) * w]
    return out, h, w


def rotate_ccw(gray, w, h):
    """Rotate an 8-bit gray buffer 90 degrees counter-clockwise."""
    out = bytearray(w * h)
    for y in range(h):
        out[y::h] = gray[y * w:(y + 1) * w][::-1]
    return out, h, w


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
    """Split a CUPS options string into a dict.

    CUPS escapes spaces inside values as "\\ ", so split only on whitespace
    that is not preceded by a backslash; otherwise a title like
    "Microsoft\\ Word\\ -\\ Regel\\ 1.docx" would create bogus keys.
    """
    opts = {}
    for tok in re.split(r"(?<!\\)\s+", (s or "").strip()):
        k, _, v = tok.partition("=")
        if k:
            opts[k] = v.replace("\\ ", " ")
    return opts


def parse_size_name(name):
    """'LW_57x32' -> (57.0, 32.0) or None."""
    if not name.startswith("LW_"):
        return None
    a, _, b = name[3:].partition("x")
    try:
        return float(a), float(b)
    except ValueError:
        return None


def find_media(size_w, size_h, table=None):
    """Media whose label dimensions match (within 1 mm), for the pitch."""
    for name, spec in (media_table() if table is None else table).items():
        dims = parse_size_name(name)
        if dims and abs(dims[0] - size_w) <= 1.0 and abs(dims[1] - size_h) <= 1.0:
            return spec
    return None


def media_geometry(opts, w_mm, h_mm, table=None):
    """Geometry for this job: (size_w, size_h, pitch, gap, voffset, left, top).

    The label size is what the printer needs; the raster page size is only a
    fallback. Word/macOS does NOT send media=LW_57x32 but
    media=Custom.90.71x161.57 plus the PPD name in
    com.apple.print.PageToPaperMappingMediaName, so look for both.
    """
    table = media_table() if table is None else table
    name = opts.get("media", "")
    if parse_size_name(name) is None:
        name = opts.get("com.apple.print.PageToPaperMappingMediaName", "")
    dims = parse_size_name(name)
    if dims:
        size_w, size_h = dims
    else:
        # Unknown media: trust the page size, normalised so the long side is
        # the label width (a label is printed landscape on this printer).
        size_w, size_h = max(w_mm, h_mm), min(w_mm, h_mm)
    spec = table.get(name) or find_media(size_w, size_h, table)
    def pick(key, default):
        return float(opts.get("lw-" + key, spec.get(key, default) if spec else default))

    sense = opts.get("lw-sense") or (spec.get("sense") if spec else None) or "gap"
    sense = sense.lower()
    if sense not in ("gap", "bline"):
        sense = "gap"

    return Geometry(
        size_w=size_w,
        size_h=size_h,
        pitch=pick("pitch", size_h),
        gap=pick("gap", 3.0),
        voffset=pick("voffset", 0.0),
        left=pick("left", DEFAULT_LEFT_MM),
        right=pick("right", DEFAULT_RIGHT_MM),
        top=pick("top", DEFAULT_TOP_MM),
        bottom=pick("bottom", DEFAULT_BOTTOM_MM),
        # rows: canvas height in dots. 0 = derive from the pitch (pitch - 12,
        # the vendor app's padding on the 57x32 roll). Some rolls need the
        # exact bitmap height the vendor app sends, so it can be pinned.
        rows=pick("rows", 0.0),
        # rotate: 90 = clockwise, 270 = counter-clockwise, 0 = upright.
        # A square roll whose left edge is out of the head's reach gains more
        # by turning the page: the unreachable strip then falls along the feed
        # direction, where voffset/rows can centre it.
        rotate=int(pick("rotate", 0.0)) % 360,
        # sense: "gap" (doorzichtig ertussen) of "bline" (zwarte merken /
        # gaatjes in de liner). Rols met merken moeten BLINE krijgen, anders
        # zoekt de sensor een kloof die er niet is en begint elke beurt elders.
        sense=sense,
        xoffset=pick("xoffset", 0.0),
        gapoff=pick("gapoff", 0.0),
    )


def convert(input_bytes, opts=None, table=None):
    """Full raster -> TSPL conversion. `table` overrides the PPD size catalog."""
    opts = opts or {}
    table = media_table() if table is None else table
    density = int(opts.get("lw-density", 15))
    speed = int(opts.get("lw-speed", 1))

    out = bytearray(b"\r\n")  # clear any stale partial line at the printer
    pages = 0
    for dpi_x, dpi_y, w, h, gray in read_raster(input_bytes):
        w_mm = w * 25.4 / dpi_x
        h_mm = h * 25.4 / dpi_y
        geom = media_geometry(opts, w_mm, h_mm, table)
        # Match the page to the label: Word's portrait raster for a landscape
        # label (or the other way round) is rotated back to the label.
        if (w > h) != (geom.size_w > geom.size_h):
            gray, w, h = rotate_cw(gray, w, h)
        if geom.rotate == 90:
            gray, w, h = rotate_cw(gray, w, h)
        elif geom.rotate == 270:
            gray, w, h = rotate_ccw(gray, w, h)
        # The vendor app sends 444 rows for a 38.6 mm pitch (456 dots), i.e.
        # 12 dots of padding that end up in the gap; some rolls pin it in the
        # PPD instead (rows=), which wins.
        target_h = canvas_rows(geom)
        ox, oy, cw, ch = print_window(geom, target_h)
        dark = scale_to_box(gray, w, h, cw, ch)
        bpr, canvas_h, bits = pack_canvas(dark, cw, ch, ox, oy, target_h)

        if pages == 0:
            out += (f"DENSITY {density}\r\n"
                    f"SPEED {speed}\r\n"
                    "REFERENCE 0,0\r\n"
                    "OFFSET 0 mm\r\n"
                    f"SIZE {num(geom.size_w)} mm,{num(geom.pitch)} mm\r\n"
                    f"{geom.sense.upper()} {num(geom.gap)} mm,"
                    f"{num(geom.gapoff)} mm\r\n"
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
