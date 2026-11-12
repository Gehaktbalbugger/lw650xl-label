#!/usr/bin/env python3
"""Print one label per row from a CSV file (Excel → CSV UTF-8).

Expected columns (case-insensitive, Dutch or English names):

    text      (or: tekst, etiket, label)   required; use \\n for line breaks
    qr        (optional)                   QR content
    barcode   (optional)                   e.g. CODE128:ABC123
    copies    (optional)                   number of copies
    size      (optional)                   e.g. 57x32 (mm)
    density   (optional)                   0-15
    gap       (optional)                   label spacing in mm (0 = continuous)

If the 'text' column is missing, the first column is used as the text.

With --two-up consecutive rows are PAIRED: two rows together form a block
of two labels side by side (e.g. the AM11353, two 12.5 x 25 mm per block).
Row 1 = left label, row 2 = right label. The separator (, or ;) is detected
automatically.

Usage:
    csv2labels.py addresses.csv --size 57x32
    csv2labels.py addresses.csv --dry-run
"""
import argparse
import csv
import io
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LABEL = os.path.join(HERE, "label")
if not os.path.exists(LABEL):
    LABEL = os.path.join(os.path.dirname(HERE), "label")
DEFAULT_HOST = os.environ.get("LW_HOST", "172.16.1.20")

TEXT_KEYS = ("text", "tekst", "etiket", "label", "inhoud", "content")
ALIASES = {
    "qr": ("qr", "qrcode", "qr_code"),
    "barcode": ("barcode", "streepjescode", "bar"),
    "copies": ("copies", "aantal", "exemplaren", "qty"),
    "size": ("size", "formaat", "maat"),
    "density": ("density", "dichtheid", "darkness"),
    "gap": ("gap", "tussenruimte"),
}


def read_text(path):
    """Lees UTF-8 (met/zonder BOM), of val terug op Windows/Mac-codering."""
    raw = open(path, "rb").read()
    for enc in ("utf-8-sig", "cp1252", "mac_roman"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", "replace")


def read_rows(path):
    text = read_text(path)
    sample = text[:8192]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
        reader = csv.reader(io.StringIO(text), dialect)
    except csv.Error:
        delim = ";" if sample.count(";") > sample.count(",") else ","
        reader = csv.reader(io.StringIO(text), delimiter=delim)
    return [r for r in reader if any(c.strip() for c in r)]


def pick(row, names):
    for n in names:
        if n in row and str(row[n]).strip():
            return str(row[n]).strip()
    return ""


def main():
    ap = argparse.ArgumentParser(description="CSV → labels on the LW650XL PRO")
    ap.add_argument("csv")
    ap.add_argument("--size", default="57x32", help="default label size in mm")
    ap.add_argument("--host", default=DEFAULT_HOST)
    ap.add_argument("--two-up", action="store_true",
                    help="pair consecutive rows into a block of two labels side by side")
    ap.add_argument("--dry-run", action="store_true", help="alleen tonen, niet printen")
    args = ap.parse_args()

    rows = read_rows(args.csv)
    if not rows:
        print(f"csv2labels: {args.csv} is leeg", file=sys.stderr)
        return 1

    header = [h.strip().lower() for h in rows[0]]
    has_header = any(h in TEXT_KEYS for h in header)
    if has_header:
        records = [dict(zip(header, r)) for r in rows[1:]]
    else:
        # no recognizable header row: first column = text
        records = [{"text": r[0] if r else ""} for r in rows]

    blocks = [(rec, None) for rec in records]
    if args.two_up:
        # strip empty rows before pairing (otherwise the block shifts)
        gevuld = []
        for rec in records:
            if (pick(rec, TEXT_KEYS) or "").strip():
                gevuld.append(rec)
        blocks = [(gevuld[i], gevuld[i+1] if i+1 < len(gevuld) else None)
                  for i in range(0, len(gevuld), 2)]

    printed = 0
    for i, (rec, recb) in enumerate(blocks, start=1):
        text = pick(rec, TEXT_KEYS)
        if not text:
            continue

        size = pick(rec, ALIASES["size"]) or args.size
        copies = pick(rec, ALIASES["copies"]) or "1"
        qr = pick(rec, ALIASES["qr"])
        barcode = pick(rec, ALIASES["barcode"])
        if barcode and ":" not in barcode:
            barcode = "CODE128:" + barcode
        density = pick(rec, ALIASES["density"])
        gap = pick(rec, ALIASES["gap"])

        cmd = [
            sys.executable, LABEL, text,
            "--size", size,
            "--copies", copies,
            "--host", args.host,
        ]
        if qr:
            cmd += ["--qr", qr]
        if barcode:
            cmd += ["--barcode", barcode]
        if density:
            cmd += ["--density", density]
        if gap:
            cmd += ["--gap", gap]

        tekst2 = (pick(recb, TEXT_KEYS) or "").strip() if recb else ""
        if args.two_up and not tekst2:
            print(f"csv2labels: warning - right half empty (odd number of rows)",
                  file=sys.stderr)

        if args.dry_run:
            cmd += ["--two", tekst2] if args.two_up else []
            print("DRY-RUN:", " ".join(repr(c) for c in cmd))
            printed += 1
            continue

        cmd += ["--two", tekst2] if args.two_up else []
        try:
            subprocess.run(cmd, check=True)
            printed += 1
        except subprocess.CalledProcessError as e:
            print(f"csv2labels: block {i} failed (exit {e.returncode})", file=sys.stderr)
            return 1
        except FileNotFoundError:
            print(f"csv2labels: {LABEL} niet gevonden", file=sys.stderr)
            return 1

    print(f"csv2labels: {printed} label(s) processed from {os.path.basename(args.csv)}")
    return 0 if printed else 1


if __name__ == "__main__":
    sys.exit(main())
