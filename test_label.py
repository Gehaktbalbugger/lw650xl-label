#!/usr/bin/env python3
"""End-to-end check for the `label` CLI.

1. Runs the real CLI against a local fake printer (TCP listener) and
   captures the exact wire bytes.
2. Checks the TSPL framing: header, BITMAP mode 0 (uncompressed), no
   length field, PRINT trailer.
3. Unpacks the 1-bpp bitmap and checks its size and content (dark pixels
   present, label geometry correct: 1280 dots wide, full feed height,
   content inside the measured print window).

Exit code 0 = everything passed.
"""
import re
import socket
import subprocess

HEAD_DOTS = 1280
TOP_OFFSET = 60


def capture(cmd):
    """Vanger: lokale TCP-printer nadoen en de exacte wire-bytes vastleggen."""
    srv = socket.socket()
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", 0))
    srv.listen(1)
    srv.settimeout(20)
    port = srv.getsockname()[1]
    sub = subprocess.run(cmd + ["--host", "127.0.0.1", "--port", str(port)],
                         capture_output=True, text=True, timeout=15)
    assert sub.returncode == 0, f"CLI failed: {sub.stderr}"
    conn, _ = srv.accept()
    conn.settimeout(5)
    data = b""
    try:
        while True:
            b = conn.recv(65536)
            if not b:
                break
            data += b
    except socket.timeout:
        pass
    conn.close()
    srv.close()
    return data


def unpack_bitmap(data):
    start = data.index(b"BITMAP 0,0,")
    m = re.match(rb"BITMAP 0,0,(\d+),(\d+),(\d+),", data[start:])
    assert m, "BITMAP header required"
    wb, hpx, mode = (int(x) for x in m.groups())
    assert mode == 0, "BITMAP must be mode 0 (uncompressed)"
    body = data[start + m.end():]
    end = body.index(b"\r\nPRINT 1,1\r\n")
    bits = body[:end]
    assert len(bits) == wb * hpx, f"bitmap size {len(bits)} != {wb * hpx}"
    assert b"\r\n" not in bits, "no CRLF inside the bitmap payload"
    return wb, hpx, bits


def ink_columns(bits, wb):
    """Aantal donkere dots per koppositie x (bit 0 = geprint)."""
    cols = []
    for x in range(wb * 8):
        byte, bit = divmod(x, 8)
        n = 0
        for row in range(len(bits) // wb):
            if not bits[row * wb + byte] & (1 << (7 - bit)):
                n += 1
        cols.append(n)
    return cols


def capture_payload():
    return capture(["./label", "Guard-check\nAnna de Bakker"])


def main():
    data = capture_payload()
    print(f"payload bytes: {len(data)}")
    assert data.startswith(b"\r\nDENSITY"), "payload must start with header"
    assert data.endswith(b"\r\nPRINT 1,1\r\n"), "PRINT trailer required"
    assert b"SIZE 57 mm,38.6 mm" in data, "57x32 media must use the 38.6 mm pitch"

    wb, hpx, bits = unpack_bitmap(data)
    assert wb == HEAD_DOTS // 8, f"bitmap must span the full head ({HEAD_DOTS} dots)"
    assert hpx >= TOP_OFFSET + 300, "bitmap must cover the label area"

    dark = 0
    for b in bits:
        dark += 8 - bin(b).count("1")     # bit 0 = printed dot
    print(f"bitmap {wb * 8} x {hpx} dots, dark dots: {dark}")
    assert dark > 500, "expected visible text in the bitmap"
    assert dark < len(bits) * 8 // 2, "bitmap must not be mostly black"

    # text must sit inside the print window, not in the top padding
    top = bits[: wb * TOP_OFFSET]
    assert all(b == 0xFF for b in top), "area above the label must be white"

    # --- AM11353 (LW_25x25): --two door de vanger, bits-controle -----------
    # Fysiek bewezen geometrie (kader- en snijlijnlood 12 nov): blok x
    # -2,0..23,0 mm met snijlijn op 10,5 mm; labeltop 4,5 mm onder de
    # oorsprong; canvas 354 regels zoals de vendor. De linker 2,0 mm van
    # baan A ligt links van kop-x=0: die strip knipt weg, inkt blijft
    # binnen x 0..271 dots.
    data = capture(["./label", "Anna de Bakker\nKeukenstraat 12",
                    "--two", "Piet Jansen\nBrugstraat 3",
                    "--size", "25x25", "--pitch", "34", "--gap", "3",
                    "--rows", "354", "--xoffset", "-2",
                    "--left", "0", "--media-right", "0",
                    "--media-top", "4.5", "--media-bottom", "0"])
    assert b"SIZE 25 mm,34 mm" in data, "AM11353: SIZE must be the block + pitch"
    wb2, hpx2, bits2 = unpack_bitmap(data)
    assert wb2 == 160 and hpx2 == 354, \
        f"AM11353: full head and 354 rows expected, got {wb2 * 8} x {hpx2}"
    cols2 = ink_columns(bits2, wb2)
    xs = [x for x, n in enumerate(cols2) if n]
    assert xs, "AM11353: geen inkt gevonden"
    assert xs[0] >= 0 and xs[-1] <= 271, \
        f"AM11353: inkt x {xs[0]}..{xs[-1]} valt buiten bereik 0..271 (0..23,0 mm)"
    links, rechts = sum(cols2[0:124]), sum(cols2[124:272])
    assert links > 150 and rechts > 150, \
        f"AM11353: beide halve kolommen moeten inkt dragen (L={links}, R={rechts})"
    assert cols2[124] == 0, "AM11353: de snijlijn op x=10,5 mm moet wit blijven"
    pad_top = bits2[:53 * wb2]
    assert all(b == 0xFF for b in pad_top), \
        "AM11353: de 4,5 mm vóór het label (rij < 53) moeten wit zijn"
    pad2 = bits2[349 * wb2:]
    assert all(b == 0xFF for b in pad2), \
        "AM11353: na rij 348 (label + top 4,5 mm) mag geen inkt staan"
    print(f"AM11353 2-up: inkt x {xs[0]}..{xs[-1]}, L={links} R={rechts} dots")

    # --- vierkante rol: de (ooit crashende) rotate=270-tak ------------------
    # LW_26x25 from KNOWLEDGE: ox=18, oy=52, window 272 x 295, canvas 356.
    data = capture(["./label", "vierkant", "--size", "26x25",
                    "--pitch", "33.97", "--gap", "3", "--rows", "356",
                    "--left", "1.5", "--media-right", "1.4",
                    "--media-top", "1.9", "--voffset", "2.5",
                    "--media-bottom", "0", "--rotate", "270"])
    wb3, hpx3, bits3 = unpack_bitmap(data)
    assert wb3 == 160 and hpx3 == 356, \
        f"vierkant: full head and 356 rows expected, got {wb3 * 8} x {hpx3}"
    pad3 = bits3[:52 * wb3]
    assert all(b == 0xFF for b in pad3), "vierkant: rijen vóór oy=52 moeten wit zijn"
    cols3 = ink_columns(bits3, wb3)
    xs = [x for x, n in enumerate(cols3) if n]
    assert xs and 18 <= xs[0] and xs[-1] <= 290, \
        f"vierkant: inkt x {xs[0]}..{xs[-1]} valt buiten window 18..290"
    rows = [sum(1 for byte in bits3[r * wb3:(r + 1) * wb3] if byte != 0xFF)
            for r in range(hpx3)]
    ys = [y for y, n in enumerate(rows) if n]
    assert ys[0] >= 52 and ys[-1] <= 346, \
        f"vierkant: inkt y {ys[0]}..{ys[-1]} valt outside window 52..346"
    print(f"vierkant rotate=270: inkt x {xs[0]}..{xs[-1]}, y {ys[0]}..{ys[-1]}")
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
