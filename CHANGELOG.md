# Changelog

## 1.9 — AM99017 registered; letterbox fit; printable-area page (13 Nov, installed)

- New roll **AM99017** (21.31 × 49.93 mm, vendor nominal 21.3 × 52.5): vendor
  captured with tcpdump (`SIZE 21.3,52.5 · GAP 3 · BITMAP 0,0,160,612,4`),
  but **the declared pitch 55.5 is wrong** — the physical pitch is
  **54.5 mm** (measured over two labels). Physical gap 4.5 mm (0.5 liner +
  3 hole + 1 liner) → label 50.0 mm. First roll where the
  "SIZE height + GAP = pitch" rule fails: measure the pitch.
- **The letterbox fix**: the CUPS proof printed a circle as an ellipse — the
  filter stretched the page onto the printable box axis by axis; on this
  roll that is a 19% horizontal squeeze (4 mm of a 21.3 mm page; the
  shipping roll hid it at 2%). `scale_to_box` now fits **uniformly**
  (letterbox, centred horizontally, top-anchored). The old behaviour stays
  selectable: `fit=stretch` in the `lw-media` line, `-o lw-fit=stretch` per
  job, or — from Word — the `LW_21.3x50U` size (Word groups the
  same-dimension pair `LW_21.3x50`/`LW_21.3x50U` into a submenu).
- **The printable-area page** (the user's pick): `LW_19.3x49.8
  "AM99017 50x21.3 Hangmap (49.8x19.3)"` — page = printable box exactly
  (`left=0 right=0 top=1.08 bottom=0`), raster maps 1:1, so circles stay
  round, the ink reaches every reachable edge and Word is WYSIWYG. Iterated
  49.2 → 50.2 → 49.8 (box bottom at bitmap 50.88 vs the measured edge
  51.01). One page size per roll that wants max ink: put the dead zone and
  the reserve outside the page.
- **PPD fixes**: a PageSize description may **not contain a colon** —
  `(1:1)` made Word silently drop the entry while CUPS kept it;
  `parse_size_name` now tolerates a trailing suffix so one roll can expose
  two modes (`LW_21.3x50U`) — before the fix the U name fell into the
  unknown-media path (size 49.9 × 21.3, pitch 21.3).
- **AM11354 gets the same treatment** (13 Nov evening): the full-label page
  `LW_57x32` is replaced by the 1:1 printable-area page — authored
  **portrait** as `LW_31.3x54.2` with `w=54.2 h=31.3` in the roll line, so
  Word offers the straight/landscape toggle (landscape = upright on the
  label, straight = rotated 90° clockwise). User confirmed the direction.
- **S0929120 (square) to a 1:1 page** (14 Nov): `LW_23.5x25.5` replaces
  `LW_26x25` — the page is the reachable strip (the 25.5 mm label minus
  the 2 mm dead zone) with `rotate=0` instead of 270; full-bleed capable,
  WYSIWYG, portrait-authored so Word offers the orientation toggle. The
  approved centered-square look is now the user's own 2 mm page margins.
- **AM11353 as a single Word page** (14 Nov): the user no longer uses the
  built-in 2-up composition — they design both 12.5 × 25 labels on one
  page. New printable-area portrait page `LW_23x25` (23 mm = the reachable
  strip; cut groove at page-x 10.5) replaces `LW_25x25`; `top` converged
  4.5 → 3.7 → 4.1 by print iteration (the leading-edge offset is
  seating-dependent). `./label --two` still composes 2-up on its own.
- Post-testing cleanup: both comparison variants (`LW_21.3x50` scaled,
  `LW_21.3x50U` stretch) were removed from the queue; the user kept only
  the 1:1 page. The fit=stretch mechanism stays in the filter for future
  rolls.
- Tests: `test_filter.py` (letterbox + fit/stretch + suffix), `test_label.py`
  and `test_measure.py` all green; the vendor capture is archived at
  `workflow/am99017-vendor.pcap`, the story in HANDOFF §AM99017.

## 1.8 — S0904980 registered; `plumb` mode; unknown-roll bugfix (13 Nov, installed)

- New roll **S0904980** (104.2 × 159.9 mm shipping label): vendor captured with
  tcpdump (`SIZE 104,162 · GAP 3 · DENSITY 10 · SPEED 4`), measured with
  `--markers --pitch 162 --gap 3` (within 0.2 mm), registered at
  **max ink**: `left=0 right=2 top=0.6 bottom=0`, canvas 1901 (vendor 1902).
  Frame proof via the CUPS route confirmed it after `top 0.08 → 0.6`: a
  0 mm margin next to a 0.5 mm line falls off — 0.5-0.6 mm is the lower
  bound (lesson already known from the tangent test, now confirmed on a
  second roll).
- **`./measure plumb`**: the cut plumb line as a fixed command — line in the
  expected cut groove plus dots on the lane centers; `--report <mm>` converts
  the deviation (positive = line on A) directly into the new `xoffset` and
  prints the `add-size.sh` command. 5 checks.
- **Bugfix** `resolve_geometry`: for rolls without an `lw-media` line the
  opts map carried **no media key**, so `media_geometry` normalized the page
  size to the long side ("long side is label width" — meant for Word
  portraits). Every `./measure <w> <h>` on an unmeasured PPD size with
  height > width came out sideways/wrong on paper — the S0904980 marker
  sheet revealed it (frame x 0..108.4 = full head, y up to 103). Now
  `media=<LW_bxh>` is always sent; swap check in `test_measure.py`.
- On unknown rolls the default pitch stays `height` (not height+gap): pass
  the vendor pitch explicitly on the first measurement (`--pitch 162
  --gap 3` for S0904980), or register first via `add-size.sh`.
- The tcpdump recipe for the vendor capture is in HANDOFF §S0904980.

## 1.7 — `./measure --markers`: the T/B/L/R sheet as a command (12 Nov, installed)

- New mode in `./measure`: `--markers` prints **one sheet** with the frame
  exactly on the edges of the assumed printable area plus one letter per side
  (T B L R), each with its crown toward its own label edge. The letters are
  drawn in **canvas coordinates** and placed 1:1 on the window with
  `lw-orient=off` + `lw-rotate=0` — no scale distortion and no N/Z/W/O
  direction confusion at `rotate=270` (the lesson of §4A/§10).
- `./measure solve --T <mm> --B <mm> --L <mm> --R <mm>` reads the four white
  gaps between frame and label edge; `MARKER_EDGES` maps them back per
  rotation to head-direction/feed (270: T/B→left/right, L/R→top/bottom;
  the 90 mapping sits there as the mirror image, still **uncalibrated**).
  Output: measured size, label lines in bitmap mm, center correction and the
  `add-size.sh` command (including `--xoffset` on a shifted roll, and the
  reminder for the plumb-line sheet).
- Filter: `lw-orient=off` switches off the auto-orientation rotation (needed
  for a raster that is already window-shaped in canvas orientation). On by
  default, so nothing changes for printing via Word/CLI.
- `test_measure.py`: 15 new checks — state, frame==window, raster size 1:1,
  rot0 and rot270 conversions, missing letters = error.
- Physically tested on the AM11353 (on main, after the tag): the frame line
  of the unreachable L edge is absent — so the negative-xoffset clip works
  on paper; R/B at 0 mm confirm the calibration. Then the
  `gap = pitch − height` inference was removed from markers-solve (too
  optimistic on rolls with extra liner around the notch): a separate
  `--gap` note instead.

## 1.6 — AM11353 2-up fixed and physically calibrated (12 November, approved)

- `label --two` now composes in the **DESIGN frame** (295 × 287/288 dots),
  as two half pages of 295 × ~144 dots stacked, and only then applies
  **the single-label rotation** (270°): top half → left column, bottom →
  right. The old build was canvas coordinates (590 × 287) without rotation;
  the image fell mostly outside the block (7.5..32.5 mm) — on the sheet,
  "a few pixels". 2-up forces 270° when the PPD gives no rotation, because
  two half lanes of 12.5 mm side by side are always sideways.
- **Bug in the rotation branch** taken along: `args.box` was turned into a
  3-tuple while `render_label` unpacks 4 values — so every `rotate=270`
  print via the CLI crashed ("not enough values to unpack"). Now a clean h/w
  swap; the rotated image lands exactly in the measurement window (tested on
  the square roll: canvas 356, ink inside the x/y window).
- Smoke test in `test_label.py`: the catcher (TCP listener) grabs the wire
  bytes and the bits check verifies for AM11353: BITMAP 160 B × 354 rows
  (like the vendor capture), ink within 0..271 dots, both half columns carry
  ink, the cut line stays white and the white bands before row 53 and after
  row 348 (top=4.5 mm) are empty.
- Two CLI wires repaired: `--rows/--rotate/--xoffset/--sense/--gapoff` were
  unconditionally set to `None` after argparse, so PPD hints always overrode
  user flags; and `--media-bottom`/`--media-right` did nothing — they now
  reach the print plane. `--two` text now also replaces `\n` for line breaks,
  as csv2labels documents.
- **Physical calibration of the roll** (3 feeds, 12 Nov): the old liner story
  (x 6..36, block 7.5..32.5, rail 20 mm — 1 mm ruler + Labellife) was wrong;
  the first sheet landed 10 mm too far right and 5 mm too early. Two 6 × 10 mm
  boxes were centered after xoffset −2.5/top 4.5; a 0.25 mm plumb line pinned
  the rail at **x = 10.5 mm** → final `xoffset=-2 top=4.5`. See KNOWLEDGE
  §AM11353; lesson: one cut-line plumb calibrates a 2-up roll.
- **Negative xoffset** is now a legal concept: `content_box` (CLI) and
  `print_window` (filter) clip the unreachable strip left of head-x=0;
  `pack_canvas` ignores pixels with `px < 0` (it used to negative-index!).
  `test_filter` 6a and the smoke test run on the measured numbers.
- Installed on the iMac (`install.sh`, filter/PPD md5 identical to the repo);
  `./label --two` without flags composes 295 × 295 from the installed PPD
  rules. Sheet approved by the user.

## 1.5 — square roll installed at maximum width; coordinates final

- The S0929120 roll was measured and **installed** at the maximum rectangle:
  `pitch=33.97 gap=3 rows=356 left=1.5 right=1.4 top=1.9 voffset=2.5 bottom=0
  rotate=270` → printable area 23.03 × 24.98 mm, white 2.00 mm at the top
  (unreachable), 0.47 mm at the bottom, 0.00 / 0.61 mm along the feed.
- The first R/S frame line ran off the label; `right` 0.95 → **1.4 mm** fixes
  that without measurable loss.
- **Coordinates solved with a corner sheet** (P/Q/R/S): a user sees left/right
  along the **canvas y axis** (the feed direction), up/down along the canvas
  x axis. A normally drawn design comes out upright on the label after
  `rotate=270`: no design rotation needed in Word or Excel.
- The exit side is the **smallest canvas y**. An earlier, misread "+y
  confirmation" is explicitly retracted in the documentation.
- New: **`test-print.sh`** — the same proof prints with per-job options
  (`--status`, `--flush`, `--final`) and `--commit` to then put them into the
  PPD and install. That way a test needs no admin rights.
- Two pitfalls recorded in `KNOWLEDGE.md`: sending a canvas page through
  `convert()` scales the whole measurement image back (distorted sheet), and
  `26 × 11.811` dots in a 295-dot design falls off the edge (unreadable
  arrow). Diagnostics now name positions only as canvas numbers or corner
  letters.
- `./measure` gained `--rows`/`--rotate`; `KNOWLEDGE.md` §4A now carries the
  measured mapping, `HANDOFF.md` the installed state and the rest points.

## 1.4 — square roll centered, measuring tools extended, knowledge documented

- The square roll was measured and centered: the label is **25.5 × 25.5 mm**
  (1 inch), not 26 × 25 as the packaging and our first advice said.
  2 mm left of x=0 is unreachable, so the largest centered square is
  21.51 mm with 2 mm of white all around.
- `lw-media` gained four fields: `rows` (bitmap height in dots; Labellife
  sends 356 for this roll), `rotate` (90/270: the design sideways, like the
  vendor app), `sense` (`gap`/`bline`) and `gapoff` (mm of liner between the
  label end and the gap). `add-size.sh` and the `label` CLI follow that.
- The PPD parser now also stores non-numeric values (`sense=bline`); until
  then a silent `GAP` was sent.
- `./measure`: `--rows`, `--rotate` and a `ladder` mode (numbered bands over
  one feed) for rolls whose start position is unknown.
- The rule that explains everything, now documented: **`SIZE height + GAP` is
  the distance per label**. Labellife sends `SIZE 25 mm,33.97 mm` +
  `GAP 3 mm` = 36.97 mm, exactly the measured pitch; overlaying our cross on
  theirs shows the same position.
- The test that damaged the working tree (`git checkout` on the PPD) now runs
  on a copy via `LW_PPD`, and an explicit `--top 0` is kept: zero is a
  measurement, not a missing option.
- New documents: **`KNOWLEDGE.md`** (everything measured on the printer,
  including the Labellife capture and the command matrix) and **`HANDOFF.md`**
  (state of play, open points, the lesson that corner letters T/B/L/R work
  better than a numbered scale on a rotated roll).

## 1.3 — S0929120 (25 × 25 mm square) and two new roll knobs

- New size `LW_26x25`: the Dymo S0929120 / 30332 roll measured 26 × 25 mm
  (not 25 × 25). The roll line is: 25 mm label, 4 mm liner, 3 mm notch,
  5 mm liner = 37 mm pitch. A 25 × 25 Word page is mapped onto it
  automatically.
- The roll definitions gained two fields: `rows` (bitmap height in dots;
  default `pitch - 12`, like the vendor app sends) and `rotate` (90 / 270:
  print the design sideways). `add-size.sh` gained `--rows` and `--rotate`.
- Labellife turned out to send `SIZE 25 mm,33.97 mm`, `GAP 3 mm` and 356
  bitmap rows for this roll; with those values and 0.6 mm of white all
  around the image stands centered. Earlier assumptions (pitch 38 mm,
  spacing 13 mm) were why the printer started every feed elsewhere: that
  gap does not exist, so the gap-hunter jumped around.
- Ink cannot go left of x=0; on a narrower roll that is a physical dead
  zone. Center by giving up on the right as much as is unreachable on the
  left. The largest centered square on this roll is thereby
  23.03 × 23.03 mm (1.5 mm left/right, 1.0 mm top/bottom):
  `left=1.5 right=1.45 voffset=5.1 bottom=1.95`.
- Key insight: for this printer **SIZE height + GAP = the real pitch**. With
  `SIZE 26 mm,34 mm` + `GAP 3 mm` (37 mm) five loose feeds landed exactly
  identical; as long as the sum was right the sensor did not care that the
  notches fall outside its range.
- Bug in `./measure`: the cross print sent `SIZE <w>,<h>` instead of the
  given `--pitch`/`--gap`, so the printer under-fed and the image landed
  half on the liner. Both measuring modes now send exactly the computed
  geometry.
- `./measure` gained a `ladder` mode (numbered bands over one feed) to see
  where a roll starts, and `--step` for readable scales on small labels.
- `test_filter.py` (40 checks) and `test_measure.py` (20 checks) cover
  `rows`, `rotate`, the inverse rotation and the pitch/gap pass-through.

## 1.2 — ./measure, a new roll in two commands

- `./measure <width> <height>` prints one label with `0,0` in the middle of
  the expected printable area, 1 mm ticks and N/Z/W/O on the expected edges,
  as mode-0 TSPL straight to port 9100 — no driver and no root.
- `./measure solve --N .. --Z .. --W .. --O ..` converts the four readings
  into `left`/`right`/`top`/`bottom` and prints the matching `add-size.sh`
  command. The used center position is kept in a state file, so readings no
  longer get lost.
- The computation comes from `cups/lw650xl.py` itself: measuring and printing
  compute identically. `--preview` and `--dry-run` show without printing.
- `test_measure.py` covers the print/solve round trip.

## 1.1 — AM99012 / Dymo S0722400 (36 × 89 mm, portrait)

- New size `LW_36x89`: this roll sits 90° differently on the printer than the
  AM11354 — 36 mm across the head, 89 mm in the feed direction, pitch 93 mm.
- Roll positioning is now configurable per size in the PPD: `left`, `right`,
  `top` and `bottom` next to `pitch`, `gap` and `voffset`
  (`*% lw-media LW_36x89 pitch=93 gap=4 left=3 right=3 top=-0.5 bottom=1`).
- `left`/`right`/`top`/`bottom` are settable as a CUPS option (`-o lw-right=3`)
  and as CLI options (`--media-right 3`, `--media-top`, `--media-bottom`).
- The model now matches reality: a negative `top` (label starts above the
  head's reach) is clamped to row 0, and ink cannot go left of x=0 — so the
  right side of the print gives up as much as the unreachable left edge.
  Measured margins: 3.34 / 3.28 mm (W/E) and 0.84 / 0.87 mm (N/S).
- `add-size.sh` gained `--left`, `--right`, `--top` and `--bottom`; the
  manual (NL) and README describe how to read a roll with a measurement
  label.
- `test_filter.py`: 34 checks, including the AM99012 geometry and the equal
  left/right margins.

## 1.0 — first working version

- TSPL `BITMAP` mode 0, bit 1 = white, 1:1 on the 1280-dot head.
- Measurably centered geometry for the AM11354 (57 × 32 mm, pitch 38.6 mm,
  printable area x 0–640, `voffset` 0.34 mm).
- CUPS filter that really reads the cgpdftoraster rasters: 1796-byte header
  per page, sync word only before page 1, and multiple pages = multiple
  labels.
- Word-like options are undone: `media=Custom.90.71x161.57` +
  `orientation-requested=4` (label arrives standing → rotate 90° clockwise
  back) and the PPD choice via
  `com.apple.print.PageToPaperMappingMediaName`.
- Shared SMB inbox (Labelprinter) with launchd watcher, Word and Excel
  macros, `label` CLI, `setup.sh` / `install.sh` / `add-size.sh`, tests.
