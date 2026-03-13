#!/bin/bash
# Workflow: Create a box and export to STEP
# Usage: bash workflow_box_to_step.sh

set -euo pipefail

CLI="cli-anything-freecad"

echo "=== Creating project ==="
$CLI project new -n "BoxDemo" -o /tmp/box_demo.json

echo "=== Adding box primitive ==="
$CLI part box -l 100 -w 60 -h 40

echo "=== Adding fillet ==="
$CLI part fillet --base Box -r 5

echo "=== Exporting to STEP ==="
$CLI export step -o /tmp/box_demo.step --overwrite

echo "=== Exporting to STL ==="
$CLI export stl -o /tmp/box_demo.stl --overwrite

echo "=== Done ==="
$CLI project info
