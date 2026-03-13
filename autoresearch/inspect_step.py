"""Inspect a STEP file and report geometric properties.

Runs inside FreeCADCmd (FreeCAD Python environment).

Usage:
    freecadcmd inspect_step.py <step_file> [--output result.json]

Reports: volume, surface area, bounding box, face/edge/vertex counts,
center of mass — as JSON to stdout or file.
"""

import json
import os
import sys

import FreeCAD
import Part
import Import


def inspect(step_path: str) -> dict:
    """Load a STEP file and extract geometric properties."""
    if not os.path.exists(step_path):
        return {"error": f"File not found: {step_path}"}

    doc = FreeCAD.newDocument("Inspect")
    Import.insert(step_path, doc.Name)
    doc.recompute()

    # Collect all shapes
    shapes = []
    for obj in doc.Objects:
        if hasattr(obj, "Shape") and obj.Shape.Solids:
            shapes.append(obj.Shape)

    if not shapes:
        return {"error": "No solid shapes found in STEP file"}

    # Fuse all shapes into one compound for overall metrics
    if len(shapes) == 1:
        combined = shapes[0]
    else:
        combined = shapes[0]
        for s in shapes[1:]:
            combined = combined.fuse(s)

    bbox = combined.BoundBox
    com = combined.CenterOfMass

    result = {
        "file": os.path.basename(step_path),
        "volume": combined.Volume,
        "surface_area": combined.Area,
        "bounding_box": {
            "xmin": bbox.XMin,
            "ymin": bbox.YMin,
            "zmin": bbox.ZMin,
            "xmax": bbox.XMax,
            "ymax": bbox.YMax,
            "zmax": bbox.ZMax,
            "xlen": bbox.XLength,
            "ylen": bbox.YLength,
            "zlen": bbox.ZLength,
            "diagonal": bbox.DiagonalLength,
        },
        "center_of_mass": {
            "x": com.x,
            "y": com.y,
            "z": com.z,
        },
        "num_solids": len(combined.Solids),
        "num_faces": len(combined.Faces),
        "num_edges": len(combined.Edges),
        "num_vertices": len(combined.Vertexes),
    }

    FreeCAD.closeDocument(doc.Name)
    return result


def main():
    # Parse args manually (FreeCADCmd passes script args after script path)
    args = sys.argv[sys.argv.index(__file__) + 1:] if __file__ in sys.argv else sys.argv[1:]

    if not args:
        print("Usage: freecadcmd inspect_step.py <step_file> [--output result.json]")
        sys.exit(1)

    step_path = args[0]
    output_path = None
    if "--output" in args:
        idx = args.index("--output")
        if idx + 1 < len(args):
            output_path = args[idx + 1]

    result = inspect(step_path)

    json_str = json.dumps(result, indent=2)

    if output_path:
        with open(output_path, "w") as f:
            f.write(json_str)
        print(f"[OK] Wrote {output_path}")
    else:
        print(json_str)


if __name__ == "__main__":
    main()
