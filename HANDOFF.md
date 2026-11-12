# Handoff — continuing work on this printer

Sessions of 9–12 November 2026. Everything is on GitHub; nothing is pending in
the workspace. Knowledge and measurements live in [`KNOWLEDGE.md`](KNOWLEDGE.md);
this file only carries **where we are and what the next step is**.

## Status

| | |
|---|---|
| repo | https://github.com/Gehaktbalbugger/lw650xl-label — **public** |
| releases | up to **v1.7** (Latest): v1.0 AM11354, v1.1 AM99012, v1.2 `./measure`, v1.3 S0929120, v1.4/v1.5 square roll, v1.6 AM11353 2-up calibrated, v1.7 `./measure --markers`; v1.8 staged on main (S0904980, `plumb`, unknown-roll bugfix) |
| rolls | **5 installed**: AM11354 (57×32), AM99012 (36×89 portrait), S0929120 (square, 2 mm all around), AM11353 (2-up block, calibrated), **S0904980 (104×159 shipping label, max ink)** |
| signed off | **AM99012, AM11354, AM11353 2-up, S0904980** by the user (12 Nov); square roll installed with 2 mm margins |
| iMac | filter + PPD installed and identical to the repo (`/usr/libexec/cups/filter/lw650xl.py`, `/etc/cups/ppd/LW650XL_Labels.ppd`) |
| tests | `python3 test_filter.py`, `test_measure.py`, `test_label.py` — all green |
| **Word route** | **tested end to end on 12 Nov and working** (S0904980 via the CUPS queue: frame + text + circle landed on the printable area) |
| MacBook | still **not** updated: `cd ~/label-printer && git pull && sudo ./install.sh` |
| `gh` CLI | lives in `~/.local/bin` (not on PATH): `export PATH="$HOME/.local/bin:$PATH"` |
| tooling | `brew` is broken on this Mac (write permissions on `/usr/local/share/man/man8`) — download directly |

Five rolls in the driver: AM99012 and AM11354 are signed off, S0929120 is
installed with 2 mm margins, AM11353 is calibrated and approved as 2-up
(v1.6), S0904980 is measured and approved (staged for v1.8).

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

Stopping here. Continuity for the next context: releases up to **v1.7** are on
GitHub (v1.8 staged on main), the repo is **public**, and everything measured
is recorded in KNOWLEDGE.md and CHANGELOG.md — nothing needs to be re-shown.
Nothing was broken this session: the iMac runs the state above, the MacBook
waits for `git pull && sudo ./install.sh`.

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

## What is on the iMac now (v1.7 released; v1.8 staged, installed, signed off)

- **driver**: 5 rolls installed — AM11354, AM99012, S0929120 (2 mm all
  around), AM11353 as block with the **calibrated** line
  `LW_25x25 pitch=34 gap=3 rows=354 xoffset=-2 top=4.5` and **S0904980** with
  `LW_104x159 pitch=162 gap=3 left=0 right=2 top=0.6 bottom=0` (max ink;
  filter and PPD installed via `install.sh`, md5s identical to the repo).
- AM99012, AM11354, the AM11353 2-up and S0904980: approved by the user.
- The **Word route verified end to end** (S0904980): prints correctly through
  the CUPS queue.
- Releases up to **v1.7** (v1.8 staged on main); repo **public**.

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
- Eight PPD sizes have never been measured on a real roll (104x159 is
  measured: S0904980, 12 Nov).
