"""Export pipeline — save FreeCAD documents, export to STEP/STL/OBJ/IGES/BREP.

All exports go through the real FreeCAD backend. We first save the project
as .FCStd, then use FreeCAD's export modules for format conversion.
"""

from __future__ import annotations

import os
from typing import Any

from cli_anything.freecad.core.project import save_fcstd
from cli_anything.freecad.utils.freecad_backend import export_document, run_script


# Supported export formats with descriptions
EXPORT_FORMATS = {
    "step": {"extensions": [".step", ".stp"], "description": "STEP (ISO 10303)"},
    "iges": {"extensions": [".iges", ".igs"], "description": "IGES"},
    "stl": {"extensions": [".stl"], "description": "STL mesh"},
    "obj": {"extensions": [".obj"], "description": "Wavefront OBJ mesh"},
    "brep": {"extensions": [".brep", ".brp"], "description": "OpenCASCADE BREP"},
    "fcstd": {"extensions": [".fcstd"], "description": "FreeCAD native"},
    "dxf": {"extensions": [".dxf"], "description": "DXF (TechDraw 2D)"},
    "svg": {"extensions": [".svg"], "description": "SVG (TechDraw 2D)"},
    "pdf": {"extensions": [".pdf"], "description": "PDF (TechDraw 2D)"},
}


def export(
    project: dict[str, Any],
    output_path: str,
    preset: str | None = None,
    overwrite: bool = False,
    object_names: list[str] | None = None,
) -> dict[str, Any]:
    """Export project to the specified format.

    Pipeline:
    1. Save project as .FCStd (intermediate)
    2. Use FreeCAD backend to export to target format

    Args:
        project: Project dict with objects.
        output_path: Output file path (format determined by extension).
        preset: Export preset name (maps to format).
        overwrite: Whether to overwrite existing files.
        object_names: Optional list of specific objects to export.

    Returns:
        Dict with export results including output path and file size.
    """
    output_path = os.path.abspath(output_path)

    if os.path.exists(output_path) and not overwrite:
        return {"success": False, "error": f"File exists: {output_path}. Use --overwrite."}

    ext = os.path.splitext(output_path)[1].lower()
    if preset:
        fmt = EXPORT_FORMATS.get(preset)
        if fmt and ext not in fmt["extensions"]:
            ext = fmt["extensions"][0]
            output_path = os.path.splitext(output_path)[0] + ext

    # For .fcstd, just save directly
    if ext == ".fcstd":
        result = save_fcstd(project, output_path)
        if result.get("success"):
            r = result.get("result", {})
            return {
                "success": True,
                "output": output_path,
                "file_size": r.get("file_size", 0),
                "format": "fcstd",
                "method": "freecad-native",
            }
        return {"success": False, "error": result.get("result", {}).get("error", "Save failed")}

    # For other formats: save as FCStd first, then export
    import tempfile
    with tempfile.TemporaryDirectory(prefix="cli_anything_fc_") as tmpdir:
        fcstd_path = os.path.join(tmpdir, "temp.FCStd")

        # Save as FCStd
        save_result = save_fcstd(project, fcstd_path)
        if not save_result.get("success"):
            err = save_result.get("result", {}).get("error", "Failed to create FCStd")
            return {"success": False, "error": f"FCStd creation failed: {err}"}

        # Export via FreeCAD backend
        exp_result = export_document(fcstd_path, output_path, object_names)

        if exp_result.get("success") and exp_result.get("result", {}).get("output"):
            r = exp_result["result"]
            return {
                "success": True,
                "output": r["output"],
                "file_size": r.get("file_size", 0),
                "format": r.get("format", ext),
                "method": "freecad-backend",
            }
        else:
            err = exp_result.get("result", {}).get("error", "Export failed")
            stderr = exp_result.get("stderr", "")
            return {"success": False, "error": err, "stderr": stderr}


def list_formats() -> list[dict[str, str]]:
    """List all supported export formats.

    Returns:
        List of format info dicts.
    """
    return [
        {"name": name, "extensions": ", ".join(info["extensions"]), "description": info["description"]}
        for name, info in EXPORT_FORMATS.items()
    ]
