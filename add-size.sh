#!/bin/bash
# Add a label size to the PPD *before or after* installing (re-run install.sh
# afterwards if the queue already exists).
#
# Usage:  ./add-size.sh <name> <description> <width_mm> <height_mm>
#                       [--gap <mm>] [--pitch <mm>] [--voffset <mm>]
#                       [--left <mm>] [--right <mm>] [--top <mm>] [--bottom <mm>]
#                       [--rows <n>]
#
# Examples:
#   ./add-size.sh LW_76x51 "Logistics 76x51 mm" 76 51
#   ./add-size.sh LW_30x15 "Kasbon 30x15 mm" 30 15 --gap 0
#   ./add-size.sh LW_57x32 "Etiket 57x32 mm (AM11354)" 57 32 --gap 3 --pitch 38.6 --voffset 0.34
#   ./add-size.sh LW_36x89 "Adres 36x89 mm (AM99012, staand)" 36 89 \
#       --gap 4 --pitch 93 --left 3 --right 3 --top -0.5 --bottom 1
#
# --gap      distance between labels in mm, 0 for continuous stock (default 3)
# --pitch    what the printer feeds per label = label height + gap/liner.
#            Default is height + gap; measure the real roll if labels drift.
# --voffset  move the print down the label by this many mm (default 0), for
#            rolls whose printed area is not centred on the label.
# --left     dead zone between the label's left edge and the start of the head
#            (default 2). A narrower roll sits further left in the printer;
#            those mm can never be printed.
# --right    mm to keep free at the label's right edge (default 0.8). Set it
#            equal to --left to keep the print centred on such a roll.
# --top      distance from the bitmap origin to the label's top edge (default
#            5.1). The bitmap is anchored at its bottom, so tall labels start
#            higher up; measure with the ruler print. Negative is allowed:
#            those rows are out of the head's reach and print starts at 0.
# --bottom   mm to keep free at the label's bottom edge (default 0.7). Raise
#            it to match a top edge that is unreachable, so the print stays
#            centred on the label.
# --rotate   90 (clockwise) or 270 (counter-clockwise): print the page turned
#            on its side, useful when the unreachable edge must fall along the
#            feed direction instead of the label's left edge.
# --rows     pin the bitmap height in dots. Default: pitch in dots minus 12,
#            which is what the vendor app sends on most rolls; square rolls
#            from Labellife came with e.g. 356 rows for a 33.97 mm pitch.
set -euo pipefail

if [[ $# -lt 4 ]]; then
    echo "Usage: $0 <name> <description> <width_mm> <height_mm> [--gap <mm>] [--pitch <mm>] [--voffset <mm>] [--left <mm>] [--right <mm>] [--top <mm>] [--bottom <mm>]" >&2
    exit 1
fi

NAME="$1"; DESC="$2"; W_MM="$3"; H_MM="$4"; shift 4
GAP_MM=3.0
PITCH_MM=""
VOFFSET_MM=""
EXTRA=()
while [[ $# -gt 0 ]]; do
    case "$1" in
        --gap)    GAP_MM="${2:?--gap needs a value}"; shift 2 ;;
        --pitch)  PITCH_MM="${2:?--pitch needs a value}"; shift 2 ;;
        --voffset) EXTRA+=("voffset=${2:?--voffset needs a value}"); shift 2 ;;
        --left)   EXTRA+=("left=${2:?--left needs a value}"); shift 2 ;;
        --right)  EXTRA+=("right=${2:?--right needs a value}"); shift 2 ;;
        --top)    EXTRA+=("top=${2:?--top needs a value}"); shift 2 ;;
        --bottom) EXTRA+=("bottom=${2:?--bottom needs a value}"); shift 2 ;;
        --rows)   EXTRA+=("rows=${2:?--rows needs a value}"); shift 2 ;;
        --rotate) EXTRA+=("rotate=${2:?--rotate needs a value}"); shift 2 ;;
        *) echo "unknown option: $1" >&2; exit 1 ;;
    esac
done
[[ -n "$PITCH_MM" ]] || PITCH_MM="$(python3 -c "print(round($H_MM + $GAP_MM, 2))")"

here="$(cd "$(dirname "$0")" && pwd)"
PPD="${LW_PPD:-$here/cups/lw650xl-labels.ppd}"   # test runs can point at a copy
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
python3 - "$PPD" "$NAME" "$PITCH_MM" "$GAP_MM" "${EXTRA[@]}" <<'EOF'
import re, sys
ppd, name, pitch, gap, *extra = sys.argv[1:]
# Only the options the user actually typed are written: a 0 is a meaningful
# measurement (top=0 means the label starts exactly at the first print row),
# and anything absent falls back to the filter's default.
line = f"*% lw-media {name} pitch={pitch} gap={gap}"
for kv in extra:
    if kv.split("=", 1)[1].strip():
        line += f" {kv}"
line += "\n"
src = open(ppd).read()
src = re.sub(rf"^\*%\s*lw-media\s+{re.escape(name)}\b.*\n", "", src, flags=re.M)
i = src.find("*EOF")
src = (src[:i] + line + src[i:]) if i != -1 else (src + line)
open(ppd, "w").write(src)
EOF

echo "Added $NAME to $PPD (pitch $PITCH_MM, gap $GAP_MM ${EXTRA[*]:-})"
echo "  filter:   -o media=$NAME   (te overschrijven met -o lw-pitch / lw-gap / lw-voffset)"
echo "  CLI:      ./label \"tekst\" --size ${W_MM}x${H_MM} --pitch $PITCH_MM --gap $GAP_MM --voffset $VOFFSET_MM"
if command -v lpstat >/dev/null 2>&1 && lpstat -p LW650XL_Labels >/dev/null 2>&1; then
    echo "Re-run  sudo ./install.sh  to apply the change to the installed printer."
fi
