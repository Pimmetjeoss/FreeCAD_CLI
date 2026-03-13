#!/bin/bash
# Workflow: Create a model with full technical drawing and PDF export
# Usage: bash workflow_drawing.sh

set -euo pipefail

CLI="cli-anything-freecad"

echo "=== Creating project ==="
$CLI project new -n "TechnicalDrawing" -o /tmp/techdraw_demo.json

echo "=== Building 3D model ==="
$CLI part box -l 200 -w 100 -h 50 --name Base
$CLI part cylinder -r 15 -ht 60 --name Hole --px 100 --py 50 --pz -5
$CLI part cut --base Base --tool Hole --name BaseWithHole

echo "=== Creating drawing page ==="
$CLI techdraw page --template A3_Landscape --scale 0.5

echo "=== Adding projection views ==="
$CLI techdraw projection --source BaseWithHole --projections Front,Top,Right

echo "=== Adding section view ==="
$CLI techdraw section --source BaseWithHole --base-view Front --normal x

echo "=== Adding dimensions ==="
$CLI techdraw dimension --view Front --type Distance --edge Edge1
$CLI techdraw dimension --view Front --type DistanceX --edge Edge2 -y 25

echo "=== Adding centerline ==="
$CLI techdraw centerline --view Front --orientation vertical --position 100

echo "=== Adding hatch to section ==="
$CLI techdraw hatch --view SectionA --face Face1 --pattern ansi31

echo "=== Adding annotations ==="
$CLI techdraw annotate --text "GENERAL TOLERANCE: +/- 0.5mm" -x 20 -y 190
$CLI techdraw leader --view Front --text "Bore D30" --start-x 100 --start-y 50 --end-x 140 --end-y 70

echo "=== Adding GD&T annotations ==="
$CLI techdraw datum Page Front A -x 50 -y 120
$CLI techdraw datum Page Front B -x 150 -y 120
$CLI techdraw gdt Page Front -c position -t 0.05 -d A -d B -m MMC --diameter-zone
$CLI techdraw gdt Page Front -c flatness -t 0.01
$CLI techdraw surface-finish Page Front --ra 1.6 -p removal_required

echo "=== Adding weld symbols ==="
$CLI techdraw weld Page Front -t fillet -s arrow --size 5 --length 50 -x 120 -y 90
$CLI techdraw weld Page Front -t v_groove -s arrow --size 6 --all-around --tail "GMAW" -x 120 -y 60
$CLI techdraw weld-tile Page Weld1 -t fillet -s other --size 3

echo "=== Adding balloons ==="
$CLI techdraw balloon --view Front --text "1" --origin-x 50 --origin-y 25

echo "=== Adding BOM ==="
$CLI techdraw bom --items "1,Base,Steel S235,1" "2,Hole (bore),D30 x 60,1"

echo "=== Setting title block ==="
$CLI techdraw title-block \
    --title "Base Plate Assembly" \
    --author "Engineer" \
    --date "2026-03-13" \
    --scale "1:2" \
    --material "Steel S235" \
    --revision "A" \
    --company "Workshop" \
    --drawing-number "DWG-001"

echo "=== Exporting ==="
$CLI techdraw export-pdf -o /tmp/techdraw_demo.pdf --overwrite
$CLI techdraw export-svg -o /tmp/techdraw_demo.svg --overwrite
$CLI techdraw export-dxf -o /tmp/techdraw_demo.dxf --overwrite

echo "=== Exporting 3D model ==="
$CLI export step -o /tmp/techdraw_demo.step --overwrite

echo "=== Done! ==="
echo "PDF: /tmp/techdraw_demo.pdf"
echo "SVG: /tmp/techdraw_demo.svg"
echo "DXF: /tmp/techdraw_demo.dxf"
echo "STEP: /tmp/techdraw_demo.step"
