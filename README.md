# FreeCAD CLI

A command-line interface for **FreeCAD** that lets you create, modify, and export parametric 3D models without opening the GUI. Includes full support for 2D fabrication drawings (TechDraw).

## Features

- **3D Modeling** — Primitives (box, cylinder, sphere, cone, torus), boolean operations, positioning
- **2D Sketches** — Lines, circles, arcs, rectangles with constraints
- **TechDraw Drawings** — Views, projection groups, cross-sections, detail views, dimensions, title block, centerlines, hatches, leader lines, balloons, bill of materials (BOM), **GD&T tolerances (ISO 1101 / ASME Y14.5), datum symbols, surface finish (ISO 1302)**
- **Export** — STEP, STL, OBJ, IGES, BREP, DXF, SVG, PDF
- **Interactive REPL** and one-shot commands
- **JSON output** for AI agent integration
- **Undo/redo** with session history

## Prerequisites

**FreeCAD** must be installed:

```bash
# Debian/Ubuntu
apt install freecad

# macOS
brew install --cask freecad

# Arch Linux
pacman -S freecad

# Windows
winget install FreeCAD
```

Verify:
```bash
freecadcmd --version
```

## Installation

```bash
git clone https://github.com/Pimmetjeoss/FreeCAD_CLI.git
cd FreeCAD_CLI
pip install -e .
```

## Quick Start

```bash
# Create a new project
cli-anything-freecad project new -n Cabinet -o cabinet.json

# Add 3D objects
cli-anything-freecad --project cabinet.json part box -l 900 -w 500 -H 800 -n Body
cli-anything-freecad --project cabinet.json part box -l 900 -w 500 -H 20 -n TopPanel --pz 800

# Create a fabrication drawing
cli-anything-freecad --project cabinet.json techdraw page -n Sheet1 -t A3_Landscape -s 0.1
cli-anything-freecad --project cabinet.json techdraw view Sheet1 Body -d front-elevation
cli-anything-freecad --project cabinet.json techdraw view Sheet1 Body -d side-elevation -x 300
cli-anything-freecad --project cabinet.json techdraw dimension Sheet1 View -t DistanceX
cli-anything-freecad --project cabinet.json techdraw title-block Sheet1 \
  --title "Cabinet Drawing" --material "Solid Oak" --scale "1:10"

# Bill of materials
cli-anything-freecad --project cabinet.json techdraw bom Sheet1 \
  -i "item=1,name=Body,material=Oak,quantity=1" \
  -i "item=2,name=Top Panel,material=Oak,quantity=1"

# Export
cli-anything-freecad --project cabinet.json techdraw export-svg Sheet1 cabinet.svg --overwrite
cli-anything-freecad --project cabinet.json export step cabinet.step --overwrite
```

## Command Overview

| Group | Commands |
|-------|----------|
| `project` | `new`, `open`, `save`, `info`, `close` |
| `part` | `box`, `cylinder`, `sphere`, `cone`, `torus`, `fuse`, `cut`, `common`, `fillet`, `chamfer`, `move`, `list` |
| `sketch` | `new`, `line`, `circle`, `arc`, `rect`, `constrain`, `close`, `list` |
| `mesh` | `import`, `from-part` |
| `techdraw` | `page`, `view`, `projection`, `section`, `detail`, `dimension`, `annotate`, `title-block`, `centerline`, `hatch`, `leader`, `balloon`, `bom`, **`gdt`**, **`datum`**, **`surface-finish`**, `list`, `export-dxf`, `export-svg`, `export-pdf` |
| `export` | `step`, `stl`, `obj`, `iges`, `brep`, `render`, `formats` |
| `session` | `status`, `undo`, `redo`, `history` |

## TechDraw 2D Drawings

Full support for professional fabrication drawings:

```bash
# Title block
techdraw title-block Sheet1 --title "..." --author "..." --material "..." --scale "1:10"

# Detail view (magnification)
techdraw detail Sheet1 Box FrontView --ax 10 --ay 5 -r 15 -s 3.0

# Centerlines
techdraw centerline Sheet1 FrontView -o vertical -p 50

# Hatching (cross-sections)
techdraw hatch Sheet1 SectionView -f Face0 -p ansi31

# Leader lines
techdraw leader Sheet1 FrontView --sx 10 --sy 20 --ex 60 --ey 70 -t "See detail A"

# Balloons (item numbering)
techdraw balloon Sheet1 FrontView -t "1" -s circular -x 80 -y 30

# Bill of Materials (BOM)
techdraw bom Sheet1 -i "item=1,name=Side Panel,material=Oak,quantity=2"
```

### GD&T — Geometric Dimensioning & Tolerancing

```bash
# Datum feature symbols
techdraw datum Sheet1 FrontView A
techdraw datum Sheet1 FrontView B

# Position tolerance with datums and MMC
techdraw gdt Sheet1 FrontView -c position -t 0.05 -d A -d B -m MMC --diameter-zone

# Flatness (form tolerance, no datums)
techdraw gdt Sheet1 FrontView -c flatness -t 0.01

# Surface finish (ISO 1302)
techdraw surface-finish Sheet1 FrontView --ra 1.6 -p removal_required
```

14 GD&T characteristics supported (form, orientation, location, runout, profile). All render in SVG export as ISO-standard Feature Control Frames.

## JSON Mode

All commands support `--json` output for AI agent integration:

```bash
cli-anything-freecad --json --project p.json part box -l 20
# {"name": "Box", "type": "Part::Box", "params": {"length": 20.0, ...}}
```

## Architecture

```
cli_anything/freecad/
  freecad_cli.py          # Click CLI entry point + REPL
  core/
    project.py            # Project state (JSON) + FreeCAD script generation
    session.py            # Undo/redo with deep-copy snapshots
    techdraw.py           # 2D drawings, views, dimensions, export
    export.py             # Export pipeline (project -> FCStd -> STEP/STL/etc.)
  utils/
    freecad_backend.py    # freecadcmd subprocess wrapper
    repl_skin.py          # Interactive REPL styling
  tests/
    test_core.py          # Unit + CLI tests (264 tests)
    test_full_e2e.py      # End-to-end tests with FreeCAD backend
```

The CLI stores project state as JSON. On export/save it generates a FreeCAD Python script and executes it via `freecadcmd` (headless), so all geometry uses the real OpenCASCADE kernel.

## Tests

```bash
pip install -e .
pytest cli_anything/freecad/tests/ -v
```

## License

MIT
