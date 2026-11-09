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


def capture_payload():
    srv = socket.socket()
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", 0))
    srv.listen(1)
    port = srv.getsockname()[1]
    sub = subprocess.run(
        ["./label", "Guard-check\nAnna de Bakker",
         "--host", "127.0.0.1", "--port", str(port)],
        capture_output=True, text=True, timeout=15)
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
    assert sub.returncode == 0, f"CLI failed: {sub.stderr}"
    return data


def main():
    data = capture_payload()
    print(f"payload bytes: {len(data)}")
    assert data.startswith(b"\r\nDENSITY"), "payload must start with header"
    assert data.endswith(b"\r\nPRINT 1,1\r\n"), "PRINT trailer required"
    assert b"SIZE 57 mm,38.6 mm" in data, "57x32 media must use the 38.6 mm pitch"
    assert b"BITMAP 0,0," in data

    start = data.index(b"BITMAP 0,0,")
    m = re.match(rb"BITMAP 0,0,(\d+),(\d+),(\d+),", data[start:])
    assert m, "BITMAP header required"
    wb, hpx, mode = (int(x) for x in m.groups())
    assert mode == 0, "BITMAP must be mode 0 (uncompressed)"
    assert wb == HEAD_DOTS // 8, f"bitmap must span the full head ({HEAD_DOTS} dots)"
    assert hpx >= TOP_OFFSET + 300, "bitmap must cover the label area"

    body = data[start + m.end():]
    end = body.index(b"\r\nPRINT 1,1\r\n")
    bits = body[:end]
    assert len(bits) == wb * hpx, f"bitmap size {len(bits)} != {wb * hpx}"
    assert b"\r\n" not in body[:end], "no CRLF inside the bitmap payload"

    dark = 0
    for b in bits:
        dark += 8 - bin(b).count("1")     # bit 0 = printed dot
    print(f"bitmap {wb * 8} x {hpx} dots, dark dots: {dark}")
    assert dark > 500, "expected visible text in the bitmap"
    assert dark < len(bits) * 8 // 2, "bitmap must not be mostly black"

    # text must sit inside the print window, not in the top padding
    top = bits[: wb * TOP_OFFSET]
    assert all(b == 0xFF for b in top), "area above the label must be white"

    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
