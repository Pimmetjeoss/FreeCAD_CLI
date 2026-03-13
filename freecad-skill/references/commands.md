# FreeCAD CLI Harness — Complete Command Reference

## Global Options

| Option | Description |
|--------|-------------|
| --json | Output in JSON format (machine-readable) |
| --help | Show help for any command |

## 1. Project Commands

### project new
Create a new FreeCAD project.

```
project new [OPTIONS]
  -n, --name TEXT        Project name [default: Untitled]
  -o, --output PATH      Output path for project JSON file
```

### project open
Open an existing project from JSON file.

```
project open PATH
  PATH                   Path to project .json file (required)
```

### project save
Save current project to disk.

```
project save [OPTIONS]
  -o, --output PATH      Save to specific path (uses project_path if omitted)
```

### project save-fcstd
Export current project as .FCStd (native FreeCAD format).

```
project save-fcstd PATH
  PATH                   Output .FCStd file path (required)
```

### project info
Display project metadata and object tree.

```
project info
  (no options - shows name, dates, object count, object list)
```

### project inspect
Inspect a .FCStd file without opening it as a project.

```
project inspect PATH
  PATH                   Path to .FCStd file (required)
```

Returns: object names, types, labels, shape types, volumes, areas, bounding boxes.

---

## 2. Part Commands (3D Solids)

### part box
Create a box primitive.

```
part box [OPTIONS]
  -l, --length FLOAT     Length (X axis) [default: 10]
  -w, --width FLOAT      Width (Y axis) [default: 10]
  -h, --height FLOAT     Height (Z axis) [default: 10]
  --name TEXT             Object name [auto-generated if omitted]
  --px FLOAT             X position [default: 0]
  --py FLOAT             Y position [default: 0]
  --pz FLOAT             Z position [default: 0]
```

### part cylinder
Create a cylinder primitive.

```
part cylinder [OPTIONS]
  -r, --radius FLOAT     Radius [default: 5]
  -ht, --height FLOAT    Height [default: 10]
  -a, --angle FLOAT      Sweep angle in degrees [default: 360]
  --name TEXT             Object name
  --px, --py, --pz FLOAT Placement position [default: 0]
```

### part sphere
Create a sphere primitive.

```
part sphere [OPTIONS]
  -r, --radius FLOAT     Radius [default: 5]
  --name TEXT             Object name
  --px, --py, --pz FLOAT Placement position [default: 0]
```

### part cone
Create a cone primitive.

```
part cone [OPTIONS]
  --r1, --radius1 FLOAT  Bottom radius [default: 5]
  --r2, --radius2 FLOAT  Top radius [default: 2]
  -ht, --height FLOAT    Height [default: 10]
  --name TEXT             Object name
  --px, --py, --pz FLOAT Placement position [default: 0]
```

### part torus
Create a torus primitive.

```
part torus [OPTIONS]
  --r1, --radius1 FLOAT  Major radius [default: 10]
  --r2, --radius2 FLOAT  Minor radius [default: 2]
  --name TEXT             Object name
  --px, --py, --pz FLOAT Placement position [default: 0]
```

### part fuse
Boolean union of two objects.

```
part fuse [OPTIONS]
  --base TEXT             Base object name (required)
  --tool TEXT             Tool object name (required)
  --name TEXT             Result object name
```

### part cut
Boolean subtraction (base minus tool).

```
part cut [OPTIONS]
  --base TEXT             Base object name (required)
  --tool TEXT             Tool object name (required)
  --name TEXT             Result object name
```

### part common
Boolean intersection of two objects.

```
part common [OPTIONS]
  --base TEXT             Base object name (required)
  --tool TEXT             Tool object name (required)
  --name TEXT             Result object name
```

### part fillet
Fillet all edges of an object.

```
part fillet [OPTIONS]
  --base TEXT             Object to fillet (required)
  -r, --radius FLOAT     Fillet radius [default: 1]
  --name TEXT             Result object name
```

### part chamfer
Chamfer all edges of an object.

```
part chamfer [OPTIONS]
  --base TEXT             Object to chamfer (required)
  -s, --size FLOAT       Chamfer size [default: 1]
  --name TEXT             Result object name
```

### part list
List all Part objects in the project.

```
part list
  (no options)
```

### part remove
Remove an object from the project.

```
part remove NAME
  NAME                   Object name to remove (required)
```

### part move
Move an object to a new position.

```
part move [OPTIONS]
  --name TEXT             Object name (required)
  --px FLOAT             New X position [default: 0]
  --py FLOAT             New Y position [default: 0]
  --pz FLOAT             New Z position [default: 0]
```

---

## 3. Sketch Commands (2D)

### sketch new
Create a new sketch on a plane.

```
sketch new [OPTIONS]
  --plane [XY|XZ|YZ]     Sketch plane [default: XY]
  --name TEXT             Sketch object name
```

### sketch line
Add a line segment to a sketch.

```
sketch line [OPTIONS]
  --sketch TEXT           Target sketch name (required)
  --x1 FLOAT             Start X [default: 0]
  --y1 FLOAT             Start Y [default: 0]
  --x2 FLOAT             End X [default: 10]
  --y2 FLOAT             End Y [default: 0]
```

### sketch circle
Add a circle to a sketch.

```
sketch circle [OPTIONS]
  --sketch TEXT           Target sketch name (required)
  --cx FLOAT             Center X [default: 0]
  --cy FLOAT             Center Y [default: 0]
  -r, --radius FLOAT     Radius [default: 5]
```

### sketch arc
Add an arc to a sketch.

```
sketch arc [OPTIONS]
  --sketch TEXT           Target sketch name (required)
  --cx FLOAT             Center X [default: 0]
  --cy FLOAT             Center Y [default: 0]
  -r, --radius FLOAT     Radius [default: 5]
  --start-angle FLOAT    Start angle in degrees [default: 0]
  --end-angle FLOAT      End angle in degrees [default: 90]
```

### sketch rect
Add a rectangle (4 line segments + auto-constraints).

```
sketch rect [OPTIONS]
  --sketch TEXT           Target sketch name (required)
  -x FLOAT               Origin X [default: 0]
  -y FLOAT               Origin Y [default: 0]
  -w, --width FLOAT      Width [default: 10]
  -ht, --height FLOAT    Height [default: 10]
```

### sketch constrain
Add a constraint to sketch geometry.

```
sketch constrain [OPTIONS]
  --sketch TEXT           Target sketch name (required)
  --type TEXT             Constraint type: Horizontal, Vertical, Distance, Radius,
                          Coincident, Parallel, Perpendicular, Equal, Angle (required)
  --geometry INT          Geometry index (required)
  --value FLOAT           Constraint value (for Distance, Radius, Angle)
  --geometry2 INT         Second geometry index (for Coincident, Parallel, etc.)
  --point1 INT            First point index (for Coincident)
  --point2 INT            Second point index (for Coincident)
```

### sketch list
List all geometry and constraints in a sketch.

```
sketch list [OPTIONS]
  --sketch TEXT           Sketch name (required)
```

---

## 4. Mesh Commands

### mesh import
Import a mesh file (STL, OBJ, PLY).

```
mesh import PATH
  PATH                   Path to mesh file (required)
  --name TEXT             Object name
```

### mesh from-part
Convert a Part solid to mesh representation.

```
mesh from-part [OPTIONS]
  --source TEXT           Part object name to convert (required)
  --name TEXT             Resulting mesh object name
```

---

## 5. Export Commands

### export step
Export project to STEP format.

```
export step [OPTIONS]
  -o, --output PATH      Output file path (required)
  --overwrite            Overwrite existing file
  --objects TEXT          Comma-separated object names (default: all)
```

### export stl
Export project to STL mesh format.

```
export stl [OPTIONS]
  -o, --output PATH      Output file path (required)
  --overwrite            Overwrite existing file
  --objects TEXT          Comma-separated object names (default: all)
```

### export obj
Export project to Wavefront OBJ format.

```
export obj [OPTIONS]
  -o, --output PATH      Output file path (required)
  --overwrite            Overwrite existing file
```

### export iges
Export project to IGES format.

```
export iges [OPTIONS]
  -o, --output PATH      Output file path (required)
  --overwrite            Overwrite existing file
```

### export brep
Export project to OpenCASCADE BREP format.

```
export brep [OPTIONS]
  -o, --output PATH      Output file path (required)
  --overwrite            Overwrite existing file
```

### export render
Export via FreeCAD backend (format determined by file extension).

```
export render [OPTIONS]
  -o, --output PATH      Output file path (required)
  --overwrite            Overwrite existing file
```

### export formats
List all supported export formats.

```
export formats
  (no options)
```

---

## 6. TechDraw Commands (2D Fabrication Drawings)

### techdraw page
Create a drawing page.

```
techdraw page [OPTIONS]
  --name TEXT             Page name [default: Page]
  --template TEXT         Paper template: A4_Landscape, A4_Portrait, A3_Landscape,
                          A3_Portrait, A2_Landscape, A1_Landscape, A0_Landscape
                          [default: A4_Landscape]
  --scale FLOAT           Drawing scale [default: 1.0]
```

### techdraw view
Add a single 2D orthogonal view of a 3D object.

```
techdraw view [OPTIONS]
  --page TEXT             Target page name [default: Page]
  --source TEXT           Source 3D object name (required)
  --direction TEXT        View direction: front, back, top, bottom, left, right, iso,
                          front-elevation, side-elevation, plan, rear-elevation
                          [default: front]
  --name TEXT             View name
  -x FLOAT               X position on page [default: 150]
  -y FLOAT               Y position on page [default: 100]
  --rotation FLOAT        View rotation in degrees [default: 0]
```

### techdraw projection
Add a multi-view projection group (multiple standard views at once).

```
techdraw projection [OPTIONS]
  --page TEXT             Target page name [default: Page]
  --source TEXT           Source 3D object name (required)
  --projections TEXT      Comma-separated views: Front,Top,Right,Left,Bottom,Rear
                          [default: Front,Top,Right]
  --name TEXT             Projection group name
  -x FLOAT               X position [default: 200]
  -y FLOAT               Y position [default: 150]
```

### techdraw section
Add a cross-section view.

```
techdraw section [OPTIONS]
  --page TEXT             Target page name [default: Page]
  --source TEXT           Source 3D object name (required)
  --base-view TEXT        Name of the base view to section (required)
  --normal TEXT           Section plane normal: x, y, z, or custom "nx,ny,nz"
                          [default: x]
  --origin TEXT           Section plane origin "ox,oy,oz" [default: "0,0,0"]
  --name TEXT             Section view name
  -x FLOAT               X position on page [default: 300]
  -y FLOAT               Y position on page [default: 150]
```

### techdraw detail
Add a magnified detail view with highlight circle.

```
techdraw detail [OPTIONS]
  --page TEXT             Target page name [default: Page]
  --source TEXT           Source 3D object name (required)
  --base-view TEXT        Base view to detail from (required)
  --anchor-x FLOAT       Detail circle center X [default: 0]
  --anchor-y FLOAT        Detail circle center Y [default: 0]
  --radius FLOAT          Detail circle radius [default: 10]
  --detail-scale FLOAT    Magnification scale [default: 2.0]
  --name TEXT             Detail view name
  -x FLOAT               X position on page [default: 350]
  -y FLOAT               Y position on page [default: 100]
```

### techdraw dimension
Add a dimension annotation to a view.

```
techdraw dimension [OPTIONS]
  --page TEXT             Target page name [default: Page]
  --view TEXT             View name to dimension (required)
  --type TEXT             Dimension type: Distance, DistanceX, DistanceY, Radius,
                          Diameter, Angle [default: Distance]
  --edge TEXT             Edge reference (e.g., "Edge1") [default: Edge1]
  -x FLOAT               Dimension label X position [default: 0]
  -y FLOAT               Dimension label Y position [default: 20]
```

### techdraw annotate
Add a text annotation.

```
techdraw annotate [OPTIONS]
  --page TEXT             Target page name [default: Page]
  --text TEXT             Annotation text (required)
  -x FLOAT               X position [default: 50]
  -y FLOAT               Y position [default: 50]
  --font-size FLOAT       Font size [default: 5]
```

### techdraw title-block
Set title block fields on a drawing page.

```
techdraw title-block [OPTIONS]
  --page TEXT             Target page name [default: Page]
  --title TEXT            Drawing title
  --author TEXT           Author name
  --date TEXT             Date string
  --scale TEXT            Scale string (e.g., "1:10")
  --material TEXT         Material specification
  --revision TEXT         Revision number
  --company TEXT          Company name
  --drawing-number TEXT   Drawing number
  --sheet TEXT            Sheet number
  --checked-by TEXT       Checked by
  --approved-by TEXT      Approved by
```

### techdraw centerline
Add a centerline to a view.

```
techdraw centerline [OPTIONS]
  --page TEXT             Target page name [default: Page]
  --view TEXT             View name (required)
  --orientation TEXT      vertical or horizontal [default: vertical]
  --position FLOAT        Position along the perpendicular axis [default: 0]
  --extent-low FLOAT      Low extent [default: -20]
  --extent-high FLOAT     High extent [default: 20]
```

### techdraw hatch
Add a hatch pattern to a face.

```
techdraw hatch [OPTIONS]
  --page TEXT             Target page name [default: Page]
  --view TEXT             View name (required)
  --face TEXT             Face reference (e.g., "Face1") [default: Face1]
  --pattern TEXT          Hatch pattern: ansi31, ansi32, ansi33, ansi34, ansi35,
                          ansi36, ansi37, ansi38 [default: ansi31]
  --scale FLOAT           Pattern scale [default: 1.0]
  --rotation FLOAT        Pattern rotation in degrees [default: 0]
  --color TEXT            Hatch color [default: "0,0,0"]
```

### techdraw leader
Add a leader line (reference line with text and arrow).

```
techdraw leader [OPTIONS]
  --page TEXT             Target page name [default: Page]
  --view TEXT             View name (required)
  --start-x FLOAT        Start X [default: 0]
  --start-y FLOAT        Start Y [default: 0]
  --end-x FLOAT          End X [default: 30]
  --end-y FLOAT          End Y [default: 15]
  --text TEXT             Leader text (required)
  --arrow-style TEXT      Arrow style [default: "filled"]
```

### techdraw balloon
Add a balloon (item number reference).

```
techdraw balloon [OPTIONS]
  --page TEXT             Target page name [default: Page]
  --view TEXT             View name (required)
  --origin-x FLOAT       Origin X (on the part) [default: 0]
  --origin-y FLOAT        Origin Y [default: 0]
  --text TEXT             Balloon text / item number (required)
  --shape TEXT            Balloon shape: circular, rectangular, triangle, hexagon
                          [default: circular]
  -x FLOAT               Balloon position X [default: 30]
  -y FLOAT               Balloon position Y [default: 30]
```

### techdraw bom
Add a Bill of Materials (stuklijst) table.

```
techdraw bom [OPTIONS]
  --page TEXT             Target page name [default: Page]
  --items TEXT            BOM items as comma-separated values:
                          "pos,name,material,quantity" (multiple allowed)
  -x FLOAT               Table X position [default: 10]
  -y FLOAT               Table Y position [default: 10]
  --font-size FLOAT       Font size [default: 3.5]
  --columns TEXT          Column headers (comma-separated)
                          [default: "Pos,Naam,Materiaal,Aantal"]
```

### techdraw gdt
Add a geometric tolerance frame (Feature Control Frame) per ISO 1101 / ASME Y14.5.

```
techdraw gdt PAGE_NAME VIEW_NAME [OPTIONS]
  PAGE_NAME              Target page name (required)
  VIEW_NAME              Target view name (required)
  -c, --characteristic   GD&T type: flatness, straightness, circularity, cylindricity,
                          perpendicularity, parallelism, angularity, position,
                          concentricity, symmetry, circular_runout, total_runout,
                          profile_line, profile_surface (required)
  -t, --tolerance FLOAT  Tolerance value in mm (required)
  -d, --datum TEXT        Datum reference letter (repeat for multiple, max 3)
  -m, --material-condition
                          Material condition: MMC, LMC, RFS [default: RFS]
  --diameter-zone        Use diameter (∅) tolerance zone
  -n, --name TEXT         GD&T annotation name [auto-generated]
  -x FLOAT               X position on page [default: 100]
  -y FLOAT               Y position on page [default: 80]
```

Examples:
```bash
# Position tolerance 0.05mm relative to datums A and B, MMC
techdraw gdt Sheet1 FrontView -c position -t 0.05 -d A -d B -m MMC --diameter-zone

# Flatness 0.01mm (form tolerance, no datums needed)
techdraw gdt Sheet1 FrontView -c flatness -t 0.01

# Perpendicularity 0.1mm to datum A
techdraw gdt Sheet1 FrontView -c perpendicularity -t 0.1 -d A
```

### techdraw datum
Add a datum feature symbol (triangle + letter box) per ISO 5459 / ASME Y14.5.

```
techdraw datum PAGE_NAME VIEW_NAME LETTER [OPTIONS]
  PAGE_NAME              Target page name (required)
  VIEW_NAME              Target view name (required)
  LETTER                 Datum letter: A, B, C, etc. (required)
  -n, --name TEXT         Datum symbol name [auto-generated]
  -x FLOAT               X position on page [default: 100]
  -y FLOAT               Y position on page [default: 100]
```

Example:
```bash
techdraw datum Sheet1 FrontView A -x 50 -y 120
```

### techdraw surface-finish
Add a surface finish (roughness) symbol per ISO 1302.

```
techdraw surface-finish PAGE_NAME VIEW_NAME [OPTIONS]
  PAGE_NAME              Target page name (required)
  VIEW_NAME              Target view name (required)
  --ra FLOAT             Ra roughness value in µm (arithmetic mean)
  --rz FLOAT             Rz roughness value in µm (mean peak-to-valley)
  -p, --process          Process: any, removal_required, removal_prohibited [default: any]
  --lay TEXT             Lay direction symbol (=, ⊥, X, M, C, R)
  -n, --name TEXT         Surface finish name [auto-generated]
  -x FLOAT               X position on page [default: 100]
  -y FLOAT               Y position on page [default: 100]
```

Note: At least one of --ra or --rz must be specified.

Examples:
```bash
# Ra 1.6 µm, machining required
techdraw surface-finish Sheet1 FrontView --ra 1.6 -p removal_required

# Ra and Rz with lay direction
techdraw surface-finish Sheet1 FrontView --ra 1.6 --rz 6.3 --lay "="
```

### techdraw list
List all elements on a drawing page (views, dimensions, annotations, GD&T, datums, surface finishes).

```
techdraw list [OPTIONS]
  --page TEXT             Page name [default: Page]
```

### techdraw export-dxf
Export a drawing page to DXF format.

```
techdraw export-dxf [OPTIONS]
  --page TEXT             Page name [default: Page]
  -o, --output PATH      Output DXF file path (required)
  --overwrite            Overwrite existing file
```

### techdraw export-svg
Export a drawing page to SVG format.

```
techdraw export-svg [OPTIONS]
  --page TEXT             Page name [default: Page]
  -o, --output PATH      Output SVG file path (required)
  --overwrite            Overwrite existing file
```

### techdraw export-pdf
Export a drawing page to PDF format.

```
techdraw export-pdf [OPTIONS]
  --page TEXT             Page name [default: Page]
  -o, --output PATH      Output PDF file path (required)
  --overwrite            Overwrite existing file
```

---

## 7. Session Commands

### session status
Show session state.

```
session status
  Returns: has_project, project_name, modified, undo_available, redo_available, object_count
```

### session undo
Undo the last operation.

```
session undo
  Returns: undone operation name + restored project state
```

### session redo
Redo the last undone operation.

```
session redo
  Returns: restored project state
```

### session history
Show operation history.

```
session history
  Returns: chronological list of all performed operations
```

---

## 8. Utility Commands

### version
Show CLI and FreeCAD versions.

```
version
  Returns: cli-anything-freecad version + FreeCAD version
```

### repl
Enter interactive REPL mode.

```
repl
  Opens interactive prompt with auto-completion and command history
  Prompt format: "freecad [ProjectName*] > " (* = unsaved changes)
```
