#!/bin/bash
# Add a label size to the PPD *before or after* installing (re-run install.sh
# afterwards if the queue already exists).
#
# Usage:  ./add-size.sh <name> <description> <width_mm> <height_mm>
#                       [--gap <mm>] [--pitch <mm>]
#
# Examples:
#   ./add-size.sh LW_76x51 "Logistics 76x51 mm" 76 51
#   ./add-size.sh LW_30x15 "Kasbon 30x15 mm" 30 15 --gap 0
#   ./add-size.sh LW_57x32 "Etiket 57x32 mm (AM11354)" 57 32 --gap 3 --pitch 38.6 --voffset 1
#
# --gap      distance between labels in mm, 0 for continuous stock (default 3)
# --pitch    what the printer feeds per label = label height + gap/liner.
#            Default is height + gap; measure the real roll if labels drift.
# --voffset  move the print down the label by this many mm (default 0), for
#            rolls whose printed area is not centred on the label.
set -euo pipefail

if [[ $# -lt 4 ]]; then
    echo "Usage: $0 <name> <description> <width_mm> <height_mm> [--gap <mm>] [--pitch <mm>] [--voffset <mm>]" >&2
    exit 1
fi

NAME="$1"; DESC="$2"; W_MM="$3"; H_MM="$4"; shift 4
GAP_MM=3.0
PITCH_MM=""
VOFFSET_MM=0.0
while [[ $# -gt 0 ]]; do
    case "$1" in
        --gap)     GAP_MM="${2:?--gap needs a value}"; shift 2 ;;
        --pitch)   PITCH_MM="${2:?--pitch needs a value}"; shift 2 ;;
        --voffset) VOFFSET_MM="${2:?--voffset needs a value}"; shift 2 ;;
        *) echo "unknown option: $1" >&2; exit 1 ;;
    esac
done
[[ -n "$PITCH_MM" ]] || PITCH_MM="$(python3 -c "print(round($H_MM + $GAP_MM, 2))")"

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

add "PageSize"  "DefaultPageSize"  "*PageSize $NAME/$DESC: \"<</PageSize[$w_pt $h_pt]/ImagingBBox null>>setpagedevice\""
add "PageRegion" "DefaultPageRegion" "*PageRegion $NAME/$DESC: \"<</PageSize[$w_pt $h_pt]/ImagingBBox null>>setpagedevice\""
add "ImageableArea" "DefaultImageableArea" "*ImageableArea $NAME/$DESC: \"0 0 $w_pt $h_pt\""
add "PaperDimension" "DefaultPaperDimension" "*PaperDimension $NAME/$DESC: \"$w_pt $h_pt\""

# Record the geometry for the filter and the CLI in one PPD comment line:
#   *% lw-media LW_57x32 pitch=38.6 gap=3
# CUPS copies comments into /etc/cups/ppd/<queue>.ppd and passes that path to
# filters, so nothing else has to know about this size.
python3 - "$PPD" "$NAME" "$PITCH_MM" "$GAP_MM" "$VOFFSET_MM" <<'EOF'
import re, sys
ppd, name, pitch, gap, voffset = sys.argv[1:6]
line = f"*% lw-media {name} pitch={pitch} gap={gap}"
if float(voffset):
    line += f" voffset={voffset}"
line += "\n"
src = open(ppd).read()
src = re.sub(rf"^\*%\s*lw-media\s+{re.escape(name)}\b.*\n", "", src, flags=re.M)
i = src.find("*EOF")
src = (src[:i] + line + src[i:]) if i != -1 else (src + line)
open(ppd, "w").write(src)
EOF

echo "Added $NAME to $PPD  (pitch $PITCH_MM mm, gap $GAP_MM mm, voffset $VOFFSET_MM mm)"
echo "  filter:   -o media=$NAME   (te overschrijven met -o lw-pitch / lw-gap / lw-voffset)"
echo "  CLI:      ./label \"tekst\" --size ${W_MM}x${H_MM} --pitch $PITCH_MM --gap $GAP_MM --voffset $VOFFSET_MM"
if command -v lpstat >/dev/null 2>&1 && lpstat -p LW650XL_Labels >/dev/null 2>&1; then
    echo "Re-run  sudo ./install.sh  to apply the change to the installed printer."
fi
