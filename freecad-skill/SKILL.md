---
name: freecad-cli-harness
description: Comprehensive skill for driving the cli-anything FreeCAD CLI harness — parametric 3D modeling, 2D sketching, boolean operations, PartDesign (Pad, Pocket, Patterns, Draft, Fillet, Chamfer, Thickness), Assembly workbench (multi-part products, constraints, exploded views), FEM analysis (stress, thermal, modal), TechDraw fabrication drawings with GD&T (ISO 1101 / ASME Y14.5), datum symbols, surface finish (ISO 1302), weld symbols (AWS A2.4 / ISO 2553), DXF/SVG import for laser cutting, 3MF export for 3D printing, and multi-format export via the real FreeCAD/OCCT backend. This skill should be used when creating, modifying, analyzing, or exporting 3D CAD models through the FreeCAD CLI, including building parts from primitives, parametric design, assembly management, finite element analysis, generating technical drawings with dimensions, tolerances, weld annotations, and manufacturing validation. Covers all 130+ commands across 12 command groups.
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

# 3. PartDesign operations (parametric)
cli-anything-freecad sketch new -p XY
cli-anything-freecad sketch line sketch001 --x1 0 --y1 0 --x2 50 --y2 0
cli-anything-freecad partdesign pad sketch001 -l 10
cli-anything-freecad partdesign linear-pattern Pad001 -d X -l 100 -n 5

# 4. Boolean operations
cli-anything-freecad part cut --base Box --tool Cylinder

# 5. Export to STEP
cli-anything-freecad export step -o output.step

# 6. Create technical drawing
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
| part | box, cylinder, sphere, cone, torus, **helix**, fuse, cut, common, fillet, chamfer, **import-step, import-dxf**, list, remove, move | 3D solid primitives, operations, and import |
| **partdesign** | **body, pad, pocket, features, linear-pattern, polar-pattern, draft, fillet, chamfer, thickness, edge-treatments, patterns** | **Parametric modeling with sketches** |
| sketch | new, line, **construction-line**, circle, arc, rect, constrain (**+Tangent, Symmetric**), list | 2D parametric sketching with construction lines |
| **assembly** | **create, add-part, constraint, explode, info** | **Multi-part product assembly** |
| **fem** | **analysis, material, mesh, fixed, force, solve, info** | **Finite element analysis (stress/thermal)** |
| mesh | import, from-part | Mesh import and conversion |
| export | step, stl, obj, iges, brep, **3mf**, render, formats | Multi-format export pipeline |
| **dxf-import** | **dxf-import, dxf-info** | **DXF import for laser cutting workflows** |
| **svg-import** | **svg-import** | **SVG import for vector graphics** |
| **validate-lasercut** | **validate-lasercut** | **Manufacturing QA validation** |
| techdraw | page, view, projection, section, detail, dimension, annotate, title-block, centerline, hatch, leader, **balloon, auto-balloon, bom, documentation**, gdt, datum, surface-finish, weld, weld-tile, list, export-dxf, export-svg, export-pdf | 2D fabrication drawings + GD&T + welds + **BOM** |
| session | status, undo, redo, history | Session state and undo/redo |
| (root) | version, repl, **dxf-info** | Utilities |

### New Manufacturing Features (Tier 1-3)

#### DXF Import (Laser Cutting)
```bash
# Import DXF for laser cutting
cli-anything-freecad dxf-import customer_drawing.dxf -u mm -l "CUT_LAYER,ENGRAVE_LAYER"
cli-anything-freecad dxf-info customer_drawing.dxf  # Analyze without importing
```

#### 3MF Export (3D Printing)
```bash
# Export for 3D printing with metadata
cli-anything-freecad export 3mf model.3mf --overwrite
```

#### PartDesign (Parametric Manufacturing)
```bash
# Parametric pad from sketch
cli-anything-freecad sketch new -p XY -n BaseSketch
cli-anything-freecad sketch rect BaseSketch -w 100 -H 50
cli-anything-freecad partdesign pad BaseSketch -l 10 -n BasePlate

# Manufacturing patterns
cli-anything-freecad partdesign linear-pattern BasePlate -d X -l 200 -n 5  # Hole array
cli-anything-freecad partdesign polar-pattern Hole001 -a Z --angle 360 -n 8  # Bolt circle

# Manufacturing edge treatment
cli-anything-freecad partdesign fillet Edge001 -r 2.0  # Stress relief
cli-anything-freecad partdesign chamfer Edge002 -s 1.5 -a 45  # Deburring
cli-anything-freecad partdesign draft Face001 -a 3.0  # Casting draft

# Shell structures
cli-anything-freecad partdesign thickness Face001 -t 2.0 -m thickness  # Sheet metal
```

#### Assembly (Multi-Part Products)
```bash
# Create assembly
cli-anything-freecad assembly create -n Cabinet -p Base,Top,Side1,Side2

# Add constraints
cli-anything-freecad assembly constraint Cabinet Base Top -t coincident
cli-anything-freecad assembly constraint Cabinet Base Side1 -t perpendicular

# Assembly documentation
cli-anything-freecad assembly explode Cabinet -f 2.0
cli-anything-freecad assembly info Cabinet
```

#### FEM Analysis (Structural Validation)
```bash
# Setup analysis
cli-anything-freecad fem analysis -n StressTest
cli-anything-freecad fem material StressTest Part001 -m Steel
cli-anything-freecad fem mesh StressTest Part001 -s 5.0

# Apply loads and solve
cli-anything-freecad fem fixed StressTest Part001 -f BaseFace
cli-anything-freecad fem force StressTest Part001 -z -1000 -f TopFace
cli-anything-freecad fem solve StressTest -s CalculiX -t static
cli-anything-freecad fem info StressTest
```

#### Manufacturing Validation
```bash
# Validate geometry for laser cutting
cli-anything-freecad validate-lasercut --min-feature 0.5 --kerf-width 0.15 --plate-width 1000 --plate-height 500
```

## Project State Model

The project JSON structure forms the core of all operations:

```json
{
  "name": "MyProject",
  "created_at": "2026-03-17T04:30:00",
  "modified_at": "2026-03-17T04:35:10",
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

### Object Types (Extended)

| Type | JSON type Field | Key Parameters |
|------|-----------------|----------------|
| **Part Primitives** | | |
| Box | Part::Box | length, width, height |
| Cylinder | Part::Cylinder | radius, height, angle |
| Sphere | Part::Sphere | radius |
| Cone | Part::Cone | radius1, radius2, height |
| Torus | Part::Torus | radius1 (major), radius2 (minor) |
| **Helix** | **Part::Helix** | **radius, pitch, height, angle, ccw** |
| **PartDesign** | | |
| **Pad** | **PartDesign::Pad** | **sketch, length, symmetric, reversed** |
| **Pocket** | **PartDesign::Pocket** | **sketch, type (Length/ThroughAll/UpToFace), length** |
| **Linear Pattern** | **PartDesign::LinearPattern** | **feature, direction, length, occurrences** |
| **Polar Pattern** | **PartDesign::PolarPattern** | **feature, axis, angle, occurrences** |
| **Draft** | **PartDesign::Draft** | **face, angle, neutral_plane, reversed** |
| **Fillet** | **PartDesign::Fillet** | **edge, radius** |
| **Chamfer** | **PartDesign::Chamfer** | **edge, size, angle** |
| **Thickness** | **PartDesign::Thickness** | **face, thickness, mode, join** |
| **Assembly** | | |
| **Assembly** | **Assembly::AssemblyObject** | **parts[], constraints[]** |
| **Constraint** | **Assembly::Constraint** | **type, part1, part2** |
| **Exploded View** | **Assembly::ExplodedView** | **assembly, explode_factor** |
| **FEM** | | |
| **Analysis** | **Fem::FemAnalysis** | **materials[], meshes[], constraints[], solvers[]** |
| **Material** | **Fem::Material** | **name, properties (Young's modulus, Poisson's ratio, etc.)** |
| **Mesh** | **Fem::FemMeshMesh** | **shape, element_size, element_type** |
| **Fixed Constraint** | **Fem::ConstraintFixed** | **references[], face** |
| **Force Constraint** | **Fem::ConstraintForce** | **references[], force_x/y/z, face** |
| **Solver** | **Fem::FemSolverObject** | **solver_type, analysis_type** |
| **Manufacturing** | | |
| **DXF Import** | **Part::Feature** | **filepath, units, layer_filter, scale** |
| **SVG Import** | **ImportSVG** | **filepath, target_units, scale** |
| **Lasercut Validation** | N/A | **min_feature, kerf_width, plate_dimensions** |
| **Boolean Operations** | | |
| Boolean Fuse | Part::Fuse | base, tool (object names) |
| Boolean Cut | Part::Cut | base, tool (object names) |
| Boolean Common | Part::Common | base, tool (object names) |
| **Sketching** | | |
| Sketch | Sketcher::SketchObject | plane, geometry[], constraints[] |
| **Construction Line** | (line with construction=True) | **x1, y1, x2, y2, construction: true** |
| **Constraints** | | |
| **Tangent** | Sketcher::Constraint('Tangent') | **geometry, geometry2** |
| **Symmetric** | Sketcher::Constraint('Symmetric') | **geometry, geometry2** |
| **TechDraw (Extended)** | | |
| Drawing Page | TechDraw::DrawPage | template, scale, views[], dimensions[], annotations[], title_block, centerlines[], hatches[], leaders[], **balloons[], bom[]**, gdt[], datums[], surface_finishes[], welds[] |
| **BOM** | **Spreadsheet::Sheet** | **template, items[], headers[]** |
| **Balloon** | **TechDraw::DrawViewBalloon** | **source_view, x, y, text, symbol** |
| GD&T Tolerance | TechDraw::GeometricTolerance | characteristic, symbol, tolerance, datum_refs[], material_condition, diameter_zone |
| Datum Symbol | TechDraw::DatumSymbol | letter, view, x, y |
| Surface Finish | TechDraw::SurfaceFinish | ra, rz, process, lay_direction |
| Weld Symbol | TechDraw::WeldSymbol | weld_type, tiles[], all_around, field_weld, tail, contour |

## TechDraw (Technical Drawings)

TechDraw is the most feature-rich command group. Refer to references/techdraw.md for the complete TechDraw reference.

### Drawing Workflow

```
1. Create page      --> techdraw page --template A3_Landscape
2. Add views        --> techdraw view / projection / section / detail
3. Add dimensions   --> techdraw dimension (Distance, Radius, Diameter, Angle)
4. Add GD&T         --> techdraw datum, techdraw gdt, techdraw surface-finish
5. Add welds        --> techdraw weld, techdraw weld-tile
6. Add annotations  --> techdraw annotate, leader, **balloon, auto-balloon, bom**
7. Set title block  --> techdraw title-block
8. Add details      --> techdraw centerline, hatch
9. **Documentation** --> **techdraw documentation** (list all BOMs/balloons)
10. Export           --> techdraw export-pdf / export-svg / export-dxf
```

### BOM and Balloons (New)

```bash
# Create Bill of Materials
cli-anything-freecad techdraw bom Sheet1 -t default -o "Part1,Part2,Part3"

# Add balloon callouts
cli-anything-freecad techdraw balloon Sheet1 View001 -t "1" -x 50 -y 30 -s circle

# Auto-generate balloons for all parts
cli-anything-freecad techdraw auto-balloon Sheet1 View001 -n 1 -s circle

# List all documentation on page
cli-anything-freecad techdraw documentation Sheet1
```

## Manufacturing Workflows

### Laser Cutting Workflow
```bash
# 1. Import customer DXF
cli-anything-freecad dxf-import customer_part.dxf -u mm -l "CUT"

# 2. Validate for manufacturing
cli-anything-freecad validate-lasercut --min-feature 0.5 --kerf-width 0.15

# 3. Export for laser cutter
cli-anything-freecad export dxf laser_ready.dxf --overwrite
```

### 3D Printing Workflow
```bash
# 1. Create parametric model
cli-anything-freecad sketch new -p XY
cli-anything-freecad sketch rect sketch001 -w 40 -H 40
cli-anything-freecad partdesign pad sketch001 -l 20

# 2. Add features
cli-anything-freecad partdesign pocket sketch002 --through-all  # Mounting holes

# 3. Export for printing
cli-anything-freecad export 3mf print_ready.3mf --overwrite
```

### Assembly Manufacturing Workflow
```bash
# 1. Create assembly
cli-anything-freecad assembly create -n Product -p Part1,Part2,Part3

# 2. Add constraints
cli-anything-freecad assembly constraint Product Part1 Part2 -t coincident

# 3. Generate assembly drawing
cli-anything-freecad techdraw page -n AssemblyDrawing -t A2_Landscape
cli-anything-freecad techdraw view AssemblyDrawing Product -d front
cli-anything-freecad techdraw bom AssemblyDrawing -t detailed
cli-anything-freecad techdraw auto-balloon AssemblyDrawing View001

# 4. Export
cli-anything-freecad techdraw export-pdf AssemblyDrawing assembly.pdf
```

## Best Practices

1. **Always create a project first** - All operations require an active project
2. **Use parametric design** - Sketches + PartDesign for manufacturing intent
3. **Validate before manufacturing** - Use validate-lasercut for laser cutting
4. **Generate documentation** - TechDraw BOM + balloons for assembly instructions
5. **Use JSON output** - For AI integration: `--json` flag
6. **Checkpoint frequently** - Undo/redo works on checkpoints

## Integration with AI Agents

The FreeCAD CLI is designed for AI agent integration:

- **JSON output** on all commands (`--json` flag)
- **Structured state** in project JSON files
- **Deterministic operations** via FreeCAD backend
- **Self-describing** via `--help` on all commands
- **Undo/redo** for safe experimentation

Example AI workflow:
```bash
# AI can create models, validate, and export autonomously
cli-anything-freecad --json project new -n "AI_Model" -o model.json
cli-anything-freecad --json part box -l 100 -w 50 -h 25
cli-anything-freecad --json validate-lasercut
cli-anything-freecad --json export step model.step
```