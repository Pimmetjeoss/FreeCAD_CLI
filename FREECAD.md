# FreeCAD CLI Harness — SOP

## Software Overview

**FreeCAD** is a parametric 3D CAD modeler. It uses OpenCASCADE (OCCT) as its
geometry kernel and provides a rich Python scripting API.

## Backend

- **Engine**: OpenCASCADE Technology (OCCT) via FreeCAD Python modules
- **Headless CLI**: `freecadcmd` — FreeCAD console mode (no GUI)
- **Console REPL**: `freecadcmd -c` — interactive Python console
- **Script execution**: `freecadcmd script.py` — run Python scripts
- **Export**: `freecadcmd --output output.step input.fcstd`

## File Format

- **Native**: `.FCStd` — ZIP archive containing:
  - `Document.xml` — object tree, properties, metadata
  - `GuiDocument.xml` — view settings (colors, visibility)
  - `Thumbnails/Thumbnail.png` — preview image
  - Shape data files (BREP format)
- **Import/Export**: STEP, IGES, STL, OBJ, PLY, BREP, DXF, SVG, 3MF, AMF

## Python API Modules

| Module | Purpose |
|--------|---------|
| `FreeCAD` | Core: documents, objects, properties, configuration |
| `Part` | Solid modeling: primitives, booleans, shape operations |
| `PartDesign` | Feature-based parametric design (Pad, Pocket, Fillet) |
| `Sketcher` | 2D sketch creation and constraint solving |
| `Mesh` | Triangle mesh import/export and operations |
| `Draft` | 2D drafting tools |
| `MeshPart` | Mesh ↔ Part conversion |
| `Import` | STEP/IGES import/export |

## CLI Command Groups

### 1. Project Management
- `project new` — create new FreeCAD document
- `project open` — open existing .FCStd file
- `project save` — save current document
- `project info` — show document metadata and object tree
- `project close` — close document

### 2. Part (3D Solids)
- `part box` — create a box primitive
- `part cylinder` — create a cylinder
- `part sphere` — create a sphere
- `part cone` — create a cone
- `part torus` — create a torus
- `part fuse` — boolean union
- `part cut` — boolean subtraction
- `part common` — boolean intersection
- `part fillet` — fillet edges
- `part chamfer` — chamfer edges
- `part move` — move object to new position (--px, --py, --pz)
- `part list` — list all Part objects

### 3. Sketch (2D)
- `sketch new` — create a new sketch on a plane
- `sketch line` — add a line segment
- `sketch circle` — add a circle
- `sketch arc` — add an arc
- `sketch rect` — add a rectangle (4 lines + constraints)
- `sketch constrain` — add a constraint
- `sketch close` — close/complete the sketch
- `sketch list` — list sketch geometry

### 4. Mesh
- `mesh import` — import mesh file (STL, OBJ, PLY)
- `mesh export` — export mesh
- `mesh from-part` — convert Part shape to mesh
- `mesh info` — show mesh statistics

### 5. TechDraw (2D Fabrication Drawings)
- `techdraw page` — create a drawing page (A0–A4, landscape/portrait)
- `techdraw view` — add a 2D view of a 3D object
- `techdraw projection` — add a multi-view projection group (Front, Top, Right, etc.)
- `techdraw section` — add a cross-section view
- `techdraw detail` — add a detail (magnified) view
- `techdraw dimension` — add dimensions (Distance, DistanceX/Y, Radius, Diameter, Angle)
- `techdraw annotate` — add text annotations
- `techdraw title-block` — set title block fields (title, author, date, scale, material, revision, company, drawing number)
- `techdraw centerline` — add centerlines (vertical/horizontal, dash-dot pattern)
- `techdraw hatch` — add hatch patterns to faces (ansi31, etc.)
- `techdraw leader` — add leader lines (reference lines with text and arrows)
- `techdraw balloon` — add balloons (item number references, circular/rectangular/triangle/hexagon)
- `techdraw bom` — add Bill of Materials table (stuklijst)
- `techdraw gdt` — add a geometric tolerance frame (Feature Control Frame, ISO 1101 / ASME Y14.5)
- `techdraw datum` — add a datum feature symbol (triangle + letter, ISO 5459)
- `techdraw surface-finish` — add a surface finish symbol (Ra/Rz roughness, ISO 1302)
- `techdraw weld` — add a weld symbol (AWS A2.4 / ISO 2553) with type, side, size, length, pitch, contour
- `techdraw weld-tile` — add additional tile to existing weld (double-sided welds)
- `techdraw list` — list all elements on a drawing page (including GD&T, datums, surface finishes, welds)
- `techdraw export-dxf` — export drawing to DXF
- `techdraw export-svg` — export drawing to SVG (includes all annotations, centerlines, hatches, balloons, BOM, GD&T)
- `techdraw export-pdf` — export drawing to PDF

#### GD&T Characteristics (ISO 1101)
| Category | Characteristics |
|----------|----------------|
| Form | flatness ⏥, straightness ⏤, circularity ○, cylindricity ⌭ |
| Orientation | perpendicularity ⊥, parallelism ∥, angularity ∠ |
| Location | position ⌖, concentricity ◎, symmetry ⌯ |
| Runout | circular_runout ↗, total_runout ⇗ |
| Profile | profile_line ⌒, profile_surface ⌓ |

Material conditions: MMC (Ⓜ), LMC (Ⓛ), RFS (default)

#### Weld Types (AWS A2.4 / ISO 2553)
| Type | Symbol |
|------|--------|
| fillet | △ |
| v_groove | V |
| square_groove | ‖ |
| bevel_groove | ⌐V |
| u_groove | U |
| j_groove | J |
| plug | ○ |
| bead | ⌢ |
| spot | ● |
| seam | ═● |
| edge | ╲ |
| flare_v | )( |
| flare_bevel | ) |

Contour symbols: flush (—), convex (⌢), concave (⌣)

### 6. Export
- `export step` — export to STEP format
- `export stl` — export to STL format
- `export obj` — export to OBJ format
- `export iges` — export to IGES format
- `export render` — export via FreeCAD backend (any supported format)

### 7. Session
- `session status` — show session state
- `session undo` — undo last operation
- `session redo` — redo last undone operation
- `session history` — show operation history

## State Model

Session state stored as JSON:
```json
{
  "project_path": "/path/to/project.json",
  "fcstd_path": "/path/to/doc.FCStd",
  "document_name": "MyProject",
  "objects": [...],
  "history": [...],
  "modified": true
}
```

## Backend Integration

The CLI generates FreeCAD Python scripts and executes them via `freecadcmd`:

```bash
freecadcmd /tmp/cli_anything_script.py
```

This ensures all geometry operations use the real OCCT kernel, not
reimplemented approximations.

## Dependencies

- **FreeCAD** (system): `apt install freecad` (required, hard dependency)
- **Python**: click, prompt-toolkit (pip)
