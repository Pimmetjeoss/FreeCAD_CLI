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
- `techdraw` — 2D fabrication drawings (pages, views, projections, dimensions, DXF/SVG/PDF export)
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
