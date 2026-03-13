"""FreeCAD build script — generates experiment.step.

This is the file the agent iteratively improves.
Runs inside FreeCADCmd (FreeCAD Python environment).

Usage:
    freecadcmd freecad_build.py

Current version: v0 — baseline cylinder R13.5 x H28.
"""

import os
import sys

import FreeCAD
import Part

# Output path: experiment.step in same directory as this script
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_PATH = os.path.join(SCRIPT_DIR, "experiment.step")

doc = FreeCAD.newDocument("Experiment")

# --- v0: Simple cylinder as baseline ---
# Reference is ~Ø27 x 28mm (R13.5 x H28), centered at origin
body = Part.makeCylinder(13.5, 28.0)

# Add shape to document
part_obj = doc.addObject("Part::Feature", "Body")
part_obj.Shape = body
doc.recompute()

# Export to STEP
Part.export([part_obj], OUTPUT_PATH)

print(f"[OK] Exported {OUTPUT_PATH}")
print(f"     Volume: {body.Volume:.2f} mm³")
print(f"     BBox: {body.BoundBox.XLength:.2f} x {body.BoundBox.YLength:.2f} x {body.BoundBox.ZLength:.2f}")

FreeCAD.closeDocument(doc.Name)
sys.exit(0)
