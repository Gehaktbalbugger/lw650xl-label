#!/usr/bin/env python3
"""Bepaal de CUPS-mediaoptie die bij het paginaformaat van een PDF hoort.

Gebruik:
    pdfmedia.py bestand.pdf [--ppd /pad/naar/lw650xl-labels.ppd]

Uitvoer (één of twee regels, geschikt om in bash te parsen):
    media=LW_57x32
    orientation=4          # alleen als de pagina 90 graden gedraaid moet worden

Exitcodes:
    0  ok
    2  paginaformaat valt buiten het bereik van de printer/PPD
    3  PDF onleesbaar of geen MediaBox gevonden
"""
import argparse
import re
import sys

PT_PER_MM = 72.0 / 25.4
MM_PER_PT = 25.4 / 72.0
TOL_PT = 3.0  # ~1 mm: kleine afrondingsverschillen in Word/PDF-export


def page_size_pt(path):
    """Geef (breedte, hoogte) van pagina 1 in punten, inclusief /Rotate."""
    with open(path, "rb") as f:
        data = f.read()

    boxes = re.findall(
        rb"/MediaBox\s*\[\s*(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)\s*\]",
        data,
    )
    if not boxes:
        boxes = re.findall(
            rb"/CropBox\s*\[\s*(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)\s*\]",
            data,
        )
    if not boxes:
        raise ValueError("geen /MediaBox of /CropBox gevonden")

    x1, y1, x2, y2 = (float(v) for v in boxes[0])
    w, h = abs(x2 - x1), abs(y2 - y1)
    if w <= 0 or h <= 0:
        raise ValueError(f"ongeldig MediaBox {boxes[0]!r}")

    rot = re.search(rb"/Rotate\s+(-?\d+)", data)
    if rot and int(rot.group(1)) % 180 == 90:
        w, h = h, w
    return w, h


def ppd_sizes(path):
    """Lees *PageSize regels uit een PPD: [(naam, breedte_pt, hoogte_pt), ...]."""
    try:
        text = open(path, "r", encoding="latin-1").read()
    except OSError:
        return []
    out = []
    for m in re.finditer(
        r'^\*PageSize\s+(\S+?)/.*?"<<\s*/PageSize\s*\[\s*([\d.]+)\s+([\d.]+)\s*\]',
        text,
        re.M,
    ):
        out.append((m.group(1), float(m.group(2)), float(m.group(3))))
    return out


def fmt_mm(v):
    s = f"{v:.1f}"
    return s[:-2] if s.endswith(".0") else s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("--ppd", default="/etc/cups/ppd/LW650XL_Labels.ppd")
    args = ap.parse_args()

    try:
        w, h = page_size_pt(args.pdf)
    except Exception as e:
        print(f"pdfmedia: {e}", file=sys.stderr)
        return 3

    sizes = ppd_sizes(args.ppd)

    # 1) exact match with a known label size
    for name, sw, sh in sizes:
        if abs(w - sw) <= TOL_PT and abs(h - sh) <= TOL_PT:
            print(f"media={name}")
            return 0

    # 2) page is rotated 90 degrees relative to the label size
    for name, sw, sh in sizes:
        if abs(w - sh) <= TOL_PT and abs(h - sw) <= TOL_PT:
            print(f"media={name}")
            print("orientation=4")
            return 0

    # 3) vrije maat: CUPS custom media (bereik uit de PPD: 28-341 x 14-652 pt)
    if not (28.0 <= w <= 341.0 and 14.0 <= h <= 652.0):
        print(
            f"pdfmedia: pagina is {w * MM_PER_PT:.1f} x {h * MM_PER_PT:.1f} mm; "
            "does not fit this printer (max. 120 x 230 mm). "
            "Set the page size in Word/Excel equal to the label.",
            file=sys.stderr,
        )
        return 2

    print(f"media=Custom.{fmt_mm(w * MM_PER_PT)}x{fmt_mm(h * MM_PER_PT)}mm")
    return 0


if __name__ == "__main__":
    sys.exit(main())
