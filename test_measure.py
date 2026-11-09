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
          "meet nog de steek" in out and "--pitch" not in out.split("./add-size.sh")[1])

    # --- 4. a roll that sits fully in reach ---------------------------------
    st2 = json.load(open(state))
    # pretend the label starts at x=+2 mm (nothing unreachable)
    code, out = run("solve", "--N", str(N), "--Z", str(Z),
                    "--W", str(round(2.0 - st2["centre_x_mm"], 2)),
                    "--O", str(round(38.0 - st2["centre_x_mm"], 2)),
                    "--pitch", "93", "--state", state)
    check("solve: reachable left edge needs no left/right trim",
          "--left" not in out.split("./add-size.sh")[1])

    os.path.exists(state) and os.unlink(state)
    print("OK" if ok else "FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
