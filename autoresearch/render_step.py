"""Render a STEP file to PNG via STL + matplotlib.

Two-step process:
1. freecadcmd converts STEP → temporary STL
2. matplotlib 3D plot of STL mesh → PNG (512x512)

Usage:
    python render_step.py <step_file> <output_png>
    python render_step.py reference.step reference.png
"""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np


def find_freecadcmd() -> str:
    """Find the FreeCADCmd executable."""
    for name in ("freecadcmd", "FreeCADCmd", "FreeCADCmd.exe", "freecad-cmd"):
        path = shutil.which(name)
        if path:
            return path
    # Check common Windows install paths
    common_paths = [
        r"C:\Program Files\FreeCAD 1.0\bin\FreeCADCmd.exe",
        r"C:\Program Files\FreeCAD\bin\FreeCADCmd.exe",
        r"C:\Program Files (x86)\FreeCAD\bin\FreeCADCmd.exe",
    ]
    for p in common_paths:
        if os.path.exists(p):
            return p
    raise RuntimeError(
        "FreeCADCmd not found. Install FreeCAD 1.0+ and add bin/ to PATH.\n"
        "  Windows: https://www.freecad.org/downloads.php\n"
        "  Linux:   apt install freecad\n"
        "  macOS:   brew install --cask freecad"
    )


def step_to_stl(step_path: str, stl_path: str) -> None:
    """Convert STEP to STL using FreeCADCmd."""
    freecadcmd = find_freecadcmd()

    script = f"""
import FreeCAD
import Part
import Import
import Mesh
import MeshPart
import os

doc = FreeCAD.newDocument("Convert")
Import.insert({step_path!r}, doc.Name)
doc.recompute()

meshes = []
for obj in doc.Objects:
    if hasattr(obj, "Shape") and obj.Shape.Solids:
        m = MeshPart.meshFromShape(
            obj.Shape,
            LinearDeflection=0.05,
            AngularDeflection=0.3,
        )
        meshes.append(m)

if meshes:
    combined = meshes[0]
    for m in meshes[1:]:
        combined.addMesh(m)
    combined.write({stl_path!r})
    print("[OK] STL written")
else:
    print("[ERROR] No solids found")

FreeCAD.closeDocument(doc.Name)
"""

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, prefix="render_"
    ) as f:
        f.write(script)
        script_path = f.name

    try:
        proc = subprocess.run(
            [freecadcmd, script_path],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if proc.returncode != 0:
            print(f"[WARN] FreeCADCmd stderr:\n{proc.stderr}", file=sys.stderr)
        if not os.path.exists(stl_path):
            raise RuntimeError(
                f"STL conversion failed.\nstdout: {proc.stdout}\nstderr: {proc.stderr}"
            )
    finally:
        os.unlink(script_path)


def load_stl(stl_path: str) -> tuple[np.ndarray, np.ndarray]:
    """Load STL file and return vertices and faces.

    Returns:
        vertices: (N, 3) array of vertex positions
        faces: (M, 3) array of face vertex indices
    """
    try:
        import trimesh
        mesh = trimesh.load(stl_path)
        return np.array(mesh.vertices), np.array(mesh.faces)
    except ImportError:
        pass

    # Fallback: manual binary STL parser
    with open(stl_path, "rb") as f:
        header = f.read(80)
        num_triangles = int.from_bytes(f.read(4), "little")
        vertices = []
        faces = []
        for i in range(num_triangles):
            normal = np.frombuffer(f.read(12), dtype=np.float32)
            v1 = np.frombuffer(f.read(12), dtype=np.float32)
            v2 = np.frombuffer(f.read(12), dtype=np.float32)
            v3 = np.frombuffer(f.read(12), dtype=np.float32)
            attr = f.read(2)
            base = len(vertices)
            vertices.extend([v1.copy(), v2.copy(), v3.copy()])
            faces.append([base, base + 1, base + 2])

    return np.array(vertices), np.array(faces)


def render_mesh(
    vertices: np.ndarray,
    faces: np.ndarray,
    output_path: str,
    size: int = 512,
) -> None:
    """Render mesh as isometric 3D plot to PNG."""
    import matplotlib
    matplotlib.use("Agg")
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    import matplotlib.pyplot as plt

    fig = plt.figure(figsize=(size / 100, size / 100), dpi=100)
    ax = fig.add_subplot(111, projection="3d")

    # Build polygon collection from faces
    polys = vertices[faces]
    collection = Poly3DCollection(
        polys,
        alpha=0.85,
        edgecolor=(0.2, 0.2, 0.2, 0.15),
        linewidth=0.1,
        facecolor=(0.7, 0.75, 0.8),
    )
    ax.add_collection3d(collection)

    # Set limits based on mesh bounds
    mins = vertices.min(axis=0)
    maxs = vertices.max(axis=0)
    center = (mins + maxs) / 2
    span = (maxs - mins).max() / 2 * 1.2

    ax.set_xlim(center[0] - span, center[0] + span)
    ax.set_ylim(center[1] - span, center[1] + span)
    ax.set_zlim(center[2] - span, center[2] + span)

    # Fixed isometric camera
    ax.view_init(elev=30, azim=45)
    ax.set_box_aspect([1, 1, 1])

    # Clean appearance
    ax.set_axis_off()
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    plt.tight_layout(pad=0)
    fig.savefig(output_path, dpi=100, bbox_inches="tight", pad_inches=0.1)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description="Render STEP file to PNG.")
    parser.add_argument("step_file", type=str, help="Input STEP file")
    parser.add_argument("output_png", type=str, help="Output PNG file")
    parser.add_argument("--size", type=int, default=512, help="Image size in pixels")
    args = parser.parse_args()

    if not os.path.exists(args.step_file):
        print(f"[ERROR] File not found: {args.step_file}")
        sys.exit(1)

    # Step 1: STEP → STL
    with tempfile.NamedTemporaryFile(suffix=".stl", delete=False) as tmp:
        stl_path = tmp.name

    try:
        print(f"[1/2] Converting {args.step_file} → STL ...")
        step_to_stl(args.step_file, stl_path)

        # Step 2: STL → PNG
        print(f"[2/2] Rendering STL → {args.output_png} ...")
        vertices, faces = load_stl(stl_path)
        render_mesh(vertices, faces, args.output_png, args.size)
        print(f"[OK] Saved {args.output_png}")
    finally:
        if os.path.exists(stl_path):
            os.unlink(stl_path)


if __name__ == "__main__":
    main()
