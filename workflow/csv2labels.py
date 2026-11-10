#!/usr/bin/env python3
"""Print één etiket per rij uit een CSV-bestand (Excel → CSV UTF-8).

Verwachte kolommen (hoofdletterongevoelig, Nederlandse of Engelse namen):

    text      (of: tekst, etiket, label)   verplicht; gebruik \\n voor regeleinden
    qr        (optioneel)                  QR-inhoud
    barcode   (optioneel)                  bv. CODE128:ABC123
    copies    (optioneel)                  aantal exemplaren
    size      (optioneel)                  bv. 57x32 (mm)
    density   (optioneel)                  0-15
    gap       (optioneel)                  etiketafstand in mm (0 = continu)

Ontbreekt de kolom 'text', dan wordt de eerste kolom als tekst gebruikt.

Met --two-up worden opeenvolgende rijen GEPAARD: twee rijen samen vormen
een blok met twee etiketten naast elkaar (bv. de AM11353, twee keer
12,5 x 25 mm per blok). Rij 1 = linker etiket, rij 2 = rechter etiket.
Het scheidingsteken (, of ;) wordt automatisch herkend.

Gebruik:
    csv2labels.py adressen.csv --size 57x32
    csv2labels.py adressen.csv --dry-run
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
    ap = argparse.ArgumentParser(description="CSV → etiketten op de LW650XL PRO")
    ap.add_argument("csv")
    ap.add_argument("--size", default="57x32", help="standaard etiketformaat in mm")
    ap.add_argument("--host", default=DEFAULT_HOST)
    ap.add_argument("--two-up", action="store_true",
                    help="paar opeenvolgende rijen toteen blok met twee etiketten naast elkaar")
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
        # geen herkenbare kopregel: eerste kolom = tekst
        records = [{"text": r[0] if r else ""} for r in rows]

    blocks = [(rec, None) for rec in records]
    if args.two_up:
        # lege rijen eruit halen voordat we paren (anders verspringt het blok)
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
            print(f"csv2labels: waarschuwing - rechter helft leeg (oneven aantal rijen)",
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
            print(f"csv2labels: blok {i} mislukt (exit {e.returncode})", file=sys.stderr)
            return 1
        except FileNotFoundError:
            print(f"csv2labels: {LABEL} niet gevonden", file=sys.stderr)
            return 1

    print(f"csv2labels: {printed} etiket(ten) verwerkt uit {os.path.basename(args.csv)}")
    return 0 if printed else 1


if __name__ == "__main__":
    sys.exit(main())
