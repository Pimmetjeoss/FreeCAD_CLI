"""FreeCAD backend — invokes the real FreeCAD for all geometry operations.

This module wraps `freecadcmd` to execute Python scripts headlessly.
FreeCAD is a HARD dependency — the CLI is useless without it.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from typing import Any


def find_freecadcmd() -> str:
    """Find the freecadcmd executable.

    Returns:
        Path to freecadcmd.

    Raises:
        RuntimeError: If FreeCAD is not installed.
    """
    for name in ("freecadcmd", "FreeCADCmd", "freecad-cmd"):
        path = shutil.which(name)
        if path:
            return path
    raise RuntimeError(
        "FreeCAD is not installed. Install it with:\n"
        "  apt install freecad          # Debian/Ubuntu\n"
        "  brew install --cask freecad  # macOS\n"
        "  pacman -S freecad            # Arch Linux"
    )


def run_script(script: str, timeout: int = 120) -> dict[str, Any]:
    """Execute a FreeCAD Python script via freecadcmd.

    The script is written to a temp file, executed, and results are
    communicated via a JSON output file.

    Args:
        script: Python code to execute inside FreeCAD.
        timeout: Max execution time in seconds.

    Returns:
        Dict with keys: success, output, error, result (parsed JSON if any).
    """
    freecadcmd = find_freecadcmd()

    with tempfile.TemporaryDirectory(prefix="cli_anything_fc_") as tmpdir:
        script_path = os.path.join(tmpdir, "script.py")
        result_path = os.path.join(tmpdir, "result.json")

        # Wrap script to write results to JSON
        wrapped = (
            "import json, sys, os\n"
            f"_result_path = {result_path!r}\n"
            "_cli_result = {}\n"
            "try:\n"
        )
        # Indent the user script
        for line in script.splitlines():
            wrapped += f"    {line}\n"
        wrapped += (
            "except Exception as _e:\n"
            "    _cli_result['error'] = str(_e)\n"
            "    import traceback\n"
            "    _cli_result['traceback'] = traceback.format_exc()\n"
            "finally:\n"
            "    with open(_result_path, 'w') as _f:\n"
            "        json.dump(_cli_result, _f)\n"
        )

        with open(script_path, "w") as f:
            f.write(wrapped)

        proc = subprocess.run(
            [freecadcmd, script_path],
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        result: dict[str, Any] = {
            "success": proc.returncode == 0,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "returncode": proc.returncode,
        }

        if os.path.exists(result_path):
            with open(result_path) as f:
                result["result"] = json.load(f)
            if "error" in result["result"]:
                result["success"] = False
        else:
            result["result"] = {}

        return result


def get_version() -> str:
    """Get FreeCAD version string."""
    freecadcmd = find_freecadcmd()
    proc = subprocess.run(
        [freecadcmd, "--version"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    return proc.stdout.strip() or proc.stderr.strip()


def export_document(
    fcstd_path: str,
    output_path: str,
    object_names: list[str] | None = None,
) -> dict[str, Any]:
    """Export a FreeCAD document to another format via freecadcmd.

    Args:
        fcstd_path: Path to .FCStd input file.
        output_path: Desired output path (format determined by extension).
        object_names: Optional list of object names to export (default: all).

    Returns:
        Dict with export results.
    """
    ext = os.path.splitext(output_path)[1].lower()

    if object_names:
        obj_filter = (
            f"objs = [{', '.join(f'doc.getObject({n!r})' for n in object_names)}]\n"
            "objs = [o for o in objs if o is not None]\n"
        )
    else:
        obj_filter = "objs = [o for o in doc.Objects if hasattr(o, 'Shape')]\n"

    script = (
        "import FreeCAD\n"
        f"doc = FreeCAD.openDocument({fcstd_path!r})\n"
        f"{obj_filter}"
        "if not objs:\n"
        "    _cli_result['error'] = 'No exportable objects found'\n"
        "else:\n"
    )

    if ext in (".step", ".stp"):
        script += (
            f"    import Part\n"
            f"    Part.export(objs, {output_path!r})\n"
        )
    elif ext in (".iges", ".igs"):
        script += (
            f"    import Part\n"
            f"    Part.export(objs, {output_path!r})\n"
        )
    elif ext in (".stl",):
        script += (
            f"    import Mesh\n"
            f"    import MeshPart\n"
            f"    meshes = []\n"
            f"    for obj in objs:\n"
            f"        if hasattr(obj, 'Shape'):\n"
            f"            m = MeshPart.meshFromShape(obj.Shape, LinearDeflection=0.1, AngularDeflection=0.5)\n"
            f"            meshes.append(m)\n"
            f"    if meshes:\n"
            f"        combined = meshes[0]\n"
            f"        for m in meshes[1:]:\n"
            f"            combined.addMesh(m)\n"
            f"        combined.write({output_path!r})\n"
        )
    elif ext in (".obj",):
        script += (
            f"    import Mesh\n"
            f"    import MeshPart\n"
            f"    meshes = []\n"
            f"    for obj in objs:\n"
            f"        if hasattr(obj, 'Shape'):\n"
            f"            m = MeshPart.meshFromShape(obj.Shape, LinearDeflection=0.1, AngularDeflection=0.5)\n"
            f"            meshes.append(m)\n"
            f"    if meshes:\n"
            f"        combined = meshes[0]\n"
            f"        for m in meshes[1:]:\n"
            f"            combined.addMesh(m)\n"
            f"        combined.write({output_path!r})\n"
        )
    elif ext in (".brep", ".brp"):
        script += (
            f"    import Part\n"
            f"    if len(objs) == 1:\n"
            f"        objs[0].Shape.exportBrep({output_path!r})\n"
            f"    else:\n"
            f"        compound = Part.makeCompound([o.Shape for o in objs])\n"
            f"        compound.exportBrep({output_path!r})\n"
        )
    else:
        # Generic: try Import module
        script += (
            f"    import importlib\n"
            f"    try:\n"
            f"        import Import\n"
            f"        Import.export(objs, {output_path!r})\n"
            f"    except Exception as e:\n"
            f"        _cli_result['error'] = f'Export to {ext} failed: {{e}}'\n"
        )

    script += (
        f"    import os\n"
        f"    if os.path.exists({output_path!r}):\n"
        f"        _cli_result['output'] = {output_path!r}\n"
        f"        _cli_result['file_size'] = os.path.getsize({output_path!r})\n"
        f"        _cli_result['format'] = {ext!r}\n"
        f"    elif 'error' not in _cli_result:\n"
        f"        _cli_result['error'] = 'Export produced no output file'\n"
    )

    return run_script(script)
