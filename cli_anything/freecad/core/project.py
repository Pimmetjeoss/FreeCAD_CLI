"""Project management — create, open, save, inspect FreeCAD documents.

The project state is stored as a JSON file that tracks the document,
its objects, and metadata. The actual geometry lives in .FCStd files
managed by FreeCAD.
"""

from __future__ import annotations

import json
import os
import time
from typing import Any

from cli_anything.freecad.utils.freecad_backend import run_script


def create_project(
    name: str = "Untitled",
    output_path: str | None = None,
) -> dict[str, Any]:
    """Create a new FreeCAD project.

    Args:
        name: Document name.
        output_path: Path for the project JSON file.

    Returns:
        Project dict with metadata.
    """
    project = {
        "name": name,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "modified_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "fcstd_path": None,
        "objects": [],
        "history": [],
        "modified": False,
    }

    if output_path:
        project["project_path"] = os.path.abspath(output_path)
        with open(output_path, "w") as f:
            json.dump(project, f, indent=2)

    return project


def load_project(project_path: str) -> dict[str, Any]:
    """Load a project from its JSON file.

    Args:
        project_path: Path to project JSON file.

    Returns:
        Project dict.

    Raises:
        FileNotFoundError: If project file doesn't exist.
    """
    with open(project_path) as f:
        project = json.load(f)
    project["project_path"] = os.path.abspath(project_path)
    return project


def save_project(project: dict[str, Any], path: str | None = None) -> str:
    """Save project state to JSON.

    Args:
        project: Project dict.
        path: Output path (uses project_path if None).

    Returns:
        Path where project was saved.
    """
    path = path or project.get("project_path")
    if not path:
        raise ValueError("No save path specified and no project_path set")

    project["modified_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    project["project_path"] = os.path.abspath(path)

    with open(path, "w") as f:
        json.dump(project, f, indent=2)

    project["modified"] = False
    return path


def save_fcstd(project: dict[str, Any], fcstd_path: str) -> dict[str, Any]:
    """Save the project objects as a .FCStd file via FreeCAD.

    Args:
        project: Project dict with objects.
        fcstd_path: Output .FCStd path.

    Returns:
        Result dict from FreeCAD backend.
    """
    fcstd_path = os.path.abspath(fcstd_path)
    script = _build_project_script(project)
    script += (
        f"doc.saveAs({fcstd_path!r})\n"
        f"_cli_result['fcstd_path'] = {fcstd_path!r}\n"
        f"import os\n"
        f"_cli_result['file_size'] = os.path.getsize({fcstd_path!r})\n"
        f"_cli_result['object_count'] = len(doc.Objects)\n"
    )

    result = run_script(script)
    if result.get("success") and result.get("result", {}).get("fcstd_path"):
        project["fcstd_path"] = fcstd_path
        project["modified"] = True
    return result


def get_project_info(project: dict[str, Any]) -> dict[str, Any]:
    """Get detailed project information.

    Args:
        project: Project dict.

    Returns:
        Info dict with metadata and object details.
    """
    info = {
        "name": project.get("name", "Untitled"),
        "created_at": project.get("created_at"),
        "modified_at": project.get("modified_at"),
        "fcstd_path": project.get("fcstd_path"),
        "object_count": len(project.get("objects", [])),
        "objects": [],
        "modified": project.get("modified", False),
    }

    for obj in project.get("objects", []):
        info["objects"].append({
            "name": obj.get("name"),
            "type": obj.get("type"),
            "label": obj.get("label", obj.get("name")),
        })

    return info


def inspect_fcstd(fcstd_path: str) -> dict[str, Any]:
    """Inspect a .FCStd file using FreeCAD to extract its contents.

    Args:
        fcstd_path: Path to .FCStd file.

    Returns:
        Dict with document info, objects, properties.
    """
    script = (
        "import FreeCAD\n"
        f"doc = FreeCAD.openDocument({fcstd_path!r})\n"
        "_cli_result['name'] = doc.Name\n"
        "_cli_result['label'] = doc.Label\n"
        "_cli_result['object_count'] = len(doc.Objects)\n"
        "_cli_result['objects'] = []\n"
        "for obj in doc.Objects:\n"
        "    o = {'name': obj.Name, 'type': obj.TypeId, 'label': obj.Label}\n"
        "    if hasattr(obj, 'Shape'):\n"
        "        s = obj.Shape\n"
        "        o['shape_type'] = s.ShapeType\n"
        "        try:\n"
        "            o['volume'] = round(s.Volume, 4)\n"
        "        except Exception:\n"
        "            pass\n"
        "        try:\n"
        "            o['area'] = round(s.Area, 4)\n"
        "        except Exception:\n"
        "            pass\n"
        "        bb = s.BoundBox\n"
        "        o['bounding_box'] = {\n"
        "            'x_min': round(bb.XMin, 4), 'x_max': round(bb.XMax, 4),\n"
        "            'y_min': round(bb.YMin, 4), 'y_max': round(bb.YMax, 4),\n"
        "            'z_min': round(bb.ZMin, 4), 'z_max': round(bb.ZMax, 4),\n"
        "        }\n"
        "    _cli_result['objects'].append(o)\n"
    )
    return run_script(script)


def _build_project_script(project: dict[str, Any]) -> str:
    """Build a FreeCAD Python script that recreates all project objects.

    Args:
        project: Project dict with objects.

    Returns:
        Python script string.
    """
    name = project.get("name", "Untitled")
    script = (
        "import FreeCAD\n"
        "import Part\n"
        f"doc = FreeCAD.newDocument({name!r})\n"
    )

    for obj in project.get("objects", []):
        script += _object_to_script(obj)

    script += "doc.recompute()\n"
    return script


def _placement_script(params: dict[str, Any]) -> str:
    """Generate FreeCAD Placement code if placement is present in params."""
    placement = params.get("placement")
    if not placement:
        return ""
    px = placement.get("x", 0)
    py = placement.get("y", 0)
    pz = placement.get("z", 0)
    return f"_obj.Placement = FreeCAD.Placement(FreeCAD.Vector({px}, {py}, {pz}), FreeCAD.Rotation(0,0,0,1))\n"


def _object_to_script(obj: dict[str, Any]) -> str:
    """Convert a project object dict to FreeCAD Python code.

    Args:
        obj: Object dict with type and parameters.

    Returns:
        Python code string.
    """
    obj_type = obj.get("type", "")
    name = obj.get("name", "Shape")
    params = obj.get("params", {})

    if obj_type == "Part::Box":
        l = params.get("length", 10)
        w = params.get("width", 10)
        h = params.get("height", 10)
        return (
            f"_obj = doc.addObject('Part::Box', {name!r})\n"
            f"_obj.Length = {l}\n"
            f"_obj.Width = {w}\n"
            f"_obj.Height = {h}\n"
        ) + _placement_script(params)
    elif obj_type == "Part::Cylinder":
        r = params.get("radius", 5)
        h = params.get("height", 10)
        a = params.get("angle", 360)
        return (
            f"_obj = doc.addObject('Part::Cylinder', {name!r})\n"
            f"_obj.Radius = {r}\n"
            f"_obj.Height = {h}\n"
            f"_obj.Angle = {a}\n"
        ) + _placement_script(params)
    elif obj_type == "Part::Sphere":
        r = params.get("radius", 5)
        return (
            f"_obj = doc.addObject('Part::Sphere', {name!r})\n"
            f"_obj.Radius = {r}\n"
        ) + _placement_script(params)
    elif obj_type == "Part::Cone":
        r1 = params.get("radius1", 5)
        r2 = params.get("radius2", 2)
        h = params.get("height", 10)
        return (
            f"_obj = doc.addObject('Part::Cone', {name!r})\n"
            f"_obj.Radius1 = {r1}\n"
            f"_obj.Radius2 = {r2}\n"
            f"_obj.Height = {h}\n"
        ) + _placement_script(params)
    elif obj_type == "Part::Torus":
        r1 = params.get("radius1", 10)
        r2 = params.get("radius2", 2)
        return (
            f"_obj = doc.addObject('Part::Torus', {name!r})\n"
            f"_obj.Radius1 = {r1}\n"
            f"_obj.Radius2 = {r2}\n"
        ) + _placement_script(params)
    elif obj_type == "Part::Fuse":
        base = params.get("base")
        tool = params.get("tool")
        return (
            f"_obj = doc.addObject('Part::Fuse', {name!r})\n"
            f"_obj.Base = doc.getObject({base!r})\n"
            f"_obj.Tool = doc.getObject({tool!r})\n"
        )
    elif obj_type == "Part::Cut":
        base = params.get("base")
        tool = params.get("tool")
        return (
            f"_obj = doc.addObject('Part::Cut', {name!r})\n"
            f"_obj.Base = doc.getObject({base!r})\n"
            f"_obj.Tool = doc.getObject({tool!r})\n"
        )
    elif obj_type == "Part::Common":
        base = params.get("base")
        tool = params.get("tool")
        return (
            f"_obj = doc.addObject('Part::Common', {name!r})\n"
            f"_obj.Base = doc.getObject({base!r})\n"
            f"_obj.Tool = doc.getObject({tool!r})\n"
        )
    elif obj_type == "Part::Fillet":
        base = params.get("base")
        radius = params.get("radius", 1)
        return (
            f"doc.recompute()\n"
            f"_base = doc.getObject({base!r})\n"
            f"_obj = doc.addObject('Part::Fillet', {name!r})\n"
            f"_obj.Base = _base\n"
            f"_edges = [(i+1, {radius}, {radius}) for i in range(len(_base.Shape.Edges))]\n"
            f"_obj.Shape = _base.Shape.makeFillet({radius}, _base.Shape.Edges)\n"
        )
    elif obj_type == "Part::Chamfer":
        base = params.get("base")
        size = params.get("size", 1)
        return (
            f"doc.recompute()\n"
            f"_base = doc.getObject({base!r})\n"
            f"_obj = doc.addObject('Part::Chamfer', {name!r})\n"
            f"_obj.Base = _base\n"
            f"_edges = [(i+1, {size}, {size}) for i in range(len(_base.Shape.Edges))]\n"
            f"_obj.Shape = _base.Shape.makeChamfer({size}, _base.Shape.Edges)\n"
        )
    elif obj_type == "Part::Revolution":
        source = params.get("source")
        axis_x = params.get("axis_x", 0)
        axis_y = params.get("axis_y", 0)
        axis_z = params.get("axis_z", 1)
        base_x = params.get("base_x", 0)
        base_y = params.get("base_y", 0)
        base_z = params.get("base_z", 0)
        angle = params.get("angle", 360)
        return (
            f"_obj = doc.addObject('Part::Revolution', {name!r})\n"
            f"_obj.Source = doc.getObject({source!r})\n"
            f"_obj.Axis = FreeCAD.Vector({axis_x}, {axis_y}, {axis_z})\n"
            f"_obj.Base = FreeCAD.Vector({base_x}, {base_y}, {base_z})\n"
            f"_obj.Angle = {angle}\n"
        )
    elif obj_type == "Part::Sweep":
        profile = params.get("profile")
        path = params.get("path")
        solid = params.get("solid", True)
        frenet = params.get("frenet", True)
        return (
            f"doc.recompute()\n"
            f"_profile = doc.getObject({profile!r})\n"
            f"_path = doc.getObject({path!r})\n"
            f"_sweep = doc.addObject('Part::Sweep', {name!r})\n"
            f"_sweep.Sections = [_profile]\n"
            f"_sweep.Spine = (_path, ['Edge1'])\n"
            f"_sweep.Solid = {solid}\n"
            f"_sweep.Frenet = {frenet}\n"
        )
    elif obj_type == "Part::Extrusion":
        base = params.get("base")
        dx = params.get("dx", 0)
        dy = params.get("dy", 0)
        dz = params.get("dz", 10)
        return (
            f"_obj = doc.addObject('Part::Extrusion', {name!r})\n"
            f"_obj.Base = doc.getObject({base!r})\n"
            f"_obj.Dir = FreeCAD.Vector({dx}, {dy}, {dz})\n"
        )
    elif obj_type == "Sketcher::SketchObject":
        plane = params.get("plane", "XY")
        geometry = params.get("geometry", [])
        constraints = params.get("constraints", [])
        script = (
            f"import Sketcher\n"
            f"_obj = doc.addObject('Sketcher::SketchObject', {name!r})\n"
        )
        if plane == "XY":
            script += "_obj.Placement = FreeCAD.Placement(FreeCAD.Vector(0,0,0), FreeCAD.Rotation(0,0,0,1))\n"
        elif plane == "XZ":
            script += "_obj.Placement = FreeCAD.Placement(FreeCAD.Vector(0,0,0), FreeCAD.Rotation(FreeCAD.Vector(1,0,0), -90))\n"
        elif plane == "YZ":
            script += "_obj.Placement = FreeCAD.Placement(FreeCAD.Vector(0,0,0), FreeCAD.Rotation(FreeCAD.Vector(0,1,0), 90))\n"

        for geom in geometry:
            script += _sketch_geometry_to_script(geom)

        for con in constraints:
            script += _sketch_constraint_to_script(con)

        return script
    elif obj_type == "Mesh::Import":
        filepath = params.get("filepath", "")
        return (
            f"import Mesh\n"
            f"Mesh.insert({filepath!r}, doc.Name)\n"
        )
    else:
        return f"# Unknown object type: {obj_type}\n"


def _sketch_geometry_to_script(geom: dict[str, Any]) -> str:
    """Convert sketch geometry dict to FreeCAD Python code."""
    gtype = geom.get("type", "")

    if gtype == "line":
        x1, y1 = geom.get("x1", 0), geom.get("y1", 0)
        x2, y2 = geom.get("x2", 10), geom.get("y2", 0)
        return (
            f"_obj.addGeometry(Part.LineSegment("
            f"FreeCAD.Vector({x1},{y1},0), "
            f"FreeCAD.Vector({x2},{y2},0)))\n"
        )
    elif gtype == "circle":
        cx, cy = geom.get("cx", 0), geom.get("cy", 0)
        r = geom.get("radius", 5)
        return (
            f"_obj.addGeometry(Part.Circle("
            f"FreeCAD.Vector({cx},{cy},0), "
            f"FreeCAD.Vector(0,0,1), {r}))\n"
        )
    elif gtype == "arc":
        cx, cy = geom.get("cx", 0), geom.get("cy", 0)
        r = geom.get("radius", 5)
        a1 = geom.get("start_angle", 0)
        a2 = geom.get("end_angle", 90)
        import math
        a1_rad = math.radians(a1)
        a2_rad = math.radians(a2)
        return (
            f"import math\n"
            f"_obj.addGeometry(Part.ArcOfCircle("
            f"Part.Circle(FreeCAD.Vector({cx},{cy},0), "
            f"FreeCAD.Vector(0,0,1), {r}), "
            f"{a1_rad}, {a2_rad}))\n"
        )
    elif gtype == "rect":
        x, y = geom.get("x", 0), geom.get("y", 0)
        w, h = geom.get("width", 10), geom.get("height", 10)
        return (
            f"_gi = _obj.GeometryCount\n"
            f"_obj.addGeometry(Part.LineSegment(FreeCAD.Vector({x},{y},0), FreeCAD.Vector({x+w},{y},0)))\n"
            f"_obj.addGeometry(Part.LineSegment(FreeCAD.Vector({x+w},{y},0), FreeCAD.Vector({x+w},{y+h},0)))\n"
            f"_obj.addGeometry(Part.LineSegment(FreeCAD.Vector({x+w},{y+h},0), FreeCAD.Vector({x},{y+h},0)))\n"
            f"_obj.addGeometry(Part.LineSegment(FreeCAD.Vector({x},{y+h},0), FreeCAD.Vector({x},{y},0)))\n"
            f"_obj.addConstraint(Sketcher.Constraint('Coincident', _gi, 2, _gi+1, 1))\n"
            f"_obj.addConstraint(Sketcher.Constraint('Coincident', _gi+1, 2, _gi+2, 1))\n"
            f"_obj.addConstraint(Sketcher.Constraint('Coincident', _gi+2, 2, _gi+3, 1))\n"
            f"_obj.addConstraint(Sketcher.Constraint('Coincident', _gi+3, 2, _gi, 1))\n"
            f"_obj.addConstraint(Sketcher.Constraint('Horizontal', _gi))\n"
            f"_obj.addConstraint(Sketcher.Constraint('Vertical', _gi+1))\n"
            f"_obj.addConstraint(Sketcher.Constraint('Horizontal', _gi+2))\n"
            f"_obj.addConstraint(Sketcher.Constraint('Vertical', _gi+3))\n"
        )
    return f"# Unknown sketch geometry: {gtype}\n"


def _sketch_constraint_to_script(con: dict[str, Any]) -> str:
    """Convert sketch constraint dict to FreeCAD Python code."""
    ctype = con.get("type", "")
    geom = con.get("geometry", 0)
    value = con.get("value")

    if ctype in ("Horizontal", "Vertical"):
        return f"_obj.addConstraint(Sketcher.Constraint({ctype!r}, {geom}))\n"
    elif ctype == "Distance":
        if value is not None:
            return f"_obj.addConstraint(Sketcher.Constraint('Distance', {geom}, {value}))\n"
    elif ctype == "Radius":
        if value is not None:
            return f"_obj.addConstraint(Sketcher.Constraint('Radius', {geom}, {value}))\n"
    elif ctype == "Coincident":
        g2 = con.get("geometry2", 0)
        p1 = con.get("point1", 1)
        p2 = con.get("point2", 1)
        return f"_obj.addConstraint(Sketcher.Constraint('Coincident', {geom}, {p1}, {g2}, {p2}))\n"
    elif ctype == "Parallel":
        g2 = con.get("geometry2", 0)
        return f"_obj.addConstraint(Sketcher.Constraint('Parallel', {geom}, {g2}))\n"
    elif ctype == "Perpendicular":
        g2 = con.get("geometry2", 0)
        return f"_obj.addConstraint(Sketcher.Constraint('Perpendicular', {geom}, {g2}))\n"
    elif ctype == "Equal":
        g2 = con.get("geometry2", 0)
        return f"_obj.addConstraint(Sketcher.Constraint('Equal', {geom}, {g2}))\n"
    elif ctype == "Angle":
        if value is not None:
            import math
            val_rad = math.radians(value)
            return f"_obj.addConstraint(Sketcher.Constraint('Angle', {geom}, {val_rad}))\n"

    return f"# Unknown constraint: {ctype}\n"
