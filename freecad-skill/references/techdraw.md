# TechDraw API Reference

## Overview

TechDraw is the 2D fabrication drawing module. It generates ISO-standard technical drawings
from 3D models with views, dimensions, annotations, BOM tables, and exports to DXF/SVG/PDF.

## Drawing Page Structure (JSON)

```json
{
  "name": "Page",
  "type": "TechDraw::DrawPage",
  "label": "Page",
  "params": {
    "template": "A3_Landscape",
    "scale": 1.0,
    "views": [
      {
        "name": "FrontView",
        "type": "TechDraw::DrawViewPart",
        "source": "Box",
        "direction": [0, 0, 1],
        "x": 150, "y": 100,
        "rotation": 0
      }
    ],
    "dimensions": [
      {
        "view": "FrontView",
        "type": "Distance",
        "edge": "Edge1",
        "x": 0, "y": 20
      }
    ],
    "annotations": [
      {
        "text": "DETAIL A",
        "x": 50, "y": 50,
        "font_size": 5
      }
    ],
    "title_block": {
      "title": "Assembly Drawing",
      "author": "Engineer",
      "date": "2026-03-13",
      "scale": "1:5",
      "material": "Steel",
      "revision": "A",
      "company": "ACME",
      "drawing_number": "DWG-001",
      "sheet": "1/1",
      "checked_by": "QA",
      "approved_by": "PM"
    },
    "centerlines": [
      {
        "view": "FrontView",
        "orientation": "vertical",
        "position": 50,
        "extent_low": -30,
        "extent_high": 30
      }
    ],
    "hatches": [
      {
        "view": "SectionView",
        "face": "Face1",
        "pattern": "ansi31",
        "scale": 1.0,
        "rotation": 0,
        "color": "0,0,0"
      }
    ],
    "leaders": [
      {
        "view": "FrontView",
        "start_x": 10, "start_y": 10,
        "end_x": 40, "end_y": 25,
        "text": "Surface finish Ra 1.6",
        "arrow_style": "filled"
      }
    ],
    "balloons": [
      {
        "view": "FrontView",
        "origin_x": 50, "origin_y": 25,
        "text": "1",
        "shape": "circular",
        "x": 70, "y": 40
      }
    ],
    "bom": [
      {
        "pos": "1",
        "name": "Corpus",
        "material": "Multiplex 18mm",
        "quantity": "1"
      }
    ],
    "gdt": [
      {
        "name": "GDT1",
        "type": "TechDraw::GeometricTolerance",
        "view": "FrontView",
        "characteristic": "position",
        "symbol": "⌖",
        "category": "location",
        "tolerance": 0.05,
        "diameter_zone": true,
        "material_condition": "MMC",
        "material_condition_symbol": "Ⓜ",
        "datum_refs": ["A", "B"],
        "x": 100, "y": 80
      }
    ],
    "datums": [
      {
        "name": "DatumA",
        "type": "TechDraw::DatumSymbol",
        "view": "FrontView",
        "letter": "A",
        "x": 50, "y": 120
      }
    ],
    "surface_finishes": [
      {
        "name": "SF1",
        "type": "TechDraw::SurfaceFinish",
        "view": "FrontView",
        "ra": 1.6,
        "rz": null,
        "process": "removal_required",
        "process_symbol": "▽",
        "lay_direction": "=",
        "x": 80, "y": 60
      }
    ]
  }
}
```

## View Types

### DrawViewPart (Single View)
A single 2D projection of a 3D object from a specific direction.

FreeCAD API:
```python
view = doc.addObject('TechDraw::DrawViewPart', 'FrontView')
view.Source = [doc.getObject('Box')]
view.Direction = FreeCAD.Vector(0, 0, 1)
view.X, view.Y = 150, 100
view.Rotation = 0
page.addView(view)
```

### DrawProjGroup (Projection Group)
Multiple standard orthographic views arranged automatically.

Available projections: Front, Top, Right, Left, Bottom, Rear

FreeCAD API:
```python
group = doc.addObject('TechDraw::DrawProjGroup', 'ProjGroup')
group.Source = [doc.getObject('Box')]
group.X, group.Y = 200, 150
page.addView(group)
group.addProjection('Front')
group.addProjection('Top')
group.addProjection('Right')
```

### DrawViewSection (Cross-Section)
A sectional view through the object along a cutting plane.

Section plane defined by:
- normal: Direction perpendicular to the cutting plane (x, y, z, or custom vector)
- origin: Point on the cutting plane

FreeCAD API:
```python
section = doc.addObject('TechDraw::DrawViewSection', 'SectionA')
section.BaseView = doc.getObject('FrontView')
section.Source = [doc.getObject('Box')]
section.SectionNormal = FreeCAD.Vector(1, 0, 0)
section.SectionOrigin = FreeCAD.Vector(0, 0, 0)
section.X, section.Y = 300, 150
page.addView(section)
```

### DrawViewDetail (Detail View)
A magnified view of a specific area, with highlight circle on the base view.

Parameters:
- anchor_x, anchor_y: Center of the detail circle (on the base view)
- radius: Size of the highlight circle
- detail_scale: Magnification factor

FreeCAD API:
```python
detail = doc.addObject('TechDraw::DrawViewDetail', 'DetailA')
detail.BaseView = doc.getObject('FrontView')
detail.Source = [doc.getObject('Box')]
detail.AnchorPoint = FreeCAD.Vector(anchor_x, anchor_y, 0)
detail.Radius = 10
detail.Scale = FreeCAD.Vector(2, 2, 2)
detail.X, detail.Y = 350, 100
page.addView(detail)
```

## Dimension Types

| Type | Measures | Edge Reference |
|------|----------|----------------|
| Distance | Edge length | Edge1, Edge2, ... |
| DistanceX | Horizontal extent | Edge reference |
| DistanceY | Vertical extent | Edge reference |
| Radius | Arc/circle radius | Edge reference |
| Diameter | Arc/circle diameter | Edge reference |
| Angle | Angle between edges | Edge reference |

FreeCAD API:
```python
dim = doc.addObject('TechDraw::DrawViewDimension', 'Dim_Distance')
dim.Type = 'Distance'
dim.References2D = [(doc.getObject('FrontView'), 'Edge1')]
dim.X, dim.Y = 0, 20
page.addView(dim)
```

## Annotations

### Text Annotation
Simple text label placed at coordinates on the page.

```python
anno = doc.addObject('TechDraw::DrawViewAnnotation', 'Annotation')
anno.Text = ['Line 1', 'Line 2']
anno.X, anno.Y = 50, 50
anno.TextSize = 5
page.addView(anno)
```

### Leader Line
A reference line from a point on the view to a text label, with arrow.

### Balloon
A numbered reference (typically for BOM items). Shapes: circular, rectangular, triangle, hexagon.

### Bill of Materials (BOM)
Table listing all parts with position number, name, material, and quantity.
Default columns: Pos, Naam, Materiaal, Aantal (Dutch convention).

## Hatch Patterns

ANSI standard hatch patterns for cross-section fills:

| Pattern | Description |
|---------|-------------|
| ansi31 | General-purpose cross-hatch (45 degrees) |
| ansi32 | Steel |
| ansi33 | Bronze/brass/copper |
| ansi34 | Plastic/rubber |
| ansi35 | Fire brick |
| ansi36 | Marble/slate |
| ansi37 | Lead/zinc |
| ansi38 | Aluminum |

## Centerlines

Centerlines mark axes of symmetry on views. Two orientations:
- **vertical**: Vertical line at a given X position
- **horizontal**: Horizontal line at a given Y position

Parameters:
- position: Location along the perpendicular axis
- extent_low/extent_high: How far the centerline extends

## Title Block Fields

| Field | Description |
|-------|-------------|
| title | Drawing title |
| author | Author/designer name |
| date | Date string |
| scale | Scale notation (e.g., "1:10") |
| material | Material specification |
| revision | Revision identifier |
| company | Company name |
| drawing_number | Unique drawing number |
| sheet | Sheet number (e.g., "1/3") |
| checked_by | QA reviewer |
| approved_by | Approval authority |

## GD&T — Geometric Dimensioning & Tolerancing (ISO 1101 / ASME Y14.5)

### Feature Control Frame (FCF)
A bordered row of cells containing: characteristic symbol | tolerance value | datum references.
Rendered as `TechDraw::DrawViewAnnotation` in FreeCAD scripts and as SVG `<rect>` + `<text>` groups in SVG export.

### GD&T Characteristics

| Category | Characteristic | Symbol | Description |
|----------|---------------|--------|-------------|
| Form | flatness | ⏥ | Surface flatness |
| Form | straightness | ⏤ | Line straightness |
| Form | circularity | ○ | Roundness of cross-section |
| Form | cylindricity | ⌭ | Combined roundness + straightness |
| Orientation | perpendicularity | ⊥ | 90° to datum |
| Orientation | parallelism | ∥ | Parallel to datum |
| Orientation | angularity | ∠ | Angle to datum |
| Location | position | ⌖ | True position (most common) |
| Location | concentricity | ◎ | Coaxiality |
| Location | symmetry | ⌯ | Symmetrical about datum |
| Runout | circular_runout | ↗ | Single rotation runout |
| Runout | total_runout | ⇗ | Full-length rotation runout |
| Profile | profile_line | ⌒ | Line profile tolerance |
| Profile | profile_surface | ⌓ | Surface profile tolerance |

### Material Condition Modifiers

| Modifier | Symbol | Meaning |
|----------|--------|---------|
| MMC | Ⓜ | Maximum Material Condition — tolerance applies at largest size |
| LMC | Ⓛ | Least Material Condition — tolerance applies at smallest size |
| RFS | (none) | Regardless of Feature Size (default) |

### Diameter Zone
When `diameter_zone=True`, the tolerance value is prefixed with ∅, indicating a cylindrical tolerance zone instead of two parallel planes.

## Datum Feature Symbols (ISO 5459)

Datum symbols mark reference surfaces/features for geometric tolerances.
Rendered as a filled triangle (▼) with the datum letter in a bordered box.

- Letters: A through Z (single uppercase letter, auto-uppercased)
- Maximum 3 datum references per GD&T tolerance frame

## Surface Finish Symbols (ISO 1302)

Surface finish annotations specify manufacturing roughness requirements.

### Roughness Parameters
| Parameter | Description |
|-----------|-------------|
| Ra | Arithmetic mean roughness (µm) |
| Rz | Mean peak-to-valley roughness (µm) |

### Process Types
| Process | Symbol | Meaning |
|---------|--------|---------|
| any | √ | Any manufacturing process allowed |
| removal_required | ▽ | Material removal (machining) required |
| removal_prohibited | ▽̶ | No material removal allowed (cast/forged as-is) |

### Lay Direction
Symbols: `=` (parallel), `⊥` (perpendicular), `X` (crossed), `M` (multi-directional), `C` (circular), `R` (radial)

## Weld Symbols (AWS A2.4 / ISO 2553)

### Weld JSON Structure
```json
{
  "name": "Weld1",
  "weld_type": "fillet",
  "view": "FrontView",
  "tiles": [
    {
      "weld_type": "fillet",
      "side": "arrow",
      "size": "5",
      "length": "50",
      "pitch": null
    }
  ],
  "all_around": false,
  "field_weld": false,
  "tail": null,
  "contour": null,
  "x": 100,
  "y": 80
}
```

### Weld Types
| Type | Symbol | Description |
|------|--------|-------------|
| fillet | △ | Fillet (corner) weld |
| v_groove | V | V-groove butt weld |
| square_groove | ‖ | Square groove butt weld |
| bevel_groove | ⌐V | Single bevel groove |
| u_groove | U | U-groove butt weld |
| j_groove | J | J-groove weld |
| plug | ○ | Plug or slot weld |
| bead | ⌢ | Surfacing / bead weld |
| spot | ● | Resistance spot weld |
| seam | ═● | Seam weld |
| edge | ╲ | Edge weld |
| flare_v | )( | Flare-V groove |
| flare_bevel | ) | Flare-bevel groove |

### Contour Symbols
| Contour | Symbol | Meaning |
|---------|--------|---------|
| flush | — | Flush (ground flat) |
| convex | ⌢ | Convex finish |
| concave | ⌣ | Concave finish |

### Welding Processes (Tail Text)
| Abbr | Process |
|------|---------|
| SMAW | Shielded Metal Arc Welding (stick) |
| GMAW | Gas Metal Arc Welding (MIG) |
| GTAW | Gas Tungsten Arc Welding (TIG) |
| FCAW | Flux-Cored Arc Welding |
| SAW | Submerged Arc Welding |
| RSW | Resistance Spot Welding |
| OFW | Oxy-Fuel Welding |
| PAW | Plasma Arc Welding |
| EBW | Electron Beam Welding |
| LBW | Laser Beam Welding |

### SVG Rendering
Weld symbols are rendered as custom SVG with:
- Reference line (horizontal, 40mm)
- Arrow line (angled, with arrowhead marker)
- Type-specific symbol geometry (polygon for fillet, polyline for V-groove, etc.)
- All-around circle (r=2.5) at junction when enabled
- Field weld flag (filled polygon) at junction when enabled
- Dimension texts (size left, length right, pitch center)
- Contour symbol above weld symbol
- Tail text at end of reference line

## Export Functions

### DXF Export
Exports via FreeCAD's Import.export() with the drawing page views.

### SVG Export
Full SVG output including all views, dimensions, annotations, centerlines, hatches, balloons, BOM table, GD&T feature control frames, datum symbols, surface finish symbols, and weld symbols. Uses TechDraw's native SVG generation with custom SVG rendering for GD&T and weld elements.

### PDF Export
Generates PDF via FreeCAD's TechDraw PDF export or SVG-to-PDF conversion.

## Template Resolution

Drawing page templates are .svg files located in FreeCAD's installation:
- Path: {FreeCAD_install}/Mod/TechDraw/Templates/
- The harness dynamically searches for matching template files
- Fallback: Creates pages without template if not found

## Complete Drawing Workflow Example

```bash
# Create project with 3D model
cli-anything-freecad project new -n "Assembly" -o assembly.json
cli-anything-freecad part box -l 200 -w 100 -h 50 --name Base
cli-anything-freecad part cylinder -r 20 -ht 80 --name Column --px 100 --py 50

# Create A3 drawing
cli-anything-freecad techdraw page --template A3_Landscape --scale 0.5

# Add multi-view projection
cli-anything-freecad techdraw projection --source Base --projections Front,Top,Right

# Add section view
cli-anything-freecad techdraw section --source Base --base-view Front --normal x

# Add detail view
cli-anything-freecad techdraw detail --source Base --base-view Front \
    --anchor-x 50 --anchor-y 25 --radius 15 --detail-scale 3

# Add dimensions
cli-anything-freecad techdraw dimension --view Front --type Distance --edge Edge1
cli-anything-freecad techdraw dimension --view Front --type DistanceX --edge Edge2

# Add centerline
cli-anything-freecad techdraw centerline --view Front --orientation vertical --position 100

# Add hatch to section
cli-anything-freecad techdraw hatch --view SectionA --face Face1 --pattern ansi31

# Add annotations
cli-anything-freecad techdraw annotate --text "GENERAL TOLERANCE: 0.5mm" -x 20 -y 190
cli-anything-freecad techdraw leader --view Front --text "Surface Ra 1.6" \
    --start-x 50 --start-y 25 --end-x 80 --end-y 40

# Add GD&T annotations
cli-anything-freecad techdraw datum Page Front A -x 50 -y 120
cli-anything-freecad techdraw datum Page Front B -x 150 -y 120
cli-anything-freecad techdraw gdt Page Front -c position -t 0.05 -d A -d B -m MMC --diameter-zone
cli-anything-freecad techdraw gdt Page Front -c flatness -t 0.01
cli-anything-freecad techdraw surface-finish Page Front --ra 1.6 -p removal_required

# Add balloons for BOM references
cli-anything-freecad techdraw balloon --view Front --text "1" --origin-x 100 --origin-y 25
cli-anything-freecad techdraw balloon --view Front --text "2" --origin-x 100 --origin-y 75

# Add BOM table
cli-anything-freecad techdraw bom \
    --items "1,Base,Steel S235,1" "2,Column,Steel S235,1"

# Set title block
cli-anything-freecad techdraw title-block \
    --title "Assembly Drawing" --author "Engineer" --date "2026-03-13" \
    --scale "1:2" --material "Steel" --revision "A" --company "ACME" \
    --drawing-number "DWG-001"

# Export
cli-anything-freecad techdraw export-pdf -o assembly_drawing.pdf
cli-anything-freecad techdraw export-svg -o assembly_drawing.svg
cli-anything-freecad techdraw export-dxf -o assembly_drawing.dxf
```
