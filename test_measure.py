#!/usr/bin/env python3
"""Tests for ./measure - the roll calibration helper.

1. print mode builds a full label-size TSPL job and records where its 0,0 sits
2. solve mode turns four edge readings back into add-size.sh arguments
3. the round trip (print, then read the edges it claims) returns the geometry

No printer needed: print mode runs with --dry-run, solve reads the state file.
Run: python3 test_measure.py
"""
import json
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
MEASURE = os.path.join(HERE, "measure")
DPM = 300.0 / 25.4


def run(*args):
    r = subprocess.run([MEASURE, *args], capture_output=True, text=True, timeout=60)
    return r.returncode, r.stdout + r.stderr


def main():
    ok = True
    state = tempfile.mktemp(suffix=".json")

    def check(name, cond):
        nonlocal ok
        print(("  ok   " if cond else "  FAIL ") + name)
        ok = ok and bool(cond)

    # --- 1. print mode ------------------------------------------------------
    code, out = run("36", "89", "--name", "LW_36x89", "--dry-run", "--state", state)
    check("print: exit 0", code == 0)
    check("print: SIZE uses width + pitch", "SIZE 36 mm,93 mm" in out)
    check("print: GAP from the roll", "GAP 4 mm,0 mm" in out)
    check("print: uncompressed BITMAP mode 0", "BITMAP 0,0,160," in out)
    check("print: nothing sent (dry run)", "DRY-RUN" in out)

    st = json.load(open(state))
    check("state: label size kept", (st["w"], st["h"]) == (36.0, 89.0))
    check("state: 0,0 inside the label", 0 < st["centre_x_mm"] < 36 and
          0 < st["centre_y_mm"] < 89)
    # the printed centre must be the centre of the accepted print window:
    # left 3 mm and right 3 mm, so x = -3 + (36 - 3 - 3)/2 = 15 mm
    check("state: centre x follows left/right", abs(st["centre_x_mm"] - 15.03) < 0.15)

    # --- 1b. an unknown roll must still feed what it was told ---------------
    # (regression: the cross print silently used SIZE <h>,<h> instead of the
    # --pitch/--gap given on the command line, so it fed 13 mm too little)
    other = tempfile.mktemp(suffix=".json")
    code, out = run("25", "25", "--pitch", "38", "--gap", "13",
                    "--dry-run", "--state", other)
    os.path.exists(other) and os.unlink(other)
    check("unknown roll: SIZE uses the given pitch", "SIZE 25 mm,38 mm" in out)
    check("unknown roll: GAP uses the given gap", "GAP 13 mm,0 mm" in out)

    # --- 2. solve mode ------------------------------------------------------
    cx, cy = st["centre_x_mm"], st["centre_y_mm"]
    # read the edges where the print model says they are: -3..33 mm and
    # -0.5..88.5 mm, expressed relative to the printed 0,0
    N = round(-0.5 - cy, 2)
    Z = round(88.5 - cy, 2)
    W = round(-3.0 - cx, 2)
    O = round(33.0 - cx, 2)
    code, out = run("solve", "--N", str(N), "--Z", str(Z), "--W", str(W), "--O", str(O),
                    "--pitch", "93", "--gap", "4", "--state", state)
    check("solve: exit 0", code == 0)
    cmd = [line for line in out.splitlines() if line.startswith("./add-size.sh")]
    check("solve: prints an add-size.sh command", bool(cmd))
    cmd = cmd[0] if cmd else ""
    check("solve: recovers the 36x89 size",
          re.search(r"\bLW_36x89\b.* 36 89\b", cmd) is not None)
    check("solve: recovers left ~3 mm", re.search(r"--left 2\.9\d| 3(\.0+)?\b", cmd) is not None)
    check("solve: centres by trimming the right side", "--right" in cmd)
    check("solve: recovers the negative top", "--top -0" in cmd or "--top 0" in cmd)
    check("solve: pitch and gap passed through",
          "--pitch 93" in cmd and "--gap 4" in cmd)
    check("solve: mentions the install step", "install.sh" in out)

    # --- 3. no measuring of the pitch invented --------------------------------
    code, out = run("solve", "--N", str(N), "--Z", str(Z), "--W", str(W), "--O", str(O),
                    "--state", state)
    check("solve: without --pitch it asks for a measurement",
          "measure the pitch next" in out and "--pitch" not in out.split("./add-size.sh")[1])

    # --- 4. a roll that sits fully in reach ---------------------------------
    st2 = json.load(open(state))
    # pretend the label starts at x=+2 mm (nothing unreachable)
    code, out = run("solve", "--N", str(N), "--Z", str(Z),
                    "--W", str(round(2.0 - st2["centre_x_mm"], 2)),
                    "--O", str(round(38.0 - st2["centre_x_mm"], 2)),
                    "--pitch", "93", "--state", state)
    check("solve: reachable left edge needs no left/right trim",
          "--left" not in out.split("./add-size.sh")[1])

    # --- marker sheet: T/B/L/R frame + solve --T --B --L --R ---------------
    mstate = tempfile.mktemp(suffix=".json")
    code, out = run("36", "89", "--name", "LW_36x89", "--markers",
                    "--dry-run", "--state", mstate)
    check("markers: exit 0", code == 0)
    check("markers: TSPL to the full head", "BITMAP 0,0,160," in out)
    check("markers: framesuggestie in de tekst", "solve --T" in out)
    st = json.load(open(mstate))
    check("markers: state onthoudt modus en rotatie",
          st.get("mode") == "markers" and st.get("rotate") == 0)
    fr = st.get("frame", {})
    check("markers: frame = oud printbaar vlak",
          abs(fr.get("x1", 0) - 30.06) < 0.3 and fr.get("y0") is not None)

    # image == window: no distortion, the frame falls on the window edges
    png = tempfile.mktemp(suffix=".png")
    code, out = run("26", "25", "--markers", "--preview", png, "--state", mstate)
    check("markers: rotated roll uses rotate from the PPD",
          json.load(open(mstate))["rotate"] == 270)
    from PIL import Image
    im = Image.open(png)
    dpm = 300.0 / 25.4
    st26 = json.load(open(mstate))
    fr26 = st26["frame"]
    check("markers: rastermaat == venster (1:1, geen scale-vervorming)",
          im.width == int(round((fr26["x1"] - fr26["x0"]) * dpm)) and
          im.height == int(round((fr26["y1"] - fr26["y0"]) * dpm)))

    # §4A-mapping: bij rotate=270 is de user T/B de KOPKANT (left/right)
    code, out = run("solve", "--T", "2.0", "--B", "0.5", "--L", "1.0", "--R", "1.0",
                    "--state", mstate)
    check("markers solve: exit 0", code == 0)
    cmd = out.split("./add-size.sh")[1] if "./add-size.sh" in out else ""
    check("markers solve: T/B became left/right (left 2.0)", "--left 2" in cmd)
    check("markers solve: measured width across the head ~25.5 mm",
          "25.5" in out)
    check("markers solve: reminds about the plumb-line sheet",
          "plumb-line" in out)

    # rotatie 0: T/B blijven boven/beneden, L/R links/rechts
    code, out = run("36", "89", "--markers", "--dry-run", "--state", mstate)
    code, out = run("solve", "--T", "1", "--B", "1", "--L", "0", "--R", "0",
                    "--state", mstate)
    cmd = out.split("./add-size.sh")[1] if "./add-size.sh" in out else ""
    check("markers solve: rot0 leaves left/right alone (no dead zone)",
          "--left" not in cmd)
    check("markers solve: rot0 maps T/B to the feed (--top)", "--top" in cmd)

    code, out = run("solve", "--T", "1", "--state", mstate)
    check("markers solve: te weinig letters = foutmelding",
          code != 0 and "--B" in out)

    # --- plumb: the cut plumb line as a fixed command ----------------------
    code, out = run("plumb", "25", "25", "--dry-run")
    check("plumb: exit 0", code == 0)
    check("plumb: line tracks the calibrated roll's rail",
          "plumb at x 10.4" in out or "plumb at x 10.5" in out)
    code, out = run("plumb", "25", "25", "--report", "0.5")
    check("plumb: +0,5 mm op A verhogen xoffset met 0,5",
          "-1.5" in out and "--xoffset -1.5" in out)
    check("plumb: report drukt niet (rekent alleen)", "DRY-RUN" not in out)
    code, out = run("plumb", "25", "25", "--report", "-0.5")
    check("plumb: deviation toward B lowers xoffset",
          "-2.5" in out or "-2.50" in out)

    # --- onbekende rol met hoogte > breedte: NIET swappen (S0904980-bug) ---
    # (104x159 zit inmiddels in de PPD en find_media matcht tot 1 mm —
    #  dus een maat die ver van elke tabelrij zit)
    code, out = run("104", "179", "--name", "LW_104x179", "--markers",
                    "--pitch", "162", "--gap", "3", "--dry-run")
    check("unknown roll: size stays 104x179 (long-side swap gone)",
          "0.00..103.21" in out and "5.08..160.95" in out)

    os.path.exists(mstate) and os.unlink(mstate)
    os.path.exists(png) and os.unlink(png)

    os.path.exists(state) and os.unlink(state)
    print("OK" if ok else "FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
