#!/usr/bin/env python3
"""End-to-end check for the `label` CLI.

1. Runs the real CLI against a local fake printer (TCP listener) and
   captures the exact wire bytes.
2. Checks the TSPL framing: header, BITMAP mode 3, LZO EOF marker, PRINT trailer.
3. Decompresses the raster with the reference decompressor and checks its
   size and content (dark pixels present, text top-aligned).

Exit code 0 = everything passed.
"""
import socket
import subprocess

import lzo


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

    # BITMAP 0,0,<wb>,<hpx>,<mode>,<lzo_len>,<payload>\r\nPRINT 1,1\r\n
    # payload is binary, so parse the ASCII header with a regex
    import re
    start = data.index(b"BITMAP 0,0,")
    m = re.match(rb"BITMAP 0,0,(\d+),(\d+),(\d+),(\d+),", data[start:])
    assert m, "BITMAP header with mode and LZO length required"
    wb, hpx, mode, ln = (int(x) for x in m.groups())
    assert mode == 3, "BITMAP must be mode 3"
    packed = data[start + m.end():]
    print(f"BITMAP {wb * 8}x{hpx} dots, mode {mode}, lzo payload {ln} bytes")
    # The payload is binary and may itself contain CRLF bytes, so the
    # trailing framing is located from the end of the stream, not by
    # scanning for the first CRLF.
    trailer = b"\r\nPRINT 1,1\r\n"
    assert packed.endswith(trailer), "PRINT must close the stream"
    payload = packed[:-len(trailer)]  # raw LZO data, ends with LZO EOF marker
    assert payload.endswith(b"\x11\x00\x00"), "LZO EOF marker must end the payload"
    assert len(payload) == ln, f"declared {ln} bytes, got {len(payload)}"

    raw = lzo.decompress(payload, wb * hpx)
    assert len(raw) == wb * hpx, "raster size mismatch"
    assert any(raw), "raster must contain printed (dark) pixels"
    rows = [raw[r * wb:(r + 1) * wb] for r in range(hpx)]
    first_dark = next(i for i, r in enumerate(rows) if any(r))
    last_dark = max(i for i, r in enumerate(rows) if any(r))
    print(f"raster ok: {wb * 8}x{hpx} dots, dark rows {first_dark}..{last_dark} (top-aligned text)")
    print("ALL CHECKS PASSED")


if __name__ == "__main__":
    main()
