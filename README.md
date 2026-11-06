# LW650XL PRO — label printing for macOS (terminal + Word)

The LW650XL PRO is a rebranded **Aimo 650** (Xiamen Aimo Technology /
AIMOmate) desktop label printer: 4-inch, 300 dpi, direct thermal.
It speaks **TSPL** over raw TCP port 9100, with the vendor twist that
`BITMAP` must be **LZO-compressed (mode 3)** and bit 1 = printed dot.
This repo encodes that itself — no vendor driver needed.

It contains two ways to print:

1. **`label`** — command-line tool for quick labels.
2. **CUPS driver** (`cups/`) — a macOS print queue with real label
   sizes, so **Word / Pages / Preview** can print with a page size
   that matches the label in the printer.

## Status

- **Tested**: verified live against the printer (labels print, printer
  answers `SSSGETPRINTING:DOING → DONE`, no command errors).
- **CLI tests**: `python3 lzo.py` (LZO round-trip suite) and
  `python3 test_label.py` (end-to-end framing check via a fake TCP
  printer) — both pass.
- **Driver tests**: the filter's output was validated the same way
  (framing + LZO round-trip) and PPD rendering goes through
  `cgpdftoraster` at 300 dpi, 8-bit gray, with correct page size.

## Part 1: terminal tool

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

## Part 2: CUPS driver for Word & friends

### One-time install

```
cd label-printer
sudo ./install.sh
```

This installs

- `/usr/libexec/cups/filter/lw650xl` — raster → TSPL filter
- `/etc/cups/ppd/LW650XL_Labels.ppd` — label size catalog
- the queue **LW650XL_Labels** (socket://172.16.1.20:9100)

### Print from Word

1. In Word: **File → Print** (⌘P).
2. Printer: **LW650XL Labels**.
3. In the paper/page section choose the **paper size** with the same
   name as the label roll that is loaded (e.g. *Verzendetiket
   102x59 mm*).
4. Make sure the document's **page setup / paper size matches** the
   same label size (File → Page Setup), so nothing gets scaled.
5. Print. The label comes out with 1:1 framing.

Tip: in Word's *Layout → Margins* set narrow margins (~0.2 cm) —
thermal labels have no printer margin, the printable area is the
full label.

### Printing from other apps or the command line

```
lp -d LW650XL_Labels -o media=LW_102x59 mylabel.pdf
cupsfilter -p /etc/cups/ppd/LW650XL_Labels.ppd \
           -o media=LW_102x59 -m application/vnd.cups-raw mylabel.pdf \
           | nc 172.16.1.20 9100
```

### Changing label size / adding a new size

Built-in sizes (from the PPD): 104x159, 102x59, 101x54, 89x36,
89x28, 54x25, 50x12, 57x57, 62x100 mm.

**Add a new size:**

```
./add-size.sh LW_76x51 "Logistics 76x51 mm" 76 51          # die-cut (2 mm gap)
./add-size.sh LW_30x15 "Kasbon 30x15 mm" 30 15 --gap 0     # continuous
sudo ./install.sh                                          # re-apply
```

The size then appears as a paper size in every app.

**Switching the loaded roll:** nothing to configure for align‑ment —
pick the matching paper size in the print dialog. For continuous
(vgap-less) media pass `-o lw-gap=0` (`lp`), or in Word just use the
matching paper size that `add-size.sh --gap 0` created.

**Parameters of an existing size:** edit
`cups/lw650xl-labels.ppd` (entries `*PageSize`, `*PageRegion`,
`*ImageableArea`, `*PaperDimension` in points — 1 mm = 2.8346 pt)
and run `sudo ./install.sh` again.

### How it works

```
Word/Pages/… → PDF → cgpdftoraster (macOS)
            → lw650xl (this repo; threshold + bit-pack + LZO)
            → TSPL over TCP 9100 (socket backend)
```

Custom CUPS options understood by the filter: `lw-gap` (gap mm,
default 2), `lw-density` (default 8), `lw-speed` (default 4).

## Files

- `label` — the CLI (Python 3 + Pillow, both already on this Mac).
- `lzo.py` — pure-Python LZO1X-1 compressor/decompressor for the
  BITMAP mode-3 payload. `python3 lzo.py` runs its round-trip self-test.
- `test_label.py` — end-to-end framing test against a fake TCP printer.
- `cups/lw650xl` — CUPS raster→TSPL filter (self-contained).
- `cups/lw650xl-labels.ppd` — queue PPD with the label size catalog.
- `cups/test.pdf` — 102x59 mm test page for `lp`.
- `install.sh` / `uninstall.sh` / `add-size.sh` — queue management.
