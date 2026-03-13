---
name: freecad-cli-harness
description: Comprehensive skill for driving the cli-anything FreeCAD CLI harness — parametric 3D modeling, 2D sketching, boolean operations, TechDraw fabrication drawings, and multi-format export via the real FreeCAD/OCCT backend. This skill should be used when creating, modifying, or exporting 3D CAD models through the FreeCAD CLI, including building parts from primitives, generating technical drawings with dimensions and annotations, and exporting to STEP/STL/DXF/PDF. Covers all 58+ commands across 8 command groups.
---

# FreeCAD CLI Harness

## Overview

The FreeCAD CLI harness (cli-anything-freecad) provides full parametric 3D CAD through a JSON-based state machine. All geometry operations execute via the real FreeCAD/OpenCASCADE kernel through headless freecadcmd subprocess calls. The harness supports one-shot commands and an interactive REPL.

**Entry point:** cli-anything-freecad (or python -m cli_anything.freecad)
**Source:** cli_anything/freecad/
**State format:** JSON project files with immutable checkpoint-based undo/redo

## Architecture

```
User Input (CLI/REPL)
    |
    v
Click command validation + argument parsing
    |
    v
JSON object creation (immutable state)
    |
    v
Checkpoint to undo stack (max 50 snapshots)
    |
    v
FreeCAD Python script generation from JSON objects
    |
    v
Execute via freecadcmd subprocess (headless)
    |
    v
Parse JSON result --> Output (JSON or human-readable)
```

**Key design decisions:**
- All state stored as serializable JSON dicts (never FreeCAD-native objects)
- Mutations create new snapshots via session.checkpoint() before changes
- FreeCAD accessed only via subprocess (no in-process embedding)
- Auto-save triggers when project_path is set after each checkpoint

## Quick Start Workflow

```bash
# 1. Create project
cli-anything-freecad project new -n "MyModel" -o project.json

# 2. Add 3D primitives
cli-anything-freecad part box -l 100 -w 50 -h 30
cli-anything-freecad part cylinder -r 10 -ht 40 --py 25

# 3. Boolean operations
cli-anything-freecad part cut --base Box --tool Cylinder

# 4. Export to STEP
cli-anything-freecad export step -o output.step

# 5. Create technical drawing
cli-anything-freecad techdraw page --template A3_Landscape
cli-anything-freecad techdraw projection --source Cut --projections front,top,right
cli-anything-freecad techdraw dimension --view Front --type Distance --edge Edge1
cli-anything-freecad techdraw export-pdf -o drawing.pdf
```

## Command Reference

All commands support --json flag for machine-readable output. Refer to references/commands.md for the complete command reference with all parameters and options.

### Command Groups Overview

| Group | Commands | Purpose |
|-------|----------|---------|
| project | new, open, save, save-fcstd, info, inspect | Project lifecycle management |
| part | box, cylinder, sphere, cone, torus, fuse, cut, common, fillet, chamfer, list, remove, move | 3D solid primitives and operations |
| sketch | new, line, circle, arc, rect, constrain, list | 2D parametric sketching |
| mesh | import, from-part | Mesh import and conversion |
| export | step, stl, obj, iges, brep, render, formats | Multi-format export pipeline |
| techdraw | page, view, projection, section, detail, dimension, annotate, title-block, centerline, hatch, leader, balloon, bom, list, export-dxf, export-svg, export-pdf | 2D fabrication drawings |
| session | status, undo, redo, history | Session state and undo/redo |
| (root) | version, repl | Utilities |

## Project State Model

The project JSON structure forms the core of all operations:

```json
{
  "name": "MyProject",
  "created_at": "2026-03-13T12:34:56",
  "modified_at": "2026-03-13T12:35:10",
  "fcstd_path": "/path/to/doc.FCStd",
  "project_path": "/path/to/project.json",
  "objects": [
    {
      "name": "Box",
      "type": "Part::Box",
      "label": "Box",
      "params": {
        "length": 100, "width": 50, "height": 30,
        "placement": {"x": 0, "y": 0, "z": 0}
      }
    }
  ],
  "history": [],
  "modified": false
}
```

### Object Types

| Type | JSON type Field | Key Parameters |
|------|-----------------|----------------|
| Box | Part::Box | length, width, height |
| Cylinder | Part::Cylinder | radius, height, angle |
| Sphere | Part::Sphere | radius |
| Cone | Part::Cone | radius1, radius2, height |
| Torus | Part::Torus | radius1 (major), radius2 (minor) |
| Boolean Fuse | Part::Fuse | base, tool (object names) |
| Boolean Cut | Part::Cut | base, tool (object names) |
| Boolean Common | Part::Common | base, tool (object names) |
| Fillet | Part::Fillet | base, radius |
| Chamfer | Part::Chamfer | base, size |
| Extrusion | Part::Extrusion | base, dx, dy, dz |
| Sketch | Sketcher::SketchObject | plane, geometry[], constraints[] |
| Mesh Import | Mesh::Import | filepath |
| Drawing Page | TechDraw::DrawPage | template, scale, views[], dimensions[], annotations[], title_block, centerlines[], hatches[], leaders[], balloons[], bom[] |

All primitives support placement via --px, --py, --pz flags for positioning in 3D space.

## TechDraw (Technical Drawings)

TechDraw is the most feature-rich command group. Refer to references/techdraw.md for the complete TechDraw reference.

### Drawing Workflow

```
1. Create page      --> techdraw page --template A3_Landscape
2. Add views        --> techdraw view / projection / section / detail
3. Add dimensions   --> techdraw dimension (Distance, Radius, Diameter, Angle)
4. Add annotations  --> techdraw annotate, leader, balloon, bom
5. Set title block  --> techdraw title-block
6. Add details      --> techdraw centerline, hatch
7. Export           --> techdraw export-pdf / export-svg / export-dxf
```

### Paper Sizes

| Template | Size (mm) |
|----------|-----------|
| A4_Landscape | 297 x 210 |
| A4_Portrait | 210 x 297 |
| A3_Landscape | 420 x 297 |
| A3_Portrait | 297 x 420 |
| A2_Landscape | 594 x 420 |
| A1_Landscape | 841 x 594 |
| A0_Landscape | 1189 x 841 |

### View Directions

| Name | Vector | Use Case |
|------|--------|----------|
| front | (0,0,1) | Default front view |
| back | (0,0,-1) | Rear view |
| top | (0,-1,0) | Top-down view |
| bottom | (0,1,0) | Bottom view |
| left | (-1,0,0) | Left side view |
| right | (1,0,0) | Right side view |
| iso | (1,-1,1) | Isometric perspective |
| front-elevation | (0,-1,0) | Engineering: width x height |
| side-elevation | (1,0,0) | Engineering: depth x height |
| plan | (0,0,1) | Engineering: width x depth |
| rear-elevation | (0,1,0) | Engineering: rear view |

## Export Pipeline

The export flow always goes through FreeCAD's real geometry kernel:

```
Project JSON --> Save as .FCStd (temp) --> FreeCAD export module --> Target format
```

### Supported Formats

| Format | Extensions | Export Method |
|--------|------------|--------------|
| STEP | .step, .stp | Part.export() |
| IGES | .iges, .igs | Part.export() |
| STL | .stl | MeshPart.meshFromShape() + Mesh.write() |
| OBJ | .obj | MeshPart.meshFromShape() + Mesh.write() |
| BREP | .brep, .brp | shape.exportBrep() |
| FreeCAD | .fcstd | Native save |
| DXF | .dxf | TechDraw export |
| SVG | .svg | TechDraw export |
| PDF | .pdf | TechDraw export |

## FreeCAD Python Script Generation

Each JSON object is converted to FreeCAD Python code. Refer to references/script-patterns.md for the complete FreeCAD Python API patterns and script generation logic.

### Core Pattern

```python
import FreeCAD
import Part
doc = FreeCAD.newDocument("MyProject")

# Primitives
_obj = doc.addObject('Part::Box', 'Box')
_obj.Length, _obj.Width, _obj.Height = 100, 50, 30
_obj.Placement = FreeCAD.Placement(
    FreeCAD.Vector(0, 0, 0), FreeCAD.Rotation(0, 0, 0, 1))

# Boolean operations
_obj = doc.addObject('Part::Cut', 'Cut')
_obj.Base = doc.getObject('Box')
_obj.Tool = doc.getObject('Cylinder')

doc.recompute()
```

### Backend Execution

All scripts execute via freecad_backend.run_script():
1. Script written to temp file
2. Wrapped with try/except and JSON result writer
3. Executed via freecadcmd script.py
4. Results parsed from JSON output file
5. Temp files cleaned up automatically

## Sketch System

Sketches support 2D geometry on XY, XZ, or YZ planes:

### Geometry Types

| Type | Parameters | FreeCAD API |
|------|------------|-------------|
| line | x1, y1, x2, y2 | Part.LineSegment(Vector, Vector) |
| circle | cx, cy, radius | Part.Circle(center, normal, radius) |
| arc | cx, cy, radius, start_angle, end_angle | Part.ArcOfCircle(circle, a1_rad, a2_rad) |
| rect | x, y, width, height | 4 LineSegments + Coincident + H/V constraints |

### Constraint Types

| Constraint | Parameters | Description |
|------------|------------|-------------|
| Horizontal | geometry | Force horizontal |
| Vertical | geometry | Force vertical |
| Distance | geometry, value | Set length |
| Radius | geometry, value | Set radius |
| Coincident | geometry, geometry2, point1, point2 | Connect points |
| Parallel | geometry, geometry2 | Force parallel |
| Perpendicular | geometry, geometry2 | Force perpendicular |
| Equal | geometry, geometry2 | Equal length/radius |
| Angle | geometry, value (degrees) | Set angle |

## Session Management

- **Undo stack:** Max 50 deep-copy snapshots (FIFO overflow)
- **Checkpoint:** Called before every mutation, saves full project state
- **Auto-save:** Triggers after each checkpoint when project_path is set
- **History:** Lists all performed operations in chronological order

## Error Handling Patterns

- **Input validation:** Click framework validates types, ranges, and required fields
- **File safety:** Overwrites blocked without explicit --overwrite flag
- **Backend errors:** Captured in _cli_result['error'] + _cli_result['traceback']
- **User-facing:** raise click.ClickException("readable message")
- **JSON mode:** {"error": "message"} + sys.exit(1)

## Common Workflows

### Furniture / Enclosure Modeling

```bash
project new -n "Kast" -o kast.json
part box -l 800 -w 400 -h 1200 --name Corpus
part box -l 780 -w 380 -h 20 --name Plank --pz 400
part box -l 20 -w 380 -h 1160 --name ZijwandL --px 0 --pz 20
part box -l 20 -w 380 -h 1160 --name ZijwandR --px 780 --pz 20
export step -o kast.step
```

### Technical Drawing with BOM

```bash
techdraw page --template A3_Landscape --scale 1:10
techdraw projection --source Corpus --projections front,top,right
techdraw dimension --view Front --type Distance --edge Edge1
techdraw title-block --title "Kast" --author "Ontwerper" --scale "1:10"
techdraw bom --items "1,Corpus,Multiplex 18mm,1" "2,Plank,Multiplex 18mm,3"
techdraw export-pdf -o kast_tekening.pdf
```

### Boolean Subtraction (Holes/Cutouts)

```bash
part box -l 100 -w 100 -h 50 --name Base
part cylinder -r 15 -ht 60 --name Hole --px 50 --py 50 --pz -5
part cut --base Base --tool Hole
export stl -o base_with_hole.stl
```

### Sketch to Extrusion

```bash
sketch new --plane XY --name Profile
sketch rect --sketch Profile -x 0 -y 0 -w 50 -ht 30
sketch circle --sketch Profile --cx 25 --cy 15 -r 8
export step -o extruded.step
```

## Resources

### references/

- commands.md - Complete CLI command reference with all parameters, flags, and options
- techdraw.md - Full TechDraw API reference: views, dimensions, annotations, hatches, BOM, export
- script-patterns.md - FreeCAD Python API patterns, script generation, and backend integration

### scripts/

- workflow_box_to_step.sh - Example end-to-end workflow: create box, export to STEP
- workflow_drawing.sh - Example: create model with full technical drawing and PDF export
