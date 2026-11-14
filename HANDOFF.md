# Handoff — continuing work on this printer

Sessions of 9–12 November 2026. Everything is on GitHub; nothing is pending in
the workspace. Knowledge and measurements live in [`KNOWLEDGE.md`](KNOWLEDGE.md);
this file only carries **where we are and what the next step is**.

## Status

| | |
|---|---|
| repo | https://github.com/Gehaktbalbugger/lw650xl-label — **public** |
| releases | **up to v1.9** (Latest): v1.0 AM11354, v1.1 AM99012, v1.2 `./measure`, v1.3 S0929120, v1.4/v1.5 square roll, v1.6 AM11353 2-up calibrated, v1.7 `./measure --markers`, v1.8 S0904980 + `plumb` + unknown-roll bugfix, v1.9 AM99017 + letterbox fit |
| rolls | **6 installed**: AM11354 (57×32, 1:1 portrait page), AM99012 (36×89 portrait), S0929120 (square, 2 mm all around), AM11353 (2-up block, 1:1 portrait page `LW_23x25`), S0904980 (104×159 shipping label, max ink), **AM99017 (21.3×50, 1:1 printable-area page)** |
| signed off | **AM11354, AM11353, S0929120, AM99017** as single 1:1 pages (14 Nov); AM99012 and S0904980 approved on their original pages |
| iMac | filter + PPD installed and identical to the repo (`/usr/libexec/cups/filter/lw650xl.py`, `/etc/cups/ppd/LW650XL_Labels.ppd`) |
| tests | `python3 test_filter.py`, `test_measure.py`, `test_label.py` — all green |
| **Word route** | **tested end to end on 12 Nov and working** (S0904980 via the CUPS queue: frame + text + circle landed on the printable area) |
| MacBook | still **not** updated: `cd ~/label-printer && git pull && sudo ./install.sh` |
| `gh` CLI | lives in `~/.local/bin` (not on PATH): `export PATH="$HOME/.local/bin:$PATH"` |
| tooling | `brew` is broken on this Mac (write permissions on `/usr/local/share/man/man8`) — download directly |

Six rolls in the driver: AM99012 and AM11354 are signed off, S0929120 is
installed with 2 mm margins, AM11353 is calibrated and approved as 2-up
(v1.6), S0904980 is measured and approved (v1.8), AM99017 is measured,
registered with the printable-area page and approved (v1.9).

## AM99017: 21.3 × 50 mm roll with a lying vendor pitch (13 Nov, approved)

A small portrait roll (vendor nominal 21.3 × 52.5) that exposed two problems
at once: the vendor's declared feed is wrong, and the label is small enough
that the fixed 4 mm of unreachable strip becomes 19% of the page.

1. **Vendor captured with tcpdump** (`workflow/am99017-vendor.pcap`): four
   identical feeds — `SIZE 21.3 mm,52.5 mm · GAP 3 mm,0 mm · REFERENCE 0,0 ·
   DENSITY 10/15 · SPEED 4/1 · BITMAP 0,0,160,612,4`. DENSITY/SPEED follow the
   app's quality choice, as on every roll. **The declared pitch (52.5 + 3 =
   55.5) is wrong**: the physical pitch is **54.5 mm** (measured top edge →
   top edge). The physical gap is 4.5 mm — 0.5 mm liner, 3 mm sensor hole
   (that is the GAP 3), 1 mm liner — so the label is **50.0 mm** long. The
   "SIZE height + GAP = pitch" rule held on five rolls and fails on this one:
   measure the pitch over two labels before trusting the vendor numbers.
2. **Measured with `--markers`**: two passes (the roll was re-seated in
   between, the right edge moved ~0.7 mm — the left dead zone stayed at 2 mm).
   Final: label **21.31 × 49.93 mm**, bitmap span x −2.00..19.31, y 1.08..51.01
   — the familiar 2 mm dead zone on the left again, and the top edge ~1 mm
   inside the bitmap.
3. **The CUPS proof printed a circle as an ellipse — root cause found**: the
   filter stretched the full-page raster onto the printable box axis by axis
   (`scale_to_box`). This roll's box is 17.3 mm of a 21.3 mm page → 19%
   horizontal squeeze (the L/R frame lines read 4 mm instead of 2; S0904980
   never showed it at 2%). **Fix (v1.9)**: `scale_to_box` now fits uniformly
   (letterbox, centred horizontally, top-anchored). Selectable per roll with
   `fit=stretch` in the `lw-media` line or per job with `-o lw-fit=stretch`
   — the old behaviour stays reachable. Word selects between the two via
   two page sizes with the same dimensions (`LW_21.3x50` fit /
   `LW_21.3x50U` stretch); Word groups same-dimension sizes into a submenu.
4. **The clean answer is a page that IS the printable area**: final
   **`LW_19.3x49.8` "AM99017 50x21.3 Hangmap (49.8x19.3)"**: (description convention: label number, paper format, use)
   `pitch=54.5 gap=4.5 gapoff=0.5 left=0 right=0 top=1.08 bottom=0 fit=fit`.
   The page equals the box exactly (228 × 588 dots at 300 dpi), so the
   raster goes through `scale_to_box` at scale 1.0: **circle round, ink to
   every reachable edge, zero whitespace, WYSIWYG in Word**. The 2 mm dead
   zone and the 0.13 mm bottom reserve are outside the page by construction.
   Iterated 49.2 → 50.2 (overshot, ink would touch the liner) → 49.8
   (box bottom at bitmap 50.88 vs the measured edge 51.01). Approved by the
   user as "perfect".
5. **PPD lessons**: a UI description may **not contain a colon** —
   "(1:1)" made Word's strict parser silently drop the whole PageSize entry
   while CUPS kept it ("colon-free text) fixed it). `parse_size_name` now tolerates
   a trailing suffix (`LW_21.3x50U`) so one roll can expose both modes;
   before the fix the U variant fell into the unknown-media path and got
   size 49.9 × 21.3 with pitch 21.3.

## The square roll: state of play

Centering is done: **21.51 × 21.51 mm with 2 mm of white all around**. The
label turned out to measure **25.5 × 25.5 mm** (1 inch), not 26 × 25 as the
packaging and our first advice suggested; the reachable strip is 23.5 × 25.5 mm
because 2 mm falls left of x=0.

White measured by the user: left 2.00 / right 1.99 / top 2.03 / bottom
1.96 mm. Geometry in the PPD: `left=1.5 right=3.0 top=1.9 voffset=4.5
bottom=3.5 rotate=270 rows=356 pitch=33.97 gap=3`.

The square fills 84% of the reachable width. Gaining more is only possible by
shrinking that dead zone (options 1 and 2) or by giving up the square and
using the full 23.5 mm strip with slanted white.

### Tracks to pick up next, in order of promise

1. **`SHIFT`** — the firmware accepted `SHIFT 0` (no `Cmd error`), but we
   never tried what it does. Question: does it move the head start in dots?
   Test without burning labels:
   `printf '\r\nSHIFT 18\r\n' | nc -w2 172.16.1.20 9100` and then print one
   square; if the left margin gets less white, this is the knob to win the
   dead zone back. Also try `SHIFT -18` and `SHIFT 400`.
2. **Mechanical**: the roll rests against the left guide. If 1.5 mm of play
   can be added there (thicker ring, a piece of liner as spacer), the whole
   label moves toward the middle of the head and you win the same 1.5 mm
   back — without firmware and for every roll of this size.
3. **No centering**: set `right` to 0 (`-o lw-right=0` or in the PPD) gives
   24.5 × 25 mm of ink with 1.5 mm of white left and none right. If the user
   prefers "maximal" over "centered", this is a single number.
4. **Reconsider label rotation**: it prints `rotate=270` (sideways, like
   Labellife). `rotate=0` is also possible; readings then stay in the same
   direction as the PPD dims, which is easier to reason about.

## To do / to ask

- Update the MacBook (command above) and print one label per roll there.
- Further sizes: the PPD carries 8 sizes that have **never been measured on a
  real roll** (102x59, 101x54, 89x36, 89x28, 54x25, 50x12, 57x57, 62x100).
  They have no `lw-media` line, so their pitch is "height + 3 mm" and their
  side margin is the default. As soon as such a roll is actually loaded:
  measure with `./measure <w> <h> --markers --pitch <vendor> --gap <gap>`,
  then `add-size.sh` with the measured values, then `install.sh`.
- Regression: the margins of the known-good rolls live only in KNOWLEDGE.md.
  A table test that extracts the ink bbox from the generated TSPL per roll and
  compares it to the expected margins would catch drift in `print_window`
  instantly — right now that needs a manual print.
- `./measure` cannot derive the **pitch (steek)** from the cross/sheet; that is
  still ruler work. Idea: `PRINT 20,1` with an empty bitmap, then measure the
  20 fed labels (total length / 20) and feed that number to `solve` as
  `--pitch`. Still to be built.

## Working with this repo

```bash
cd ~/Documents/Standaardproject/label-printer    # or on the MacBook: ~/label-printer
git pull
python3 test_filter.py && python3 test_measure.py && python3 test_label.py

# measure a roll (don't print unnecessarily: --preview or --dry-run)
./measure 26 25 --name LW_26x25 --step 5 --preview /tmp/x.png
./measure 26 25 --name LW_26x25 --step 5
./measure solve --N -8 --Z 17 --W -13 --O 13 --pitch 34 --gap 3

# register and install a roll (root; copy the source to /Users/Shared first)
./add-size.sh LW_26x25 "Square multipurpose 26x25 mm" 26 25 \
    --pitch 34 --gap 3 --left 1.5 --right 1.45 --top 0 --voffset 5.1 --bottom 1.95 --rotate 270
rsync -a --exclude .git --exclude .DS_Store ./ /Users/Shared/Labelprinter/setup/
sudo /Users/Shared/Labelprinter/setup/install.sh

# print for verification
lp -d LW650XL_Labels -o media=LW_26x25 /tmp/label.pdf
./label "test" --size 26x25                      # CLI/Excel route, own path
```

After every install, check that the machine really runs the same files as the
repo (this bit us twice this session, both times through a forgotten `rsync`):

```bash
md5 -q cups/lw650xl.py            /usr/libexec/cups/filter/lw650xl.py
md5 -q cups/lw650xl-labels.ppd    /etc/cups/ppd/LW650XL_Labels.ppd
grep -n "lw-media" /etc/cups/ppd/LW650XL_Labels.ppd
lpoptions -p LW650XL_Labels -l | head -2          # sizes + default
```

CUPS copies the PPD literally, so the `*% lw-media` lines must be there too;
if they are missing, the source PPD or the copy step is wrong.

Two pitfalls that cost this session time (full list: KNOWLEDGE §8):

- `install.sh`/`setup.sh` must run from `/Users/Shared/Labelprinter/setup`;
  root cannot read `~/Documents`.
- After every PPD change: `rsync` **and** `install.sh`. The queue and the
  filter read `/etc/cups/ppd/LW650XL_Labels.ppd`, not the repo.

## Cutting a release

```bash
export PATH="$HOME/.local/bin:$PATH"
git add -A && git commit -F <message>
git tag -a v1.8 -m "<short summary>" && git push origin main v1.8
gh release create v1.8 --title "…" --notes-file <(sed -n '/## 1.8/,/## 1.7/p' CHANGELOG.md | sed '$d')
```

Keep `CHANGELOG.md` up to date: per release the measured values and the reason
behind them, because those numbers are untraceable from the code otherwise.

## Next session in a fresh context

1. Clone or pull the repo (github.com/Gehaktbalbugger/lw650xl-label, public),
   then open `HANDOFF.md`. The --two/2-up branch is **fixed, calibrated,
   installed and signed off in v1.6** — no physical test pending except the
   MacBook (point 3).
2. **Done (12 Nov):** the T/B/L/R marker sheet lives in `./measure` as
   `--markers` (+ `solve --T --B --L --R`), with the §4A rotation mapping in
   `MARKER_EDGES` and 16 checks in `test_measure.py`. Physically tested on the
   AM11353: the L line was absent as predicted (frame at x −2.03 = unreachable,
   the negative-clip works), R and B read 0 = calibration confirmed; solve
   reproduced `xoffset −2.0` and size 25.0. The `--gap` inference was then
   removed from markers-solve (it was wrong: 8.5 instead of 3 — there is
   extra liner around the notch). **Tangent test closed (12 Nov)**: test
   lines at 3.99 and 29.85 mm both fell OUTSIDE the label, the anchors at
   4.49/29.46 landed on it → label ≈ 4.0..29.5+ (height ~25.0-25.3), the
   calibrated band 4.49..29.46 closes all around. The marker sheet's T=0.5
   was reading noise; `top` stays 4.5 and there is no `h=25.5` win. Lesson
   for next time: with a 0.5 mm reading next to a 0.25 mm line, print the
   tangent first, then touch the PPD.
3. **Done (12 Nov):** the **Word route tested end to end and working**
   (S0904980 via the CUPS queue).
4. Update the MacBook: `cd ~/label-printer && git pull && sudo ./install.sh`,
   then print one label per roll there.
5. Only then the rest: "Tracks to pick up next", "To do / to ask" and the
   points under "What is on the iMac now".

Stopping here. Continuity for the next context: releases up to **v1.8** are
on GitHub, the repo is **public**, and everything measured is recorded in
KNOWLEDGE.md and CHANGELOG.md — nothing needs to be re-shown. Nothing was
broken this session: the iMac runs the state above, the MacBook waits for
`git pull && sudo ./install.sh`.

## FIXED: label --two printed almost nothing (v1.6; physically calibrated, approved)

A physical sheet on the square roll produced "a few pixels" instead of two
labels. The bug sat in the **--two composition of the CLI**, not in the roll
and not in the filter.

**The bug** (proven 10 Nov): the composition ran in **canvas coordinates** —
`Image.new("L", (box[3] * 2, box[2]))` = **590 × 287 dots** instead of the
**295 × 288 design dots** — and dropped the rotation. The two halves were
pasted at (0,0) and (295,0), i.e. 0..590 dots across the head; the image
therefore fell mostly outside the label — on paper: "a few pixels". A third
bug on the same branch: the single-label rotation crash (`args.box` became a
3-tuple while `render_label` unpacks 4) — `--rotate 270` had always crashed.

**The fix** (applied exactly as prescribed): compose in the DESIGN frame, two
half pages stacked, then apply the single-label rotation (270°; the top half
becomes the left column, the bottom the right — as csv2labels promises).
In `label`:

```python
ox, oy, ch, cw = args.box            # window: (-24, 53, 295, 295) after calibration
half = ch // 2                       # half page: 295 × ~144 dots
a2.box = (ox, oy, half, cw)
img = Image.new("1", (cw, ch), 1)    # design frame, not canvas
img.paste(e_boven, (0, 0))           # label A (left column after rotation)
img.paste(e_onder, (0, half))        # label B (right column after rotation)
img = img.rotate(-rot, expand=True)  # the single-label rotation, rot=270 for 2-up
```

**Then the roll geometry also turned out different** (12 Nov, three feeds):
the first composed sheet landed 10 mm too far right and 5 mm too early — the
old liner assumption (7.5..32.5 mm) had never been physically proven by a
print. 6 × 10 mm boxes were centered with `xoffset=-2,5 top=4,5`; a 0.25 mm
plumb line pinned the cut rail at **10.5 mm** → final `xoffset=-2`. A negative
xoffset clips the unreachable 2 mm of lane A (`content_box`/`print_window`/
`pack_canvas` were adapted for that).

**Smoke test captured** (`test_label.py`, catcher + bits check): canvas
160 B × 354 rows like the vendor, ink within 0..271 dots, both half columns
carry ink, the cut line is white, rows < 53 and ≥ 348 are empty. Fixed along
the way: `--two` text now also replaces `\n` (per the csv2labels
documentation), and the CLI flags `--rows/--rotate/--xoffset/--sense/--gapoff`
were always reset to None after argparse — that reset is gone; `--media-bottom`
and `--media-right` now actually reach the print plane.

**Signed off**: installed on the iMac (rsync + `install.sh`, identical md5s),
the Anna/Piet sheet approved — both labels centered, text sideways like the
vendor app. Per roll change: re-print the plumb line as recalibration
(KNOWLEDGE §AM11353).

## S0904980: shipping label measured and registered (12 Nov, approved)

The roll Labellife could already print — our task: turn the PPD size
`LW_104x159` (one of the nine unmeasured ones) into physical truth:

1. **Vendor captured with tcpdump**: `SIZE 104 mm,162 mm · GAP 3 mm,0 mm ·
   DENSITY 10 · SPEED 4 · BITMAP 0,0,160,1902,4` — pitch 162 = 159+3 ✓,
   canvas 1901 (vendor 1902). Recipe: `tcpdump -i en0 -nn -s0 -w sheet.pcap
   -C 8 tcp port 9100` (root; `-i any` does not work in Apple's tcpdump),
   then `strings sheet.pcap | grep -aE 'SIZE|GAP|BITMAP|SPEED|DENSITY'`.
2. **`./measure 104 159 --markers --pitch 162 --gap 3`** → four readings →
   `solve`: measured **104.2 × 159.9 mm** (within 0.2 of the nominal!),
   label lines x −2.0..102.2 (the same 2 mm dead zone on the left as the
   square roll), y 0.08..159.95 (the label starts almost at the bitmap origin).
3. **Registered at max ink**: `left=0 right=2 top=0.6 bottom=0` — ink to the
   edges, only the unavoidable dead zone on the left.
4. **Frame proof via the CUPS route** (first time on this roll!): frame on
   the printable boundary, text, circle Ø 51 mm. The top frame line fell off
   at `top=0.08` (0 margin next to a 0.5 mm line) → safety margin `top=0.6`
   → everything inside. Lesson: never set a 0 margin on a first roll;
   0.5–0.6 is the lower bound.

## What is on the iMac now (v1.9 installed; AM99017 signed off)

- **driver**: 6 rolls installed — AM11354, AM99012, S0929120 (2 mm all
  around), S0929120 (square) with the **printable-area portrait page** `LW_23.5x25.5
  pitch=33.97 gap=3 rows=356 left=0 right=0 top=4.4 bottom=0 rotate=0
  fit=fit` (14 Nov — page = the reachable strip, full-bleed capable; the
  old centered 21.5 mm page `LW_26x25 rotate=270` was removed),
  AM11353 with the **calibrated** geometry, since 14 Nov as the
  **printable-area portrait page** `LW_23x25 pitch=34 gap=3 rows=354
  left=0 right=0 top=4.1 bottom=0 fit=fit` (23 mm = the reachable strip;
  the old full-block `LW_25x25 xoffset=-2` page was removed; the user
  designs the two 12.5 mm labels themselves, cut groove at page-x 10.5,
  WYSIWYG; top converged 4.5 → 3.7 → 4.1 by print iteration — the
  leading-edge offset is seating-dependent), **S0904980** with
  `LW_104x159 pitch=162 gap=3 left=0 right=2 top=0.6 bottom=0` (max ink),
  **AM99017** with the printable-area page
  `LW_19.3x49.8 pitch=54.5 gap=4.5 gapoff=0.5 left=0 right=0 top=1.08
  bottom=0 fit=fit`, and **AM11354** (13 Nov evening) with the
  **portrait-authored** printable-area page
  `LW_31.3x54.2 pitch=38.6 gap=3 left=0 right=0 top=5.42 bottom=0 fit=fit
  w=54.2 h=31.3` (the old full-label page `LW_57x32` and the intermediate
  landscape-authored `LW_54.2x31.3` were removed from the menu).
- **Word orientation toggle** (works for AM99017 and AM11354): Word only
  offers the straight/landscape switch on portrait-dimensioned pages, so a
  landscape roll that wants it carries a portrait page whose `lw-media`
  line overrides the label size with `w=`/`h=`. The filter's orient-swap
  then maps both Word orientations 1:1 onto the printable box:
  **landscape = content upright on the label**, **straight = content
  rotated 90° clockwise** (reads sideways). Both AM11354 orientations are
  regression-tested (`test_filter.py` §9); the sideways direction is not
  yet user-confirmed — if it should read the other way, that is a
  `rotate=180` feature to add.
- Both AM99017 comparison variants (scaled `LW_21.3x50`, stretch
  `LW_21.3x50U`) were removed after testing — the fit=stretch mechanism
  remains in the filter.
- AM99012, AM11354, the AM11353 2-up, S0904980 and AM99017: approved by the
  user (13 Nov).
- **Filter v1.9**: `scale_to_box` fits uniformly (letterbox) instead of
  stretching; `fit=stretch` per roll or `-o lw-fit=stretch` per job brings
  the old behaviour back. Word's Custom-size path and `parse_size_name`
  tolerate size-name suffixes.
- The **Word route verified end to end** (S0904980, and AM99017 through the
  1:1 printable-area page): prints correctly through the CUPS queue.
- Releases up to **v1.9**; repo **public**.

## Still open at the start of the next session

- AM11353: the left **2.0 mm of lane A** falls left of head-x=0 and is
  clipped. `SHIFT` (below) might win that strip back — start the head
  24 dots later.
- `SHIFT` is accepted by the firmware (`SHIFT 0` gave no `Cmd error`) but has
  never been tested. If it shifts the head start sideways, you win ~2 mm.
- The spacing cap on the right of the roll as a mechanical alternative.
- Marker mapping for `rotate=90` is in `MARKER_EDGES` as the mirror of 270
  but is still **uncalibrated**; measuring a rotated roll with `--markers`
  for the first time = physical confirmation of the map.
- Rest point: on the square roll the exit side (your right) has 0.00 mm of
  reserve. If that line ever gets too tight, raise `bottom` by 0.5 mm — not
  `voffset`.
- Side effect of the same measurement: the square label is 25.5 mm long in
  the feed direction but the PPD name `LW_26x25` carries 25 mm, so 0.5 mm
  stays unused. A `w=`/`h=` override in `lw-media` is the clean fix.
- The eight unmeasured built-in PPD sizes were **removed from the PPD** on
  13 Nov (v1.9): Word's Paper Size menu now only offers measured rolls. They
  return the same way as any roll: measure the physical roll, then
  `add-size.sh`.
