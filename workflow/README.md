# Printing labels from Word and Excel (multiple machines)

This setup lets the **iMac** produce all labels. Word and Excel on Windows,
macOS, or even a phone only need to drop a **PDF** or **CSV** into a shared
folder. The iMac converts that into the printer's own language (TSPL) and
sends it to `172.16.1.20:9100`.

So there is **no printer driver needed on the clients** and the printer does
not have to understand PCL5 or PostScript.

```
Word / Excel / phone
        │  PDF or CSV
        ▼
/Users/Shared/Labelprinter/inbox        (SMB share "Labelprinter")
        │  launchd watcher
        ▼
CUPS queue LW650XL_Labels
        │  cgpdftoraster (300 dpi) → lw650xl filter
        ▼
TSPL (bitmap mode 0)  →  socket://172.16.1.20:9100  →  LW650XL PRO
```

---

## 1. One-time installation

Open Terminal on the iMac:

```bash
cd ~/Documents/Standaardproject/label-printer
./setup.sh
```

The script asks for your macOS password. It does three things:

1. installs the CUPS filter and the queue **LW650XL_Labels**;
2. creates the shared folder **Labelprinter** (SMB);
3. installs the watcher that drains the inbox automatically.

Then verify:

```bash
lpstat -p LW650XL_Labels
lp -d LW650XL_Labels -o media=LW_57x32 ~/Documents/Standaardproject/label-printer/cups/test.pdf
```

The second command prints one test label. If nothing comes out, see
[Troubleshooting](#7-troubleshooting).

---

## 2. Word: designing and printing a label

### 2.1 Match the page size to the label

This is the most important step: **the page in Word must be exactly the size
of the label**. Otherwise the printer scales the image or the watcher
refuses the file.

Tip: printing directly from Word to the printer **LW650XL PRO Labels (TSPL)**
is also allowed, as long as you pick the same label under paper size (e.g.
*Label 57x32 mm*). The filter corrects the portrait page and the `Custom`
size that Word sends; every document page becomes one label.

In Word:

1. **Layout → Size → More paper sizes…**
2. Choose **Custom** and fill in:
   - Label 57 × 32 mm (AM11354, default in the printer): width
     **5.7 cm**, height **3.2 cm**, landscape.
   - Shipping label 102 × 59 mm: width **10.2 cm**, height **5.9 cm**,
     landscape.
   - PostNL XL 104 × 159 mm: width **10.4 cm**, height **15.9 cm**,
     portrait.
3. **Margins → Custom**: 0.2 cm all around, header and footer 0 cm.
4. Set **Scaling** to **100%** (not "fit to page").

Quick fill works with the macros `Label_Pagina_57x32`,
`Label_Pagina_102x59` and `Label_Pagina_104x159` (see 2.2).

### 2.2 Installing the macro

1. In Word: **Tools → Macro → Visual Basic** (Alt+F11).
2. **File → Import file…** and pick `workflow/word/LabelPrinter.bas`.
3. Close the editor.
4. Put **Label_NaarPrinter** on the Quick Access toolbar:
   arrow at the top right → **More commands → All commands → Macros**.

The macro exports the document as PDF into the shared inbox. The iMac picks
it up automatically, so you never choose a printer.

> On the iMac itself you can also just do ⌘P → **LW650XL Labels**. Choose
> the paper size that matches the loaded roll.

### 2.3 Printing a label

1. Design the label (text, table, logo, optionally a barcode font).
2. Click **Label_NaarPrinter**.
3. The message "Label(s) sent to the label printer." appears.
4. Within seconds the label rolls out.

### 2.4 Mail merge: many labels at once (addresses from Excel)

1. Make a list in Excel with columns (e.g. `Naam`, `Straat`, `Postcode`,
   `Plaats`).
2. In Word: **Mailings → Start Mail Merge → Letters**.
3. **Select Recipients → Use an Existing List** → pick the Excel file.
4. Place the fields on the label (one label per page).
5. **Finish & Merge → Edit Individual Documents… → All**.
6. A new document opens with one label per page. Click **Label_NaarPrinter**.

The PDF contains all pages; the filter prints **one label per page**.
This is the fastest route for dozens of addresses.

---

## 3. Excel: one label per row (CSV)

For loose labels or an address list without Word there is a second route:
Excel writes a CSV, the iMac prints each row as a label.

### 3.1 Preparing the sheet

Put these headers in **row 1** (only `text` is required):

| text | qr | barcode | copies | size |
|---|---|---|---|---|
| Anna de Bakker\nKeukenstraat 12\n1011 AB Amsterdam | https://track/1 | CODE128:ABC123 | 1 | 57x32 |
| Pakket #1234 | | | 2 | |

- `text`: use `\n` for a new line.
- `qr`, `barcode`, `copies`, `size` may stay empty.
- `size` is the label size in mm; empty = 57x32.

### 3.2 Sending

**Method A – with the macro (Windows):**

1. Tools → Macro → Visual Basic → Import file →
   `workflow/excel/LabelPrinter.bas`.
2. Tools → Macro → Macros → **Label_ExportCSV**.

**Method B – manual (any system):**

1. **File → Save as → CSV UTF-8 (comma separated)**.
2. Drop the file into the shared folder `Labelprinter/inbox`.

The watcher prints one label per row. The separator (`;` or `,`) does not
matter; it is detected automatically.

> Rather print a single label by hand? On the iMac:
> `./label "Text\nline 2" --size 57x32`

---

## 4. From another machine

### Windows

Open Explorer and go to:

```
\\iMac2020\Labelprinter\inbox
```

or, if the name does not resolve:

```
\\172.16.1.101\Labelprinter\inbox
```

Sign in with the iMac's macOS account (or guest, if enabled). Drop the PDF
or CSV in. Done.

### macOS / iPhone / iPad

Finder → **Go → Connect to Server…** →

```
smb://iMac2020.local/Labelprinter
```

The folder then shows up under `/Volumes/Labelprinter/inbox`.

### MacBook: its own printer queue (print straight from Word)

```bash
xcode-select --install                       # first time only (Python 3 + git)
git clone https://github.com/Gehaktbalbugger/lw650xl-label.git ~/label-printer
cd ~/label-printer
sudo ./install.sh
```

Do **not** clone into `Documents`, `Desktop` or `Downloads`: macOS does not
let `sudo` read those folders, and the install fails with "Operation not
permitted". A plain folder in your home directory (here `~/label-printer`)
or `/tmp` works fine.

Update later: `cd ~/label-printer && git pull && sudo ./install.sh`.
Test: `lp -d LW650XL_Labels ~/label-printer/cups/test.pdf`.

On a second Mac run only **`install.sh`**: it creates the queue.
`setup.sh` (or `workflow/install-workflow.sh`) is for the iMac — that is the
shared-inbox-plus-watcher set, and you don't want it twice.

Then choose in Word or Excel printer **LW650XL PRO Labels (TSPL)** and paper
size **Label 57x32 mm (AM11354)**.

You can remove the vendor's Labellife driver and queues: System Settings →
**Printers & Scanners** → delete the old LW650XL queue. They do nothing and
only get in the way.

It also works without an install, but then through the iMac:

- PDF/CSV into the share above (no driver needed), or
- add the queue via **`ipp://iMac2020.local:631/printers/LW650XL_Labels`**.
  Note: macOS copies the iMac's PPD and sometimes renders locally — the
  filter is missing on that Mac and the job fails. Use `install.sh` instead.

### What the clients need

Only write access to the share. No driver, no software, no printer settings.
The iMac does the work.

---

## 5. What the watcher exactly does

- **PDF**: reads the page size from the PDF, picks the matching label size
  (or a custom size), and prints through the CUPS queue.
- **CSV**: reads the rows and prints one label per row via the `label` CLI
  (with text, QR and/or barcode).
- Finished files move to `printed/<date>/`; failures go to `failed/` with a
  `.error.txt`.
- The watcher starts at login/boot, watches the folder continuously, and
  additionally sweeps every 60 seconds as a safety net.

File names can be anything; avoid starting with `~$` (those are Word lock
files).

---

## 6. Label sizes

Available by default (from the PPD):

| Name | Size |
|---|---|
| `LW_104x159` | XL shipping label 104 × 159 mm |
| `LW_57x32` | Label 57 × 32 mm (AM11354, default) |
| `LW_102x59` | Shipping label 102 × 59 mm |
| `LW_101x54` | Name badge 101 × 54 mm |
| `LW_89x36` | Address wide 89 × 36 mm |
| `LW_36x89` | Address 36 × 89 mm (AM99012 / Dymo S0722400, **portrait**) |
| `LW_26x25` | Square multipurpose 26 × 25 mm (S0929120 / Dymo 30332), printed sideways |
| `LW_25x25` | Block of two labels 12.5 × 25 mm (AM11353 / Dymo 11353) |
| `LW_89x28` | Address 89 × 28 mm |
| `LW_54x25` | Return 54 × 25 mm |
| `LW_50x12` | Hanging folder 50 × 12 mm |
| `LW_57x57` | CD/DVD 57 × 57 mm |
| `LW_62x100` | Continuous 62 × 100 mm |

**How a new roll is added:** the PPD is the single place where a roll is
defined. `add-size.sh` writes the paper size (the one you pick in Word) plus
one comment line with the geometry:

```bash
./add-size.sh LW_76x51 "Logistics 76x51 mm" 76 51 --gap 3 --pitch 54.5 --voffset 0.34
./add-size.sh LW_36x89 "Address 36x89 mm (AM99012, portrait)" 36 89 \
    --gap 4 --pitch 93 --left 3 --right 3 --top -0.5 --bottom 1
sudo ./install.sh
```

```
*% lw-media LW_36x89 pitch=93 gap=4 left=3 right=3 top=-0.5 bottom=1
```

The filter and the `label` CLI read that line, so Word, `lp` and the shared
inbox all work immediately — no code changes. `--gap`, `--pitch` and
`--voffset` may be omitted: the gap defaults to 3 mm, the pitch = height +
gap and the print starts at the label's top edge.

Beyond that, three numbers for a roll that **sits differently on the liner**
(narrower, offset or taller than the standard roll). You find them with a
measurement sheet:

- `--left` — mm of label that falls left of the head. That edge is
  unreachable and therefore always white. AM11354: 2 mm, AM99012 (36 mm
  narrow): 3 mm.
- `--right` — mm kept free on the right. Ink cannot go left of x=0, so a
  roll with an unreachable left edge is centered by giving up the same on
  the right (AM99012: left 3, right 3 → 30 mm wide print, equal all around).
- `--top` — mm from the bitmap origin to the label's top edge. On a tall
  label it can be negative (AM99012: −0.5 mm); those rows are then not
  printed.
- `--bottom` — mm kept free at the bottom. Set it equal to an unreachable
  top edge and the print is centered (AM99012: 1 mm at −0.5 mm top).
- `--gap` and `--gapoff` — length of the gap/notch, and separately how much
  plain liner sits between the label and that gap. This roll is 25 mm label
  + 4 mm liner + 3 mm notch + 5 mm liner.
- `--sense` — `gap` (default) or `bline` for black marks. A 26 mm roll
  against the left guide never reaches a sensor sitting mid-path; `BLINE`
  then only produces a paper error. What makes the feeds repeatable is that
  `SIZE height + gap` equals the true pitch.
- `--xoffset` — mm between the head start (x=0) and the liner's left edge;
  **may be negative**. The AM11353 was physically calibrated (boxes +
  plumb line, 12 Nov): the 30 mm liner starts at x ≈ −3.5 mm and label A at
  −2.0 mm — so the left 2 mm of A is out of reach and gets clipped, and the
  cut rail sits at x = 10.5 mm. Without this value the whole sheet lands
  too far right and the right lane falls off the liner.
- `--rows` — bitmap height in dots, instead of the default `pitch - 12`.
  Labellife sends 356 rows for the square roll; adopting that value gave
  the same registration as the vendor app.
- `--rotate` — `90` or `270`: print the design sideways (like Labellife does
  on square rolls). This does not change the dead zone, only the reading
  direction.

**`--voffset`** shifts the whole print down on the label. The printable area
starts exactly at the top edge, so a page that Word centers vertically sits
slightly too high. Proof prints on the AM11354 roll centered at 0.34 mm
(4 dots; 0 mm too high, 0.5 mm too low). With `--voffset 0` you print from
the top edge again.

**Pitch is the feed distance per label, not the label height.** For the
57 × 32 mm roll it is 38.6 mm. Does the printer drift slowly after a few
labels? Measure the distance between the same point on two consecutive
labels on the roll and feed that back. Continuous material: `--gap 0`, then
the pitch equals the height.

**Measuring an unknown roll** takes two commands, no driver and no root:

```bash
./measure 36 89 --name LW_36x89 --pitch 93 --gap 4    # print the cross sheet
./measure solve --N -44.5 --Z 44.5 --W -18 --O 18      # reading -> add-size.sh
```

`measure` prints one label with `0,0` in the middle of the expected printable
area, 1 mm ticks with numbers and N/Z/W/O on the expected edges. Read which
mm value falls on the four real edges; `solve` prints the matching
`add-size.sh` command with `--left`, `--right`, `--top` and `--bottom`. With
`--preview picture.png` or `--dry-run` nothing is sent to the printer. The
pitch (`--pitch`) is not on that cross: measure 20 labels and divide by 20.

On a rotated or shifted roll, prefer the marker sheet: `./measure <w> <h>
--markers` (frame on the printable edges, one letter per side) and
`./measure solve --T .. --B .. --L .. --R ..` — see KNOWLEDGE §10. The pitch
is not on that sheet either: measure 20 labels and divide by 20.

**Swapping rolls** is easy: pick the right size in Word. Is the print skewed
or cut off at one side? Re-measure the four edges with a cross sheet (0,0 in
the middle, 1 mm scale, letters N/Z/W/O) and adjust `--left`, `--top`,
`--bottom` and `--voffset` via `add-size.sh` + `sudo ./install.sh`.

**Repeatability stands or falls with the feed.** This printer counts
`SIZE height + gap` as the distance per label. For the square roll that is
34 + 3 = 37 mm, equal to the measured pitch; five loose prints fell exactly
identical after that. A wrong sum shows up immediately: each label lands a
bit higher or lower.

The watcher reads the same PPD; only for a single deviating roll you can set
`LW_GAP` or `LW_PITCH` in the LaunchDaemon. For a one-off test:

```bash
lp -d LW650XL_Labels -o media=LW_76x51 -o lw-pitch=55 -o lw-gap=2 job.pdf
./label "text" --size 76x51 --pitch 55 --gap 2
```

---

## 7. Troubleshooting

**Nothing comes out of the printer**

```bash
lpstat -p LW650XL_Labels -l          # is the queue active?
lpq -P LW650XL_Labels                # are there pending jobs?
nc -z -G 2 172.16.1.20 9100 && echo "printer reachable"
```

- Is the printer on and on the network (not only Bluetooth)?
- Does the printer still have a fixed IP? If not, make a DHCP reservation
  for `172.16.1.20`.
- Close the Labelife app once; some printers accept only one connection at
  a time.

**Installation fails with "Operation not permitted"**

`sudo` on macOS may not read the folders **Documents**, **Desktop** and
**Downloads**. Put the repo in a plain folder, e.g. `~/label-printer`, and
run `sudo ./install.sh` from there.

**A print job hangs or reports "Filter failed"**

```bash
lpstat -W completed -l -o LW650XL_Labels     # last jobs + warning
sudo cp /var/log/cups/error_log /tmp/cups.err && tail -40 /tmp/cups.err
```

- "no working Python 3 found": `xcode-select --install` or
  `brew install python`, then run `sudo ./install.sh` again.
- "bad raster magic": the installed filter is outdated — `git pull` and
  `sudo ./install.sh`.
- The filter and PPD live in `/usr/libexec/cups/filter/` and
  `/etc/cups/ppd/LW650XL_Labels.ppd`; they must be identical to the repo
  (`md5 /usr/libexec/cups/filter/lw650xl.py`).

**The file disappears into `failed/`**

Open `failed/<name>.error.txt` and `/Users/Shared/Labelprinter/logs/print.log`.
Usually the page size does not match the label (e.g. A4). Set the custom
page size correctly in Word.

**The print is skewed or too high/low**

- Check that the loaded roll matches the chosen size.
- Adjust the label spacing: `lw-gap` (default 3 mm). For continuous
  material: `-o lw-gap=0` or a size with `add-size.sh ... --gap 0`.
- Is the print too high or low on the label: `--voffset` in `add-size.sh`
  (or once with `-o lw-voffset=<mm>` / `--voffset <mm>`). Does the print sit
  too far to one side and is that side unreachable: set `--left` and
  `--right` equal.
- The feed height (`SIZE`) is the label *pitch* (label + spacing), not the
  label height: 38.6 mm for the 57 × 32 mm roll. For another roll:
  `-o lw-pitch=<mm>`.
- The filter uses the page edge as reference; keep 0.2 cm margins in Word.

**The share is not visible**

- System Settings → General → Sharing → **File Sharing** on.
- Check that `Labelprinter` is among the shared folders.
- Firewall: allow incoming traffic for `cupsd` and `smbd`.

**Logs and status**

```bash
tail -f /Users/Shared/Labelprinter/logs/print.log
tail -f /Users/Shared/Labelprinter/logs/watcher.err.log
sudo launchctl print system/com.benno.labelprinter.watcher
```

**Restarting the watcher**

```bash
sudo launchctl kickstart -k system/com.benno.labelprinter.watcher
```

**Removing everything**

```bash
sudo ./workflow/uninstall-workflow.sh
sudo ./uninstall.sh
```

---

## 8. Background and further reading

- **[KNOWLEDGE.md](../KNOWLEDGE.md)** — everything measured on the printer:
  why the bitmap format is what it is, how registration works, the roll line
  of every roll and which commands this firmware does/doesn't know.
- **[HANDOFF.md](../HANDOFF.md)** — where we left off, which roll is next to
  add and which points are still open.

## 9. Files

| File | Purpose |
|---|---|
| `setup.sh` | one-time complete installation |
| `install.sh` | only the CUPS queue |
| `workflow/print-inbox.sh` | the watcher |
| `workflow/pdfmedia.py` | page size → CUPS media |
| `workflow/csv2labels.py` | CSV → one label per row |
| `workflow/word/LabelPrinter.bas` | Word macros |
| `workflow/excel/LabelPrinter.bas` | Excel macro (CSV) |
| `workflow/com.benno.labelprinter.watcher.plist` | launchd template |
