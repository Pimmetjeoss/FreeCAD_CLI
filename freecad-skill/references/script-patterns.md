# FreeCAD Python API Patterns & Script Generation

## Overview

The CLI harness generates FreeCAD Python scripts from JSON object definitions. These scripts
are executed headlessly via `freecadcmd`. This reference documents the FreeCAD Python API
patterns used and how the harness translates JSON to Python.

## Module Imports

| Module | Purpose |
|--------|---------|
| FreeCAD | Core: documents, objects, properties, vectors, rotations |
| Part | Solid modeling: primitives, booleans, shape operations, STEP/IGES export |
| PartDesign | Feature-based parametric design (Pad, Pocket, Fillet) |
| Sketcher | 2D sketch creation and constraint solving |
| Mesh | Triangle mesh import/export and operations |
| MeshPart | Mesh-to-Part and Part-to-Mesh conversion |
| TechDraw | 2D fabrication drawing pages, views, dimensions |
| Import | STEP/IGES/DXF import and export |

## Document Lifecycle

```python
# Create new document
doc = FreeCAD.newDocument("MyDoc")

# Open existing document
doc = FreeCAD.openDocument("/path/to/file.FCStd")

# Recompute (required after adding/modifying objects)
doc.recompute()

# Save document
doc.saveAs("/path/to/output.FCStd")
```

## Primitive Creation

### Box
```python
_obj = doc.addObject('Part::Box', 'Box')
_obj.Length = 100
_obj.Width = 50
_obj.Height = 30
```

### Cylinder
```python
_obj = doc.addObject('Part::Cylinder', 'Cylinder')
_obj.Radius = 10
_obj.Height = 40
_obj.Angle = 360  # Sweep angle (partial cylinder if < 360)
```

### Sphere
```python
_obj = doc.addObject('Part::Sphere', 'Sphere')
_obj.Radius = 25
```

### Cone
```python
_obj = doc.addObject('Part::Cone', 'Cone')
_obj.Radius1 = 10  # Bottom radius
_obj.Radius2 = 3   # Top radius
_obj.Height = 20
```

### Torus
```python
_obj = doc.addObject('Part::Torus', 'Torus')
_obj.Radius1 = 20  # Major radius (center to tube center)
_obj.Radius2 = 5   # Minor radius (tube radius)
```

## Placement (Positioning)

```python
_obj.Placement = FreeCAD.Placement(
    FreeCAD.Vector(px, py, pz),         # Position
    FreeCAD.Rotation(0, 0, 0, 1)        # Quaternion rotation (identity = no rotation)
)
```

The harness generates placement code only when placement parameters (x, y, z) are non-zero.

## Boolean Operations

### Fuse (Union)
```python
_obj = doc.addObject('Part::Fuse', 'Fuse')
_obj.Base = doc.getObject('Shape1')
_obj.Tool = doc.getObject('Shape2')
```

### Cut (Subtraction)
```python
_obj = doc.addObject('Part::Cut', 'Cut')
_obj.Base = doc.getObject('BaseShape')
_obj.Tool = doc.getObject('CuttingTool')
```

### Common (Intersection)
```python
_obj = doc.addObject('Part::Common', 'Common')
_obj.Base = doc.getObject('Shape1')
_obj.Tool = doc.getObject('Shape2')
```

## Edge Operations

### Fillet
```python
doc.recompute()
_base = doc.getObject('Box')
_obj = doc.addObject('Part::Fillet', 'Fillet')
_obj.Base = _base
_edges = [(i+1, radius, radius) for i in range(len(_base.Shape.Edges))]
_obj.Shape = _base.Shape.makeFillet(radius, _base.Shape.Edges)
```

### Chamfer
```python
doc.recompute()
_base = doc.getObject('Box')
_obj = doc.addObject('Part::Chamfer', 'Chamfer')
_obj.Base = _base
_edges = [(i+1, size, size) for i in range(len(_base.Shape.Edges))]
_obj.Shape = _base.Shape.makeChamfer(size, _base.Shape.Edges)
```

Note: Both fillet and chamfer require a recompute before accessing edges.

## Sketcher

### Create Sketch on Plane
```python
import Sketcher

_obj = doc.addObject('Sketcher::SketchObject', 'Sketch')

# XY plane (default)
_obj.Placement = FreeCAD.Placement(
    FreeCAD.Vector(0, 0, 0), FreeCAD.Rotation(0, 0, 0, 1))

# XZ plane
_obj.Placement = FreeCAD.Placement(
    FreeCAD.Vector(0, 0, 0), FreeCAD.Rotation(FreeCAD.Vector(1, 0, 0), -90))

# YZ plane
_obj.Placement = FreeCAD.Placement(
    FreeCAD.Vector(0, 0, 0), FreeCAD.Rotation(FreeCAD.Vector(0, 1, 0), 90))
```

### Geometry

```python
# Line
_obj.addGeometry(Part.LineSegment(
    FreeCAD.Vector(x1, y1, 0),
    FreeCAD.Vector(x2, y2, 0)))

# Circle
_obj.addGeometry(Part.Circle(
    FreeCAD.Vector(cx, cy, 0),    # Center
    FreeCAD.Vector(0, 0, 1),       # Normal (Z-up for XY plane)
    radius))

# Arc
import math
_obj.addGeometry(Part.ArcOfCircle(
    Part.Circle(FreeCAD.Vector(cx, cy, 0), FreeCAD.Vector(0, 0, 1), radius),
    math.radians(start_angle),
    math.radians(end_angle)))

# Rectangle (4 lines + auto-constraints)
_gi = _obj.GeometryCount
_obj.addGeometry(Part.LineSegment(FreeCAD.Vector(x, y, 0), FreeCAD.Vector(x+w, y, 0)))
_obj.addGeometry(Part.LineSegment(FreeCAD.Vector(x+w, y, 0), FreeCAD.Vector(x+w, y+h, 0)))
_obj.addGeometry(Part.LineSegment(FreeCAD.Vector(x+w, y+h, 0), FreeCAD.Vector(x, y+h, 0)))
_obj.addGeometry(Part.LineSegment(FreeCAD.Vector(x, y+h, 0), FreeCAD.Vector(x, y, 0)))
# Auto-add coincident constraints for corners + horizontal/vertical constraints
```

### Constraints

```python
# Geometric constraints
_obj.addConstraint(Sketcher.Constraint('Horizontal', geom_index))
_obj.addConstraint(Sketcher.Constraint('Vertical', geom_index))
_obj.addConstraint(Sketcher.Constraint('Parallel', geom1, geom2))
_obj.addConstraint(Sketcher.Constraint('Perpendicular', geom1, geom2))
_obj.addConstraint(Sketcher.Constraint('Equal', geom1, geom2))

# Dimensional constraints
_obj.addConstraint(Sketcher.Constraint('Distance', geom_index, value))
_obj.addConstraint(Sketcher.Constraint('Radius', geom_index, value))
_obj.addConstraint(Sketcher.Constraint('Angle', geom_index, math.radians(degrees)))

# Point constraints
_obj.addConstraint(Sketcher.Constraint('Coincident', geom1, point1, geom2, point2))
```

## Extrusion

```python
_obj = doc.addObject('Part::Extrusion', 'Extrusion')
_obj.Base = doc.getObject('Sketch')
_obj.Dir = FreeCAD.Vector(dx, dy, dz)  # Direction and length
```

## Mesh Operations

### Import Mesh
```python
import Mesh
Mesh.insert("/path/to/file.stl", doc.Name)
```

### Part to Mesh Conversion
```python
import MeshPart
mesh = MeshPart.meshFromShape(
    obj.Shape,
    LinearDeflection=0.1,     # Accuracy (smaller = finer mesh)
    AngularDeflection=0.5     # Angular tolerance
)
```

## Export Strategies

### STEP/IGES
```python
import Part
Part.export([obj1, obj2], "/path/to/output.step")
```

### STL/OBJ (mesh formats)
```python
import Mesh, MeshPart
meshes = []
for obj in objects:
    m = MeshPart.meshFromShape(obj.Shape, LinearDeflection=0.1, AngularDeflection=0.5)
    meshes.append(m)
combined = meshes[0]
for m in meshes[1:]:
    combined.addMesh(m)
combined.write("/path/to/output.stl")
```

### BREP
```python
# Single object
obj.Shape.exportBrep("/path/to/output.brep")

# Multiple objects (compound)
import Part
compound = Part.makeCompound([o.Shape for o in objects])
compound.exportBrep("/path/to/output.brep")
```

## GD&T Annotation Script Generation

GD&T elements are rendered as `TechDraw::DrawViewAnnotation` objects since FreeCAD's TechDraw workbench does not have native GD&T frame objects.

### Feature Control Frame
```python
# GD&T Feature Control Frame (position tolerance, MMC, datums A, B)
_gdt = doc.addObject('TechDraw::DrawViewAnnotation', 'GDT1')
_gdt.Text = ['⌖ | ∅ 0.05 Ⓜ | A | B']
_gdt.X, _gdt.Y = 100, 80
page.addView(_gdt)
```

### Datum Symbol
```python
# Datum feature symbol (triangle + letter)
_datum = doc.addObject('TechDraw::DrawViewAnnotation', 'DatumA')
_datum.Text = ['▼ [A]']
_datum.X, _datum.Y = 50, 120
page.addView(_datum)
```

### Surface Finish
```python
# Surface finish annotation (ISO 1302)
_sf = doc.addObject('TechDraw::DrawViewAnnotation', 'SurfFinish1')
_sf.Text = ['▽ Ra 1.6']
_sf.X, _sf.Y = 80, 60
page.addView(_sf)
```

In SVG export, these are rendered as custom SVG elements:
- **FCF**: Row of bordered `<rect>` cells with `<text>` for symbol, tolerance, and datum refs
- **Datum**: Filled triangle (`<polygon>`) with letter in bordered box
- **Surface finish**: Checkmark polyline with roughness values as text

## Backend Execution Wrapper

The freecad_backend.run_script() function wraps all user scripts:

```python
import json, sys, os
_result_path = "/tmp/result.json"
_cli_result = {}
try:
    # === USER SCRIPT GOES HERE (indented) ===
    import FreeCAD
    import Part
    doc = FreeCAD.newDocument("MyDoc")
    # ... all generated code ...
    doc.recompute()
except Exception as _e:
    _cli_result['error'] = str(_e)
    import traceback
    _cli_result['traceback'] = traceback.format_exc()
finally:
    with open(_result_path, 'w') as _f:
        json.dump(_cli_result, _f)
```

The `_cli_result` dict is the communication channel between the FreeCAD subprocess and
the CLI harness. Any key/value pairs written to it are available in the result.

## Shape Inspection

```python
shape = obj.Shape
shape.ShapeType     # 'Solid', 'Compound', etc.
shape.Volume        # Volume in mm^3
shape.Area          # Surface area in mm^2
shape.Edges         # List of edges
shape.Faces         # List of faces

bb = shape.BoundBox
bb.XMin, bb.XMax    # Bounding box extents
bb.YMin, bb.YMax
bb.ZMin, bb.ZMax
```
