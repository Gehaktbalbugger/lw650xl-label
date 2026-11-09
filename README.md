# LW650XL PRO — label printing for macOS (terminal + Word)

The LW650XL PRO is a rebranded **Aimo 650** (Xiamen Aimo Technology /
AIMOmate) desktop label printer: 4-inch, 300 dpi, direct thermal.
It speaks **TSPL** over raw TCP port 9100. The bitmap format was
reverse-engineered from the vendor app (Labellife) and verified on the
hardware: `BITMAP` **mode 0** (uncompressed), payload directly after the
last comma (no length, no CRLF), **bit 1 = white**, and the bitmap is
mapped 1:1 onto the 1280-dot print head. This repo encodes that itself —
no vendor driver needed.

It contains three ways to print:

1. **`label`** — command-line tool for quick labels.
2. **CUPS driver** (`cups/`) — a macOS print queue with real label
   sizes, so **Word / Pages / Preview** can print with a page size
   that matches the label in the printer.
3. **Shared inbox** (`workflow/`) — Word/Excel on any system on the home
   network drops a PDF or CSV into a shared folder; this iMac prints it.
   No driver on the clients. See **[workflow/README.nl.md](workflow/README.nl.md)**
   (Dutch) and run `./setup.sh` once.

## Status

- **Verified on hardware**: geometry, polarity and framing were checked
  against the vendor app's own traffic (captured with `tcpdump`) and with
  ruler/edge test prints on an AM11354 57 × 32 mm roll.
- **End-to-end**: PDF in the shared inbox → watcher → CUPS → printer
  produces a correctly aligned label (job `LW650XL_Labels-148`).
- **Word directly**: printing straight to the queue from Word — including a
  multi-page landscape label document — produces one aligned label per page.
- **CLI tests**: `python3 test_label.py` (framing + geometry check via a
  fake TCP printer) and `python3 lzo.py` (legacy LZO round-trip) pass.
- **Filter tests**: `python3 test_filter.py` builds real cgpdftoraster
  layouts (multi-page, Word's portrait raster, Custom media) and decodes
  the TSPL back; printing a 2-page Word document works end to end.

## Part 1: terminal tool

```
./label "Anna de Bakker\nKeukenstraat 12\n1011 AB Amsterdam"
./label "Pakket #1234" --size 104x159 --font 12 --qr "https://track/1234"
./label "Sale" --barcode "CODE128:ABC123" --copies 3
./label "Test" --preview out.png          # render PNG, do not print
```

- Default label size 57x32 mm (the AM11354 roll in the printer);
  use `--size 102x59` for the large shipping labels or `--size 104x159`
  for the extra-large PostNL ones. Pass `--pitch` if the roll's
  label+gap pitch differs from its height (57x32 uses 38.6 mm).
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

- `/usr/libexec/cups/filter/lw650xl` (+ `lw650xl.py`) — raster → TSPL filter
- `/etc/cups/ppd/LW650XL_Labels.ppd` — label size catalog
- the queue **LW650XL_Labels** (socket://172.16.1.20:9100)

### Install on another Mac

Only the queue is needed on a client Mac — not `setup.sh`, which creates the
shared inbox and watcher for the host:

```
xcode-select --install   # first time only, provides a real python3 + git
git clone https://github.com/Gehaktbalbugger/lw650xl-label.git ~/label-printer
cd ~/label-printer
sudo ./install.sh
```

Do NOT clone into `Documents`, `Desktop` or `Downloads`: macOS does not let
`sudo` read those folders and the install fails with "Operation not
permitted". A plain folder in your home directory (or /tmp) works.
Update later with `cd ~/label-printer && git pull && sudo ./install.sh`.

Pick **LW650XL PRO Labels (TSPL)** and paper size *Etiket 57x32 mm (AM11354)*
in Word. Remove any vendor (Labellife) queues from System Settings →
Printers & Scanners; they are not used and only get in the way.

### Print from Word

1. In Word: **File → Print** (⌘P).
2. Printer: **LW650XL Labels**.
3. In the paper/page section choose the **paper size** with the same
   name as the label roll that is loaded (default: *Etiket 57x32 mm
   (AM11354)*).
4. Make sure the document's **page setup / paper size matches** the
   same label size (File → Page Setup), so nothing gets scaled.
5. Print. The label comes out with 1:1 framing.

Tip: in Word's *Layout → Margins* set narrow margins (~0.2 cm) —
thermal labels have no printer margin, the printable area is the
full label.

### Printing from other apps or the command line

```
lp -d LW650XL_Labels -o media=LW_57x32 mylabel.pdf
cupsfilter -p /etc/cups/ppd/LW650XL_Labels.ppd \
           -o media=LW_57x32 -m application/vnd.cups-raw mylabel.pdf \
           | nc 172.16.1.20 9100
```

### Changing label size / adding a new size

Built-in sizes (from the PPD): **57x32 (default, AM11354)**, 104x159,
102x59, 101x54, 89x36, 89x28, 54x25, 50x12, 57x57, 62x100 mm.

For the 57x32 roll the printer expects the label *pitch* (38.6 mm) in
`SIZE`, not the 32 mm label height; the filter knows this. For other
rolls whose pitch differs from the label height, pass
`-o lw-pitch=<mm>`.

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
            → lw650xl (this repo; threshold + bit-pack, mode 0)
            → TSPL over TCP 9100 (socket backend)
```

Custom CUPS options understood by the filter: `lw-gap` (gap mm,
default 3), `lw-pitch` (feed height mm, default 38.6 for 57x32),
`lw-density` (default 15), `lw-speed` (default 1).

Things the filter has to undo for a Word job (macOS print pipeline):

- Word sends `media=Custom.90.71x161.57`, not the PPD name; the label size
  is read from `com.apple.print.PageToPaperMappingMediaName` instead.
- `orientation-requested=4` makes `cgpdftoraster` hand over a PORTRAIT
  raster for a landscape label, so it is rotated 90° clockwise back.
- Multi-page documents: the raster has one 4-byte sync word, then a
  1796-byte header per page, so page 2 onwards must be parsed without it.
  Each page becomes its own label (one `PRINT` per page).

## Part 3: shared Word/Excel workflow (multiple systems)

Run once:

```
sudo ./setup.sh
```

This installs the queue (shared via IPP/Bonjour), creates the SMB share
**Labelprinter** (`/Users/Shared/Labelprinter/inbox`) and starts a launchd
watcher. Any system can then drop a **PDF** (Word: *Label_NaarPrinter*
macro) or a **CSV** (Excel: one label per row) into that folder; the iMac
converts it to TSPL and prints it. Full Dutch guide:
[`workflow/README.nl.md`](workflow/README.nl.md).

## Files

- `label` — the CLI (Python 3 + Pillow, both already on this Mac).
- `lzo.py` — pure-Python LZO1X-1 codec, kept for reference/testing;
  the printer's working BITMAP mode 0 is uncompressed and does not use it.
- `test_label.py` — end-to-end framing test against a fake TCP printer.
- `test_filter.py` — CUPS raster parser test: multi-page rasters, Word's
  media/orientation options, bitmap decoding (no printer needed).
- `cups/lw650xl` — CUPS filter wrapper (picks a working Python 3).
- `cups/lw650xl.py` — the raster→TSPL conversion (self-contained).
- `cups/lw650xl-labels.ppd` — queue PPD with the label size catalog.
- `cups/test.pdf` — test page for `lp` (regenerate for another size).
- `install.sh` / `uninstall.sh` / `add-size.sh` — queue management.
