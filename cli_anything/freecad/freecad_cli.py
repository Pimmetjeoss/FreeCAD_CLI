"""cli-anything FreeCAD — CLI harness for FreeCAD parametric 3D CAD.

Provides both one-shot subcommands and an interactive REPL for
creating, modifying, and exporting 3D models via the real FreeCAD backend.

Usage:
    cli-anything-freecad                          # Enter REPL
    cli-anything-freecad project new -o proj.json  # One-shot command
    cli-anything-freecad --json part box -l 20     # JSON output
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any

import click

from cli_anything.freecad import __version__
from cli_anything.freecad.core.session import Session

# Global session (shared across commands in REPL mode)
_session = Session()

# Whether to output JSON
_json_mode = False


def _output(data: dict[str, Any], human_message: str = "") -> None:
    """Output data in JSON or human-readable format."""
    if _json_mode:
        click.echo(json.dumps(data, indent=2, default=str))
    elif human_message:
        click.echo(human_message)


def _ensure_project() -> dict[str, Any]:
    """Ensure a project is open, raise error if not."""
    if not _session.has_project:
        msg = "No project open. Use 'project new' or 'project open' first."
        if _json_mode:
            click.echo(json.dumps({"error": msg}))
            sys.exit(1)
        else:
            raise click.ClickException(msg)
    return _session.project


# ── Main CLI group ───────────────────────────────────────────────────

@click.group(invoke_without_command=True)
@click.option("--json", "json_output", is_flag=True, help="Output in JSON format")
@click.option("--project", "project_path", type=click.Path(), help="Load project file")
@click.option("--version", is_flag=True, help="Show version")
@click.pass_context
def cli(ctx: click.Context, json_output: bool, project_path: str | None, version: bool) -> None:
    """cli-anything-freecad — CLI harness for FreeCAD 3D CAD."""
    global _json_mode
    _json_mode = json_output

    if version:
        if json_output:
            click.echo(json.dumps({"version": __version__, "software": "FreeCAD"}))
        else:
            click.echo(f"cli-anything-freecad v{__version__}")
        ctx.exit(0)

    if project_path:
        try:
            _session.open_project(project_path)
        except FileNotFoundError:
            raise click.ClickException(f"Project file not found: {project_path}")

    if ctx.invoked_subcommand is None:
        ctx.invoke(repl, project_path=None)


# ── Project commands ─────────────────────────────────────────────────

@cli.group()
def project() -> None:
    """Project management commands."""
    pass


@project.command("new")
@click.option("-n", "--name", default="Untitled", help="Project name")
@click.option("-o", "--output", "output_path", type=click.Path(), help="Output project JSON path")
def project_new(name: str, output_path: str | None) -> None:
    """Create a new FreeCAD project."""
    proj = _session.new_project(name=name, path=output_path)
    _output(proj, f"Created project '{name}'")
    if output_path and not _json_mode:
        click.echo(f"  Saved to: {output_path}")


@project.command("open")
@click.argument("path", type=click.Path(exists=True))
def project_open(path: str) -> None:
    """Open an existing project file."""
    proj = _session.open_project(path)
    name = proj.get("name", "Untitled")
    count = len(proj.get("objects", []))
    _output(proj, f"Opened '{name}' ({count} objects)")


@project.command("save")
@click.option("-o", "--output", "output_path", type=click.Path(), help="Save path (optional)")
def project_save(output_path: str | None) -> None:
    """Save current project."""
    _ensure_project()
    path = _session.save(output_path)
    _output({"saved": path}, f"Project saved to: {path}")


@project.command("save-fcstd")
@click.argument("path", type=click.Path())
@click.option("--overwrite", is_flag=True, help="Overwrite existing file")
def project_save_fcstd(path: str, overwrite: bool) -> None:
    """Save project as FreeCAD .FCStd file."""
    proj = _ensure_project()
    if os.path.exists(path) and not overwrite:
        raise click.ClickException(f"File exists: {path}. Use --overwrite.")
    from cli_anything.freecad.core.project import save_fcstd
    result = save_fcstd(proj, path)
    if result.get("success"):
        r = result.get("result", {})
        _output(r, f"Saved FCStd: {path} ({r.get('object_count', 0)} objects)")
    else:
        err = result.get("result", {}).get("error", "Save failed")
        raise click.ClickException(err)


@project.command("info")
def project_info() -> None:
    """Show project information."""
    proj = _ensure_project()
    from cli_anything.freecad.core.project import get_project_info
    info = get_project_info(proj)
    _output(info)
    if not _json_mode:
        click.echo(f"Project: {info['name']}")
        click.echo(f"Objects: {info['object_count']}")
        click.echo(f"Modified: {info['modified']}")
        if info["objects"]:
            click.echo("\nObject tree:")
            for obj in info["objects"]:
                click.echo(f"  - {obj['name']} ({obj['type']})")


@project.command("inspect")
@click.argument("path", type=click.Path(exists=True))
def project_inspect(path: str) -> None:
    """Inspect a .FCStd file without opening it as project."""
    from cli_anything.freecad.core.project import inspect_fcstd
    result = inspect_fcstd(path)
    if result.get("success"):
        r = result.get("result", {})
        _output(r)
        if not _json_mode:
            click.echo(f"Document: {r.get('label', r.get('name', '?'))}")
            click.echo(f"Objects: {r.get('object_count', 0)}")
            for obj in r.get("objects", []):
                line = f"  - {obj['name']} [{obj['type']}]"
                if "volume" in obj:
                    line += f" vol={obj['volume']}"
                if "area" in obj:
                    line += f" area={obj['area']}"
                click.echo(line)
    else:
        err = result.get("result", {}).get("error", "Inspect failed")
        raise click.ClickException(err)


# ── Part commands ────────────────────────────────────────────────────

@cli.group()
def part() -> None:
    """3D solid modeling commands (Part workbench)."""
    pass


def _next_name(prefix: str) -> str:
    """Generate a unique object name."""
    if not _session.has_project:
        return prefix
    existing = {o.get("name") for o in _session.project.get("objects", [])}
    if prefix not in existing:
        return prefix
    i = 1
    while f"{prefix}{i:03d}" in existing:
        i += 1
    return f"{prefix}{i:03d}"


@part.command("box")
@click.option("-l", "--length", type=float, default=10, help="Length (X)")
@click.option("-w", "--width", type=float, default=10, help="Width (Y)")
@click.option("-H", "--height", type=float, default=10, help="Height (Z)")
@click.option("--px", type=float, default=0, help="Position X")
@click.option("--py", type=float, default=0, help="Position Y")
@click.option("--pz", type=float, default=0, help="Position Z")
@click.option("-n", "--name", default=None, help="Object name")
def part_box(length: float, width: float, height: float, px: float, py: float, pz: float, name: str | None) -> None:
    """Create a box primitive."""
    _ensure_project()
    name = name or _next_name("Box")
    params: dict[str, Any] = {"length": length, "width": width, "height": height}
    if px != 0 or py != 0 or pz != 0:
        params["placement"] = {"x": px, "y": py, "z": pz}
    obj = {
        "name": name,
        "type": "Part::Box",
        "label": name,
        "params": params,
    }
    _session.add_object(obj, f"add box '{name}'")
    pos_str = f" at ({px}, {py}, {pz})" if (px or py or pz) else ""
    _output(obj, f"Created box '{name}' ({length} x {width} x {height}){pos_str}")


@part.command("cylinder")
@click.option("-r", "--radius", type=float, default=5, help="Radius")
@click.option("-H", "--height", type=float, default=10, help="Height")
@click.option("-a", "--angle", type=float, default=360, help="Angle (degrees)")
@click.option("--px", type=float, default=0, help="Position X")
@click.option("--py", type=float, default=0, help="Position Y")
@click.option("--pz", type=float, default=0, help="Position Z")
@click.option("-n", "--name", default=None, help="Object name")
def part_cylinder(radius: float, height: float, angle: float, px: float, py: float, pz: float, name: str | None) -> None:
    """Create a cylinder primitive."""
    _ensure_project()
    name = name or _next_name("Cylinder")
    params: dict[str, Any] = {"radius": radius, "height": height, "angle": angle}
    if px != 0 or py != 0 or pz != 0:
        params["placement"] = {"x": px, "y": py, "z": pz}
    obj = {
        "name": name,
        "type": "Part::Cylinder",
        "label": name,
        "params": params,
    }
    _session.add_object(obj, f"add cylinder '{name}'")
    pos_str = f" at ({px}, {py}, {pz})" if (px or py or pz) else ""
    _output(obj, f"Created cylinder '{name}' (r={radius}, h={height}){pos_str}")


@part.command("sphere")
@click.option("-r", "--radius", type=float, default=5, help="Radius")
@click.option("--px", type=float, default=0, help="Position X")
@click.option("--py", type=float, default=0, help="Position Y")
@click.option("--pz", type=float, default=0, help="Position Z")
@click.option("-n", "--name", default=None, help="Object name")
def part_sphere(radius: float, px: float, py: float, pz: float, name: str | None) -> None:
    """Create a sphere primitive."""
    _ensure_project()
    name = name or _next_name("Sphere")
    params: dict[str, Any] = {"radius": radius}
    if px != 0 or py != 0 or pz != 0:
        params["placement"] = {"x": px, "y": py, "z": pz}
    obj = {
        "name": name,
        "type": "Part::Sphere",
        "label": name,
        "params": params,
    }
    _session.add_object(obj, f"add sphere '{name}'")
    pos_str = f" at ({px}, {py}, {pz})" if (px or py or pz) else ""
    _output(obj, f"Created sphere '{name}' (r={radius}){pos_str}")


@part.command("cone")
@click.option("-r1", "--radius1", type=float, default=5, help="Bottom radius")
@click.option("-r2", "--radius2", type=float, default=2, help="Top radius")
@click.option("-H", "--height", type=float, default=10, help="Height")
@click.option("--px", type=float, default=0, help="Position X")
@click.option("--py", type=float, default=0, help="Position Y")
@click.option("--pz", type=float, default=0, help="Position Z")
@click.option("-n", "--name", default=None, help="Object name")
def part_cone(radius1: float, radius2: float, height: float, px: float, py: float, pz: float, name: str | None) -> None:
    """Create a cone primitive."""
    _ensure_project()
    name = name or _next_name("Cone")
    params: dict[str, Any] = {"radius1": radius1, "radius2": radius2, "height": height}
    if px != 0 or py != 0 or pz != 0:
        params["placement"] = {"x": px, "y": py, "z": pz}
    obj = {
        "name": name,
        "type": "Part::Cone",
        "label": name,
        "params": params,
    }
    _session.add_object(obj, f"add cone '{name}'")
    pos_str = f" at ({px}, {py}, {pz})" if (px or py or pz) else ""
    _output(obj, f"Created cone '{name}' (r1={radius1}, r2={radius2}, h={height}){pos_str}")


@part.command("torus")
@click.option("-r1", "--radius1", type=float, default=10, help="Major radius")
@click.option("-r2", "--radius2", type=float, default=2, help="Minor radius")
@click.option("--px", type=float, default=0, help="Position X")
@click.option("--py", type=float, default=0, help="Position Y")
@click.option("--pz", type=float, default=0, help="Position Z")
@click.option("-n", "--name", default=None, help="Object name")
def part_torus(radius1: float, radius2: float, px: float, py: float, pz: float, name: str | None) -> None:
    """Create a torus primitive."""
    _ensure_project()
    name = name or _next_name("Torus")
    params: dict[str, Any] = {"radius1": radius1, "radius2": radius2}
    if px != 0 or py != 0 or pz != 0:
        params["placement"] = {"x": px, "y": py, "z": pz}
    obj = {
        "name": name,
        "type": "Part::Torus",
        "label": name,
        "params": params,
    }
    _session.add_object(obj, f"add torus '{name}'")
    pos_str = f" at ({px}, {py}, {pz})" if (px or py or pz) else ""
    _output(obj, f"Created torus '{name}' (R={radius1}, r={radius2}){pos_str}")


@part.command("fuse")
@click.argument("base")
@click.argument("tool")
@click.option("-n", "--name", default=None, help="Result name")
def part_fuse(base: str, tool: str, name: str | None) -> None:
    """Boolean union of two objects."""
    proj = _ensure_project()
    if not _session.get_object(base):
        raise click.ClickException(f"Object not found: {base}")
    if not _session.get_object(tool):
        raise click.ClickException(f"Object not found: {tool}")
    name = name or _next_name("Fuse")
    obj = {
        "name": name,
        "type": "Part::Fuse",
        "label": name,
        "params": {"base": base, "tool": tool},
    }
    _session.add_object(obj, f"fuse '{base}' + '{tool}'")
    _output(obj, f"Created fuse '{name}' ({base} + {tool})")


@part.command("cut")
@click.argument("base")
@click.argument("tool")
@click.option("-n", "--name", default=None, help="Result name")
def part_cut(base: str, tool: str, name: str | None) -> None:
    """Boolean subtraction (base - tool)."""
    proj = _ensure_project()
    if not _session.get_object(base):
        raise click.ClickException(f"Object not found: {base}")
    if not _session.get_object(tool):
        raise click.ClickException(f"Object not found: {tool}")
    name = name or _next_name("Cut")
    obj = {
        "name": name,
        "type": "Part::Cut",
        "label": name,
        "params": {"base": base, "tool": tool},
    }
    _session.add_object(obj, f"cut '{base}' - '{tool}'")
    _output(obj, f"Created cut '{name}' ({base} - {tool})")


@part.command("common")
@click.argument("base")
@click.argument("tool")
@click.option("-n", "--name", default=None, help="Result name")
def part_common(base: str, tool: str, name: str | None) -> None:
    """Boolean intersection of two objects."""
    proj = _ensure_project()
    if not _session.get_object(base):
        raise click.ClickException(f"Object not found: {base}")
    if not _session.get_object(tool):
        raise click.ClickException(f"Object not found: {tool}")
    name = name or _next_name("Common")
    obj = {
        "name": name,
        "type": "Part::Common",
        "label": name,
        "params": {"base": base, "tool": tool},
    }
    _session.add_object(obj, f"common '{base}' & '{tool}'")
    _output(obj, f"Created common '{name}' ({base} & {tool})")


@part.command("fillet")
@click.argument("base")
@click.option("-r", "--radius", type=float, default=1, help="Fillet radius")
@click.option("-n", "--name", default=None, help="Result name")
def part_fillet(base: str, radius: float, name: str | None) -> None:
    """Fillet all edges of an object."""
    proj = _ensure_project()
    if not _session.get_object(base):
        raise click.ClickException(f"Object not found: {base}")
    name = name or _next_name("Fillet")
    obj = {
        "name": name,
        "type": "Part::Fillet",
        "label": name,
        "params": {"base": base, "radius": radius},
    }
    _session.add_object(obj, f"fillet '{base}' r={radius}")
    _output(obj, f"Created fillet '{name}' on '{base}' (r={radius})")


@part.command("chamfer")
@click.argument("base")
@click.option("-s", "--size", type=float, default=1, help="Chamfer size")
@click.option("-n", "--name", default=None, help="Result name")
def part_chamfer(base: str, size: float, name: str | None) -> None:
    """Chamfer all edges of an object."""
    proj = _ensure_project()
    if not _session.get_object(base):
        raise click.ClickException(f"Object not found: {base}")
    name = name or _next_name("Chamfer")
    obj = {
        "name": name,
        "type": "Part::Chamfer",
        "label": name,
        "params": {"base": base, "size": size},
    }
    _session.add_object(obj, f"chamfer '{base}' s={size}")
    _output(obj, f"Created chamfer '{name}' on '{base}' (s={size})")


@part.command("list")
def part_list() -> None:
    """List all objects in the project."""
    _ensure_project()
    objects = _session.list_objects()
    _output({"objects": objects})
    if not _json_mode:
        if not objects:
            click.echo("No objects in project")
        else:
            for obj in objects:
                click.echo(f"  {obj['name']:<20} {obj['type']}")


@part.command("remove")
@click.argument("name")
def part_remove(name: str) -> None:
    """Remove an object from the project."""
    _ensure_project()
    removed = _session.remove_object(name)
    if removed:
        _output(removed, f"Removed '{name}'")
    else:
        raise click.ClickException(f"Object not found: {name}")


@part.command("move")
@click.argument("name")
@click.option("--px", type=float, required=True, help="New position X")
@click.option("--py", type=float, required=True, help="New position Y")
@click.option("--pz", type=float, required=True, help="New position Z")
def part_move(name: str, px: float, py: float, pz: float) -> None:
    """Move an object to a new position."""
    _ensure_project()
    obj = _session.get_object(name)
    if not obj:
        raise click.ClickException(f"Object not found: {name}")
    _session.checkpoint(f"move '{name}'")
    obj["params"]["placement"] = {"x": px, "y": py, "z": pz}
    _session._auto_save()
    _output(obj, f"Moved '{name}' to ({px}, {py}, {pz})")


# ── Sketch commands ──────────────────────────────────────────────────

@cli.group()
def sketch() -> None:
    """2D sketch commands (Sketcher workbench)."""
    pass


@sketch.command("new")
@click.option("-p", "--plane", type=click.Choice(["XY", "XZ", "YZ"]), default="XY", help="Sketch plane")
@click.option("-n", "--name", default=None, help="Sketch name")
def sketch_new(plane: str, name: str | None) -> None:
    """Create a new sketch on a plane."""
    _ensure_project()
    name = name or _next_name("Sketch")
    obj = {
        "name": name,
        "type": "Sketcher::SketchObject",
        "label": name,
        "params": {"plane": plane, "geometry": [], "constraints": []},
    }
    _session.add_object(obj, f"add sketch '{name}' on {plane}")
    _output(obj, f"Created sketch '{name}' on {plane} plane")


@sketch.command("line")
@click.argument("sketch_name")
@click.option("--x1", type=float, default=0, help="Start X")
@click.option("--y1", type=float, default=0, help="Start Y")
@click.option("--x2", type=float, default=10, help="End X")
@click.option("--y2", type=float, default=0, help="End Y")
def sketch_line(sketch_name: str, x1: float, y1: float, x2: float, y2: float) -> None:
    """Add a line to a sketch."""
    _ensure_project()
    sketch_obj = _session.get_object(sketch_name)
    if not sketch_obj or sketch_obj.get("type") != "Sketcher::SketchObject":
        raise click.ClickException(f"Sketch not found: {sketch_name}")
    _session.checkpoint(f"add line to '{sketch_name}'")
    geom = {"type": "line", "x1": x1, "y1": y1, "x2": x2, "y2": y2}
    sketch_obj["params"]["geometry"].append(geom)
    _output(geom, f"Added line ({x1},{y1}) -> ({x2},{y2}) to '{sketch_name}'")


@sketch.command("circle")
@click.argument("sketch_name")
@click.option("--cx", type=float, default=0, help="Center X")
@click.option("--cy", type=float, default=0, help="Center Y")
@click.option("-r", "--radius", type=float, default=5, help="Radius")
def sketch_circle(sketch_name: str, cx: float, cy: float, radius: float) -> None:
    """Add a circle to a sketch."""
    _ensure_project()
    sketch_obj = _session.get_object(sketch_name)
    if not sketch_obj or sketch_obj.get("type") != "Sketcher::SketchObject":
        raise click.ClickException(f"Sketch not found: {sketch_name}")
    _session.checkpoint(f"add circle to '{sketch_name}'")
    geom = {"type": "circle", "cx": cx, "cy": cy, "radius": radius}
    sketch_obj["params"]["geometry"].append(geom)
    _output(geom, f"Added circle ({cx},{cy}) r={radius} to '{sketch_name}'")


@sketch.command("rect")
@click.argument("sketch_name")
@click.option("--x", type=float, default=0, help="Origin X")
@click.option("--y", type=float, default=0, help="Origin Y")
@click.option("-w", "--width", type=float, default=10, help="Width")
@click.option("-H", "--height", type=float, default=10, help="Height")
def sketch_rect(sketch_name: str, x: float, y: float, width: float, height: float) -> None:
    """Add a rectangle to a sketch (4 lines + constraints)."""
    _ensure_project()
    sketch_obj = _session.get_object(sketch_name)
    if not sketch_obj or sketch_obj.get("type") != "Sketcher::SketchObject":
        raise click.ClickException(f"Sketch not found: {sketch_name}")
    _session.checkpoint(f"add rect to '{sketch_name}'")
    geom = {"type": "rect", "x": x, "y": y, "width": width, "height": height}
    sketch_obj["params"]["geometry"].append(geom)
    _output(geom, f"Added rectangle ({x},{y}) {width}x{height} to '{sketch_name}'")


@sketch.command("arc")
@click.argument("sketch_name")
@click.option("--cx", type=float, default=0, help="Center X")
@click.option("--cy", type=float, default=0, help="Center Y")
@click.option("-r", "--radius", type=float, default=5, help="Radius")
@click.option("--start", "start_angle", type=float, default=0, help="Start angle (degrees)")
@click.option("--end", "end_angle", type=float, default=90, help="End angle (degrees)")
def sketch_arc(sketch_name: str, cx: float, cy: float, radius: float, start_angle: float, end_angle: float) -> None:
    """Add an arc to a sketch."""
    _ensure_project()
    sketch_obj = _session.get_object(sketch_name)
    if not sketch_obj or sketch_obj.get("type") != "Sketcher::SketchObject":
        raise click.ClickException(f"Sketch not found: {sketch_name}")
    _session.checkpoint(f"add arc to '{sketch_name}'")
    geom = {"type": "arc", "cx": cx, "cy": cy, "radius": radius, "start_angle": start_angle, "end_angle": end_angle}
    sketch_obj["params"]["geometry"].append(geom)
    _output(geom, f"Added arc ({cx},{cy}) r={radius} {start_angle}-{end_angle} deg to '{sketch_name}'")


@sketch.command("constrain")
@click.argument("sketch_name")
@click.option("-t", "--type", "ctype", required=True, help="Constraint type (Horizontal, Vertical, Distance, Radius, etc.)")
@click.option("-g", "--geometry", "geom_idx", type=int, default=0, help="Geometry index")
@click.option("-v", "--value", type=float, default=None, help="Constraint value (for dimensional constraints)")
@click.option("-g2", "--geometry2", type=int, default=None, help="Second geometry index (for relational constraints)")
def sketch_constrain(sketch_name: str, ctype: str, geom_idx: int, value: float | None, geometry2: int | None) -> None:
    """Add a constraint to a sketch."""
    _ensure_project()
    sketch_obj = _session.get_object(sketch_name)
    if not sketch_obj or sketch_obj.get("type") != "Sketcher::SketchObject":
        raise click.ClickException(f"Sketch not found: {sketch_name}")
    _session.checkpoint(f"add constraint to '{sketch_name}'")
    con = {"type": ctype, "geometry": geom_idx}
    if value is not None:
        con["value"] = value
    if geometry2 is not None:
        con["geometry2"] = geometry2
    sketch_obj["params"]["constraints"].append(con)
    _output(con, f"Added constraint {ctype} to '{sketch_name}'")


@sketch.command("list")
@click.argument("sketch_name")
def sketch_list(sketch_name: str) -> None:
    """List geometry and constraints of a sketch."""
    _ensure_project()
    sketch_obj = _session.get_object(sketch_name)
    if not sketch_obj or sketch_obj.get("type") != "Sketcher::SketchObject":
        raise click.ClickException(f"Sketch not found: {sketch_name}")
    params = sketch_obj.get("params", {})
    data = {
        "sketch": sketch_name,
        "plane": params.get("plane", "XY"),
        "geometry": params.get("geometry", []),
        "constraints": params.get("constraints", []),
    }
    _output(data)
    if not _json_mode:
        click.echo(f"Sketch: {sketch_name} (plane: {data['plane']})")
        click.echo(f"Geometry ({len(data['geometry'])}):")
        for i, g in enumerate(data["geometry"]):
            click.echo(f"  [{i}] {g['type']}: {g}")
        click.echo(f"Constraints ({len(data['constraints'])}):")
        for i, c in enumerate(data["constraints"]):
            click.echo(f"  [{i}] {c['type']}: {c}")


# ── Mesh commands ────────────────────────────────────────────────────

@cli.group()
def mesh() -> None:
    """Mesh import/export commands."""
    pass


@mesh.command("import")
@click.argument("filepath", type=click.Path(exists=True))
@click.option("-n", "--name", default=None, help="Object name")
def mesh_import(filepath: str, name: str | None) -> None:
    """Import a mesh file (STL, OBJ, PLY)."""
    _ensure_project()
    name = name or _next_name("Mesh")
    filepath = os.path.abspath(filepath)
    obj = {
        "name": name,
        "type": "Mesh::Import",
        "label": name,
        "params": {"filepath": filepath},
    }
    _session.add_object(obj, f"import mesh '{filepath}'")
    _output(obj, f"Imported mesh '{name}' from {filepath}")


@mesh.command("from-part")
@click.argument("part_name")
@click.option("-n", "--name", default=None, help="Mesh object name")
def mesh_from_part(part_name: str, name: str | None) -> None:
    """Convert a Part object to mesh."""
    _ensure_project()
    part_obj = _session.get_object(part_name)
    if not part_obj:
        raise click.ClickException(f"Object not found: {part_name}")
    name = name or _next_name("Mesh")
    obj = {
        "name": name,
        "type": "Mesh::FromPart",
        "label": name,
        "params": {"source": part_name},
    }
    _session.add_object(obj, f"mesh from part '{part_name}'")
    _output(obj, f"Created mesh '{name}' from part '{part_name}'")


# ── Export commands ──────────────────────────────────────────────────

@cli.group()
def export() -> None:
    """Export commands."""
    pass


@export.command("render")
@click.argument("output_path", type=click.Path())
@click.option("-p", "--preset", type=click.Choice(["step", "iges", "stl", "obj", "brep", "fcstd"]),
              help="Export format preset")
@click.option("--overwrite", is_flag=True, help="Overwrite existing file")
@click.option("--objects", multiple=True, help="Specific objects to export")
def export_render(output_path: str, preset: str | None, overwrite: bool, objects: tuple[str, ...]) -> None:
    """Export project to file format via FreeCAD backend."""
    proj = _ensure_project()
    from cli_anything.freecad.core.export import export as do_export
    obj_names = list(objects) if objects else None
    result = do_export(proj, output_path, preset=preset, overwrite=overwrite, object_names=obj_names)
    _output(result)
    if not _json_mode:
        if result.get("success"):
            click.echo(f"Exported: {result['output']} ({result.get('file_size', 0):,} bytes)")
            click.echo(f"Format: {result.get('format', '?')}, Method: {result.get('method', '?')}")
        else:
            raise click.ClickException(result.get("error", "Export failed"))


@export.command("formats")
def export_formats() -> None:
    """List supported export formats."""
    from cli_anything.freecad.core.export import list_formats
    fmts = list_formats()
    _output({"formats": fmts})
    if not _json_mode:
        click.echo("Supported export formats:")
        for fmt in fmts:
            click.echo(f"  {fmt['name']:<8} {fmt['extensions']:<16} {fmt['description']}")


# Convenience export shortcuts
for _fmt in ["step", "stl", "obj", "iges", "brep"]:
    def _make_export_cmd(fmt_name):
        @export.command(fmt_name)
        @click.argument("output_path", type=click.Path())
        @click.option("--overwrite", is_flag=True, help="Overwrite existing file")
        def _cmd(output_path, overwrite, _fmt=fmt_name):
            f"""Export to {fmt_name.upper()} format."""
            proj = _ensure_project()
            from cli_anything.freecad.core.export import export as do_export
            result = do_export(proj, output_path, preset=_fmt, overwrite=overwrite)
            _output(result)
            if not _json_mode:
                if result.get("success"):
                    click.echo(f"Exported: {result['output']} ({result.get('file_size', 0):,} bytes)")
                else:
                    raise click.ClickException(result.get("error", "Export failed"))
        _cmd.__doc__ = f"Export to {fmt_name.upper()} format."
        return _cmd
    _make_export_cmd(_fmt)


# ── TechDraw commands ────────────────────────────────────────────────

@cli.group()
def techdraw() -> None:
    """TechDraw 2D fabrication drawing commands."""
    pass


@techdraw.command("page")
@click.option("-n", "--name", default=None, help="Page name")
@click.option("-t", "--template", default="A4_Landscape",
              type=click.Choice(["A4_Landscape", "A4_Portrait", "A3_Landscape",
                                 "A3_Portrait", "A2_Landscape", "A1_Landscape",
                                 "A0_Landscape"]),
              help="Paper size template")
@click.option("-s", "--scale", type=float, default=1.0, help="Drawing scale")
def techdraw_page(name: str | None, template: str, scale: float) -> None:
    """Create a TechDraw drawing page."""
    _ensure_project()
    from cli_anything.freecad.core.techdraw import create_drawing
    name = name or _next_name("Page")
    page_obj = create_drawing(_session.project, page_name=name, template=template, scale=scale)
    _session.add_object(page_obj, f"add drawing page '{name}'")
    _output(page_obj, f"Created drawing page '{name}' ({template}, scale={scale})")


@techdraw.command("view")
@click.argument("page_name")
@click.argument("source_name")
@click.option("-n", "--name", default=None, help="View name")
@click.option("-d", "--direction", default="front",
              type=click.Choice(["front", "back", "top", "bottom", "left", "right", "iso"]),
              help="View direction")
@click.option("-x", type=float, default=100, help="X position on page (mm)")
@click.option("-y", type=float, default=150, help="Y position on page (mm)")
@click.option("-r", "--rotation", type=float, default=0, help="View rotation (degrees)")
def techdraw_view(page_name: str, source_name: str, name: str | None,
                  direction: str, x: float, y: float, rotation: float) -> None:
    """Add a 2D view of a 3D object to a drawing page."""
    _ensure_project()
    from cli_anything.freecad.core.techdraw import add_view
    page_obj = _session.get_object(page_name)
    if not page_obj or page_obj.get("type") != "TechDraw::DrawPage":
        raise click.ClickException(f"Drawing page not found: {page_name}")
    if not _session.get_object(source_name):
        raise click.ClickException(f"Source object not found: {source_name}")
    name = name or _next_name("View")
    _session.checkpoint(f"add view '{name}' to page '{page_name}'")
    view = add_view(page_obj, source_name, view_name=name, direction=direction, x=x, y=y, rotation=rotation)
    _session.project["modified"] = True
    _session._auto_save()
    _output(view, f"Added {direction} view '{name}' of '{source_name}' to '{page_name}'")


@techdraw.command("projection")
@click.argument("page_name")
@click.argument("source_name")
@click.option("-n", "--name", default=None, help="Projection group name")
@click.option("-p", "--projections", multiple=True, default=["Front", "Top", "Right"],
              help="Projections to include (Front, Top, Right, Left, Rear, Bottom)")
@click.option("-x", type=float, default=150, help="X position on page (mm)")
@click.option("-y", type=float, default=150, help="Y position on page (mm)")
def techdraw_projection(page_name: str, source_name: str, name: str | None,
                        projections: tuple[str, ...], x: float, y: float) -> None:
    """Add a multi-view projection group to a drawing page."""
    _ensure_project()
    from cli_anything.freecad.core.techdraw import add_projection_group
    page_obj = _session.get_object(page_name)
    if not page_obj or page_obj.get("type") != "TechDraw::DrawPage":
        raise click.ClickException(f"Drawing page not found: {page_name}")
    if not _session.get_object(source_name):
        raise click.ClickException(f"Source object not found: {source_name}")
    name = name or _next_name("ProjGroup")
    _session.checkpoint(f"add projection group '{name}' to page '{page_name}'")
    proj = add_projection_group(page_obj, source_name, group_name=name,
                                projections=list(projections), x=x, y=y)
    _session.project["modified"] = True
    _session._auto_save()
    _output(proj, f"Added projection group '{name}' ({', '.join(projections)})")


@techdraw.command("section")
@click.argument("page_name")
@click.argument("source_name")
@click.argument("base_view_name")
@click.option("-n", "--name", default=None, help="Section view name")
@click.option("--nx", type=float, default=0, help="Section normal X")
@click.option("--ny", type=float, default=1, help="Section normal Y")
@click.option("--nz", type=float, default=0, help="Section normal Z")
@click.option("--ox", type=float, default=0, help="Section origin X")
@click.option("--oy", type=float, default=0, help="Section origin Y")
@click.option("--oz", type=float, default=0, help="Section origin Z")
@click.option("-x", type=float, default=200, help="X position on page (mm)")
@click.option("-y", type=float, default=150, help="Y position on page (mm)")
def techdraw_section(page_name: str, source_name: str, base_view_name: str,
                     name: str | None, nx: float, ny: float, nz: float,
                     ox: float, oy: float, oz: float, x: float, y: float) -> None:
    """Add a cross-section view to a drawing page."""
    _ensure_project()
    from cli_anything.freecad.core.techdraw import add_section_view
    page_obj = _session.get_object(page_name)
    if not page_obj or page_obj.get("type") != "TechDraw::DrawPage":
        raise click.ClickException(f"Drawing page not found: {page_name}")
    name = name or _next_name("Section")
    _session.checkpoint(f"add section '{name}' to page '{page_name}'")
    section = add_section_view(page_obj, source_name, base_view_name,
                               section_name=name, normal=(nx, ny, nz),
                               origin=(ox, oy, oz), x=x, y=y)
    _session.project["modified"] = True
    _session._auto_save()
    _output(section, f"Added section view '{name}' to '{page_name}'")


@techdraw.command("dimension")
@click.argument("page_name")
@click.argument("view_name")
@click.option("-t", "--type", "dim_type", default="Distance",
              type=click.Choice(["Distance", "DistanceX", "DistanceY", "Radius", "Diameter", "Angle"]),
              help="Dimension type")
@click.option("-e", "--edge", "edge_ref", default="Edge0", help="Edge/vertex reference (Edge0, Vertex0)")
@click.option("-n", "--name", default=None, help="Dimension name")
@click.option("-x", type=float, default=100, help="Dimension text X position")
@click.option("-y", type=float, default=50, help="Dimension text Y position")
@click.option("-f", "--format", "format_spec", default="%.2f", help="Dimension format string")
def techdraw_dimension(page_name: str, view_name: str, dim_type: str,
                       edge_ref: str, name: str | None, x: float, y: float,
                       format_spec: str) -> None:
    """Add a dimension to a view on a drawing page."""
    _ensure_project()
    from cli_anything.freecad.core.techdraw import add_dimension
    page_obj = _session.get_object(page_name)
    if not page_obj or page_obj.get("type") != "TechDraw::DrawPage":
        raise click.ClickException(f"Drawing page not found: {page_name}")
    name = name or _next_name("Dim")
    _session.checkpoint(f"add dimension '{name}' to page '{page_name}'")
    dim = add_dimension(page_obj, view_name, dim_type=dim_type, edge_ref=edge_ref,
                        dim_name=name, x=x, y=y, format_spec=format_spec)
    _session.project["modified"] = True
    _session._auto_save()
    _output(dim, f"Added {dim_type} dimension '{name}' on '{view_name}'")


@techdraw.command("annotate")
@click.argument("page_name")
@click.argument("text", nargs=-1, required=True)
@click.option("-n", "--name", default=None, help="Annotation name")
@click.option("-x", type=float, default=50, help="X position (mm)")
@click.option("-y", type=float, default=200, help="Y position (mm)")
@click.option("-s", "--font-size", type=float, default=5.0, help="Font size (mm)")
def techdraw_annotate(page_name: str, text: tuple[str, ...], name: str | None,
                      x: float, y: float, font_size: float) -> None:
    """Add a text annotation to a drawing page."""
    _ensure_project()
    from cli_anything.freecad.core.techdraw import add_annotation
    page_obj = _session.get_object(page_name)
    if not page_obj or page_obj.get("type") != "TechDraw::DrawPage":
        raise click.ClickException(f"Drawing page not found: {page_name}")
    name = name or _next_name("Anno")
    _session.checkpoint(f"add annotation '{name}' to page '{page_name}'")
    anno = add_annotation(page_obj, list(text), anno_name=name, x=x, y=y, font_size=font_size)
    _session.project["modified"] = True
    _session._auto_save()
    _output(anno, f"Added annotation '{name}' to '{page_name}'")


@techdraw.command("list")
@click.argument("page_name")
def techdraw_list(page_name: str) -> None:
    """List views, dimensions, and annotations on a drawing page."""
    _ensure_project()
    page_obj = _session.get_object(page_name)
    if not page_obj or page_obj.get("type") != "TechDraw::DrawPage":
        raise click.ClickException(f"Drawing page not found: {page_name}")
    params = page_obj.get("params", {})
    data = {
        "page": page_name,
        "template": params.get("template", "A4_Landscape"),
        "scale": params.get("scale", 1.0),
        "views": params.get("views", []),
        "dimensions": params.get("dimensions", []),
        "annotations": params.get("annotations", []),
    }
    _output(data)
    if not _json_mode:
        click.echo(f"Page: {page_name} ({data['template']}, scale={data['scale']})")
        click.echo(f"Views ({len(data['views'])}):")
        for v in data["views"]:
            click.echo(f"  - {v.get('name', '?')} [{v.get('type', '?')}] source={v.get('source', '?')}")
        click.echo(f"Dimensions ({len(data['dimensions'])}):")
        for d in data["dimensions"]:
            click.echo(f"  - {d.get('name', '?')} [{d.get('dim_type', '?')}]")
        click.echo(f"Annotations ({len(data['annotations'])}):")
        for a in data["annotations"]:
            click.echo(f"  - {a.get('name', '?')}: {' '.join(a.get('text', []))}")


@techdraw.command("export-dxf")
@click.argument("page_name")
@click.argument("output_path", type=click.Path())
@click.option("--overwrite", is_flag=True, help="Overwrite existing file")
def techdraw_export_dxf(page_name: str, output_path: str, overwrite: bool) -> None:
    """Export a drawing page to DXF format."""
    proj = _ensure_project()
    if os.path.exists(output_path) and not overwrite:
        raise click.ClickException(f"File exists: {output_path}. Use --overwrite.")
    from cli_anything.freecad.core.techdraw import export_drawing_dxf
    result = export_drawing_dxf(proj, page_name, output_path)
    r = result.get("result", {})
    if result.get("success") and r.get("output"):
        _output({"success": True, **r}, f"Exported DXF: {r['output']} ({r.get('file_size', 0):,} bytes)")
    else:
        err = r.get("error", "DXF export failed")
        if _json_mode:
            _output({"success": False, "error": err})
        else:
            raise click.ClickException(err)


@techdraw.command("export-svg")
@click.argument("page_name")
@click.argument("output_path", type=click.Path())
@click.option("--overwrite", is_flag=True, help="Overwrite existing file")
def techdraw_export_svg(page_name: str, output_path: str, overwrite: bool) -> None:
    """Export a drawing page to SVG format."""
    proj = _ensure_project()
    if os.path.exists(output_path) and not overwrite:
        raise click.ClickException(f"File exists: {output_path}. Use --overwrite.")
    from cli_anything.freecad.core.techdraw import export_drawing_svg
    result = export_drawing_svg(proj, page_name, output_path)
    r = result.get("result", {})
    if result.get("success") and r.get("output"):
        _output({"success": True, **r}, f"Exported SVG: {r['output']} ({r.get('file_size', 0):,} bytes)")
    else:
        err = r.get("error", "SVG export failed")
        if _json_mode:
            _output({"success": False, "error": err})
        else:
            raise click.ClickException(err)


@techdraw.command("export-pdf")
@click.argument("page_name")
@click.argument("output_path", type=click.Path())
@click.option("--overwrite", is_flag=True, help="Overwrite existing file")
def techdraw_export_pdf(page_name: str, output_path: str, overwrite: bool) -> None:
    """Export a drawing page to PDF format."""
    proj = _ensure_project()
    if os.path.exists(output_path) and not overwrite:
        raise click.ClickException(f"File exists: {output_path}. Use --overwrite.")
    from cli_anything.freecad.core.techdraw import export_drawing_pdf
    result = export_drawing_pdf(proj, page_name, output_path)
    r = result.get("result", {})
    if result.get("success") and r.get("output"):
        _output({"success": True, **r}, f"Exported PDF: {r['output']} ({r.get('file_size', 0):,} bytes)")
    else:
        err = r.get("error", "PDF export failed")
        if _json_mode:
            _output({"success": False, "error": err})
        else:
            raise click.ClickException(err)


# ── Session commands ─────────────────────────────────────────────────

@cli.group()
def session() -> None:
    """Session management commands."""
    pass


@session.command("status")
def session_status() -> None:
    """Show current session status."""
    status = _session.status()
    _output(status)
    if not _json_mode:
        click.echo(f"Project: {status['project_name'] or '(none)'}")
        click.echo(f"Modified: {status['modified']}")
        click.echo(f"Objects: {status['object_count']}")
        click.echo(f"Undo available: {status['undo_available']}")
        click.echo(f"Redo available: {status['redo_available']}")


@session.command("undo")
def session_undo() -> None:
    """Undo last operation."""
    result = _session.undo()
    if result:
        _output(result, f"Undone: {result['undone']}")
    else:
        _output({"error": "Nothing to undo"}, "Nothing to undo")


@session.command("redo")
def session_redo() -> None:
    """Redo last undone operation."""
    result = _session.redo()
    if result:
        _output(result, "Redone last operation")
    else:
        _output({"error": "Nothing to redo"}, "Nothing to redo")


@session.command("history")
def session_history() -> None:
    """Show operation history."""
    ops = _session.history()
    _output({"history": ops})
    if not _json_mode:
        if not ops:
            click.echo("No operations recorded")
        else:
            for i, op in enumerate(ops, 1):
                click.echo(f"  {i}. {op}")


# ── Version command ──────────────────────────────────────────────────

@cli.command("version")
def version_cmd() -> None:
    """Show FreeCAD and CLI version info."""
    from cli_anything.freecad.utils.freecad_backend import get_version
    try:
        fc_version = get_version()
    except RuntimeError as e:
        fc_version = str(e)
    data = {
        "cli_version": __version__,
        "freecad_version": fc_version,
    }
    _output(data)
    if not _json_mode:
        click.echo(f"cli-anything-freecad v{__version__}")
        click.echo(f"FreeCAD: {fc_version}")


# ── REPL ─────────────────────────────────────────────────────────────

@cli.command("repl", hidden=True)
@click.argument("project_path", required=False, type=click.Path())
@click.pass_context
def repl(ctx: click.Context, project_path: str | None) -> None:
    """Interactive REPL mode."""
    from cli_anything.freecad.utils.repl_skin import ReplSkin

    skin = ReplSkin("freecad", version=__version__)
    skin.print_banner()

    if project_path:
        try:
            _session.open_project(project_path)
            skin.success(f"Opened project: {_session.project_name}")
        except FileNotFoundError:
            skin.error(f"Project not found: {project_path}")

    pt_session = skin.create_prompt_session()

    # Command help dict for REPL
    commands = {
        "project new [-n NAME] [-o PATH]": "Create new project",
        "project open <path>": "Open project file",
        "project save [-o PATH]": "Save project",
        "project save-fcstd <path>": "Save as .FCStd",
        "project info": "Show project info",
        "project inspect <path>": "Inspect .FCStd file",
        "part box [-l/-w/-H]": "Create box",
        "part cylinder [-r/-H]": "Create cylinder",
        "part sphere [-r]": "Create sphere",
        "part cone [-r1/-r2/-H]": "Create cone",
        "part torus [-r1/-r2]": "Create torus",
        "part fuse <base> <tool>": "Boolean union",
        "part cut <base> <tool>": "Boolean subtraction",
        "part common <base> <tool>": "Boolean intersection",
        "part fillet <base> [-r]": "Fillet edges",
        "part chamfer <base> [-s]": "Chamfer edges",
        "part list": "List objects",
        "part remove <name>": "Remove object",
        "sketch new [-p XY|XZ|YZ]": "New sketch",
        "sketch line <sketch> [--x1/y1/x2/y2]": "Add line",
        "sketch circle <sketch> [-r]": "Add circle",
        "sketch rect <sketch> [-w/-H]": "Add rectangle",
        "sketch arc <sketch> [-r]": "Add arc",
        "sketch constrain <sketch> -t TYPE": "Add constraint",
        "sketch list <sketch>": "List sketch geometry",
        "mesh import <file>": "Import mesh",
        "techdraw page [-t TEMPLATE]": "Create drawing page",
        "techdraw view <page> <source> [-d DIR]": "Add 2D view",
        "techdraw projection <page> <source>": "Add projection group",
        "techdraw section <page> <src> <view>": "Add section view",
        "techdraw dimension <page> <view> [-t TYPE]": "Add dimension",
        "techdraw annotate <page> <text...>": "Add annotation",
        "techdraw list <page>": "List page contents",
        "techdraw export-dxf <page> <path>": "Export to DXF",
        "techdraw export-svg <page> <path>": "Export to SVG",
        "techdraw export-pdf <page> <path>": "Export to PDF",
        "export render <path> [-p FORMAT]": "Export to format",
        "export formats": "List formats",
        "session status": "Session status",
        "session undo": "Undo",
        "session redo": "Redo",
        "session history": "History",
        "version": "Version info",
        "help": "Show this help",
        "quit / exit": "Exit REPL",
    }

    while True:
        try:
            line = skin.get_input(
                pt_session,
                project_name=_session.project_name,
                modified=_session.is_modified,
            )
        except (EOFError, KeyboardInterrupt):
            skin.print_goodbye()
            break

        if not line:
            continue

        if line.lower() in ("quit", "exit", "q"):
            if _session.is_modified:
                skin.warning("Unsaved changes will be lost!")
            skin.print_goodbye()
            break

        if line.lower() in ("help", "h", "?"):
            skin.help(commands)
            continue

        # Parse and execute as Click command
        try:
            args = line.split()
            cli.main(args=args, standalone_mode=False)
        except SystemExit:
            pass
        except click.ClickException as e:
            skin.error(e.format_message())
        except click.exceptions.UsageError as e:
            skin.error(str(e))
        except Exception as e:
            skin.error(str(e))


def main() -> None:
    """Entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()
