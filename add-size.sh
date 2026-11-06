#!/bin/bash
# Add a label size to the PPD *before or after* installing (re-run install.sh
# afterwards if the queue already exists).
#
# Usage:  ./add-size.sh <name> <description> <width_mm> <height_mm> [--gap 0]
#
# Examples:
#   ./add-size.sh LW_76x51 "Logistics 76x51 mm" 76 51
#   ./add-size.sh LW_30x15 "Kasbon 30x15 mm" 30 15 --gap 0
set -euo pipefail

if [[ $# -lt 4 ]]; then
    echo "Usage: $0 <name> <description> <width_mm> <height_mm> [--gap 0]" >&2
    exit 1
fi

NAME="$1"; DESC="$2"; W_MM="$3"; H_MM="$4"; shift 4
GAP_MM=2.0
if [[ ${1:-} == --gap && $# -ge 2 ]]; then GAP_MM="$2"; fi

here="$(cd "$(dirname "$0")" && pwd)"
PPD="$here/cups/lw650xl-labels.ppd"
[[ -f $PPD ]] || { echo "PPD not found: $PPD" >&2; exit 1; }

# mm -> points (1 mm = 72/25.4 pt)
w_pt=$(python3 -c "print(f'{$W_MM*72/25.4:.2f}')")
h_pt=$(python3 -c "print(f'{$H_MM*72/25.4:.2f}')")

add() {  # add-size <kind> <anchor-regex> <line>
    local kind="$1" anchor="$2" line="$3"
    if grep -qE "^\*$kind $NAME/|^\*$kind $NAME:" "$PPD"; then
        echo "size '$NAME' already exists ($kind), replacing ..."
        python3 - "$PPD" "$kind" "$NAME" <<'EOF'
import re, sys
ppd, kind, name = sys.argv[1], sys.argv[2], sys.argv[3]
pat = re.compile(rf"^\*{kind} {name}\b.*\n")
lines = [l for l in open(ppd) if not pat.match(l)]
open(ppd, "w").writelines(lines)
EOF
    fi
    # insert right after the anchor line (keeps related entries together)
    python3 - "$PPD" "$anchor" "$line" <<'EOF'
import re, sys
ppd, anchor_re, line = sys.argv[1], sys.argv[2], sys.argv[3]
src = open(ppd).read()
pat = re.compile(rf"^\*{anchor_re}.*\n", re.M)
m = pat.search(src)
if not m:
    sys.exit(f"anchor *{anchor_re} not found in {ppd}")
src = src[:m.end()] + line + "\n" + src[m.end():]
open(ppd, "w").write(src)
EOF
}

WPX=$(python3 -c "print(round($W_MM*300/25.4))")
HPX=$(python3 -c "print(round($H_MM*300/25.4))")
echo "Adding $NAME: ${W_MM}x${H_MM} mm = ${w_pt}x${h_pt} pt ($WPX x $HPX dots @300dpi)"

add "PageSize"  "OpenUI \*PageSize"  "*PageSize $NAME/$DESC: \"<</PageSize[$w_pt $h_pt]/ImagingBBox null>>setpagedevice\""
add "PageRegion" "OpenUI \*PageRegion" "*PageRegion $NAME/$DESC: \"<</PageSize[$w_pt $h_pt]/ImagingBBox null>>setpagedevice\""
add "ImageableArea" "DefaultImageableArea" "*ImageableArea $NAME/$DESC: \"0 0 $w_pt $h_pt\""
add "PaperDimension" "DefaultPaperDimension" "*PaperDimension $NAME/$DESC: \"$w_pt $h_pt\""

# remember the gap for the filter: keep a comment index (gap is passed via
# the lw-gap option; add-office helpers print the usage hint)
if [[ $GAP_MM != 2.0 ]]; then
    echo "*% lw-gap $NAME $GAP_MM" >> "$PPD"
    echo "  (note: use -o lw-gap=$GAP_MM for this size, or change add-size.sh)"
fi

echo "Added $NAME to $PPD"
if command -v lpstat >/dev/null 2>&1 && lpstat -p LW650XL_Labels >/dev/null 2>&1; then
    echo "Re-run  sudo ./install.sh  to apply the change to the installed printer."
fi
