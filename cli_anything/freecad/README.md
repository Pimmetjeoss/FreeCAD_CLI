# cli-anything-freecad

CLI harness for **FreeCAD** parametric 3D CAD modeler. Provides both
one-shot subcommands and an interactive REPL for creating, modifying,
and exporting 3D models via the real FreeCAD backend.

## Prerequisites

**FreeCAD** must be installed (hard dependency):

```bash
# Debian/Ubuntu
apt install freecad

# macOS
brew install --cask freecad

# Arch Linux
pacman -S freecad
```

Verify installation:
```bash
freecadcmd --version
```

## Installation

```bash
cd FreeCAD/agent-harness
pip install -e .
```

## Usage

### Interactive REPL
```bash
cli-anything-freecad
```

### One-shot commands
```bash
# Create a project
cli-anything-freecad project new -n MyPart -o part.json

# Add shapes
cli-anything-freecad --project part.json part box -l 20 -w 15 -H 10
cli-anything-freecad --project part.json part cylinder -r 5 -H 20
cli-anything-freecad --project part.json part fuse Box Cylinder

# Export to STEP
cli-anything-freecad --project part.json export step output.step --overwrite

# JSON output for agents
cli-anything-freecad --json project info
```

### TechDraw 2D fabrication drawings
```bash
# Create a drawing page
cli-anything-freecad --project part.json techdraw page -n Sheet1 -t A3_Landscape

# Add a front view of a 3D object
cli-anything-freecad --project part.json techdraw view Sheet1 Box -d front

# Add a multi-view projection group
cli-anything-freecad --project part.json techdraw projection Sheet1 Box -p Front -p Top -p Right

# Add dimensions
cli-anything-freecad --project part.json techdraw dimension Sheet1 View -t Distance -e Edge0

# Add annotations
cli-anything-freecad --project part.json techdraw annotate Sheet1 "Material: Steel" "Scale: 1:1"

# Export to DXF/SVG
cli-anything-freecad --project part.json techdraw export-dxf Sheet1 drawing.dxf --overwrite
cli-anything-freecad --project part.json techdraw export-svg Sheet1 drawing.svg --overwrite
```

### Title block (titelblok)
```bash
cli-anything-freecad --project part.json techdraw title-block Sheet1 \
  --title "Bouwtekening Dressoir" --author "Pim" \
  --material "Eiken massief" --scale "1:10" --date "2026-03-13" \
  --revision "A" --company "MijnBedrijf" --drawing-number "DWG-001"
```

### Detail view (uitvergroting)
```bash
cli-anything-freecad --project part.json techdraw detail Sheet1 Box FrontView \
  --ax 10 --ay 5 -r 15 -s 3.0
```

### Centerline (hartlijn)
```bash
cli-anything-freecad --project part.json techdraw centerline Sheet1 FrontView \
  -o vertical -p 50 --low -100 --high 100
```

### Hatch (arcering)
```bash
cli-anything-freecad --project part.json techdraw hatch Sheet1 SectionView \
  -f Face0 -p ansi31 -s 1.5 -r 45
```

### Leader line (verwijslijn)
```bash
cli-anything-freecad --project part.json techdraw leader Sheet1 FrontView \
  --sx 10 --sy 20 --ex 60 --ey 70 -t "Zie detail A"
```

### Balloon + BOM (stuklijst)
```bash
# Item-nummering met ballonnen
cli-anything-freecad --project part.json techdraw balloon Sheet1 FrontView \
  -t "1" -s circular -x 80 -y 30

# Stuklijst (Bill of Materials)
cli-anything-freecad --project part.json techdraw bom Sheet1 \
  -i "item=1,name=Zijpaneel,material=Eiken,quantity=2" \
  -i "item=2,name=Bovenpaneel,material=Eiken,quantity=1" \
  -i "item=3,name=Achterwand,material=MDF,quantity=1"
```

### Placement (positioning objects in 3D)
All primitives support `--px`, `--py`, `--pz` for 3D positioning:
```bash
cli-anything-freecad --project p.json part box -l 100 -w 50 -H 200 --px 10 --py 0 --pz 50
cli-anything-freecad --project p.json part cylinder -r 25 -H 100 --pz 200
cli-anything-freecad --project p.json part move MyBox --px 50 --py 0 --pz 100
```

### View direction aliases
Engineering-convention aliases for TechDraw views:
```bash
# Clear aliases (recommended)
cli-anything-freecad --project p.json techdraw view Sheet1 Box -d front-elevation  # width x height
cli-anything-freecad --project p.json techdraw view Sheet1 Box -d side-elevation   # depth x height
cli-anything-freecad --project p.json techdraw view Sheet1 Box -d plan             # width x depth
```

### Command groups
- `project` — Document management (new, open, save, info)
- `part` — 3D solid modeling (box, cylinder, sphere, cone, torus, booleans, move)
- `sketch` — 2D sketches (line, circle, arc, rect, constraints)
- `mesh` — Mesh import/export
- `techdraw` — 2D fabrication drawings (pages, views, projections, sections, detail views, dimensions, title block, centerlines, hatches, leaders, balloons, BOM, DXF/SVG/PDF export)
- `export` — Export to STEP, STL, OBJ, IGES, BREP, DXF, SVG, PDF
- `session` — Undo/redo, history, status

## Running tests

```bash
cd FreeCAD/agent-harness
pip install -e .
pytest cli_anything/freecad/tests/ -v -s
```

Force installed-command testing:
```bash
CLI_ANYTHING_FORCE_INSTALLED=1 pytest cli_anything/freecad/tests/ -v -s
```
