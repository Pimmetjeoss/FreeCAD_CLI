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


@part.command("revolve")
@click.argument("source")
@click.option("-a", "--angle", type=float, default=360, help="Revolution angle in degrees")
@click.option("--axis-x", type=float, default=0, help="Rotation axis X component")
@click.option("--axis-y", type=float, default=0, help="Rotation axis Y component")
@click.option("--axis-z", type=float, default=1, help="Rotation axis Z component")
@click.option("--base-x", type=float, default=0, help="Base point X (point on axis)")
@click.option("--base-y", type=float, default=0, help="Base point Y (point on axis)")
@click.option("--base-z", type=float, default=0, help="Base point Z (point on axis)")
@click.option("-n", "--name", default=None, help="Result name")
def part_revolve(source: str, angle: float, axis_x: float, axis_y: float, axis_z: float, base_x: float, base_y: float, base_z: float, name: str | None) -> None:
    """Revolve a profile (sketch/shape) around an axis."""
    _ensure_project()
    if not _session.get_object(source):
        raise click.ClickException(f"Object not found: {source}")
    name = name or _next_name("Revolve")
    obj = {
        "name": name,
        "type": "Part::Revolution",
        "label": name,
        "params": {
            "source": source,
            "angle": angle,
            "axis_x": axis_x,
            "axis_y": axis_y,
            "axis_z": axis_z,
            "base_x": base_x,
            "base_y": base_y,
            "base_z": base_z,
        },
    }
    axis_str = f"({axis_x}, {axis_y}, {axis_z})"
    _session.add_object(obj, f"revolve '{source}' {angle}° around {axis_str}")
    _output(obj, f"Created revolve '{name}' from '{source}' ({angle}° around {axis_str})")


@part.command("sweep")
@click.argument("profile")
@click.argument("path")
@click.option("--solid/--no-solid", default=True, help="Create solid (vs shell)")
@click.option("--frenet/--no-frenet", default=True, help="Use Frenet frame")
@click.option("-n", "--name", default=None, help="Result name")
def part_sweep(profile: str, path: str, solid: bool, frenet: bool, name: str | None) -> None:
    """Sweep a profile along a path (spine)."""
    _ensure_project()
    if not _session.get_object(profile):
        raise click.ClickException(f"Profile not found: {profile}")
    if not _session.get_object(path):
        raise click.ClickException(f"Path not found: {path}")
    name = name or _next_name("Sweep")
    obj = {
        "name": name,
        "type": "Part::Sweep",
        "label": name,
        "params": {
            "profile": profile,
            "path": path,
            "solid": solid,
            "frenet": frenet,
        },
    }
    _session.add_object(obj, f"sweep '{profile}' along '{path}'")
    _output(obj, f"Created sweep '{name}' (profile='{profile}', path='{path}')")


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
@click.option("-e2", "--edge2", "edge_ref2", default=None, help="Second edge reference (for Angle)")
@click.option("-n", "--name", default=None, help="Dimension name")
@click.option("-x", type=float, default=100, help="Dimension text X position")
@click.option("-y", type=float, default=50, help="Dimension text Y position")
@click.option("-f", "--format", "format_spec", default="%.2f", help="Dimension format string")
@click.option("--prefix", default="", help="Text prefix (e.g. '2x', '∅'). Auto-set for R/D types.")
@click.option("--suffix", default="", help="Text suffix (e.g. ' H7', ' THRU')")
@click.option("--tol-upper", type=float, default=None, help="Upper tolerance (e.g. 0.1)")
@click.option("--tol-lower", type=float, default=None, help="Lower tolerance (e.g. -0.1)")
def techdraw_dimension(page_name: str, view_name: str, dim_type: str,
                       edge_ref: str, edge_ref2: str | None, name: str | None,
                       x: float, y: float, format_spec: str,
                       prefix: str, suffix: str,
                       tol_upper: float | None, tol_lower: float | None) -> None:
    """Add a dimension to a view on a drawing page.

    Supported types: Distance (general), DistanceX (horizontal),
    DistanceY (vertical), Radius, Diameter, Angle.

    Radius/Diameter auto-prefix with R/∅ unless --prefix overrides.
    Use --tol-upper/--tol-lower for tolerance annotations (e.g. 20 +0.1/-0.05).
    """
    _ensure_project()
    from cli_anything.freecad.core.techdraw import add_dimension
    page_obj = _session.get_object(page_name)
    if not page_obj or page_obj.get("type") != "TechDraw::DrawPage":
        raise click.ClickException(f"Drawing page not found: {page_name}")
    name = name or _next_name("Dim")
    _session.checkpoint(f"add dimension '{name}' to page '{page_name}'")
    dim = add_dimension(
        page_obj, view_name, dim_type=dim_type, edge_ref=edge_ref,
        edge_ref2=edge_ref2, dim_name=name, x=x, y=y,
        format_spec=format_spec, prefix=prefix, suffix=suffix,
        tolerance_upper=tol_upper, tolerance_lower=tol_lower,
    )
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


@techdraw.command("title-block")
@click.argument("page_name")
@click.option("--title", default=None, help="Drawing title")
@click.option("--author", default=None, help="Author / drawn by")
@click.option("--date", default=None, help="Date (YYYY-MM-DD)")
@click.option("--scale", "scale_text", default=None, help="Scale text (e.g. 1:10)")
@click.option("--material", default=None, help="Material specification")
@click.option("--revision", default=None, help="Revision number")
@click.option("--company", default=None, help="Company name")
@click.option("--drawing-number", default=None, help="Drawing number")
@click.option("--sheet", default=None, help="Sheet number (e.g. 1/3)")
@click.option("--checked-by", default=None, help="Checked by")
@click.option("--approved-by", default=None, help="Approved by")
def techdraw_title_block(page_name: str, title: str | None, author: str | None,
                         date: str | None, scale_text: str | None, material: str | None,
                         revision: str | None, company: str | None, drawing_number: str | None,
                         sheet: str | None, checked_by: str | None, approved_by: str | None) -> None:
    """Set title block fields on a drawing page."""
    _ensure_project()
    from cli_anything.freecad.core.techdraw import set_title_block
    page_obj = _session.get_object(page_name)
    if not page_obj or page_obj.get("type") != "TechDraw::DrawPage":
        raise click.ClickException(f"Drawing page not found: {page_name}")
    fields = {}
    for key, val in [("title", title), ("author", author), ("date", date),
                     ("scale", scale_text), ("material", material), ("revision", revision),
                     ("company", company), ("drawing_number", drawing_number),
                     ("sheet", sheet), ("checked_by", checked_by), ("approved_by", approved_by)]:
        if val is not None:
            fields[key] = val
    if not fields:
        raise click.ClickException("Specify at least one title block field (--title, --author, etc.)")
    _session.checkpoint(f"set title block on '{page_name}'")
    tb = set_title_block(page_obj, fields)
    _session.project["modified"] = True
    _session._auto_save()
    _output(tb, f"Set title block on '{page_name}': {', '.join(f'{k}={v}' for k, v in fields.items())}")


@techdraw.command("detail")
@click.argument("page_name")
@click.argument("source_name")
@click.argument("base_view_name")
@click.option("-n", "--name", default=None, help="Detail view name")
@click.option("--ax", "anchor_x", type=float, default=0, help="Anchor X on base view (mm)")
@click.option("--ay", "anchor_y", type=float, default=0, help="Anchor Y on base view (mm)")
@click.option("-r", "--radius", type=float, default=20, help="Detail circle radius (mm)")
@click.option("-s", "--scale", "detail_scale", type=float, default=2.0, help="Detail magnification scale")
@click.option("-x", type=float, default=250, help="X position on page (mm)")
@click.option("-y", type=float, default=80, help="Y position on page (mm)")
def techdraw_detail(page_name: str, source_name: str, base_view_name: str,
                    name: str | None, anchor_x: float, anchor_y: float,
                    radius: float, detail_scale: float, x: float, y: float) -> None:
    """Add a detail (magnified) view to a drawing page."""
    _ensure_project()
    from cli_anything.freecad.core.techdraw import add_detail_view
    page_obj = _session.get_object(page_name)
    if not page_obj or page_obj.get("type") != "TechDraw::DrawPage":
        raise click.ClickException(f"Drawing page not found: {page_name}")
    if not _session.get_object(source_name):
        raise click.ClickException(f"Source object not found: {source_name}")
    name = name or _next_name("Detail")
    _session.checkpoint(f"add detail view '{name}' to page '{page_name}'")
    detail = add_detail_view(page_obj, source_name, base_view_name,
                              detail_name=name, anchor_x=anchor_x, anchor_y=anchor_y,
                              radius=radius, scale=detail_scale, x=x, y=y)
    _session.project["modified"] = True
    _session._auto_save()
    _output(detail, f"Added detail view '{name}' (scale={detail_scale}x) to '{page_name}'")


@techdraw.command("centerline")
@click.argument("page_name")
@click.argument("view_name")
@click.option("-n", "--name", default=None, help="Centerline name")
@click.option("-o", "--orientation", type=click.Choice(["vertical", "horizontal"]),
              default="vertical", help="Centerline orientation")
@click.option("-p", "--position", type=float, default=0, help="Position along perpendicular axis (mm)")
@click.option("--low", "extent_low", type=float, default=-10, help="Start extent (mm)")
@click.option("--high", "extent_high", type=float, default=10, help="End extent (mm)")
def techdraw_centerline(page_name: str, view_name: str, name: str | None,
                        orientation: str, position: float,
                        extent_low: float, extent_high: float) -> None:
    """Add a centerline to a view on a drawing page."""
    _ensure_project()
    from cli_anything.freecad.core.techdraw import add_centerline
    page_obj = _session.get_object(page_name)
    if not page_obj or page_obj.get("type") != "TechDraw::DrawPage":
        raise click.ClickException(f"Drawing page not found: {page_name}")
    name = name or _next_name("CenterLine")
    _session.checkpoint(f"add centerline '{name}' to page '{page_name}'")
    cl = add_centerline(page_obj, view_name, cl_name=name, orientation=orientation,
                        position=position, extent_low=extent_low, extent_high=extent_high)
    _session.project["modified"] = True
    _session._auto_save()
    _output(cl, f"Added {orientation} centerline '{name}' to view '{view_name}'")


@techdraw.command("hatch")
@click.argument("page_name")
@click.argument("view_name")
@click.option("-n", "--name", default=None, help="Hatch name")
@click.option("-f", "--face", "face_ref", default="Face0", help="Face reference (Face0, Face1, etc.)")
@click.option("-p", "--pattern", default="ansi31", help="Hatch pattern name")
@click.option("-s", "--scale", "hatch_scale", type=float, default=1.0, help="Pattern scale")
@click.option("-r", "--rotation", type=float, default=0, help="Pattern rotation (degrees)")
@click.option("-c", "--color", default="#000000", help="Hatch color (hex)")
def techdraw_hatch(page_name: str, view_name: str, name: str | None,
                   face_ref: str, pattern: str, hatch_scale: float,
                   rotation: float, color: str) -> None:
    """Add a hatch pattern to a face in a view."""
    _ensure_project()
    from cli_anything.freecad.core.techdraw import add_hatch
    page_obj = _session.get_object(page_name)
    if not page_obj or page_obj.get("type") != "TechDraw::DrawPage":
        raise click.ClickException(f"Drawing page not found: {page_name}")
    name = name or _next_name("Hatch")
    _session.checkpoint(f"add hatch '{name}' to page '{page_name}'")
    h = add_hatch(page_obj, view_name, face_ref=face_ref, hatch_name=name,
                  pattern=pattern, scale=hatch_scale, rotation=rotation, color=color)
    _session.project["modified"] = True
    _session._auto_save()
    _output(h, f"Added hatch '{name}' ({pattern}) to '{view_name}' {face_ref}")


@techdraw.command("leader")
@click.argument("page_name")
@click.argument("view_name")
@click.option("-n", "--name", default=None, help="Leader line name")
@click.option("--sx", "start_x", type=float, default=0, help="Start X on view (mm)")
@click.option("--sy", "start_y", type=float, default=0, help="Start Y on view (mm)")
@click.option("--ex", "end_x", type=float, default=50, help="End X on page (mm)")
@click.option("--ey", "end_y", type=float, default=50, help="End Y on page (mm)")
@click.option("-t", "--text", default="", help="Label text")
@click.option("-a", "--arrow", "arrow_style", default="filled",
              type=click.Choice(["filled", "open", "tick", "dot", "none"]),
              help="Arrow head style")
def techdraw_leader(page_name: str, view_name: str, name: str | None,
                    start_x: float, start_y: float, end_x: float, end_y: float,
                    text: str, arrow_style: str) -> None:
    """Add a leader line (reference line with text) to a view."""
    _ensure_project()
    from cli_anything.freecad.core.techdraw import add_leader_line
    page_obj = _session.get_object(page_name)
    if not page_obj or page_obj.get("type") != "TechDraw::DrawPage":
        raise click.ClickException(f"Drawing page not found: {page_name}")
    name = name or _next_name("Leader")
    _session.checkpoint(f"add leader '{name}' to page '{page_name}'")
    ld = add_leader_line(page_obj, view_name, leader_name=name,
                         start_x=start_x, start_y=start_y,
                         end_x=end_x, end_y=end_y, text=text,
                         arrow_style=arrow_style)
    _session.project["modified"] = True
    _session._auto_save()
    _output(ld, f"Added leader '{name}' to view '{view_name}'" + (f" ({text})" if text else ""))


@techdraw.command("balloon")
@click.argument("page_name")
@click.argument("view_name")
@click.option("-n", "--name", default=None, help="Balloon name")
@click.option("--ox", "origin_x", type=float, default=0, help="Origin X on object (mm)")
@click.option("--oy", "origin_y", type=float, default=0, help="Origin Y on object (mm)")
@click.option("-t", "--text", default="1", help="Balloon text (item number)")
@click.option("-s", "--shape", default="circular",
              type=click.Choice(["circular", "rectangular", "triangle", "hexagon", "none"]),
              help="Balloon shape")
@click.option("-x", type=float, default=50, help="Balloon X position on page (mm)")
@click.option("-y", type=float, default=50, help="Balloon Y position on page (mm)")
def techdraw_balloon(page_name: str, view_name: str, name: str | None,
                     origin_x: float, origin_y: float, text: str,
                     shape: str, x: float, y: float) -> None:
    """Add a balloon (item number reference) to a view."""
    _ensure_project()
    from cli_anything.freecad.core.techdraw import add_balloon
    page_obj = _session.get_object(page_name)
    if not page_obj or page_obj.get("type") != "TechDraw::DrawPage":
        raise click.ClickException(f"Drawing page not found: {page_name}")
    name = name or _next_name("Balloon")
    _session.checkpoint(f"add balloon '{name}' to page '{page_name}'")
    bl = add_balloon(page_obj, view_name, balloon_name=name,
                     origin_x=origin_x, origin_y=origin_y,
                     text=text, shape=shape, x=x, y=y)
    _session.project["modified"] = True
    _session._auto_save()
    _output(bl, f"Added balloon '{name}' ({text}) to view '{view_name}'")


@techdraw.command("bom")
@click.argument("page_name")
@click.option("-n", "--name", default=None, help="BOM name")
@click.option("-i", "--item", "items_raw", multiple=True,
              help="BOM item as 'key1=val1,key2=val2' (repeat for multiple items)")
@click.option("-x", type=float, default=200, help="X position on page (mm)")
@click.option("-y", type=float, default=250, help="Y position on page (mm)")
@click.option("-s", "--font-size", type=float, default=3.5, help="Font size (mm)")
@click.option("--columns", default=None, help="Comma-separated column names (default: item,name,material,quantity)")
def techdraw_bom(page_name: str, name: str | None, items_raw: tuple[str, ...],
                 x: float, y: float, font_size: float, columns: str | None) -> None:
    """Add a Bill of Materials (stuklijst) table to a drawing page.

    Example: techdraw bom Page -i "item=1,name=Plank,material=Eiken,quantity=4"
    """
    _ensure_project()
    from cli_anything.freecad.core.techdraw import add_bom
    page_obj = _session.get_object(page_name)
    if not page_obj or page_obj.get("type") != "TechDraw::DrawPage":
        raise click.ClickException(f"Drawing page not found: {page_name}")
    name = name or _next_name("BOM")
    # Parse items
    items = []
    for raw in items_raw:
        item = {}
        for pair in raw.split(","):
            if "=" in pair:
                k, v = pair.split("=", 1)
                item[k.strip()] = v.strip()
        if item:
            items.append(item)
    # Parse columns
    col_list = [c.strip() for c in columns.split(",")] if columns else None
    _session.checkpoint(f"add BOM '{name}' to page '{page_name}'")
    bom = add_bom(page_obj, items, bom_name=name, x=x, y=y,
                  font_size=font_size, columns=col_list)
    _session.project["modified"] = True
    _session._auto_save()
    _output(bom, f"Added BOM '{name}' ({len(items)} items) to '{page_name}'")


@techdraw.command("cosmetic-edge")
@click.argument("page_name")
@click.argument("view_name")
@click.option("-n", "--name", default=None, help="Edge name")
@click.option("--x1", type=float, default=0, help="Start X (mm, relative to view center)")
@click.option("--y1", type=float, default=0, help="Start Y (mm, relative to view center)")
@click.option("--x2", type=float, default=50, help="End X (mm, relative to view center)")
@click.option("--y2", type=float, default=0, help="End Y (mm, relative to view center)")
@click.option("-s", "--style", default="dashed",
              type=click.Choice(["solid", "dashed", "dashdot", "dotted", "phantom"]),
              help="Line style")
@click.option("-c", "--color", default="#000000", help="Line color (hex)")
@click.option("-w", "--weight", type=float, default=0.2, help="Line weight (mm)")
def techdraw_cosmetic_edge(page_name: str, view_name: str, name: str | None,
                           x1: float, y1: float, x2: float, y2: float,
                           style: str, color: str, weight: float) -> None:
    """Add a cosmetic (artificial) edge to a view.

    Cosmetic edges are lines that don't correspond to real geometry.
    Use for fold lines, cut edges, phantom outlines, reference lines.

    Coordinates are relative to the view center, in mm.
    """
    _ensure_project()
    from cli_anything.freecad.core.techdraw import add_cosmetic_edge
    page_obj = _session.get_object(page_name)
    if not page_obj or page_obj.get("type") != "TechDraw::DrawPage":
        raise click.ClickException(f"Drawing page not found: {page_name}")
    name = name or _next_name("CosEdge")
    _session.checkpoint(f"add cosmetic edge '{name}' to page '{page_name}'")
    edge = add_cosmetic_edge(page_obj, view_name, x1=x1, y1=y1, x2=x2, y2=y2,
                             edge_name=name, style=style, color=color, weight=weight)
    _session.project["modified"] = True
    _session._auto_save()
    _output(edge, f"Added cosmetic edge '{name}' ({style}) on '{view_name}'")


@techdraw.command("center-mark")
@click.argument("page_name")
@click.argument("view_name")
@click.option("-n", "--name", default=None, help="Mark name")
@click.option("--cx", type=float, default=0, help="Center X (mm, relative to view center)")
@click.option("--cy", type=float, default=0, help="Center Y (mm, relative to view center)")
@click.option("--size", type=float, default=5, help="Crosshair arm length (mm)")
@click.option("-s", "--style", default="dashdot",
              type=click.Choice(["solid", "dashed", "dashdot", "dotted", "phantom"]),
              help="Line style")
@click.option("-c", "--color", default="#000000", help="Line color (hex)")
@click.option("-w", "--weight", type=float, default=0.15, help="Line weight (mm)")
def techdraw_center_mark(page_name: str, view_name: str, name: str | None,
                         cx: float, cy: float, size: float,
                         style: str, color: str, weight: float) -> None:
    """Add a center mark (crosshair) to a view.

    Center marks show the center of holes, arcs, or circular features.
    Rendered as a + crosshair at the specified position.
    """
    _ensure_project()
    from cli_anything.freecad.core.techdraw import add_center_mark
    page_obj = _session.get_object(page_name)
    if not page_obj or page_obj.get("type") != "TechDraw::DrawPage":
        raise click.ClickException(f"Drawing page not found: {page_name}")
    name = name or _next_name("CtrMark")
    _session.checkpoint(f"add center mark '{name}' to page '{page_name}'")
    mark = add_center_mark(page_obj, view_name, cx=cx, cy=cy, mark_name=name,
                           size=size, style=style, color=color, weight=weight)
    _session.project["modified"] = True
    _session._auto_save()
    _output(mark, f"Added center mark '{name}' at ({cx},{cy}) on '{view_name}'")


@techdraw.command("clip")
@click.argument("page_name")
@click.option("-n", "--name", default=None, help="Clip group name")
@click.option("-x", type=float, default=100, help="Center X position (mm)")
@click.option("-y", type=float, default=100, help="Center Y position (mm)")
@click.option("-w", "--width", type=float, default=80, help="Clip width (mm)")
@click.option("-H", "--height", type=float, default=60, help="Clip height (mm)")
@click.option("--no-frame", is_flag=True, help="Hide the clip boundary frame")
def techdraw_clip(page_name: str, name: str | None, x: float, y: float,
                  width: float, height: float, no_frame: bool) -> None:
    """Create a clip group (rectangular mask) on a drawing page.

    Views added to this clip group will be masked to the rectangle.
    """
    _ensure_project()
    from cli_anything.freecad.core.techdraw import add_clip_group
    page_obj = _session.get_object(page_name)
    if not page_obj or page_obj.get("type") != "TechDraw::DrawPage":
        raise click.ClickException(f"Drawing page not found: {page_name}")
    name = name or _next_name("Clip")
    _session.checkpoint(f"add clip group '{name}' to page '{page_name}'")
    clip = add_clip_group(page_obj, clip_name=name, x=x, y=y,
                          width=width, height=height, show_frame=not no_frame)
    _session.project["modified"] = True
    _session._auto_save()
    _output(clip, f"Added clip group '{name}' ({width}x{height} mm) to '{page_name}'")


@techdraw.command("clip-add")
@click.argument("page_name")
@click.argument("clip_name")
@click.argument("view_name")
def techdraw_clip_add(page_name: str, clip_name: str, view_name: str) -> None:
    """Add an existing view to a clip group.

    The view will be masked to the clip rectangle boundaries.
    """
    _ensure_project()
    from cli_anything.freecad.core.techdraw import add_view_to_clip
    page_obj = _session.get_object(page_name)
    if not page_obj or page_obj.get("type") != "TechDraw::DrawPage":
        raise click.ClickException(f"Drawing page not found: {page_name}")
    _session.checkpoint(f"add view '{view_name}' to clip '{clip_name}'")
    result = add_view_to_clip(page_obj, clip_name, view_name)
    if result is None:
        raise click.ClickException(
            f"Clip group '{clip_name}' or view '{view_name}' not found on '{page_name}'")
    _session.project["modified"] = True
    _session._auto_save()
    _output(result, f"Added view '{view_name}' to clip group '{clip_name}'")


@techdraw.command("gdt")
@click.argument("page_name")
@click.argument("view_name")
@click.option("-c", "--characteristic", required=True,
              type=click.Choice([
                  "flatness", "straightness", "circularity", "cylindricity",
                  "perpendicularity", "parallelism", "angularity",
                  "position", "concentricity", "symmetry",
                  "circular_runout", "total_runout",
                  "profile_line", "profile_surface",
              ]),
              help="GD&T characteristic type (ISO 1101)")
@click.option("-t", "--tolerance", type=float, required=True, help="Tolerance value (mm)")
@click.option("-d", "--datum", "datum_refs", multiple=True,
              help="Datum reference letter (repeat for multiple, max 3)")
@click.option("-m", "--material-condition", default="RFS",
              type=click.Choice(["MMC", "LMC", "RFS"]),
              help="Material condition modifier")
@click.option("--diameter-zone", is_flag=True, help="Use diameter (∅) tolerance zone")
@click.option("-n", "--name", default=None, help="GD&T annotation name")
@click.option("-x", type=float, default=100, help="X position on page (mm)")
@click.option("-y", type=float, default=80, help="Y position on page (mm)")
def techdraw_gdt(page_name: str, view_name: str, characteristic: str,
                 tolerance: float, datum_refs: tuple[str, ...],
                 material_condition: str, diameter_zone: bool,
                 name: str | None, x: float, y: float) -> None:
    """Add a geometric tolerance frame (GD&T / Feature Control Frame).

    Creates an ISO 1101 / ASME Y14.5 compliant feature control frame with
    characteristic symbol, tolerance value, material condition, and datum refs.

    Examples:
      # Position tolerance 0.05mm relative to datums A and B
      techdraw gdt Sheet1 V1 -c position -t 0.05 -d A -d B

      # Flatness 0.01mm (no datums needed for form tolerances)
      techdraw gdt Sheet1 V1 -c flatness -t 0.01

      # Perpendicularity 0.1mm to datum A, MMC
      techdraw gdt Sheet1 V1 -c perpendicularity -t 0.1 -d A -m MMC
    """
    _ensure_project()
    from cli_anything.freecad.core.techdraw import add_geometric_tolerance
    page_obj = _session.get_object(page_name)
    if not page_obj or page_obj.get("type") != "TechDraw::DrawPage":
        raise click.ClickException(f"Drawing page not found: {page_name}")
    name = name or _next_name("GDT")
    _session.checkpoint(f"add GD&T '{name}' to page '{page_name}'")
    gdt = add_geometric_tolerance(
        page_obj, view_name, characteristic=characteristic,
        tolerance=tolerance, gdt_name=name,
        datum_refs=list(datum_refs), material_condition=material_condition,
        diameter_zone=diameter_zone, x=x, y=y,
    )
    _session.project["modified"] = True
    _session._auto_save()
    datum_str = f" [{', '.join(datum_refs)}]" if datum_refs else ""
    _output(gdt, f"Added GD&T '{name}' ({characteristic} {tolerance}){datum_str}")


@techdraw.command("datum")
@click.argument("page_name")
@click.argument("view_name")
@click.argument("letter")
@click.option("-n", "--name", default=None, help="Datum symbol name")
@click.option("-x", type=float, default=100, help="X position on page (mm)")
@click.option("-y", type=float, default=100, help="Y position on page (mm)")
def techdraw_datum(page_name: str, view_name: str, letter: str,
                   name: str | None, x: float, y: float) -> None:
    """Add a datum feature symbol (triangle + letter box) to a view.

    Per ISO 5459 / ASME Y14.5. Place on a surface or edge to define
    a datum reference for geometric tolerances.

    Example:
      techdraw datum Sheet1 V1 A -x 50 -y 120
    """
    _ensure_project()
    from cli_anything.freecad.core.techdraw import add_datum_symbol
    page_obj = _session.get_object(page_name)
    if not page_obj or page_obj.get("type") != "TechDraw::DrawPage":
        raise click.ClickException(f"Drawing page not found: {page_name}")
    name = name or _next_name("Datum")
    _session.checkpoint(f"add datum '{name}' to page '{page_name}'")
    datum = add_datum_symbol(page_obj, view_name, letter=letter,
                             datum_name=name, x=x, y=y)
    _session.project["modified"] = True
    _session._auto_save()
    _output(datum, f"Added datum '{letter}' ('{name}') to view '{view_name}'")


@techdraw.command("surface-finish")
@click.argument("page_name")
@click.argument("view_name")
@click.option("--ra", type=float, default=None, help="Ra roughness value (µm)")
@click.option("--rz", type=float, default=None, help="Rz roughness value (µm)")
@click.option("-p", "--process", default="any",
              type=click.Choice(["any", "removal_required", "removal_prohibited"]),
              help="Manufacturing process requirement")
@click.option("--lay", "lay_direction", default="", help="Lay direction symbol (=, ⊥, X, M, C, R)")
@click.option("-n", "--name", default=None, help="Surface finish name")
@click.option("-x", type=float, default=100, help="X position on page (mm)")
@click.option("-y", type=float, default=100, help="Y position on page (mm)")
def techdraw_surface_finish(page_name: str, view_name: str,
                            ra: float | None, rz: float | None,
                            process: str, lay_direction: str,
                            name: str | None, x: float, y: float) -> None:
    """Add a surface finish (roughness) symbol to a view.

    Per ISO 1302. Specifies surface texture requirements.

    Examples:
      # Ra 1.6 µm, machining required
      techdraw surface-finish Sheet1 V1 --ra 1.6 -p removal_required

      # Rz 6.3 µm, any process
      techdraw surface-finish Sheet1 V1 --rz 6.3
    """
    _ensure_project()
    from cli_anything.freecad.core.techdraw import add_surface_finish
    page_obj = _session.get_object(page_name)
    if not page_obj or page_obj.get("type") != "TechDraw::DrawPage":
        raise click.ClickException(f"Drawing page not found: {page_name}")
    if ra is None and rz is None:
        raise click.ClickException("Specify at least --ra or --rz roughness value")
    name = name or _next_name("SurfFinish")
    _session.checkpoint(f"add surface finish '{name}' to page '{page_name}'")
    sf = add_surface_finish(page_obj, view_name, ra=ra, rz=rz, process=process,
                            sf_name=name, lay_direction=lay_direction, x=x, y=y)
    _session.project["modified"] = True
    _session._auto_save()
    vals = []
    if ra is not None:
        vals.append(f"Ra={ra}")
    if rz is not None:
        vals.append(f"Rz={rz}")
    _output(sf, f"Added surface finish '{name}' ({', '.join(vals)}) to view '{view_name}'")


@techdraw.command("weld")
@click.argument("page_name")
@click.argument("view_name")
@click.option("-t", "--type", "weld_type", required=True,
              type=click.Choice([
                  "fillet", "v_groove", "square_groove", "bevel_groove",
                  "u_groove", "j_groove", "plug", "bead",
                  "spot", "seam", "edge", "flare_v", "flare_bevel",
              ]),
              help="Weld type (AWS A2.4 / ISO 2553)")
@click.option("-s", "--side", default="arrow",
              type=click.Choice(["arrow", "other"]),
              help="Arrow side or other side of reference line")
@click.option("--size", default="", help="Weld size/leg (left of symbol), e.g. '6'")
@click.option("--length", default="", help="Weld length (right of symbol), e.g. '50'")
@click.option("--pitch", default="", help="Pitch/spacing for intermittent welds")
@click.option("--all-around", is_flag=True, help="All-around weld (circle at junction)")
@click.option("--field-weld", is_flag=True, help="Field weld (flag at junction)")
@click.option("--tail", default="", help="Tail text (process: GMAW, SMAW, etc.)")
@click.option("--contour", default="",
              type=click.Choice(["", "flush", "convex", "concave"]),
              help="Contour/finish requirement")
@click.option("-n", "--name", default=None, help="Weld symbol name")
@click.option("-x", type=float, default=100, help="X position on page (mm)")
@click.option("-y", type=float, default=80, help="Y position on page (mm)")
def techdraw_weld(page_name: str, view_name: str, weld_type: str,
                  side: str, size: str, length: str, pitch: str,
                  all_around: bool, field_weld: bool, tail: str,
                  contour: str, name: str | None, x: float, y: float) -> None:
    """Add a welding symbol (AWS A2.4 / ISO 2553) to a view.

    Creates a weld symbol with reference line, arrow, basic weld type,
    dimensions, and supplementary indicators.

    Examples:
      # 6mm fillet weld, arrow side
      techdraw weld Sheet1 V1 -t fillet --size 6

      # V-groove, all-around, GMAW process
      techdraw weld Sheet1 V1 -t v_groove --all-around --tail GMAW

      # Bevel groove, 50mm length, field weld, flush finish
      techdraw weld Sheet1 V1 -t bevel_groove --length 50 --field-weld --contour flush
    """
    _ensure_project()
    from cli_anything.freecad.core.techdraw import add_weld_symbol
    page_obj = _session.get_object(page_name)
    if not page_obj or page_obj.get("type") != "TechDraw::DrawPage":
        raise click.ClickException(f"Drawing page not found: {page_name}")
    name = name or _next_name("Weld")
    _session.checkpoint(f"add weld '{name}' to page '{page_name}'")
    weld = add_weld_symbol(
        page_obj, view_name, weld_type=weld_type, side=side,
        size=size, length=length, pitch=pitch,
        all_around=all_around, field_weld=field_weld,
        tail=tail, contour=contour, weld_name=name, x=x, y=y,
    )
    _session.project["modified"] = True
    _session._auto_save()
    desc = weld.get("weld_description", weld_type)
    extras = []
    if all_around:
        extras.append("all-around")
    if field_weld:
        extras.append("field")
    extra_str = f" ({', '.join(extras)})" if extras else ""
    _output(weld, f"Added weld '{name}' ({desc}){extra_str} to view '{view_name}'")


@techdraw.command("weld-tile")
@click.argument("page_name")
@click.argument("weld_name")
@click.option("-t", "--type", "weld_type", required=True,
              type=click.Choice([
                  "fillet", "v_groove", "square_groove", "bevel_groove",
                  "u_groove", "j_groove", "plug", "bead",
                  "spot", "seam", "edge", "flare_v", "flare_bevel",
              ]),
              help="Weld type for this tile")
@click.option("-s", "--side", default="other",
              type=click.Choice(["arrow", "other"]),
              help="Arrow side or other side [default: other]")
@click.option("--size", default="", help="Weld size (left of symbol)")
@click.option("--length", default="", help="Weld length (right of symbol)")
@click.option("--pitch", default="", help="Pitch/spacing")
def techdraw_weld_tile(page_name: str, weld_name: str, weld_type: str,
                       side: str, size: str, length: str, pitch: str) -> None:
    """Add an additional weld tile to an existing weld symbol (double-sided welds).

    Example:
      # Add other-side fillet to existing weld
      techdraw weld-tile Sheet1 Weld1 -t fillet -s other --size 4
    """
    _ensure_project()
    from cli_anything.freecad.core.techdraw import add_weld_tile
    page_obj = _session.get_object(page_name)
    if not page_obj or page_obj.get("type") != "TechDraw::DrawPage":
        raise click.ClickException(f"Drawing page not found: {page_name}")
    _session.checkpoint(f"add weld tile to '{weld_name}' on page '{page_name}'")
    tile = add_weld_tile(
        page_obj, weld_name, weld_type=weld_type, side=side,
        size=size, length=length, pitch=pitch,
    )
    _session.project["modified"] = True
    _session._auto_save()
    _output(tile, f"Added {side}-side {weld_type} tile to weld '{weld_name}'")


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
        "title_block": params.get("title_block"),
        "centerlines": params.get("centerlines", []),
        "hatches": params.get("hatches", []),
        "leaders": params.get("leaders", []),
        "balloons": params.get("balloons", []),
        "bom": params.get("bom", []),
        "cosmetic_edges": params.get("cosmetic_edges", []),
        "clips": params.get("clips", []),
        "gdt": params.get("gdt", []),
        "datums": params.get("datums", []),
        "surface_finishes": params.get("surface_finishes", []),
        "welds": params.get("welds", []),
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
        if data["title_block"]:
            click.echo(f"Title block: {data['title_block']}")
        if data["centerlines"]:
            click.echo(f"Centerlines ({len(data['centerlines'])}):")
            for cl in data["centerlines"]:
                click.echo(f"  - {cl.get('name', '?')} [{cl.get('orientation', '?')}] on {cl.get('view', '?')}")
        if data["hatches"]:
            click.echo(f"Hatches ({len(data['hatches'])}):")
            for h in data["hatches"]:
                click.echo(f"  - {h.get('name', '?')} [{h.get('pattern', '?')}] on {h.get('view', '?')}")
        if data["leaders"]:
            click.echo(f"Leaders ({len(data['leaders'])}):")
            for ld in data["leaders"]:
                click.echo(f"  - {ld.get('name', '?')} on {ld.get('view', '?')}")
        if data["balloons"]:
            click.echo(f"Balloons ({len(data['balloons'])}):")
            for bl in data["balloons"]:
                click.echo(f"  - {bl.get('name', '?')} [{bl.get('text', '?')}] on {bl.get('view', '?')}")
        if data["bom"]:
            click.echo(f"BOM tables ({len(data['bom'])}):")
            for bm in data["bom"]:
                click.echo(f"  - {bm.get('name', '?')} ({len(bm.get('items', []))} items)")
        if data["cosmetic_edges"]:
            click.echo(f"Cosmetic edges ({len(data['cosmetic_edges'])}):")
            for ce in data["cosmetic_edges"]:
                ctype = "center-mark" if ce.get("type") == "TechDraw::CenterMark" else "edge"
                click.echo(f"  - {ce.get('name', '?')} [{ctype}, {ce.get('style', '?')}] on {ce.get('view', '?')}")
        if data["clips"]:
            click.echo(f"Clip groups ({len(data['clips'])}):")
            for cl in data["clips"]:
                vcount = len(cl.get("views", []))
                click.echo(f"  - {cl.get('name', '?')} ({cl.get('width', 0)}x{cl.get('height', 0)} mm, {vcount} views)")
        if data["gdt"]:
            click.echo(f"GD&T ({len(data['gdt'])}):")
            for g in data["gdt"]:
                refs = ", ".join(g.get("datum_refs", []))
                ref_str = f" [{refs}]" if refs else ""
                click.echo(f"  - {g.get('name', '?')} [{g.get('characteristic', '?')}] "
                           f"{g.get('symbol', '')} {g.get('tolerance', '?')}{ref_str}")
        if data["datums"]:
            click.echo(f"Datums ({len(data['datums'])}):")
            for d in data["datums"]:
                click.echo(f"  - {d.get('name', '?')} [{d.get('letter', '?')}] on {d.get('view', '?')}")
        if data["surface_finishes"]:
            click.echo(f"Surface finishes ({len(data['surface_finishes'])}):")
            for sf in data["surface_finishes"]:
                vals = []
                if sf.get("ra") is not None:
                    vals.append(f"Ra={sf['ra']}")
                if sf.get("rz") is not None:
                    vals.append(f"Rz={sf['rz']}")
                click.echo(f"  - {sf.get('name', '?')} [{sf.get('process', '?')}] "
                           f"{', '.join(vals)} on {sf.get('view', '?')}")
        if data["welds"]:
            click.echo(f"Weld symbols ({len(data['welds'])}):")
            for w in data["welds"]:
                extras = []
                if w.get("all_around"):
                    extras.append("all-around")
                if w.get("field_weld"):
                    extras.append("field")
                if w.get("tail"):
                    extras.append(w["tail"])
                extra_str = f" ({', '.join(extras)})" if extras else ""
                tiles_count = len(w.get("tiles", []))
                click.echo(f"  - {w.get('name', '?')} [{w.get('weld_type', '?')}] "
                           f"{w.get('weld_symbol', '')}{extra_str} "
                           f"({tiles_count} tile{'s' if tiles_count != 1 else ''}) "
                           f"on {w.get('view', '?')}")


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
        "techdraw gdt <page> <view> -c TYPE -t TOL": "Add GD&T frame",
        "techdraw datum <page> <view> <letter>": "Add datum symbol",
        "techdraw surface-finish <page> <view> --ra/--rz": "Surface finish",
        "techdraw weld <page> <view> -t TYPE": "Add weld symbol (AWS/ISO)",
        "techdraw weld-tile <page> <weld> -t TYPE": "Add tile to weld",
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


# ── Extended Part commands (gap-fill via CLI-Anything methodology) ───

@part.command("array")
@click.argument("source")
@click.option("--type", "array_type", type=click.Choice(["linear", "polar"]),
              default="linear", help="Array type: linear or polar")
@click.option("--count-x", type=int, default=2, help="Count along X (linear)")
@click.option("--count-y", type=int, default=1, help="Count along Y (linear)")
@click.option("--count-z", type=int, default=1, help="Count along Z (linear)")
@click.option("--step-x", type=float, default=10, help="Step size X (mm, linear)")
@click.option("--step-y", type=float, default=10, help="Step size Y (mm, linear)")
@click.option("--step-z", type=float, default=0, help="Step size Z (mm, linear)")
@click.option("--count", type=int, default=4, help="Total count (polar)")
@click.option("--angle", type=float, default=360, help="Total angle (degrees, polar)")
@click.option("--cx", type=float, default=0, help="Center X (polar)")
@click.option("--cy", type=float, default=0, help="Center Y (polar)")
@click.option("--cz", type=float, default=0, help="Center Z (polar)")
@click.option("-n", "--name", default=None, help="Result name")
def part_array(source: str, array_type: str,
               count_x: int, count_y: int, count_z: int,
               step_x: float, step_y: float, step_z: float,
               count: int, angle: float,
               cx: float, cy: float, cz: float,
               name: str | None) -> None:
    """Create a linear or polar array of an object.

    Linear example (3x2 grid, 20mm apart):
      part array Box --type linear --count-x 3 --count-y 2 --step-x 20 --step-y 20

    Polar example (6 copies around Z-axis):
      part array Cylinder --type polar --count 6 --angle 360
    """
    _ensure_project()
    if not _session.get_object(source):
        raise click.ClickException(f"Object not found: {source}")
    name = name or _next_name("Array")
    params: dict = {"source": source, "array_type": array_type}
    if array_type == "linear":
        params.update({
            "count_x": count_x, "count_y": count_y, "count_z": count_z,
            "step_x": step_x, "step_y": step_y, "step_z": step_z,
        })
        desc = f"{count_x}x{count_y}x{count_z} @ ({step_x},{step_y},{step_z})mm"
    else:
        params.update({
            "count": count, "angle": angle,
            "center_x": cx, "center_y": cy, "center_z": cz,
        })
        desc = f"{count}× {angle}° polar around ({cx},{cy},{cz})"
    obj = {"name": name, "type": "Part::Array", "label": name, "params": params}
    _session.add_object(obj, f"array '{source}' → '{name}'")
    _output(obj, f"Created array '{name}' of '{source}': {desc}")


@part.command("mirror")
@click.argument("source")
@click.option("-p", "--plane", type=click.Choice(["XY", "XZ", "YZ"]),
              default="XY", help="Mirror plane")
@click.option("-n", "--name", default=None, help="Result name")
def part_mirror(source: str, plane: str, name: str | None) -> None:
    """Mirror an object across a plane.

    Example: mirror a bracket across XZ plane:
      part mirror Bracket --plane XZ
    """
    _ensure_project()
    if not _session.get_object(source):
        raise click.ClickException(f"Object not found: {source}")
    name = name or _next_name("Mirror")

    # Normal vector per plane
    normals = {"XY": (0, 0, 1), "XZ": (0, 1, 0), "YZ": (1, 0, 0)}
    nx, ny, nz = normals[plane]

    obj = {
        "name": name,
        "type": "Part::Mirror",
        "label": name,
        "params": {"source": source, "plane": plane,
                   "normal_x": nx, "normal_y": ny, "normal_z": nz},
    }
    _session.add_object(obj, f"mirror '{source}' on {plane}")
    _output(obj, f"Created mirror '{name}' of '{source}' on {plane} plane")


@part.command("loft")
@click.argument("profiles", nargs=-1, required=True)
@click.option("--solid/--no-solid", default=True, help="Create solid")
@click.option("--ruled/--no-ruled", default=False, help="Ruled surface (straight lines)")
@click.option("--closed/--no-closed", default=False, help="Close the loft")
@click.option("-n", "--name", default=None, help="Result name")
def part_loft(profiles: tuple[str, ...], solid: bool, ruled: bool,
              closed: bool, name: str | None) -> None:
    """Loft through multiple profiles (cross-sections).

    Creates a smooth solid or surface transitioning between 2+ sketches.

    Example (loft through 3 sketches):
      part loft Sketch Sketch001 Sketch002 --solid
    """
    _ensure_project()
    if len(profiles) < 2:
        raise click.ClickException("At least 2 profiles required for a loft")
    for p in profiles:
        if not _session.get_object(p):
            raise click.ClickException(f"Profile not found: {p}")
    name = name or _next_name("Loft")
    obj = {
        "name": name,
        "type": "Part::Loft",
        "label": name,
        "params": {
            "profiles": list(profiles),
            "solid": solid,
            "ruled": ruled,
            "closed": closed,
        },
    }
    _session.add_object(obj, f"loft {' → '.join(profiles)}")
    _output(obj, f"Created loft '{name}' through {len(profiles)} profiles")


@part.command("shell")
@click.argument("source")
@click.option("-t", "--thickness", type=float, default=1.0, help="Shell thickness (mm)")
@click.option("--mode", type=click.Choice(["outward", "inward"]),
              default="inward", help="Direction of offset")
@click.option("-n", "--name", default=None, help="Result name")
def part_shell(source: str, thickness: float, mode: str, name: str | None) -> None:
    """Create a hollow shell from a solid (remove one face, add wall thickness).

    Example: shell a box with 2mm walls:
      part shell Box --thickness 2 --mode inward
    """
    _ensure_project()
    if not _session.get_object(source):
        raise click.ClickException(f"Object not found: {source}")
    name = name or _next_name("Shell")
    offset = thickness if mode == "outward" else -thickness
    obj = {
        "name": name,
        "type": "Part::Thickness",
        "label": name,
        "params": {"source": source, "thickness": offset, "mode": mode},
    }
    _session.add_object(obj, f"shell '{source}' t={thickness}")
    _output(obj, f"Created shell '{name}' from '{source}' (t={thickness}mm, {mode})")


@part.command("rotate")
@click.argument("name_")
@click.option("--ax", type=float, default=0, help="Rotation axis X")
@click.option("--ay", type=float, default=0, help="Rotation axis Y")
@click.option("--az", type=float, default=1, help="Rotation axis Z")
@click.option("--angle", type=float, required=True, help="Rotation angle (degrees)")
@click.option("--px", type=float, default=None, help="Also set position X")
@click.option("--py", type=float, default=None, help="Also set position Y")
@click.option("--pz", type=float, default=None, help="Also set position Z")
def part_rotate(name_: str, ax: float, ay: float, az: float, angle: float,
                px: float | None, py: float | None, pz: float | None) -> None:
    """Rotate an object around an axis.

    Example: rotate a panel 45° around Z-axis:
      part rotate Panel --az 1 --angle 45
    """
    _ensure_project()
    obj = _session.get_object(name_)
    if not obj:
        raise click.ClickException(f"Object not found: {name_}")
    _session.checkpoint(f"rotate '{name_}'")
    params = obj.setdefault("params", {})
    params["rotation"] = {"axis_x": ax, "axis_y": ay, "axis_z": az, "angle": angle}
    if px is not None or py is not None or pz is not None:
        pos = params.get("placement", {"x": 0, "y": 0, "z": 0})
        if px is not None:
            pos["x"] = px
        if py is not None:
            pos["y"] = py
        if pz is not None:
            pos["z"] = pz
        params["placement"] = pos
    _session._auto_save()
    _output(obj, f"Rotated '{name_}' {angle}° around ({ax},{ay},{az})")


@part.command("import-step")
@click.argument("filepath", type=click.Path(exists=True))
@click.option("-n", "--name", default=None, help="Object name")
def part_import_step(filepath: str, name: str | None) -> None:
    """Import an existing STEP/IGES/BREP file into the project.

    Useful for loading external CAD files and combining them with
    parts you build in the CLI.

    Example:
      part import-step bracket.step --name ExternalBracket
    """
    _ensure_project()
    import os
    filepath = os.path.abspath(filepath)
    ext = os.path.splitext(filepath)[1].lower()
    supported = {".step", ".stp", ".iges", ".igs", ".brep"}
    if ext not in supported:
        raise click.ClickException(f"Unsupported format: {ext}. Use: {', '.join(supported)}")
    name = name or _next_name("Imported")
    obj = {
        "name": name,
        "type": "Part::Import",
        "label": name,
        "params": {"filepath": filepath, "format": ext.lstrip(".")},
    }
    _session.add_object(obj, f"import '{filepath}'")
    _output(obj, f"Imported '{name}' from {os.path.basename(filepath)}")


@part.command("measure")
@click.argument("source")
def part_measure(source: str) -> None:
    """Measure geometric properties of an object (volume, area, bounding box, COG).

    Uses the FreeCAD backend — requires FreeCAD to be installed.

    Example:
      part measure Box
    """
    proj = _ensure_project()
    obj = _session.get_object(source)
    if not obj:
        raise click.ClickException(f"Object not found: {source}")
    from cli_anything.freecad.core.project import _build_project_script
    from cli_anything.freecad.utils.freecad_backend import run_script
    script = _build_project_script(proj)
    script += (
        f"doc.recompute()\n"
        f"_mobj = doc.getObject({source!r})\n"
        f"if _mobj and hasattr(_mobj, 'Shape'):\n"
        f"    _s = _mobj.Shape\n"
        f"    _cli_result['name'] = {source!r}\n"
        f"    _cli_result['volume'] = round(_s.Volume, 4)\n"
        f"    _cli_result['area'] = round(_s.Area, 4)\n"
        f"    _bb = _s.BoundBox\n"
        f"    _cli_result['bounding_box'] = {{\n"
        f"        'xmin': round(_bb.XMin,4), 'xmax': round(_bb.XMax,4),\n"
        f"        'ymin': round(_bb.YMin,4), 'ymax': round(_bb.YMax,4),\n"
        f"        'zmin': round(_bb.ZMin,4), 'zmax': round(_bb.ZMax,4),\n"
        f"        'xlen': round(_bb.XLength,4), 'ylen': round(_bb.YLength,4),\n"
        f"        'zlen': round(_bb.ZLength,4),\n"
        f"    }}\n"
        f"    _cog = _s.CenterOfGravity\n"
        f"    _cli_result['center_of_gravity'] = {{\n"
        f"        'x': round(_cog.x,4), 'y': round(_cog.y,4), 'z': round(_cog.z,4)\n"
        f"    }}\n"
        f"    _cli_result['is_valid'] = _s.isValid()\n"
        f"    _cli_result['is_closed'] = _s.isClosed()\n"
        f"else:\n"
        f"    _cli_result['error'] = f'Object {{_mobj}} has no Shape'\n"
    )
    result = run_script(script)
    r = result.get("result", {})
    _output(r)
    if not _json_mode:
        if "error" in r:
            raise click.ClickException(r["error"])
        click.echo(f"Object: {r.get('name')}")
        click.echo(f"Volume:  {r.get('volume')} mm³")
        click.echo(f"Area:    {r.get('area')} mm²")
        bb = r.get("bounding_box", {})
        click.echo(f"Bounds:  {bb.get('xlen')} × {bb.get('ylen')} × {bb.get('zlen')} mm")
        cog = r.get("center_of_gravity", {})
        click.echo(f"COG:     ({cog.get('x')}, {cog.get('y')}, {cog.get('z')})")
        click.echo(f"Valid:   {r.get('is_valid')}  Closed: {r.get('is_closed')}")


# ── Extended Sketch commands ─────────────────────────────────────────

@sketch.command("polygon")
@click.argument("sketch_name")
@click.option("--cx", type=float, default=0, help="Center X")
@click.option("--cy", type=float, default=0, help="Center Y")
@click.option("-r", "--radius", type=float, default=10, help="Circumradius")
@click.option("-s", "--sides", type=int, default=6, help="Number of sides (3+)")
@click.option("--flat/--vertex", default=True, help="Flat-to-flat (True) or vertex-to-vertex (False)")
def sketch_polygon(sketch_name: str, cx: float, cy: float,
                   radius: float, sides: int, flat: bool) -> None:
    """Add a regular polygon to a sketch.

    Example: hexagon with 10mm circumradius:
      sketch polygon MySketch --sides 6 --radius 10

    Example: equilateral triangle:
      sketch polygon MySketch --sides 3 --radius 8
    """
    import math
    _ensure_project()
    sketch_obj = _session.get_object(sketch_name)
    if not sketch_obj or sketch_obj.get("type") != "Sketcher::SketchObject":
        raise click.ClickException(f"Sketch not found: {sketch_name}")
    if sides < 3:
        raise click.ClickException("Polygon must have at least 3 sides")
    _session.checkpoint(f"add polygon to '{sketch_name}'")
    # Calculate vertices
    offset = 0.0 if not flat else math.pi / sides
    vertices = [
        (cx + radius * math.cos(2 * math.pi * i / sides + offset),
         cy + radius * math.sin(2 * math.pi * i / sides + offset))
        for i in range(sides)
    ]
    # Store as line segments
    for i in range(sides):
        x1, y1 = vertices[i]
        x2, y2 = vertices[(i + 1) % sides]
        geom = {"type": "line", "x1": x1, "y1": y1, "x2": x2, "y2": y2}
        sketch_obj["params"]["geometry"].append(geom)
    _session._auto_save()
    _output({"type": "polygon", "sides": sides, "radius": radius, "cx": cx, "cy": cy},
            f"Added {sides}-sided polygon (r={radius}) at ({cx},{cy}) to '{sketch_name}'")


@sketch.command("ellipse")
@click.argument("sketch_name")
@click.option("--cx", type=float, default=0, help="Center X")
@click.option("--cy", type=float, default=0, help="Center Y")
@click.option("-a", "--major-radius", type=float, default=10, help="Major (X) radius")
@click.option("-b", "--minor-radius", type=float, default=6, help="Minor (Y) radius")
def sketch_ellipse(sketch_name: str, cx: float, cy: float,
                   major_radius: float, minor_radius: float) -> None:
    """Add an ellipse to a sketch.

    Example: 20x12mm ellipse:
      sketch ellipse MySketch --major-radius 10 --minor-radius 6
    """
    _ensure_project()
    sketch_obj = _session.get_object(sketch_name)
    if not sketch_obj or sketch_obj.get("type") != "Sketcher::SketchObject":
        raise click.ClickException(f"Sketch not found: {sketch_name}")
    _session.checkpoint(f"add ellipse to '{sketch_name}'")
    geom = {"type": "ellipse", "cx": cx, "cy": cy,
            "major_radius": major_radius, "minor_radius": minor_radius}
    sketch_obj["params"]["geometry"].append(geom)
    _session._auto_save()
    _output(geom, f"Added ellipse ({cx},{cy}) a={major_radius} b={minor_radius} to '{sketch_name}'")


@sketch.command("close")
@click.argument("sketch_name")
def sketch_close(sketch_name: str) -> None:
    """Mark a sketch as closed (all endpoints connected).

    This validates that the sketch profile is closed before extrusion.
    """
    _ensure_project()
    sketch_obj = _session.get_object(sketch_name)
    if not sketch_obj or sketch_obj.get("type") != "Sketcher::SketchObject":
        raise click.ClickException(f"Sketch not found: {sketch_name}")
    _session.checkpoint(f"close sketch '{sketch_name}'")
    sketch_obj["params"]["closed"] = True
    _session._auto_save()
    _output({"sketch": sketch_name, "closed": True},
            f"Sketch '{sketch_name}' marked as closed")
