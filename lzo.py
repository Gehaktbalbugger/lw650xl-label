"""Pure-Python LZO1X-1 compressor and decompressor (classic format, no version header).

The format is derived from the Linux kernel's lib/lzo/lzo1x_decompress_safe.c
(copyright Markus F.X.J. Oberhumer, GPL-2.0). The printer firmware decompresses
with minilzo lzo1x_decompress, which is bit-compatible with this format.

Run this file directly for a self-test: python3 lzo.py
"""

M3_MAX_OFFSET = 16384
M3_MAX_LEN = 65313  # 33 + 255*255 + 255


def _emit_litrun(out, lit):
    """Emit a literal run of len(lit) >= 4 bytes (state 0 path)."""
    n = len(lit)
    if n <= 18:
        out.append(n - 3)
    else:
        z = (n - 19) // 255
        b = n - 18 - 255 * z
        out.append(0)
        out += b"\x00" * z
        out.append(b)
    out += lit


def compress(data):
    """LZO1X-1 compress. Returns bytes decompressible by lzo1x_decompress."""
    data = bytes(data)
    n = len(data)
    if n == 0:
        raise ValueError("LZO1X: empty input")

    # greedy match scan: hash of 3-byte sequences -> last position
    table = {}
    matches = []
    for i in range(min(3, n - 2)):
        table[data[i:i + 3]] = i
    pos = 3
    while pos + 3 <= n:
        h = data[pos:pos + 3]
        prev = table.get(h)
        table[h] = pos
        if prev is None or prev >= pos or pos - prev > M3_MAX_OFFSET:
            pos += 1
            continue
        length = 3
        max_len = min(M3_MAX_LEN, n - pos)
        while length < max_len and data[prev + length] == data[pos + length]:
            length += 1
        matches.append((pos, length, pos - prev))
        for p in range(pos + 1, min(pos + length, n - 2)):
            table[data[p:p + 3]] = p
        pos += length

    out = bytearray()

    # start literal run (first 3 bytes are never compressed).
    # The start-state control byte can only express runs of 1..238;
    # longer runs use the state-0 extended literal-run encoding instead.
    first = matches[0][0] if matches else n
    if first <= 238:
        out.append(17 + first)
        out += data[:first]
    else:
        _emit_litrun(out, data[:first])

    for i, (mpos, mlen, off) in enumerate(matches):
        end = mpos + mlen
        next_pos = matches[i + 1][0] if i + 1 < len(matches) else n
        gap = next_pos - end
        if gap <= 3:
            nxt, gap = gap, 0
        else:
            nxt = 0
        if mlen <= 4 and off <= 2048:
            # M4: length 3..4, offset 1..2048
            out.append(((mlen - 1) << 5) | (((off - 1) & 7) << 2) | nxt)
            out.append((off - 1) >> 3)
        elif mlen <= 33:
            # M3: length 3..33, offset 1..16384
            out.append(32 + (mlen - 2))
            out += (((off - 1) << 2) | nxt).to_bytes(2, "little")
        else:
            # M3 with extended length
            z = (mlen - 34) // 255
            b = mlen - 33 - 255 * z
            out.append(32)
            out += b"\x00" * z
            out.append(b)
            out += (((off - 1) << 2) | nxt).to_bytes(2, "little")
        if nxt:
            out += data[end:end + nxt]
        if gap:
            _emit_litrun(out, data[end:end + gap])

    out += b"\x11\x00\x00"  # EOF marker
    return bytes(out)


def decompress(src, out_len):
    """Classic LZO1X decompressor (port of the kernel's lzo1x_decompress_safe)."""
    src = bytes(src)
    out = bytearray()
    ip = 0
    if len(src) >= 5 and src[0] == 17:
        raise ValueError("bitstream version header not supported")

    t = src[ip]
    if t > 17:
        ip += 1
        t -= 17
        if t < 4:
            nxt = t
            out += src[ip:ip + nxt]
            ip += nxt
            state = nxt
        else:
            out += src[ip:ip + t]
            ip += t
            state = 4
    else:
        state = 0

    while True:
        t = src[ip]
        ip += 1
        if t < 16:
            if state == 0:
                if t == 0:
                    z = 0
                    while src[ip] == 0:
                        ip += 1
                        z += 1
                    t += 255 * z + 15 + src[ip]
                    ip += 1
                t += 3
                out += src[ip:ip + t]
                ip += t
                state = 4
                continue
            elif state != 4:
                nxt = t & 3
                off = 1 + (t >> 2) + (src[ip] << 2)
                ip += 1
                m = len(out) - off
                out += out[m:m + 2]
            else:
                nxt = t & 3
                off = 1 + 2048 + (t >> 2) + (src[ip] << 2)
                ip += 1
                m = len(out) - off
                t = 3
        elif t >= 64:
            nxt = t & 3
            off = 1 + ((t >> 2) & 7) + (src[ip] << 3)
            ip += 1
            t = (t >> 5) + 1
            m = len(out) - off
        elif t >= 32:
            t = (t & 31) + 2
            if t == 2:
                z = 0
                while src[ip] == 0:
                    ip += 1
                    z += 1
                t += 255 * z + 31 + src[ip]
                ip += 1
            u16 = int.from_bytes(src[ip:ip + 2], "little")
            ip += 2
            m = len(out) - 1 - (u16 >> 2)
            nxt = u16 & 3
        else:  # 16..31: M4 long-offset or EOF
            u16 = int.from_bytes(src[ip:ip + 2], "little")
            ip += 2
            m = len(out) - ((t & 8) << 11)
            t = (t & 7) + 2
            if t == 2:
                z = 0
                while src[ip] == 0:
                    ip += 1
                    z += 1
                t += 255 * z + 7 + src[ip]
                ip += 1
                u16 = int.from_bytes(src[ip:ip + 2], "little")
                ip += 2
            m -= u16 >> 2
            nxt = u16 & 3
            if m == len(out):
                if t != 3:
                    raise ValueError("bad EOF")
                return bytes(out[:out_len])
            m -= 16384

        for k in range(t):
            out.append(out[m + k])
        state = nxt
        out += src[ip:ip + nxt]
        ip += nxt


if __name__ == "__main__":
    import os
    import random
    random.seed(42)
    cases = [
        b"hello world",
        b"A" * 3,
        b"A" * 4,
        b"\x00" * 1000,
        b"\xff" * 708 * 153,  # a blank 102x59mm 300dpi label
        os.urandom(200),
        os.urandom(5000),
        (b"LABEL" + os.urandom(37)) * 100,
        bytes(i % 7 for i in range(66000)),
        b"abc" * 22000,
        b"X" * 19 + b"Y" + b"Z" * 500000,
        b"ABCD" * 17000,
    ]
    # structured case that looks like a label raster
    row = b"\xff" * 150 + b"\x00\x0f\xf0" * 1
    cases.append(row * 700)
    for i, data in enumerate(cases):
        c = compress(data)
        d = decompress(c, len(data))
        assert d == data, f"case {i} round-trip FAILED (len {len(data)})"
        print(f"case {i}: {len(data):>7} raw -> {len(c):>7} compressed  ok")
    print("all LZO round-trip tests passed")
