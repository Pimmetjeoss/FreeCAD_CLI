# FreeCAD CLI Harness — Complete Command Reference (130+ Commands)

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

### part helix (NEW)
Create a helix primitive for springs, screw threads, coils.

```
part helix [OPTIONS]
  -r, --radius FLOAT     Helix radius [default: 5]
  -p, --pitch FLOAT      Helix pitch (height per turn) [default: 3]
  -h, --height FLOAT     Total helix height [default: 10]
  --angle FLOAT          Conical angle (0 = cylindrical) [default: 0]
  --ccw/--cw             Counter-clockwise (default) or clockwise
  --name TEXT             Object name
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

### part import-step
Import a STEP file.

```
part import-step PATH [OPTIONS]
  PATH                   STEP file path (required)
  --name TEXT             Object name
```

### part import-dxf (NEW)
Import DXF file as Part geometry for laser cutting workflows.

```
part import-dxf PATH [OPTIONS]
  PATH                   DXF file path (required)
  -n, --name TEXT        Object name
  -u, --units TEXT       Target units (mm, cm, inch) [default: mm]
  -l, --layers TEXT      Comma-separated layer names to import
  -s, --scale FLOAT      Scale factor [default: 1.0]
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

## 3. PartDesign Commands (Parametric Modeling - NEW)

### partdesign body
Create a PartDesign body container for parametric modeling.

```
partdesign body [OPTIONS]
  -n, --name TEXT        Body name [default: Body]
  -f, --base-feature TEXT Base feature name
```

### partdesign pad
Create a parametric pad (extrusion) from a sketch.

```
partdesign pad SKETCH_NAME [OPTIONS]
  SKETCH_NAME            Name of the sketch to extrude (required)
  -n, --name TEXT        Pad name
  -l, --length FLOAT     Extrusion length (mm) [default: 10]
  --symmetric            Symmetric extrusion from sketch plane
  --reverse              Reverse extrusion direction
  --up-to-face TEXT      Extrude up to face (instead of length)
```

### partdesign pocket
Create a parametric pocket (cutout) from a sketch.

```
partdesign pocket SKETCH_NAME [OPTIONS]
  SKETCH_NAME            Name of the sketch for cutting (required)
  -n, --name TEXT        Pocket name
  -l, --length FLOAT     Cut depth (mm) [default: 10]
  --through-all          Cut through all
  --symmetric            Symmetric cut
  --reverse              Reverse cut direction
  --up-to-face TEXT      Cut up to face
```

### partdesign linear-pattern (NEW)
Create a linear pattern of a PartDesign feature.

```
partdesign linear-pattern FEATURE_NAME [OPTIONS]
  FEATURE_NAME           Feature to pattern (required)
  -d, --direction [X|Y|Z] Pattern direction [default: X]
  -l, --length FLOAT     Total pattern length (mm) [default: 20]
  -n, --occurrences INT  Number of instances [default: 2]
  --name TEXT             Pattern name
```

### partdesign polar-pattern (NEW)
Create a polar pattern of a PartDesign feature.

```
partdesign polar-pattern FEATURE_NAME [OPTIONS]
  FEATURE_NAME           Feature to pattern (required)
  -a, --axis [X|Y|Z]     Rotation axis [default: Z]
  --angle FLOAT          Total angle (degrees) [default: 360]
  -n, --occurrences INT  Number of instances [default: 6]
  --reverse              Reverse direction
  --name TEXT             Pattern name
```

### partdesign draft (NEW)
Apply draft angle to faces for casting/molding.

```
partdesign draft FACE_NAME [OPTIONS]
  FACE_NAME              Face to draft (required)
  -a, --angle FLOAT      Draft angle (degrees) [default: 3]
  --neutral-plane TEXT    Neutral plane name
  --reverse              Reverse draft direction
  --name TEXT             Draft name
```

### partdesign fillet (NEW)
Apply fillet (round) to edges for manufacturing edge breaks.

```
partdesign fillet EDGE_NAME [OPTIONS]
  EDGE_NAME              Edge to fillet (required)
  -r, --radius FLOAT     Fillet radius (mm) [default: 1]
  --name TEXT             Fillet name
```

### partdesign chamfer (NEW)
Apply chamfer to edges for manufacturing deburring.

```
partdesign chamfer EDGE_NAME [OPTIONS]
  EDGE_NAME              Edge to chamfer (required)
  -s, --size FLOAT       Chamfer size (mm) [default: 1]
  -a, --angle FLOAT      Chamfer angle (degrees) [default: 45]
  --name TEXT             Chamfer name
```

### partdesign thickness (NEW)
Create shell structure with wall thickness.

```
partdesign thickness FACE_NAME [OPTIONS]
  FACE_NAME              Face to remove for shell (required)
  -t, --thickness FLOAT  Wall thickness (mm) [default: 2]
  -m, --mode [thickness|offset|skin] Thickness mode [default: thickness]
  -j, --join [arc|intersection] Corner join type [default: arc]
  --name TEXT             Thickness name
```

### partdesign features
List all features in a PartDesign body.

```
partdesign features BODY_NAME
  BODY_NAME              Body name (required)
```

### partdesign patterns (NEW)
List all patterns in a PartDesign body.

```
partdesign patterns BODY_NAME
  BODY_NAME              Body name (required)
```

### partdesign edge-treatments (NEW)
List all fillets and chamfers in a PartDesign body.

```
partdesign edge-treatments BODY_NAME
  BODY_NAME              Body name (required)
```

---

## 4. Sketch Commands (2D)

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
sketch line SKETCH_NAME [OPTIONS]
  SKETCH_NAME            Target sketch name (required)
  --x1 FLOAT             Start X [default: 0]
  --y1 FLOAT             Start Y [default: 0]
  --x2 FLOAT             End X [default: 10]
  --y2 FLOAT             End Y [default: 0]
```

### sketch construction-line (NEW)
Add a construction line (helper/guide line) to a sketch.

```
sketch construction-line SKETCH_NAME [OPTIONS]
  SKETCH_NAME            Target sketch name (required)
  --x1 FLOAT             Start X [default: 0]
  --y1 FLOAT             Start Y [default: 0]
  --x2 FLOAT             End X [default: 10]
  --y2 FLOAT             End Y [default: 0]
```

### sketch circle
Add a circle to a sketch.

```
sketch circle SKETCH_NAME [OPTIONS]
  SKETCH_NAME            Target sketch name (required)
  --cx FLOAT             Center X [default: 0]
  --cy FLOAT             Center Y [default: 0]
  -r, --radius FLOAT     Radius [default: 5]
```

### sketch arc
Add an arc to a sketch.

```
sketch arc SKETCH_NAME [OPTIONS]
  SKETCH_NAME            Target sketch name (required)
  --cx FLOAT             Center X [default: 0]
  --cy FLOAT             Center Y [default: 0]
  -r, --radius FLOAT     Radius [default: 5]
  --start-angle FLOAT    Start angle in degrees [default: 0]
  --end-angle FLOAT      End angle in degrees [default: 90]
```

### sketch rect
Add a rectangle (4 line segments + auto-constraints).

```
sketch rect SKETCH_NAME [OPTIONS]
  SKETCH_NAME            Target sketch name (required)
  -x FLOAT               Origin X [default: 0]
  -y FLOAT               Origin Y [default: 0]
  -w, --width FLOAT      Width [default: 10]
  -ht, --height FLOAT    Height [default: 10]
```

### sketch constrain
Add a constraint to sketch geometry.

```
sketch constrain SKETCH_NAME [OPTIONS]
  SKETCH_NAME            Target sketch name (required)
  -t, --type TEXT        Constraint type: Horizontal, Vertical, Distance, Radius,
                         Coincident, Parallel, Perpendicular, Equal, Angle,
                         Tangent (NEW), Symmetric (NEW) (required)
  -g, --geometry INT     Geometry index (required)
  --value FLOAT           Constraint value (for Distance, Radius, Angle)
  --geometry2 INT         Second geometry index (for Coincident, Parallel, Tangent, Symmetric)
```

**New constraint types:**
- **Tangent**: Tangent constraint between two geometries
- **Symmetric**: Symmetry constraint between two geometries

### sketch list
List all geometry and constraints in a sketch.

```
sketch list SKETCH_NAME
  SKETCH_NAME            Sketch name (required)
```

---

## 5. Assembly Commands (NEW - Multi-Part Products)

### assembly create
Create an assembly container for multi-part products.

```
assembly create [OPTIONS]
  -n, --name TEXT        Assembly name [default: Assembly]
  -p, --parts TEXT       Comma-separated part names to add
```

### assembly add-part
Add a part to an assembly with optional placement.

```
assembly add-part ASSEMBLY_NAME PART_NAME [OPTIONS]
  ASSEMBLY_NAME          Assembly name (required)
  PART_NAME              Part name to add (required)
  -x FLOAT               X position [default: 0]
  -y FLOAT               Y position [default: 0]
  -z FLOAT               Z position [default: 0]
  -r, --rotation FLOAT   Rotation around Z (degrees) [default: 0]
```

### assembly constraint
Add constraint between parts in an assembly.

```
assembly constraint ASSEMBLY_NAME PART1_NAME PART2_NAME [OPTIONS]
  ASSEMBLY_NAME          Assembly name (required)
  PART1_NAME             First part name (required)
  PART2_NAME             Second part name (required)
  -t, --type [coincident|parallel|perpendicular|distance] Constraint type [default: coincident]
  -n, --name TEXT        Constraint name
```

### assembly explode
Create an exploded view of an assembly.

```
assembly explode ASSEMBLY_NAME [OPTIONS]
  ASSEMBLY_NAME          Assembly name (required)
  -f, --factor FLOAT     Explode factor (>1 = exploded) [default: 1.5]
  -n, --name TEXT        Exploded view name
```

### assembly info
Get information about an assembly.

```
assembly info ASSEMBLY_NAME
  ASSEMBLY_NAME          Assembly name (required)
```

---

## 6. FEM Commands (NEW - Finite Element Analysis)

### fem analysis
Create a FEM analysis container.

```
fem analysis [OPTIONS]
  -n, --name TEXT        Analysis name [default: FEMAnalysis]
```

### fem material
Add material properties to an object for FEM analysis.

```
fem material ANALYSIS_NAME OBJECT_NAME [OPTIONS]
  ANALYSIS_NAME          Analysis name (required)
  OBJECT_NAME            Object to assign material (required)
  -m, --material [Steel|Aluminum|Concrete|Custom] Material type [default: Steel]
  -n, --name TEXT        Material name
```

**Material properties included:**
- **Steel**: E=200GPa, ν=0.30, ρ=7850kg/m³
- **Aluminum**: E=70GPa, ν=0.33, ρ=2700kg/m³
- **Concrete**: E=30GPa, ν=0.20, ρ=2400kg/m³

### fem mesh
Create a finite element mesh for analysis.

```
fem mesh ANALYSIS_NAME OBJECT_NAME [OPTIONS]
  ANALYSIS_NAME          Analysis name (required)
  OBJECT_NAME            Object to mesh (required)
  -s, --element-size FLOAT Element size (mm) [default: 5]
  -t, --element-type [Tetrahedron|Hexahedron] Element type [default: Tetrahedron]
  -n, --name TEXT        Mesh name
```

### fem fixed
Add fixed constraint (boundary condition) to analysis.

```
fem fixed ANALYSIS_NAME OBJECT_NAME [OPTIONS]
  ANALYSIS_NAME          Analysis name (required)
  OBJECT_NAME            Object name (required)
  -f, --face TEXT        Specific face to fix
  -n, --name TEXT        Constraint name
```

### fem force
Add force constraint (load) to analysis.

```
fem force ANALYSIS_NAME OBJECT_NAME [OPTIONS]
  ANALYSIS_NAME          Analysis name (required)
  OBJECT_NAME            Object name (required)
  -x FLOAT               Force X (N) [default: 0]
  -y FLOAT               Force Y (N) [default: 0]
  -z FLOAT               Force Z (N) [default: -1000] (downward)
  -f, --face TEXT        Specific face for force
  -n, --name TEXT        Constraint name
```

### fem solve
Run FEM solver to calculate stresses and displacements.

```
fem solve ANALYSIS_NAME [OPTIONS]
  ANALYSIS_NAME          Analysis name (required)
  -s, --solver [CalculiX|Elmer|Z88] Solver type [default: CalculiX]
  -t, --type [static|thermal|modal] Analysis type [default: static]
  -n, --name TEXT        Solver name
```

### fem info
Get information about a FEM analysis.

```
fem info ANALYSIS_NAME
  ANALYSIS_NAME          Analysis name (required)
```

---

## 7. DXF Import Commands (NEW - Laser Cutting)

### dxf-import
Import a DXF file for laser cutting and manufacturing.

```
dxf-import PATH [OPTIONS]
  PATH                   DXF file path (required)
  -n, --name TEXT        Object name
  -u, --units [mm|cm|inch] Target units [default: mm]
  -l, --layers TEXT      Comma-separated layer names to import
  -s, --scale FLOAT      Scale factor [default: 1.0]
```

### dxf-info
Analyze a DXF file without importing.

```
dxf-info PATH
  PATH                   DXF file path (required)
```

Returns: entity counts, layers, units, bounds, geometry analysis.

---

## 8. SVG Import Commands (NEW)

### svg-import
Import an SVG file for vector graphics.

```
svg-import PATH [OPTIONS]
  PATH                   SVG file path (required)
  -u, --units [mm|cm|m|in|pt] Target units [default: mm]
  -s, --scale FLOAT      Scale factor [default: 1.0]
  --fit-width FLOAT      Scale to fit width (mm)
  --fit-height FLOAT     Scale to fit height (mm)
  -n, --name TEXT        Object name
```

---

## 9. Lasercut Validation Commands (NEW - Manufacturing QA)

### validate-lasercut
Validate geometry for laser cutting / CNC manufacturing.

```
validate-lasercut [OPTIONS]
  -o, --object TEXT      Specific object to validate (default: all)
  --min-feature FLOAT    Minimum feature size in mm [default: 0.5]
  --kerf-width FLOAT     Laser kerf width in mm [default: 0.15]
  --plate-width FLOAT    Plate width in mm (for fit check)
  --plate-height FLOAT   Plate height in mm (for fit check)
```

**Validation checks:**
- Contour closure (closed sketches required)
- Duplicate edges detection
- Minimum feature size validation
- Plate fit checking (with kerf margin)
- Kerf compensation advisory

---

## 10. Mesh Commands

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

## 11. Export Commands (Extended)

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

### export 3mf (NEW)
Export project to 3D Manufacturing Format (3D printing).

```
export 3mf [OPTIONS]
  -o, --output PATH      Output file path (required)
  --overwrite            Overwrite existing file
  --objects TEXT          Comma-separated object names (default: all)
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

**Supported formats:** STEP, STL, OBJ, IGES, BREP, 3MF, DXF, SVG, PDF, FCStd

---

## 12. TechDraw Commands (2D Fabrication Drawings - Extended)

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
Add a single 2D orthogonal view.

```
techdraw view PAGE_NAME SOURCE_NAME [OPTIONS]
  PAGE_NAME              Page name (required)
  SOURCE_NAME            Source object name (required)
  -d, --direction TEXT   View direction: front, back, top, bottom, left, right, iso
  -x, --x FLOAT          X position on page [default: auto]
  -y, --y FLOAT          Y position on page [default: auto]
  --scale FLOAT          View scale [default: page scale]
```

### techdraw projection
Add projection group (multiple standard views).

```
techdraw projection PAGE_NAME SOURCE_NAME [OPTIONS]
  PAGE_NAME              Page name (required)
  SOURCE_NAME            Source object name (required)
  --projections TEXT     Comma-separated projections: front,top,right,bottom,left,back
  -x, --x FLOAT          X position on page [default: 100]
  -y, --y FLOAT          Y position on page [default: 150]
  --scale FLOAT          View scale [default: page scale]
```

### techdraw section
Add section view.

```
techdraw section PAGE_NAME SOURCE_NAME VIEW_NAME [OPTIONS]
  PAGE_NAME              Page name (required)
  SOURCE_NAME            Source object name (required)
  VIEW_NAME              Base view name (required)
  -d, --direction TEXT   Section cut direction [default: vertical]
  -p, --position FLOAT   Cut position [default: 50]
```

### techdraw detail
Add detail view (magnified area).

```
techdraw detail PAGE_NAME VIEW_NAME [OPTIONS]
  PAGE_NAME              Page name (required)
  VIEW_NAME              Base view name (required)
  --ax FLOAT             Anchor X position [default: 0]
  --ay FLOAT             Anchor Y position [default: 0]
  -r, --radius FLOAT     Detail radius [default: 10]
  -s, --scale FLOAT      Magnification scale [default: 2.0]
```

### techdraw dimension
Add dimension to view.

```
techdraw dimension PAGE_NAME VIEW_NAME [OPTIONS]
  PAGE_NAME              Page name (required)
  VIEW_NAME              View name (required)
  -t, --type [Distance|DistanceX|DistanceY|Radius|Diameter|Angle] Dimension type [default: Distance]
  --edge TEXT             Edge reference (required)
  --edge2 TEXT            Second edge reference (for Angle)
  -v, --value FLOAT      Override dimension value
```

### techdraw annotate
Add text annotation.

```
techdraw annotate PAGE_NAME [OPTIONS]
  PAGE_NAME              Page name (required)
  -x, --x FLOAT          X position [default: 50]
  -y, --y FLOAT          Y position [default: 50]
  -t, --text TEXT        Annotation text (required)
```

### techdraw title-block
Set title block information.

```
techdraw title-block PAGE_NAME [OPTIONS]
  PAGE_NAME              Page name (required)
  --title TEXT           Drawing title
  --author TEXT          Author name
  --material TEXT        Material specification
  --scale TEXT           Drawing scale text
  --date TEXT            Drawing date
  --number TEXT          Drawing number
```

### techdraw centerline
Add centerline to view.

```
techdraw centerline PAGE_NAME VIEW_NAME [OPTIONS]
  PAGE_NAME              Page name (required)
  VIEW_NAME              View name (required)
  -o, --orientation [horizontal|vertical] Centerline orientation [default: vertical]
  -p, --position FLOAT   Position [default: 50]
```

### techdraw hatch
Add hatch pattern (for section views).

```
techdraw hatch PAGE_NAME VIEW_NAME [OPTIONS]
  PAGE_NAME              Page name (required)
  VIEW_NAME              View name (required)
  -f, --face TEXT        Face to hatch (required)
  -p, --pattern TEXT     Hatch pattern [default: ansi31]
```

### techdraw leader
Add leader line with text.

```
techdraw leader PAGE_NAME VIEW_NAME [OPTIONS]
  PAGE_NAME              Page name (required)
  VIEW_NAME              View name (required)
  --sx FLOAT             Start X [default: 50]
  --sy FLOAT             Start Y [default: 50]
  --ex FLOAT             End X [default: 100]
  --ey FLOAT             End Y [default: 30]
  -t, --text TEXT        Leader text (required)
```

### techdraw balloon (NEW)
Add balloon callout for part identification.

```
techdraw balloon PAGE_NAME VIEW_NAME [OPTIONS]
  PAGE_NAME              Page name (required)
  VIEW_NAME              View name (required)
  -x, --x FLOAT          X position (mm) [default: 50]
  -y, --y FLOAT          Y position (mm) [default: 50]
  -t, --text TEXT        Balloon text/number [default: "1"]
  -s, --symbol [circle|square|triangle] Balloon symbol [default: circle]
  --name TEXT             Balloon name
```

### techdraw auto-balloon (NEW)
Automatically add numbered balloons to all parts in view.

```
techdraw auto-balloon PAGE_NAME VIEW_NAME [OPTIONS]
  PAGE_NAME              Page name (required)
  VIEW_NAME              View name (required)
  -n, --start-number INT Starting number [default: 1]
  -s, --symbol [circle|square|triangle] Balloon symbol [default: circle]
  --spacing FLOAT        Spacing between balloons (mm) [default: 20]
```

### techdraw bom (NEW)
Create Bill of Materials table on drawing page.

```
techdraw bom PAGE_NAME [OPTIONS]
  PAGE_NAME              Page name (required)
  -o, --objects TEXT      Comma-separated object names to include (default: all)
  -t, --template [default|detailed|minimal] BOM template style [default: default]
  --name TEXT             BOM name
```

### techdraw documentation (NEW)
List all BOMs and balloons on a TechDraw page.

```
techdraw documentation PAGE_NAME
  PAGE_NAME              Page name (required)
```

### techdraw gdt
Add geometric dimensioning and tolerancing (GD&T) frame.

```
techdraw gdt PAGE_NAME VIEW_NAME [OPTIONS]
  PAGE_NAME              Page name (required)
  VIEW_NAME              View name (required)
  -c, --characteristic TEXT GD&T characteristic: flatness, straightness, circularity,
                           cylindricity, perpendicularity, parallelism, angularity,
                           position, concentricity, symmetry, circular-runout,
                           total-runout, profile-of-line, profile-of-surface
  -t, --tolerance FLOAT  Tolerance value (required)
  -d, --datum TEXT       Datum reference (repeatable)
  -m, --material-condition [MMC|LMC|RFS] Material condition
  --diameter-zone        Use diameter tolerance zone
```

### techdraw datum
Add datum feature symbol.

```
techdraw datum PAGE_NAME VIEW_NAME LETTER [OPTIONS]
  PAGE_NAME              Page name (required)
  VIEW_NAME              View name (required)
  LETTER                 Datum letter (required)
  -x, --x FLOAT          X position [default: 50]
  -y, --y FLOAT          Y position [default: 50]
```

### techdraw surface-finish
Add surface finish annotation (ISO 1302).

```
techdraw surface-finish PAGE_NAME VIEW_NAME [OPTIONS]
  PAGE_NAME              Page name (required)
  VIEW_NAME              View name (required)
  --ra FLOAT             Ra value (μm) [default: 3.2]
  --rz FLOAT             Rz value (μm)
  -p, --process [removal_required|removal_prohibited|any_method] Process type [default: removal_required]
  -x, --x FLOAT          X position [default: 50]
  -y, --y FLOAT          Y position [default: 50]
```

### techdraw weld
Add weld symbol (AWS A2.4 / ISO 2553).

```
techdraw weld PAGE_NAME VIEW_NAME [OPTIONS]
  PAGE_NAME              Page name (required)
  VIEW_NAME              View name (required)
  -t, --type TEXT        Weld type: fillet, groove, spot, seam, plug, slot, back,
                         flare-bevel, flare-V, corner, edge, surfacing, bevel, V, J, U
  -s, --side [arrow|other|both] Weld side [default: arrow]
  --size FLOAT           Weld size (mm)
  --length FLOAT         Weld length (mm)
  --pitch FLOAT          Weld pitch (mm) [for intermittent welds]
  --all-around           All-around symbol
  --field-weld           Field weld symbol
  --tail TEXT            Tail specification
  -x, --x FLOAT          X position [default: 50]
  -y, --y FLOAT          Y position [default: 50]
```

### techdraw weld-tile
Add tile to weld symbol (for complex welds).

```
techdraw weld-tile PAGE_NAME WELD_NAME [OPTIONS]
  PAGE_NAME              Page name (required)
  WELD_NAME              Weld symbol name (required)
  -t, --type TEXT        Tile type (same as weld types)
  --side [arrow|other]   Tile side [default: arrow]
  --size FLOAT           Tile size (mm)
  --length FLOAT         Tile length (mm)
```

### techdraw list
List all views, dimensions, and annotations on a page.

```
techdraw list PAGE_NAME
  PAGE_NAME              Page name (required)
```

### techdraw export-dxf
Export drawing page to DXF format.

```
techdraw export-dxf PAGE_NAME OUTPUT_PATH [OPTIONS]
  PAGE_NAME              Page name (required)
  OUTPUT_PATH            Output file path (required)
  --overwrite            Overwrite existing file
```

### techdraw export-svg
Export drawing page to SVG format.

```
techdraw export-svg PAGE_NAME OUTPUT_PATH [OPTIONS]
  PAGE_NAME              Page name (required)
  OUTPUT_PATH            Output file path (required)
  --overwrite            Overwrite existing file
```

### techdraw export-pdf
Export drawing page to PDF format.

```
techdraw export-pdf PAGE_NAME OUTPUT_PATH [OPTIONS]
  PAGE_NAME              Page name (required)
  OUTPUT_PATH            Output file path (required)
  --overwrite            Overwrite existing file
```

---

## 13. Session Commands

### session status
Show current session state.

```
session status
  (no options)
```

### session undo
Undo last operation.

```
session undo
  (no options)
```

### session redo
Redo last undone operation.

```
session redo
  (no options)
```

### session history
Show operation history.

```
session history
  (no options)
```

---

## 14. Utility Commands

### version
Show FreeCAD and CLI version information.

```
version
  (no options)
```

### repl
Start interactive REPL mode.

```
repl
  (no options - default when no command specified)
```

---

## Complete Command Count

- **Project**: 6 commands
- **Part**: 15 commands (+3 new)
- **PartDesign**: 11 commands (NEW)
- **Sketch**: 8 commands (+2 new)
- **Assembly**: 5 commands (NEW)
- **FEM**: 7 commands (NEW)
- **DXF Import**: 2 commands (NEW)
- **SVG Import**: 1 command (NEW)
- **Lasercut Validation**: 1 command (NEW)
- **Mesh**: 2 commands
- **Export**: 8 commands (+1 new)
- **TechDraw**: 22 commands (+4 new)
- **Session**: 4 commands
- **Utilities**: 2 commands

**Total: 130+ commands** (was 63+)