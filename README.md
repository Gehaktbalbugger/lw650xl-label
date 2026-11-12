# LW650XL PRO — label printing for macOS (terminal + Word)

The LW650XL PRO is a rebranded **Aimo 650** (Xiamen Aimo Technology /
AIMOmate) desktop label printer: 4-inch, 300 dpi, direct thermal.
It speaks **TSPL** over raw TCP port 9100. The bitmap format was
reverse-engineered from the vendor app (Labellife) and verified on the
hardware: `BITMAP` **mode 0** (uncompressed), payload directly after the
last comma (no length, no CRLF), **bit 1 = white**, and the bitmap is
mapped 1:1 onto the 1280-dot print head. This repo encodes that itself —
no vendor driver needed.

Everything measured off the real printer — TSPL quirks, the registration
model, the per-roll numbers and the traps — is written up in
**[KNOWLEDGE.md](KNOWLEDGE.md)**; the current state and next steps are in
**[HANDOFF.md](HANDOFF.md)**.

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
- **Calibration**: `python3 test_measure.py` checks that a printed cross and
  the readings taken from it come back as the geometry that was assumed.

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

Built-in sizes (from the PPD): **57x32 (default, AM11354)**,
**36x89 standing (AM99012 / Dymo S0722400)**, **26x25 square (S0929120 /
Dymo 30332, printed rotated 270°)**, 104x159, 102x59, 101x54, 89x36, 89x28, 54x25, 50x12, 57x57,
62x100 mm.

The PPD is the only place a roll is defined. `add-size.sh` writes the four PPD
entries that make the size show up as a paper size, plus one comment line with
the geometry the printer needs:

```
./add-size.sh LW_76x51 "Logistiek 76x51 mm" 76 51 --gap 3 --pitch 54.5 --voffset 0.34
sudo ./install.sh
```

    *% lw-media LW_76x51 pitch=54.5 gap=3 voffset=0.34

Both the CUPS filter (it is handed the PPD path) and the `label` CLI read
those lines, so a new size works from Word, from `lp` and from the shared
inbox without touching code. `--gap`, `--pitch`, `--voffset`, `--left`, `--right`, `--top`, `--bottom`,
`--rows` and `--rotate` are optional:
without them gap = 3 mm, pitch = label height + gap and the print starts flush
with the label's top edge.

Rolls that sit differently in the printer need `left`, `top` and `bottom`;
measure them with a ruler print (see below):

- **left** — mm of label to the left of bitmap x=0. The head cannot reach it,
  so it is dead zone. The 57 mm roll measures 2 mm, the narrower 36 mm roll
  sits 3 mm over the edge.
- **right** — mm kept free at the label's right edge. Ink cannot move left of
  x=0, so a roll with an unreachable left edge is centred by trimming the
  right side to the same amount (AM99012: left 3, right 3).
- **top** — mm from the bitmap origin to the label's top edge. Positive for
  short labels (5.1 mm on the AM11354), **negative when the label starts above
  the head's reach** (the 89 mm tall AM99012 starts at -0.5 mm).
- **bottom** — mm kept free at the label's bottom edge. Raise it to match an
  unreachable top edge so the print stays centred.
- **gap** and **gapoff** — the gap length and, separately, how much plain
  liner sits between the label's trailing edge and that gap. The square roll
  is 25 mm label + 4 mm liner + 3 mm notch + 5 mm liner.
- **sense** — `gap` (default) or `bline` for black marks. A 26 mm roll against
  the left guide never reaches a sensor sitting mid-path, so `BLINE` just
  stalls the printer with a paper error; what makes the jobs repeat is that
  `SIZE height + gap` equals the true pitch.
- **xoffset** — mm between the head's x=0 and the liner's left edge; may be
  negative. The AM11353 was calibrated on paper (centred 6×10 mm boxes plus
  a seam plumb-line, 12 nov): its 30 mm liner starts at x ≈ −3,5 mm and
  label A at −2,0 mm, so the leftmost 2 mm of A is out of reach and gets
  clipped; the cut rail sits at x = 10,5 mm. Without this the whole sheet
  lands 10 mm too far right and the second lane falls off the liner.
- **rows** — pin the bitmap height in dots instead of deriving `pitch - 12`.
  Labellife sends 356 rows for a 33.97 mm square roll; matching that exactly
  matched its registration.
- **rotate** — `90` or `270`: print the page on its side. For square rolls
  this is how the vendor app prints; it does not change the dead zone, only
  which way the text runs.

**voffset** shifts the whole print down the label. The measured print window
starts exactly at the label's top edge, which makes a page that Word centres
vertically sit a bit high. Trial prints on the AM11354 roll centred it at
0.34 mm (4 dots; 0 mm was too high, 0.5 mm too low). Set it to 0 to print
flush with the top edge again.

**Pitch** is the distance the printer feeds per label, not the label height:
the 57 × 32 mm roll needs 38.6 mm (label + gap + liner). If labels slowly
drift out of position, the pitch is wrong — measure the distance between the
same point on two consecutive labels and pass that. Continuous stock:
`--gap 0`, which makes the pitch equal to the height.

Overriding once, without editing the PPD:

```
lp -d LW650XL_Labels -o media=LW_36x89 -o lw-top=0 -o lw-bottom=0.7 job.pdf
./label "tekst" --size 36x89 --media-top 0 --media-bottom 0.7
```

### Measuring a new roll

`add-size.sh` only knows what you measure, and `./measure` does the measuring:

```
./measure 36 89 --name LW_36x89 --pitch 93 --gap 4      # print a cross label
./measure solve --N -44.5 --Z 44.5 --W -18 --O 18        # read off, get the command
```

`measure` prints one label with `0,0` at the centre of the assumed print
window, 1 mm ticks with numbers along both arms and N / Z / W / O at the
assumed label edges; it records where that centre sits. Read the mm value at
each of the four real label edges and pass them in: it writes the exact
`add-size.sh` line, including `--left`, `--right`, `--top` and `--bottom`.
Use `--preview out.png` or `--dry-run` to look without printing.

What the readings mean:

- equal |W| and |O| → the roll is centred on the head's start; if the label
  hangs past x=0, `left` is that many mm and `right` is set equal to it,
  because ink can never start left of x=0.
- a difference between N and Z is twice the error in the vertical centre;
  a negative `top` means part of the label is above the first printable row,
  which `bottom` then mirrors.
- pitch and gap cannot come off a cross: measure 20 labels and divide by 20,
  then pass `--pitch` (and `--gap`) to `solve`.

It sends mode-0 TSPL straight to port 9100, so it needs no driver, no root and
works before the size exists in the PPD. Like `label` it needs Pillow
(`pip3 install pillow`).

### How it works

```
Word/Pages/… → PDF → cgpdftoraster (macOS)
            → lw650xl (this repo; threshold + bit-pack, mode 0)
            → TSPL over TCP 9100 (socket backend)
```

Custom CUPS options understood by the filter: `lw-gap` (gap mm,
default 3), `lw-pitch` (feed height mm, default 38.6 for 57x32),
`lw-voffset` (print N mm lower on the label, default 0.34 for 57x32),
`lw-left` / `lw-right` / `lw-top` / `lw-bottom` (roll position, see below),
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
- `measure` — roll calibration: prints a 0,0-cross with a 1 mm scale and turns
  the four edge readings into an `add-size.sh` command.
- `test_label.py` — end-to-end framing test against a fake TCP printer.
- `test_measure.py` — print/solve round trip of `measure`.
- `KNOWLEDGE.md` — alles wat gemeten is: BITMAP-opbouw, registratiemodel,
  commando-matrix, rollen en hun getallen, veldvalleien.
- `HANDOFF.md` — status en de open punten voor de volgende sessie.
- `test_filter.py` — CUPS raster parser test: multi-page rasters, Word's
  media/orientation options, bitmap decoding (no printer needed).
- `cups/lw650xl` — CUPS filter wrapper (picks a working Python 3).
- `cups/lw650xl.py` — the raster→TSPL conversion (self-contained).
- `cups/lw650xl-labels.ppd` — queue PPD with the label size catalog.
- `cups/test.pdf` — test page for `lp` (regenerate for another size).
- `install.sh` / `uninstall.sh` / `add-size.sh` — queue management.
