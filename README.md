# label — LW650XL PRO label printing from the terminal

The LW650XL PRO is a rebranded **Aimo 650** (Xiamen Aimo Technology /
AIMOmate) desktop label printer: 4-inch, 300 dpi, direct thermal.
It speaks **TSPL** over raw TCP port 9100, with the vendor twist that
`BITMAP` must be **LZO-compressed (mode 3)** and bit 1 = printed dot.
This tool encodes that itself — no vendor driver needed.

## Status

- **Tested**: verified live against the printer (labels print, printer
  answers `SSSGETPRINTING:DOING → DONE`, no command errors).
- **Tests**: `python3 lzo.py` (LZO round-trip suite) and
  `python3 test_label.py` (end-to-end framing check via a fake TCP
  printer) — both pass.


## Usage

```
./label "Anna de Bakker\nKeukenstraat 12\n1011 AB Amsterdam"
./label "Pakket #1234" --size 104x159 --font 12 --qr "https://track/1234"
./label "Sale" --barcode "CODE128:ABC123" --copies 3
./label "Test" --preview out.png          # render PNG, do not print
```

- Default label size 102x59 mm (the 123inkt large shipping labels);
  use `--size 104x159` for the extra-large PostNL ones.
- `--host` defaults to 172.16.1.20.
- `--density 0-15` (darkness), `--speed`, `--gap` (label gap mm).
- `\n` in the text starts a new line. Text auto-wraps and auto-shrinks
  to fit.

## Files

- `label` — the CLI (Python 3 + Pillow, both already on this Mac).
- `lzo.py` — pure-Python LZO1X-1 compressor/decompressor for the
  BITMAP mode-3 payload. `python3 lzo.py` runs its round-trip self-test.

## How to extend

- New label preset: add a `--size` you always use, or an alias.
- Native QR/barcode: handled by the printer's own `QRCODE`/`BARCODE`
  commands (sent after the bitmap).
- USB: plug in, then `lp -o raw -p LW650XL_PRO <payload>` — the same
  TSPL bytes work through the existing CUPS USB queue.
