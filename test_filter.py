#!/usr/bin/env python3
"""Regression tests for the CUPS filter (cups/lw650xl.py).

No printer needed: the raster is synthesised exactly the way Apple's
cgpdftoraster writes it, and the TSPL output is checked and decoded back
into an image.

Covers the bugs that made a Word print job fail:
  - multi-page rasters: the 4-byte sync word appears ONLY before page 1,
    every page header is 1796 bytes (assuming 1800 desynchronises page 2)
  - Word sends media=Custom.90.71x161.57 and puts the PPD name in
    com.apple.print.PageToPaperMappingMediaName
  - Word's landscape label arrives as a PORTRAIT raster and must be rotated
    back clockwise

Run: python3 test_filter.py
"""
import importlib.util
import os
import re
import struct
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
FILTER_PATH = os.path.join(HERE, "cups", "lw650xl.py")

# Test table: the geometry the PPD would carry for the rolls we check.
TABLE = {
    "LW_57x32": {"pitch": 38.6, "gap": 3.0, "voffset": 0.34},
    "LW_36x89": {"pitch": 93.0, "gap": 4.0, "left": 3.0, "right": 3.0,
                 "top": -0.5, "bottom": 1.0},
    "LW_25x25": {"pitch": 33.97, "gap": 3.0, "rows": 356.0, "left": 1.0,
                 "right": 1.0, "top": 0.0, "voffset": 4.75, "bottom": 0.5,
                 "rotate": 270.0},
    "LW_76x51": {"pitch": 54.5, "gap": 3.0},
    "LW_30x15": {"pitch": 15.0, "gap": 0.0},
}
def fields(geo):
    """The geometry as a plain tuple, so the assertions stay readable."""
    return (geo.size_w, geo.size_h, geo.pitch, geo.gap, geo.voffset,
            geo.left, geo.right, geo.top, geo.bottom, geo.rows, geo.rotate)

HEADER_BYTES = 1796
MAGIC = b"3SaR"


def load_filter():
    spec = importlib.util.spec_from_file_location("lw650xl", FILTER_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def make_page(w, h, dpi=300, mark=None):
    """One raster page: 1796-byte header + W*H bytes of 8-bit gray.

    `mark` is a list of (x, y) dark pixels, used to check orientation.
    """
    hdr = bytearray(HEADER_BYTES)
    struct.pack_into("<II", hdr, 0x114, dpi, dpi)
    struct.pack_into("<II", hdr, 0x174, w, h)
    gray = bytearray(b"\xff" * (w * h))
    for (x, y) in (mark or []):
        gray[y * w + x] = 0
    return bytes(hdr) + bytes(gray)


def raster(*pages):
    return MAGIC + b"".join(pages)


def decode_bitmaps(payload):
    """Return [(width, height, bytes)] of every BITMAP in the job."""
    out = []
    for m in re.finditer(rb"BITMAP 0,0,(\d+),(\d+),(\d+),", payload):
        bpr, rows, mode = (int(m.group(i)) for i in (1, 2, 3))
        assert mode == 0, "BITMAP must be mode 0 (uncompressed)"
        body = payload[m.end():m.end() + bpr * rows]
        assert len(body) == bpr * rows, "truncated BITMAP payload"
        out.append((bpr * 8, rows, body))
    return out


def dark_pixels(width, rows, body):
    """Coordinates of printed dots (bit 0 = printed)."""
    pts = []
    for y in range(rows):
        row = body[y * (width // 8):(y + 1) * (width // 8)]
        for x in range(width):
            if not row[x >> 3] & (0x80 >> (x & 7)):
                pts.append((x, y))
    return pts


def check(name, cond):
    print(("  ok   " if cond else "  FAIL ") + name)
    return bool(cond)


def main():
    lw = load_filter()
    ok = True

    # --- 1. raster layout ---------------------------------------------------
    data = raster(make_page(60, 40), make_page(60, 40), make_page(60, 40))
    pages = list(lw.read_raster(data))
    ok &= check("3-page raster: 3 pages parsed", len(pages) == 3)
    ok &= check("3-page raster: sizes read", all(p[2:4] == (60, 40) for p in pages))
    ok &= check("3-page raster: no desynchronisation",
                all(p[4].count(0) == 0 for p in pages))

    # --- 2. options Word/macOS actually sends ------------------------------
    opts = lw.parse_options(
        r"ColorModel=Gray com.apple.print.PageToPaperMappingMediaName=LW_57x32 "
        r"media=Custom.90.71x161.57 orientation-requested=4 "
        r"PageSize=Custom.90x161 job-name=Microsoft\ Word\ -\ Regel\ 1.docx")
    ok &= check("job-name with escaped spaces kept whole",
                opts.get("job-name") == "Microsoft Word - Regel 1.docx")
    geo = lw.media_geometry(opts, 31.75, 56.81, TABLE)
    ok &= check("Custom media falls back to the PPD name: %r" % (fields(geo)[:5],),
                fields(geo)[:9] == (57.0, 32.0, 38.6, 3.0, 0.34,
                                    lw.DEFAULT_LEFT_MM, lw.DEFAULT_RIGHT_MM,
                                    lw.DEFAULT_TOP_MM, lw.DEFAULT_BOTTOM_MM))
    geo = lw.media_geometry(lw.parse_options("media=LW_36x89"), 36.0, 89.0, TABLE)
    ok &= check("standing roll keeps its own left/top: %r" % (fields(geo),),
                fields(geo)[:9] == (36.0, 89.0, 93.0, 4.0, 0.0, 3.0, 3.0, -0.5, 1.0))
    sq = lw.media_geometry(lw.parse_options("media=LW_25x25"), 25.0, 25.0, TABLE)
    ok &= check("square roll: rows and rotate come from the PPD",
                sq.rows == 356.0 and sq.rotate == 270)
    geo = lw.media_geometry(lw.parse_options("media=Custom.90.71x161.57"),
                            31.75, 56.81, TABLE)
    ok &= check("unknown media: long side becomes label width", geo[0] > geo[1])

    # --- 3. rotation --------------------------------------------------------
    # A mark in the top-left of the label: in the portrait raster it is in the
    # bottom-left, so after rotating clockwise it must return to the top-left.
    w_px, h_px = 375, 671
    blank = bytes([0xff] * (w_px * h_px))
    rotated, rw, rh = lw.rotate_cw(blank, w_px, h_px)
    ok &= check("rotate_cw swaps dimensions", (rw, rh) == (h_px, w_px))
    ok &= check("rotate_cw keeps the pixel count", len(rotated) == w_px * h_px)
    gray = bytearray(b"\xff" * (w_px * h_px))
    gray[(h_px - 20) * w_px + 5] = 0          # bottom-left of the portrait page
    rotated, rw, rh = lw.rotate_cw(bytes(gray), w_px, h_px)
    ok &= check("rotate_cw moves bottom-left to top-left",
                rotated[5 * rw + 19] == 0)

    # canvas height: pitch-12 unless the roll pins rows=
    gp = lw.media_geometry(lw.parse_options("media=LW_57x32"), 57.0, 32.0, TABLE)
    ok &= check("canvas_rows: pitch minus 12 dots",
                lw.canvas_rows(gp) == int(round(38.6 * lw.DOTS_PER_MM)) - 12)
    gs = lw.media_geometry(lw.parse_options("media=LW_25x25"), 25.0, 25.0, TABLE)
    ok &= check("canvas_rows: rows= from the PPD wins", lw.canvas_rows(gs) == 356)

    # rotate_ccw is the exact inverse of rotate_cw
    src = bytes(range(20))                       # 5 x 4 gray page
    cw_data, cW, cH = lw.rotate_cw(src, 5, 4)
    back, bW, bH = lw.rotate_ccw(cw_data, cW, cH)
    ok &= check("rotate_ccw undoes rotate_cw", back == src and (bW, bH) == (5, 4))

    # --- printable window per roll -----------------------------------------
    g57 = lw.media_geometry(lw.parse_options("media=LW_57x32"), 57.0, 32.0, TABLE)
    t57 = int(round(g57.pitch * lw.DOTS_PER_MM)) - 12          # 444 rows
    w57 = lw.print_window(g57, t57)
    ok &= check("57x32 window x 0..640, y starts at the offset",
                w57[0] == 0 and w57[2] == 640 and w57[3] == 370)
    ok &= check("57x32 voffset 0.34 mm = 4 dots lower", w57[1] == 64)

    g36 = lw.media_geometry(lw.parse_options("media=LW_36x89"), 36.0, 89.0, TABLE)
    t36 = int(round(g36.pitch * lw.DOTS_PER_MM)) - 12          # 1086 rows
    w36 = lw.print_window(g36, t36)
    # AM99012: label loops from -0.5 to 88.5 mm; rows below 0 cannot be printed
    label_top = int(round(g36.top * lw.DOTS_PER_MM))           # -6
    label_bot = label_top + int(round(89.0 * lw.DOTS_PER_MM))  # 1045
    # 3 mm hangs past the head on the west side, so the east side is trimmed
    # to the same 3 mm: the print ends up centred on the label.
    label_left, label_right = -35, -35 + int(round(36.0 * lw.DOTS_PER_MM))
    ok &= check("36x89: window centred, 30.1 mm wide (was 32.3)", w36[2] == 355)
    ok &= check("36x89: equal white west and east (%d/%d)"
                % (w36[0] - label_left, label_right - w36[0] - w36[2]),
                (w36[0] - label_left) == (label_right - w36[0] - w36[2]) == 35)
    ok &= check("36x89: print starts at row 0", w36[1] == 0)
    ok &= check("36x89: equal white above and below (%d/%d)"
                % (w36[1] - label_top, label_bot - w36[1] - w36[3]),
                w36[1] - label_top == label_bot - w36[1] - w36[3] == 6)

    # --- 4. full conversion, two pages -------------------------------------
    # Landscape 57x32 label: a dark pixel at (10, 70) in the page must end up
    # inside the print window at the same place.
    lw_opts = lw.parse_options("media=LW_57x32")
    payload = lw.convert(raster(make_page(673, 378, mark=[(10, 70)]),
                                make_page(673, 378, mark=[(600, 300)])),
                         lw_opts, TABLE)
    ok &= check("two pages -> two PRINT commands", payload.count(b"PRINT 1,1\r\n") == 2)
    ok &= check("header once: SIZE 57 mm,38.6 mm", payload.count(b"SIZE 57 mm,38.6 mm") == 1)
    ok &= check("header once: DENSITY/SPEED/CLS",
                payload.count(b"DENSITY 15") == 1 and payload.count(b"CLS") == 2)
    bits = decode_bitmaps(payload)
    ok &= check("bitmaps span the head at full feed height",
                all((w, h) == (1280, 444) for w, h, _ in bits))
    pts1 = dark_pixels(*bits[0])
    # voffset 1 mm moves the window down: y 72..442 instead of 60..430
    ok &= check("page 1 dot lands in the shifted print window: %r" % (pts1[:1],),
                pts1 and 0 <= pts1[0][0] <= 640 and 72 <= pts1[0][1] <= 442)
    pts2 = dark_pixels(*bits[1])
    ok &= check("page 2 keeps its own content", len(pts2) == 1 and pts2[0] > pts1[0])

    # portrait raster for a landscape label must be rotated back
    payload = lw.convert(raster(make_page(375, 671, mark=[(300, 20)])), lw_opts, TABLE)
    pts = dark_pixels(*decode_bitmaps(payload)[0])
    ok &= check("portrait page is rotated (single dot at %r)" % (pts[:1],),
                len(pts) == 1 and pts[0][0] > pts[0][1])

    # --- 6b. an explicit 0 must survive (top=0 is a measurement) ----------
    # Runs on a COPY of the PPD (via LW_PPD): a test must never rewrite the
    # working tree -- an earlier version of this check used `git checkout` and
    # silently discarded a roll that had just been measured.
    tmp_ppd = tempfile.mktemp(suffix=".ppd")
    with open("cups/lw650xl-labels.ppd", "rb") as src, open(tmp_ppd, "wb") as dst:
        dst.write(src.read())
    import subprocess
    code = subprocess.run(["./add-size.sh", "LW_10x10", "Test 10x10", "10", "10",
                           "--gap", "2", "--pitch", "12", "--top", "0",
                           "--voffset", "0"], capture_output=True, text=True,
                          env=dict(os.environ, LW_PPD=tmp_ppd)).returncode
    table = lw.load_ppd_media([tmp_ppd])
    ok &= check("add-size.sh: --top 0 written, not dropped",
                table.get("LW_10x10", {}).get("top") == 0.0
                and table["LW_10x10"].get("voffset") == 0.0)
    ok &= check("add-size.sh: exit 0", code == 0)
    os.path.exists(tmp_ppd) and os.unlink(tmp_ppd)

    # --- 6a. AM11353: de liner begint rechts van de kopstart --------------
    # Gemeten: liner x 6..36 mm, etiket A 7,5..20 mm, snijline 20 mm,
    # etiket B 20..32,5 mm. Labellife stuurt SIZE 25.6 mm,34 mm + GAP 3 mm
    # (37 mm voeding) met een bitmap van 354 regels.
    dpi = lw.DOTS_PER_MM
    tbl = dict(TABLE)
    tbl["LW_25x25"] = {"pitch": 34.0, "gap": 3.0, "rows": 354.0, "xoffset": 7.5,
                       "left": 0.0, "right": 0.0, "top": -0.5, "bottom": 0.7}
    gb = lw.media_geometry(lw.parse_options("media=LW_25x25"), 25.6, 25.0, tbl)
    tb = lw.canvas_rows(gb)
    bxo, byo, bw, bh = lw.print_window(gb, tb)
    ok &= check("AM11353: canvas 354 regels zoals de vendor", tb == 354)
    ok &= check("AM11353: xoffset -> blok x %.2f..%.2f mm" % (bxo/dpi, (bxo+bw)/dpi),
                abs(bxo/dpi - 7.5) < 0.1 and abs((bxo + bw)/dpi - 32.5) < 0.2)
    ok &= check("AM11353: snijlijn op x = 20 mm", abs((bxo + bw/2)/dpi - 20.0) < 0.1)
    # de vendor stuurt 25,6 mm: dat is het blok van 2 x 12,5 plus de snijrail.
    # Ons介质blok is het echte etiket: 25,0 mm.
    ok &= check("AM11353: blok 25,0 mm (twee keer 12,5)", abs(bw/dpi - 25.0) < 0.1)
    ok &= check("AM11353: y begint op rij 0 door negatieve top", byo == 0)

    # --- 7. size metadata lives in the PPD (written by add-size.sh) --------
    with tempfile.NamedTemporaryFile("w", suffix=".ppd", delete=False) as f:
        f.write('*PPD-Adobe: "4.3"\n'
                "*% lw-media LW_57x32 pitch=38.6 gap=3 voffset=1\n"
                "*% lw-media LW_76x51 pitch=54.5 gap=3\n"
                "*% lw-media LW_30x15 pitch=15 gap=0\n"
                "*% lw-media LW_36x89 pitch=93 gap=4 left=3 right=3 "
                "top=-0.5 bottom=1\n"
                "*End\n")
        tmp_ppd = f.name
    try:
        table = lw.load_ppd_media([tmp_ppd])
        ok &= check("PPD: built-in size kept", table["LW_57x32"]["pitch"] == 38.6)
        ok &= check("PPD: new size read",
                    table["LW_76x51"] == {"pitch": 54.5, "gap": 3.0})
        ok &= check("PPD: voffset read", table["LW_57x32"]["voffset"] == 1.0)
        # a PPD line only overrides the keys it carries
        ok &= check("PPD: left/top/bottom read",
                    table["LW_36x89"]["left"] == 3.0
                    and table["LW_36x89"]["right"] == 3.0
                    and table["LW_36x89"]["top"] == -0.5
                    and table["LW_36x89"]["bottom"] == 1.0
                    and table["LW_36x89"]["pitch"] == 93.0
                    and "voffset" not in table["LW_36x89"])
        geo = lw.media_geometry(lw.parse_options("media=LW_76x51"), 76.0, 51.0, table)
        ok &= check("PPD size drives SIZE/pitch: %r" % (geo,),
                    fields(geo)[:9] == (76.0, 51.0, 54.5, 3.0, 0.0,
                                   lw.DEFAULT_LEFT_MM, lw.DEFAULT_RIGHT_MM,
                                   lw.DEFAULT_TOP_MM, lw.DEFAULT_BOTTOM_MM))
        geo = lw.media_geometry(lw.parse_options("media=LW_30x15"), 30.0, 15.0, table)
        ok &= check("continuous stock: gap 0", geo[3] == 0.0)
        geo = lw.media_geometry(
            lw.parse_options("media=LW_76x51 lw-pitch=60 lw-gap=4"), 76.0, 51.0, table)
        ok &= check("-o lw-pitch overrides the PPD", geo[2] == 60.0 and geo[3] == 4.0)
        # a size known only by dimensions still finds its pitch by matching
        geo = lw.media_geometry(lw.parse_options("media=Custom.215x145"),
                                51.0, 76.0, table)
        ok &= check("unknown media falls back to the matching roll: %r" % (geo,),
                    fields(geo)[:9] == (76.0, 51.0, 54.5, 3.0, 0.0,
                                       lw.DEFAULT_LEFT_MM, lw.DEFAULT_RIGHT_MM,
                                       lw.DEFAULT_TOP_MM, lw.DEFAULT_BOTTOM_MM))
        geo = lw.media_geometry(
            lw.parse_options("media=LW_57x32 lw-voffset=0"), 57.0, 32.0, table)
        ok &= check("-o lw-voffset=0 disables the centring shift", geo.voffset == 0.0)
        geo = lw.media_geometry(
            lw.parse_options("media=LW_57x32 lw-left=4 lw-top=6"), 57.0, 32.0, table)
        ok &= check("-o lw-left / lw-top override the roll",
                    geo.left == 4.0 and geo.top == 6.0)
    finally:
        os.unlink(tmp_ppd)

    # --- 8. garbage in, error out ------------------------------------------
    try:
        lw.convert(b"not a raster at all", lw_opts)
        ok &= check("bad input raises", False)
    except ValueError:
        ok &= check("bad input raises ValueError", True)

    print("OK" if ok else "FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
