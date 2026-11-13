# What we know about the LW650XL PRO

Findings collected while reverse-engineering and tuning this printer. Every
point was measured on the real printer, not taken from documentation — the
factory sheet is wrong for this firmware. See `HANDOFF.md` to continue the
work.

## 1. The hardware

- LW650XL PRO is a re-badged **Aimo 650** (Xiamen Aimo Technology).
- Direct thermal, black-and-white, 300 dpi, **1280-dot head ≈ 108 mm**.
- Language: **TSPL** over raw TCP **port 9100**. USB exists as well, but
  everything here was verified over the network.
- 1 dot = 25.4/300 = **0.0847 mm**. The finest adjustable step is ~0.085 mm;
  "0.3 mm" does not physically exist, but 3 dots = 0.254 mm or 4 dots =
  0.339 mm do.
- The printer talks back on the same port:

  | message | meaning |
  |---|---|
  | `SSSGETPRINTING:DOING` → `:DONE` | job accepted and printed |
  | `SSSGETPAPER:NO` | no paper / sensor finds no reference |
  | `SSSGETCAP:OPEN` / `:CLOSE` | the lid or media lever moved |
  | `Cmd error:<token>` | command (or token) not understood |

## 2. Command matrix (sniffed, one command per connection)

| accepted | refused |
|---|---|
| `SIZE`, `GAP`, `BLINE`, `REFERENCE`, `OFFSET`, `DIRECTION`, `DENSITY`, `SPEED`, `CLS`, `BITMAP`, `PRINT`, `SET TEAR ON`, `SHIFT`, `SET MEDIA GAP` | `GAPAUTO`, `SET MEDIA MARK`, `SET BACK`, `SET SHIFT`, `VREF`, `PRINTM`, `SSSGETMEDIA:`, `SSSGETDEVINFO:`, `SSSGETSTATUS:` |

Only this list was actually sniffed. Commands not on it (`CODEPAGE`, `PAUSE`,
`FORMFEED`, …) are untested — they were not refused, but not confirmed either.

Careful with piped probing: the printer answers **asynchronously, one step
later** than the command you just sent. One command per TCP connection,
otherwise the answers shift and you read `Cmd error:GAP` on a `SPEED` line.

**`SHIFT` is accepted but never explored.** If it moves the head start in
dots, it is the only way to win back the unreachable left edge of narrow
rolls. See HANDOFF, the "open" item.

## 3. BITMAP format

- **mode 0 = uncompressed**, and that is what works.
- Syntax: `BITMAP x,y,width_in_bytes,height,mode,` — the binary payload starts
  **right after the last comma**: no length field, no CRLF.
- **Bit 1 = white, bit 0 = printed dot.** Rows MSB-first, each row padded to
  whole bytes. A 1280-dot bitmap is therefore 160 bytes per row.
- mode 3 (classic LZO) is **silently swallowed** by this firmware: the printer
  reports DONE but prints nothing. mode 4 is the vendor's own LZO variant:
  18 blocks of `[4-byte LE length][data]`, each ending in `11 00 00`; our
  `lzo.py` cannot decode it and no longer needs to.
- The bitmap is laid **1:1 on the head**: a 57 mm label occupies the left part
  of the 1280 dots, the rest is empty liner.

## 4. Registration: this is the core

1. **The printer anchors the bitmap at its BOTTOM.** A taller bitmap moves
   the image up the label. Want a short label? Pad the bitmap to the full
   feed height, otherwise the image lands misplaced.
2. **`SIZE` height + `GAP` length = the distance per label.** That is what
   the printer feeds. If that sum is wrong, it hunts for a reference that
   isn't there and starts every feed elsewhere. Get it right and five loose
   feeds land exactly identical — even though the notches or even the gap
   may not be seen by the sensor.
3. The default bitmap fill is `pitch_dots - 12` (that is what the vendor app
   sends on the 57 × 32 roll: 444 rows at 456 dots). Rolls that break this
   pattern pin their height with `rows=`.
4. **Ink cannot go left of x=0.** A narrow roll resting against the left
   guide therefore steals millimetres from the label that no software can
   recover. Center by giving up on the right as much as is unreachable on the
   left (`left` = `right`), not by shifting.
5. The sensor sits in the **middle of the media path** (~54 mm from the
   left). A 26 mm roll never reaches it, so mark information (BLINE) is
   useless there; `BLINE 12 mm` even put the printer in a paper error.

## 4A. Coordinates: what is true on the label

Settled definitively with a sheet carrying four corner letters (P/Q/R/S)
whose canvas positions were known. The user held the label the way they read
it:

| their view | letters on the sheet | canvas |
|---|---|---|
| top-left | P | x 3.64 / y 25.65 mm |
| top-right | Q | x 3.64 / y 7.87 mm |
| bottom-left | R | x 19.73 / y 25.65 mm |
| bottom-right | S | x 19.73 / y 7.87 mm |

So, with `rotate=270`:

| their direction | canvas |
|---|---|
| **up** (carries the 2 mm unreachable) | small x, the x=0 side |
| **down** | large x (the 23.5 mm side) |
| **left** | large y = the rear |
| **right** | small y = the **exit side**, where the FEED arrow points |

Two conclusions worth keeping:

1. Left/right sits on the **y axis** (the feed direction), not the x axis.
   All my earlier "the arrow points at B" interpretations failed because of
   that.
2. A design drawn the normal way (top-left = top-left) comes out **upright**
   on the label after `rotate=270`: corner for corner identical. You do not
   need to rotate your Word or Python design; only the page size must match
   the printable area.

Rule for diagnostics: always name a position as a canvas number or as a
letter of the sheet, never as up/left/down.

## 5. Geometry per roll, all in the PPD

One comment line per roll, written by `add-size.sh` and read by both the CUPS
filter (`$PPD` environment, fallback `/etc/cups/ppd/LW650XL_Labels.ppd`) and
the `label` CLI. CUPS keeps comment lines intact on install (verified).

```
*% lw-media <name> pitch=.. gap=.. [gapoff=..] [left=..] [right=..]
               [top=..] [bottom=..] [voffset=..] [rows=..] [rotate=..] [sense=..]
```

| field | meaning |
|---|---|
| `pitch` | what the printer feeds per label (SIZE height), not the label height |
| `gap` | length of the gap / mark / notch |
| `gapoff` | mm of plain liner between the label end and that gap |
| `left` | dead zone: mm of label left of x=0, unreachable |
| `right` | mm free on the right; equal to `left` = centered |
| `top` | mm from the bitmap origin to the label's top edge (may be negative) |
| `bottom` | mm free at the bottom; mirrors an unreachable top edge |
| `voffset` | shifts the whole print down (centering judged by eye) |
| `rows` | bitmap height in dots, overrides `pitch - 12` |
| `rotate` | 90 or 270: the design sideways; the bitmap still runs across the head |
| `sense` | `gap` (default) or `bline` |
| `xoffset` | mm between the head start (x=0) and the liner's left edge; needed when the roll begins right of the head |

### The six rolls that work now

| roll | size | roll line | pitch | geometry | result |
|---|---|---|---|---|---|
| AM11354 | 57 × 32 mm, landscape | — | 38.6 mm, gap 3 | `voffset=0.34` (4 dots), `left`/`right` default | printable 640 × 370 dots, judged "in the middle" by the user |
| AM99012 / Dymo S0722400 | 36 × 89 mm, **portrait** | — | 93 mm, gap 4 | `left=3 right=3 top=-0.5 bottom=1` | 30 × 88 mm, 3 mm white all around |
| S0929120 / Dymo 30332 | **25.5 × 25.5 mm** (1 inch; the label is neither 26 × 25 nor exactly 25 × 25) | 25.5 mm label + 4 mm liner + 3 mm notch + 5 mm liner | **36.97 mm** = `pitch 33.97 + gap 3` (canvas `rows=356`) | `left=1.5 right=3.0 top=1.9 voffset=4.5 bottom=3.5 rotate=270 rows=356` | **21.51 × 21.51 mm** square, measured white 2.00/1.99 mm and 2.03/1.96 mm |
| AM11353 / Dymo 11353 | block **2 × 12.5 × 25 mm** (2-up) | liner 30 mm: −3.5…26.5; rail 10.5; 34 + 3 = 37 mm pitch | **34 mm**, gap 3 (canvas `rows=354`) | `xoffset=-2 top=4.5 left=0 right=0 bottom=0` (2-up forces rotation 270) | physically calibrated with boxes + plumb line (12 Nov); both lanes centered, approved |
| S0904980 | **104.2 × 159.9 mm** shipping label (nominal 104 × 159) | pitch **162 mm** = 159 + 3 (vendor `SIZE 104,162`), gap 3, canvas 1901 (vendor 1902) | `left=0 right=2 top=0.6 bottom=0` — **max ink**; the vendor prints density 10, speed 4 | measured with `--markers` within 0.2 mm; frame proof on the CUPS route confirmed after top 0.08 → 0.6; 2 mm dead zone left, the same head-boundary as the square roll | approved 12 Nov |
| AM99017 | **21.31 × 49.93 mm** (nominal 21.3 × 52.5) | pitch **54.5 mm** — the vendor declares 55.5 and that is **wrong**; gap 4.5 mm = 0.5 liner + 3 hole + 1 liner | `LW_19.3x49.8` printable-area page ("AM99017 50x21.3 Hangmap"): `pitch=54.5 gap=4.5 gapoff=0.5 left=0 right=0 top=1.08 bottom=0 fit=fit` — page = box, raster 1:1 | label edges in bitmap mm: x −2.00..19.31 (2 mm dead zone left), y 1.08..51.01; the 1:1 page puts the ink on every reachable mm | approved 13 Nov; circle round after the letterbox fix (the CUPS stretch made it an ellipse) |

Matching label edges in bitmap coordinates (x = across the head, y = feed
direction):

- AM11354: x −2…55 mm, y 5.1…37.1 mm.
- AM99012: x −3…33 mm, y −0.5…88.5 mm.
- S0929120: x −2…23.5 mm, y 4.4…29.9 mm. The 2 mm on the left is unreachable;
  the reachable strip is therefore 23.5 × 25.5 mm and the largest centered
  square 21.5 mm.
- S0904980: x −2.0…102.2 mm (2 mm on the left unreachable, head boundary), y
  0.6…159.9 mm; ink band at maximum reach.
- AM99017: x −2.00…19.31 mm (2 mm dead zone left, same head boundary), y
  1.08…51.01 mm. The 1:1 page `LW_19.3x49.8` covers x 0…19.3, y 1.08…50.88:
  everything the head can reach, nothing it can't.

### PPD pitfalls (13 Nov)

- **Description convention**: `<label number> <h>x<w> <use> (<printable h>x<w>)`
  — e.g. `AM99017 50x21.3 Hangmap (49.8x19.3)`, `AM11354 32x57 Etiket
  (31.3x54.2)`. The parenthetical is what actually prints; the two numbers
  differ wherever dead zones or margins exist. Unmeasured built-in sizes
  keep their old descriptions (no roll number to lead with).
- A `*PageSize` **description may not contain a colon**: the CUPS parser
  keeps such an entry, Word's strict parser silently drops it from the
  Paper Size menu. Write `(1-op-1)`, not `(1:1)`.
- One roll, two modes: register the same dimensions twice with a suffix in
  the name (`LW_21.3x50` fit, `LW_21.3x50U` fit=stretch). Word groups
  same-dimension sizes into a submenu; `parse_size_name` tolerates the
  suffix, so the U variant resolves to its own `lw-media` line.
- The vendor's `SIZE height + GAP = pitch` rule is a **vendor claim, not
  physics**: AM99017 declares 55.5, the roll feeds 54.5 (gap 4.5 = 0.5 + 3
  hole + 1). Measure the pitch over two labels before registering.

### AM11353 / Dymo 11353: the roll begins LEFT of the head start (physically calibrated)

Labellife capture (10 November, en1 reached the printer via 172.16.1.133):

```
SIZE 25.6 mm,34 mm · GAP 3 mm,0 mm · DENSITY 15 · SPEED 6
BITMAP 0,0,160,354,4,,   PRINT 1,1
```

Old assumption — **physically refuted on 12 November**: the 1 mm ruler said
the liner started at x = 6 mm (block 7.5..32.5, cut line 20 mm). The first
printed sheets landed 10 mm too far right and 5 mm too early in the feed,
though; two 6 × 10 mm boxes were then neatly centered, and a 0.25 mm plumb
line on the supposed cut line (x = 10 mm) fell 0.5 mm **onto label A**. The
measured truth, since then in the PPD:

| | x in bitmap coordinates |
|---|---|
| liner | −3.5 … 26.5 mm |
| label A | −2.0 … 10.5 mm (the left 2.0 mm: dead zone before head-x=0) |
| cut rail A/B | 10.5 mm = dot 124 |
| label B | 10.5 … 23.0 mm |
| label top | row 53 = 4.5 mm below the bitmap origin (top=4.5) |
| label bottom | ~29.5 mm (frame row 348; test line 29.85 fell outside) |

The tangent test (lines at 3.99/29.85 mm) guards both flanks: the label top
lies in (4.0, 4.4], the bottom in [29.5, 29.9). With a 0.5 mm reading next to
a 0.25 mm line, that instrument decides — not the PPD.

`xoffset` is therefore **negative** here: the liner starts left of the head
start and the unreachable strip is clipped (CLI: `canvas.paste` with a
negative ox; filter: `pack_canvas` ignores `px < 0`). The pitch follows our
own rule again: `34 + 3 = 37 mm`, exactly like the vendor.

**2-up calibration lesson**: a single 3-dot plumb line on the expected seam
is the fastest measuring instrument for such a roll — one feed, one number,
no numbered scale that misleads when rotated. Re-seated the roll? Print the
plumb line again; it must sit in the groove.

## 6. CUPS raster (cgpdftoraster, "RaS3")

- Layout: `[4-byte sync "3SaR"] [1796-byte page header] [W*H bytes of gray]`
  and that repeats per page **without** the sync word. Anyone assuming 1800
  bytes per page reads page 2 as garbage (our first bug).
- Header-relative fields: `u32 @0x114` = dpi x, `@0x118` = dpi y, `@0x174` =
  width in pixels, `@0x178` = height.
- Pixels: 8-bit gray, 0 = black, 255 = white, rows unpadded (W bytes).
- `cupsBytesPerLine` sits at offset 0 of the header and is in practice 0;
  just count W.

## 7. What macOS/Word throws in the way

- Word does **not** send `media=LW_57x32` but `media=Custom.90.71x161.57`. The
  chosen PPD size lives in `com.apple.print.PageToPaperMappingMediaName`;
  the filter takes the roll size from there.
- Word sends `orientation-requested=4`, which makes `cgpdftoraster` rotate
  the page 90° **clockwise** into the raster. The filter rotates back; the
  direction was verified against the PDF image itself (correlation 0.455 vs
  0.000).
- Values with spaces are escaped (`job-name=Microsoft\ Word\ -\ x.docx`):
  split only on unescaped whitespace, otherwise invented options appear.
- Queue options (`lpadmin -o lw-gap=…`) beat the filter defaults; the queue
  sat on `lw-density=8` for a long time while the filter used 15.
- On an IPP queue macOS copies the server's PPD and sometimes renders
  locally; if the filter is missing there, the job fails. On a second Mac,
  simply run `install.sh`.

## 8. Valleys outside the printer

- `/usr/bin/python3` is a stub that, without the Xcode Command Line Tools,
  only opens an install dialog. The filter wrapper picks in order: CLT,
  Homebrew (arm64 + Intel), python.org, then the stub.
- `root` may not read `~/Documents`, `~/Desktop`, `~/Downloads` (TCC):
  "Operation not permitted". Install from `/Users/Shared/...`.
- `osascript … with administrator privileges`: `with prompt "…"` must come
  **after** `with administrator privileges`.
- `add-size.sh | head -2` gives SIGPIPE and bakes the PPD half-way.
- `pkill -f "tcpdump -i en"` also kills its own shell (the pattern is on the
  command line). Kill by PID.
- A test must never run `git checkout` on the working tree; ours quietly
  destroyed a just-measured roll that way.

## 9. Proof: what Labellife really sends

Sniffed twice with `tcpdump -i en0 tcp port 9100` on the square roll.
Word for word identical, only `DENSITY` followed the choice in the app:

```
SIZE 25 mm,33.97 mm
REFERENCE 0,0
GAP  3 mm, 0 mm
OFFSET 0 mm
DIRECTION 0,0
DENSITY 15
BITMAP 0,0,160,356,4,,<LZO variant>
PRINT 1,1
SPEED 4
```

What this capture yielded: the width in `SIZE` is the **label** (25 mm), the
height is the **feed minus the gap** (33.97 + 3 ≈ 37 mm), the canvas is
160 × **356** rows, and mode 4 is their own LZO variant (two commas after the
mode, then blocks). A cross that we print with `rows=356 pitch=33.97` falls
exactly on the cross of Labellife — verified by laying the two labels on top
of each other.

## 10. How to measure a new roll

1. `./measure <width> <height> --name LW_XxY [--pitch .. --gap ..] [--rotate ..]`
   prints one label with `0,0` in the middle of the expected printable area,
   1 mm (`--step` 2/5) ticks and the letters N/Z/W/O.
2. Read the four mm values on the real label's edges.
3. `./measure solve --N .. --Z .. --W .. --O .. [--pitch .. --gap ..]`
   converts them into `left`/`right`/`top`/`bottom`/`voffset` and writes the
   `add-size.sh` command.
4. Does the start position vary per feed? Measure the **pitch** over 10–20
   labels and make sure `SIZE height + gap` matches it exactly.
5. Doubting repeatability: print five separate feeds of the same image and
   lay them on top of each other.
6. **On a rotated or shifted roll: `--markers`.** `./measure <w> <h>
   --markers [--rotate 270]` prints one sheet with the frame ON the edges of
   the assumed printable area and one letter per side, crown toward its own
   edge; `./measure solve --T <mm> --B <mm> --L <mm> --R <mm>` converts the
   four white gaps (mapped per rotation per §4A: at 270 the T/B are the head
   side, L/R the feed). With `rotate`, the numbered scale of point 1 becomes
   unreadable — the letters N/Z/W/O then point the wrong way and figures on
   the liner are useless; three sessions of being stuck before one T/B/L/R
   sheet solved it in two prints. The sheets of §5 (boxes + plumb line) are
   the 2-up variation of this.
7. **Catch the vendor settings while you're at it**: tcpdump during a
   Labellife print (as root, on the interface the traffic takes:
   `tcpdump -i en0 -nn -s0 -w sheet.pcap -C 8 tcp port 9100`; `-i any` does
   not work in Apple's tcpdump), then
   `strings sheet.pcap | grep -aE 'SIZE|GAP|BITMAP|SPEED|DENSITY'`. The
   vendor pitch/gap usually equal the nominal + gap; DENSITY/SPEED are worth
   copying.
