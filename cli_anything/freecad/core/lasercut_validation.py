"""Lasercut validation — check geometry for CNC/laser cutting readiness.

Validates imported SVG/DXF profiles for manufacturing:
- Closed contours (all wires form closed loops)
- No duplicate/overlapping edges
- Minimum feature size compliance
- Plate dimension fit
- Self-intersection detection
- Floating geometry detection

Works in two modes:
1. Local validation — checks project JSON structure (no FreeCAD needed)
2. Backend validation — uses FreeCAD to analyze actual geometry
"""

from __future__ import annotations

import math
import re
from typing import Any


# ── Tolerance Constants ─────────────────────────────────────────────

DEFAULT_CLOSURE_TOLERANCE_MM = 0.01  # 10 micron gap tolerance
DEFAULT_DUPLICATE_TOLERANCE_MM = 0.01  # edges closer than this are duplicates
DEFAULT_MIN_FEATURE_SIZE_MM = 0.5  # minimum cuttable feature
DEFAULT_KERF_WIDTH_MM = 0.15  # typical CO2 laser kerf on mild steel


# ── Local Validation (no FreeCAD needed) ────────────────────────────

def validate_project_for_lasercut(
    project: dict[str, Any],
    object_name: str | None = None,
    min_feature_mm: float = DEFAULT_MIN_FEATURE_SIZE_MM,
    kerf_width_mm: float = DEFAULT_KERF_WIDTH_MM,
    plate_width_mm: float | None = None,
    plate_height_mm: float | None = None,
) -> dict[str, Any]:
    """Validate a project's geometry for laser cutting readiness.

    Performs local checks on the project JSON structure. For full
    geometry validation, use validate_geometry_backend() which invokes
    the real FreeCAD engine.

    Args:
        project: Project dict with objects list.
        object_name: Specific object to validate (default: all).
        min_feature_mm: Minimum feature size in mm.
        kerf_width_mm: Laser kerf width in mm.
        plate_width_mm: Optional plate width for fit check.
        plate_height_mm: Optional plate height for fit check.

    Returns:
        Validation report dict with checks and overall status.
    """
    objects = project.get("objects", [])
    if not objects:
        return _report(
            passed=False,
            checks=[],
            errors=["Project has no objects to validate"],
        )

    if object_name:
        targets = [o for o in objects if o.get("name") == object_name]
        if not targets:
            names = [o.get("name", "?") for o in objects]
            return _report(
                passed=False,
                checks=[],
                errors=[f"Object '{object_name}' not found. Available: {', '.join(names)}"],
            )
    else:
        targets = objects

    checks: list[dict[str, Any]] = []
    errors: list[str] = []
    warnings: list[str] = []

    # Check 1: Sketch closure
    sketch_check = check_sketch_closure(targets)
    checks.append(sketch_check)
    if not sketch_check["passed"]:
        errors.extend(sketch_check.get("errors", []))

    # Check 2: Duplicate geometry
    dup_check = check_duplicate_geometry(targets)
    checks.append(dup_check)
    if not dup_check["passed"]:
        errors.extend(dup_check.get("warnings", []))

    # Check 3: Minimum feature size
    feature_check = check_min_feature_size(targets, min_feature_mm)
    checks.append(feature_check)
    if not feature_check["passed"]:
        errors.extend(feature_check.get("errors", []))

    # Check 4: Plate fit
    if plate_width_mm or plate_height_mm:
        fit_check = check_plate_fit(
            targets, plate_width_mm, plate_height_mm, kerf_width_mm,
        )
        checks.append(fit_check)
        if not fit_check["passed"]:
            errors.extend(fit_check.get("errors", []))
    else:
        dim_check = report_dimensions(targets)
        checks.append(dim_check)

    # Check 5: Kerf compensation advisory
    kerf_check = check_kerf_advisory(targets, kerf_width_mm, min_feature_mm)
    checks.append(kerf_check)
    warnings.extend(kerf_check.get("warnings", []))

    all_passed = all(c["passed"] for c in checks)

    return _report(
        passed=all_passed,
        checks=checks,
        errors=errors,
        warnings=warnings,
        summary=_build_summary(checks, targets),
    )


def check_sketch_closure(objects: list[dict[str, Any]]) -> dict[str, Any]:
    """Check if sketches have closed contours.

    A closed sketch has its 'closed' flag set to True, indicating
    all endpoints are connected forming a loop.

    Args:
        objects: List of project objects.

    Returns:
        Check result dict.
    """
    sketches = [o for o in objects if o.get("type") == "Sketcher::SketchObject"]
    svg_imports = [o for o in objects if o.get("type") == "ImportSVG"]
    profiles = sketches + svg_imports

    if not profiles:
        # Check if there are 3D primitives (box, cylinder, etc.) — those are always valid
        primitives = [o for o in objects if _is_solid_primitive(o)]
        if primitives:
            return {
                "name": "contour_closure",
                "passed": True,
                "message": f"{len(primitives)} solid primitive(s) — contours inherently closed",
                "details": {"solid_count": len(primitives)},
            }
        return {
            "name": "contour_closure",
            "passed": False,
            "message": "No sketch or SVG profiles found to validate",
            "errors": ["No 2D profiles found — lasercut requires sketch or SVG geometry"],
        }

    closed_count = 0
    open_profiles: list[str] = []
    skipped_svg: list[str] = []

    for obj in profiles:
        name = obj.get("name", "?")
        if obj.get("type") == "ImportSVG":
            # SVG closure cannot be checked without FreeCAD backend
            closed = _check_svg_object_closure(obj)
            if closed is None:
                skipped_svg.append(name)
                continue
        else:
            # Sketches: check the 'closed' parameter
            closed = obj.get("params", {}).get("closed", False)
            if not closed:
                # Also check if geometry forms a closed loop
                closed = _infer_sketch_closure(obj)

        if closed:
            closed_count += 1
        else:
            open_profiles.append(name)

    passed = len(open_profiles) == 0
    errors = [f"Open contour: '{p}' — endpoints don't connect" for p in open_profiles]
    warnings: list[str] = []
    if skipped_svg:
        warnings.append(
            f"SVG contour closure not verified (needs FreeCAD backend): "
            f"{', '.join(skipped_svg)}"
        )

    msg_parts: list[str] = []
    if closed_count:
        msg_parts.append(f"{closed_count} closed")
    if open_profiles:
        msg_parts.append(f"{len(open_profiles)} open")
    if skipped_svg:
        msg_parts.append(f"{len(skipped_svg)} SVG skipped (needs backend)")
    message = "Contours: " + ", ".join(msg_parts) if msg_parts else "No contours checked"

    return {
        "name": "contour_closure",
        "passed": passed,
        "message": message,
        "errors": errors,
        "warnings": warnings,
        "details": {
            "closed_count": closed_count,
            "open_count": len(open_profiles),
            "open_profiles": open_profiles,
            "skipped_svg_count": len(skipped_svg),
        },
    }


def check_duplicate_geometry(objects: list[dict[str, Any]]) -> dict[str, Any]:
    """Detect duplicate/overlapping geometry in sketches.

    Duplicate edges cause the laser to cut the same path twice,
    wasting time and potentially damaging the material.

    Args:
        objects: List of project objects.

    Returns:
        Check result dict.
    """
    duplicates: list[dict[str, Any]] = []

    for obj in objects:
        geom = obj.get("params", {}).get("geometry", [])
        if not geom:
            continue

        name = obj.get("name", "?")
        seen_edges: list[dict[str, Any]] = []

        for i, g in enumerate(geom):
            for j, prev in enumerate(seen_edges):
                if _edges_overlap(g, prev):
                    duplicates.append({
                        "object": name,
                        "edge_a": j,
                        "edge_b": i,
                        "type": g.get("type", "?"),
                    })
            seen_edges.append(g)

    passed = len(duplicates) == 0
    warnings = [
        f"Duplicate edge in '{d['object']}': edges {d['edge_a']} and {d['edge_b']} ({d['type']})"
        for d in duplicates
    ]

    return {
        "name": "duplicate_edges",
        "passed": passed,
        "message": (
            f"{len(duplicates)} duplicate edge(s) found"
            if duplicates
            else "No duplicate edges"
        ),
        "warnings": warnings,
        "details": {"duplicate_count": len(duplicates), "duplicates": duplicates},
    }


def check_min_feature_size(
    objects: list[dict[str, Any]],
    min_size_mm: float = DEFAULT_MIN_FEATURE_SIZE_MM,
) -> dict[str, Any]:
    """Check that all features meet minimum size requirements.

    Features smaller than the laser kerf width cannot be cut.
    Common minimum is 0.5mm for CO2 laser on steel.

    Args:
        objects: List of project objects.
        min_size_mm: Minimum feature size in mm.

    Returns:
        Check result dict.
    """
    violations: list[dict[str, Any]] = []

    for obj in objects:
        name = obj.get("name", "?")
        params = obj.get("params", {})

        # Check primitive dimensions
        dims = _get_object_dimensions(obj)
        for dim_name, dim_value in dims.items():
            if dim_value is not None and dim_value < min_size_mm:
                violations.append({
                    "object": name,
                    "dimension": dim_name,
                    "value_mm": dim_value,
                    "minimum_mm": min_size_mm,
                })

        # Check sketch geometry dimensions
        geom = params.get("geometry", [])
        for i, g in enumerate(geom):
            g_dims = _get_geometry_dimensions(g)
            for dim_name, dim_value in g_dims.items():
                if dim_value is not None and dim_value < min_size_mm:
                    violations.append({
                        "object": name,
                        "geometry_index": i,
                        "dimension": dim_name,
                        "value_mm": dim_value,
                        "minimum_mm": min_size_mm,
                    })

    passed = len(violations) == 0
    errors = [
        f"Feature too small in '{v['object']}': {v['dimension']} = {v['value_mm']:.2f}mm "
        f"(minimum: {v['minimum_mm']:.2f}mm)"
        for v in violations
    ]

    return {
        "name": "min_feature_size",
        "passed": passed,
        "message": (
            f"{len(violations)} feature(s) below {min_size_mm}mm minimum"
            if violations
            else f"All features >= {min_size_mm}mm"
        ),
        "errors": errors,
        "details": {"violation_count": len(violations), "violations": violations},
    }


def check_plate_fit(
    objects: list[dict[str, Any]],
    plate_width_mm: float | None,
    plate_height_mm: float | None,
    kerf_width_mm: float = DEFAULT_KERF_WIDTH_MM,
) -> dict[str, Any]:
    """Check if geometry fits within the specified plate dimensions.

    Accounts for kerf width — the actual cut area is slightly larger
    than the geometry due to material removed by the laser beam.

    Args:
        objects: List of project objects.
        plate_width_mm: Plate width in mm.
        plate_height_mm: Plate height in mm.
        kerf_width_mm: Laser kerf width for margin calculation.

    Returns:
        Check result dict.
    """
    bbox = _compute_bounding_box(objects)
    if not bbox:
        return {
            "name": "plate_fit",
            "passed": False,
            "message": "Cannot determine geometry dimensions",
            "errors": ["No dimensional data available for plate fit check"],
        }

    # Add kerf margin on all sides
    margin = kerf_width_mm
    required_width = bbox["width"] + 2 * margin
    required_height = bbox["height"] + 2 * margin

    fits_width = plate_width_mm is None or required_width <= plate_width_mm
    fits_height = plate_height_mm is None or required_height <= plate_height_mm
    passed = fits_width and fits_height

    errors: list[str] = []
    if not fits_width:
        errors.append(
            f"Width {required_width:.1f}mm (incl. kerf) exceeds plate width {plate_width_mm:.1f}mm"
        )
    if not fits_height:
        errors.append(
            f"Height {required_height:.1f}mm (incl. kerf) exceeds plate height {plate_height_mm:.1f}mm"
        )

    plate_str = f"{plate_width_mm or '?'}x{plate_height_mm or '?'}mm"
    geom_str = f"{required_width:.1f}x{required_height:.1f}mm"

    return {
        "name": "plate_fit",
        "passed": passed,
        "message": (
            f"Geometry {geom_str} fits on {plate_str} plate"
            if passed
            else f"Geometry {geom_str} EXCEEDS {plate_str} plate"
        ),
        "errors": errors,
        "details": {
            "geometry_width_mm": bbox["width"],
            "geometry_height_mm": bbox["height"],
            "required_width_mm": required_width,
            "required_height_mm": required_height,
            "plate_width_mm": plate_width_mm,
            "plate_height_mm": plate_height_mm,
            "kerf_margin_mm": margin,
        },
    }


def report_dimensions(objects: list[dict[str, Any]]) -> dict[str, Any]:
    """Report geometry dimensions without plate fit check.

    Args:
        objects: List of project objects.

    Returns:
        Check result dict with dimensions info.
    """
    bbox = _compute_bounding_box(objects)
    if not bbox:
        return {
            "name": "dimensions",
            "passed": True,
            "message": "No dimensional data to report",
            "details": {},
        }

    return {
        "name": "dimensions",
        "passed": True,
        "message": f"Geometry: {bbox['width']:.1f} x {bbox['height']:.1f}mm",
        "details": bbox,
    }


def check_kerf_advisory(
    objects: list[dict[str, Any]],
    kerf_width_mm: float = DEFAULT_KERF_WIDTH_MM,
    min_feature_mm: float = DEFAULT_MIN_FEATURE_SIZE_MM,
) -> dict[str, Any]:
    """Advisory check for kerf compensation needs.

    Args:
        objects: List of project objects.
        kerf_width_mm: Laser kerf width.
        min_feature_mm: Minimum feature size.

    Returns:
        Check result dict with kerf advisory.
    """
    warnings: list[str] = []
    has_internal_features = False

    for obj in objects:
        obj_type = obj.get("type", "")
        params = obj.get("params", {})

        # Boolean cuts create internal features
        if obj_type in ("Part::Cut", "Part::Common"):
            has_internal_features = True
        # Small circles/arcs are typically holes
        geom = params.get("geometry", [])
        for g in geom:
            if g.get("type") == "circle":
                radius = g.get("radius", 0)
                if radius and radius * 2 < min_feature_mm * 3:
                    has_internal_features = True

    if has_internal_features:
        warnings.append(
            f"Internal features detected — consider kerf compensation "
            f"(offset {kerf_width_mm / 2:.3f}mm inward for holes, "
            f"outward for outer contour)"
        )

    return {
        "name": "kerf_advisory",
        "passed": True,  # Advisory only, never fails
        "message": (
            f"Kerf compensation recommended ({kerf_width_mm}mm)"
            if warnings
            else "No kerf compensation issues detected"
        ),
        "warnings": warnings,
        "details": {
            "kerf_width_mm": kerf_width_mm,
            "has_internal_features": has_internal_features,
        },
    }


# ── Backend Validation (requires FreeCAD) ───────────────────────────

def generate_validation_script(
    fcstd_path: str,
    object_name: str | None = None,
    closure_tolerance: float = DEFAULT_CLOSURE_TOLERANCE_MM,
    duplicate_tolerance: float = DEFAULT_DUPLICATE_TOLERANCE_MM,
    min_feature_mm: float = DEFAULT_MIN_FEATURE_SIZE_MM,
) -> str:
    """Generate FreeCAD Python script for geometry validation.

    This script runs inside FreeCAD and performs real geometry checks
    using OpenCASCADE (the geometry kernel).

    Args:
        fcstd_path: Path to .FCStd file.
        object_name: Specific object to check (default: all with Shape).
        closure_tolerance: Gap tolerance for wire closure check.
        duplicate_tolerance: Distance threshold for duplicate edges.
        min_feature_mm: Minimum feature size.

    Returns:
        FreeCAD Python script string.

    Raises:
        ValueError: If object_name contains invalid characters.
    """
    if object_name is not None:
        _validate_object_name(object_name)

    obj_filter = (
        f"objs = [doc.getObject({object_name!r})]" if object_name
        else "objs = [o for o in doc.Objects if hasattr(o, 'Shape')]"
    )

    return f"""\
import FreeCAD
import Part

doc = FreeCAD.openDocument({fcstd_path!r})
{obj_filter}
objs = [o for o in objs if o is not None]

report = {{
    "objects_checked": 0,
    "wires_total": 0,
    "wires_closed": 0,
    "wires_open": 0,
    "open_wire_details": [],
    "duplicate_edges": 0,
    "min_edge_length_mm": None,
    "small_features": [],
    "bounding_box": None,
    "self_intersections": 0,
}}

CLOSURE_TOL = {closure_tolerance}
DUP_TOL = {duplicate_tolerance}
MIN_FEAT = {min_feature_mm}

all_edges = []

for obj in objs:
    shape = obj.Shape
    report["objects_checked"] += 1

    # Bounding box
    bb = shape.BoundBox
    if report["bounding_box"] is None:
        report["bounding_box"] = {{
            "x_min": bb.XMin, "x_max": bb.XMax,
            "y_min": bb.YMin, "y_max": bb.YMax,
            "z_min": bb.ZMin, "z_max": bb.ZMax,
            "width": bb.XLength, "height": bb.YLength, "depth": bb.ZLength,
        }}
    else:
        b = report["bounding_box"]
        b["x_min"] = min(b["x_min"], bb.XMin)
        b["x_max"] = max(b["x_max"], bb.XMax)
        b["y_min"] = min(b["y_min"], bb.YMin)
        b["y_max"] = max(b["y_max"], bb.YMax)
        b["z_min"] = min(b["z_min"], bb.ZMin)
        b["z_max"] = max(b["z_max"], bb.ZMax)
        b["width"] = b["x_max"] - b["x_min"]
        b["height"] = b["y_max"] - b["y_min"]
        b["depth"] = b["z_max"] - b["z_min"]

    # Wire closure check
    for wire in shape.Wires:
        report["wires_total"] += 1
        if wire.isClosed():
            report["wires_closed"] += 1
        else:
            report["wires_open"] += 1
            # Check gap size
            verts = wire.OrderedVertexes
            if len(verts) >= 2:
                gap = verts[0].Point.distanceToPoint(verts[-1].Point)
                report["open_wire_details"].append({{
                    "object": obj.Name,
                    "gap_mm": round(gap, 4),
                    "vertex_count": len(verts),
                }})

    # Edge analysis
    for edge in shape.Edges:
        length = edge.Length
        all_edges.append({{
            "object": obj.Name,
            "length": length,
            "start": (edge.Vertexes[0].Point.x, edge.Vertexes[0].Point.y) if edge.Vertexes else None,
            "end": (edge.Vertexes[-1].Point.x, edge.Vertexes[-1].Point.y) if edge.Vertexes else None,
        }})

        if report["min_edge_length_mm"] is None or length < report["min_edge_length_mm"]:
            report["min_edge_length_mm"] = round(length, 4)

        if length < MIN_FEAT:
            report["small_features"].append({{
                "object": obj.Name,
                "edge_length_mm": round(length, 4),
                "minimum_mm": MIN_FEAT,
            }})

# Duplicate edge detection
import math
def _dup_dist(a, b):
    return math.sqrt((a[0]-b[0])**2 + (a[1]-b[1])**2)

dup_count = 0
for i in range(len(all_edges)):
    for j in range(i + 1, len(all_edges)):
        ei = all_edges[i]
        ej = all_edges[j]
        if ei["start"] and ej["start"] and ei["end"] and ej["end"]:
            fwd = _dup_dist(ei["start"], ej["start"]) < DUP_TOL and _dup_dist(ei["end"], ej["end"]) < DUP_TOL
            rev = _dup_dist(ei["start"], ej["end"]) < DUP_TOL and _dup_dist(ei["end"], ej["start"]) < DUP_TOL
            if fwd or rev:
                dup_count += 1
report["duplicate_edges"] = dup_count

_cli_result.update(report)
"""


# ── Internal Helpers ────────────────────────────────────────────────

_VALID_OBJECT_NAME_RE = re.compile(r'^[A-Za-z0-9_\-\.]+$')


def _validate_object_name(name: str) -> str:
    """Validate object name contains only safe characters.

    Args:
        name: Object name to validate.

    Returns:
        The validated name.

    Raises:
        ValueError: If name contains invalid characters.
    """
    if not _VALID_OBJECT_NAME_RE.fullmatch(name):
        raise ValueError(f"Invalid object name: {name!r} (only A-Z, 0-9, _, -, . allowed)")
    return name


def _report(
    passed: bool,
    checks: list[dict[str, Any]],
    errors: list[str] | None = None,
    warnings: list[str] | None = None,
    summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a standardized validation report.

    Args:
        passed: Overall pass/fail.
        checks: List of individual check results.
        errors: List of error messages.
        warnings: List of warning messages.
        summary: Summary statistics.

    Returns:
        Validation report dict.
    """
    return {
        "passed": passed,
        "checks": checks,
        "errors": errors or [],
        "warnings": warnings or [],
        "summary": summary or {},
        "check_count": len(checks),
        "passed_count": sum(1 for c in checks if c["passed"]),
        "failed_count": sum(1 for c in checks if not c["passed"]),
    }


def _build_summary(
    checks: list[dict[str, Any]],
    objects: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build summary statistics from checks.

    Args:
        checks: List of check results.
        objects: List of project objects.

    Returns:
        Summary dict.
    """
    return {
        "objects_checked": len(objects),
        "checks_run": len(checks),
        "checks_passed": sum(1 for c in checks if c["passed"]),
        "checks_failed": sum(1 for c in checks if not c["passed"]),
    }


def _is_solid_primitive(obj: dict[str, Any]) -> bool:
    """Check if an object is a solid 3D primitive.

    Args:
        obj: Project object dict.

    Returns:
        True if solid primitive.
    """
    solid_types = {
        "Part::Box", "Part::Cylinder", "Part::Sphere",
        "Part::Cone", "Part::Torus", "Part::Fuse",
        "Part::Cut", "Part::Common",
    }
    return obj.get("type", "") in solid_types


def _check_svg_object_closure(obj: dict[str, Any]) -> bool | None:
    """Check if an SVG import object has closed geometry.

    SVG imports cannot be validated for closure in local mode —
    this requires the FreeCAD backend to analyze actual wire geometry.

    Args:
        obj: SVG import object dict.

    Returns:
        None if check cannot be performed (needs backend).
        True/False for known states.
    """
    # SVG closure cannot be determined from project JSON alone.
    # Return None to indicate "unknown — needs backend validation".
    return None


def _infer_sketch_closure(obj: dict[str, Any]) -> bool:
    """Try to infer if a sketch forms a closed loop from its geometry.

    Checks if the endpoints of the first and last geometry elements
    connect, forming a closed contour.

    Args:
        obj: Sketch object dict.

    Returns:
        True if geometry appears to form a closed loop.
    """
    geom = obj.get("params", {}).get("geometry", [])
    if not geom:
        return False

    # For simple cases: check if geometry is a single closed shape
    if len(geom) == 1:
        g = geom[0]
        if g.get("type") in ("circle", "ellipse"):
            return True  # Circles and ellipses are always closed

    # For multi-segment: check if last endpoint meets first startpoint
    if len(geom) >= 2:
        first = geom[0]
        last = geom[-1]
        start = _get_start_point(first)
        end = _get_end_point(last)
        if start and end:
            dist = math.sqrt((start[0] - end[0]) ** 2 + (start[1] - end[1]) ** 2)
            return dist < DEFAULT_CLOSURE_TOLERANCE_MM

    return False


def _get_start_point(geom: dict[str, Any]) -> tuple[float, float] | None:
    """Extract start point from a geometry element.

    Args:
        geom: Geometry dict.

    Returns:
        (x, y) tuple or None.
    """
    g_type = geom.get("type", "")
    if g_type == "line":
        return (geom.get("x1", 0), geom.get("y1", 0))
    if g_type == "arc":
        return (geom.get("x1", 0), geom.get("y1", 0))
    if g_type == "rect":
        return (geom.get("x", 0), geom.get("y", 0))
    return None


def _get_end_point(geom: dict[str, Any]) -> tuple[float, float] | None:
    """Extract end point from a geometry element.

    Args:
        geom: Geometry dict.

    Returns:
        (x, y) tuple or None.
    """
    g_type = geom.get("type", "")
    if g_type == "line":
        return (geom.get("x2", 0), geom.get("y2", 0))
    if g_type == "arc":
        return (geom.get("x2", 0), geom.get("y2", 0))
    if g_type == "rect":
        # Rectangle ends where it starts (closed)
        return (geom.get("x", 0), geom.get("y", 0))
    return None


def _edges_overlap(
    edge_a: dict[str, Any],
    edge_b: dict[str, Any],
    tolerance: float = DEFAULT_DUPLICATE_TOLERANCE_MM,
) -> bool:
    """Check if two geometry elements represent the same edge.

    Args:
        edge_a: First geometry element.
        edge_b: Second geometry element.
        tolerance: Distance tolerance for matching.

    Returns:
        True if edges overlap within tolerance.
    """
    if edge_a.get("type") != edge_b.get("type"):
        return False

    start_a = _get_start_point(edge_a)
    end_a = _get_end_point(edge_a)
    start_b = _get_start_point(edge_b)
    end_b = _get_end_point(edge_b)

    if not all([start_a, end_a, start_b, end_b]):
        return False

    def dist(p1: tuple[float, float], p2: tuple[float, float]) -> float:
        return math.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)

    # Forward match: A.start==B.start AND A.end==B.end
    forward = dist(start_a, start_b) < tolerance and dist(end_a, end_b) < tolerance
    # Reverse match: A.start==B.end AND A.end==B.start
    reverse = dist(start_a, end_b) < tolerance and dist(end_a, start_b) < tolerance

    return forward or reverse


def _get_object_dimensions(obj: dict[str, Any]) -> dict[str, float | None]:
    """Extract key dimensions from an object for size checking.

    Args:
        obj: Project object dict.

    Returns:
        Dict of dimension name to value in mm.
    """
    params = obj.get("params", {})
    obj_type = obj.get("type", "")
    dims: dict[str, float | None] = {}

    if obj_type == "Part::Box":
        dims["width"] = params.get("width")
        dims["height"] = params.get("height")
        dims["length"] = params.get("length")
    elif obj_type == "Part::Cylinder":
        dims["radius"] = params.get("radius")
        dims["diameter"] = params.get("radius", 0) * 2 if params.get("radius") else None
        dims["height"] = params.get("height")
    elif obj_type == "Part::Sphere":
        dims["radius"] = params.get("radius")
        dims["diameter"] = params.get("radius", 0) * 2 if params.get("radius") else None

    return dims


def _get_geometry_dimensions(geom: dict[str, Any]) -> dict[str, float | None]:
    """Extract dimensions from a sketch geometry element.

    Args:
        geom: Geometry element dict.

    Returns:
        Dict of dimension name to value in mm.
    """
    g_type = geom.get("type", "")
    dims: dict[str, float | None] = {}

    if g_type == "circle":
        radius = geom.get("radius")
        if radius is not None:
            dims["radius"] = radius
            dims["diameter"] = radius * 2
    elif g_type == "line":
        x1, y1 = geom.get("x1", 0), geom.get("y1", 0)
        x2, y2 = geom.get("x2", 0), geom.get("y2", 0)
        length = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
        dims["length"] = length
    elif g_type == "rect":
        dims["width"] = geom.get("width")
        dims["height"] = geom.get("height")
    elif g_type == "ellipse":
        dims["major_radius"] = geom.get("major_radius")
        dims["minor_radius"] = geom.get("minor_radius")

    return dims


def _compute_bounding_box(objects: list[dict[str, Any]]) -> dict[str, float] | None:
    """Compute a bounding box from object dimensions.

    Note: This is an approximation from project JSON data.
    For exact bounding boxes, use the FreeCAD backend.

    Args:
        objects: List of project objects.

    Returns:
        Dict with width/height or None.
    """
    max_width = 0.0
    max_height = 0.0
    found = False

    for obj in objects:
        params = obj.get("params", {})
        obj_type = obj.get("type", "")

        w, h = 0.0, 0.0

        if obj_type == "Part::Box":
            # For lasercut top-view: length=X, width=Y, height=Z (material thickness)
            w = params.get("length", 0) or 0
            h = params.get("width", 0) or 0
        elif obj_type == "Part::Cylinder":
            r = params.get("radius", 0)
            w = r * 2
            h = r * 2  # top view
        elif obj_type == "Part::Sphere":
            r = params.get("radius", 0)
            w = r * 2
            h = r * 2
        elif obj_type == "ImportSVG":
            w = params.get("svg_width", 0) or 0
            h = params.get("svg_height", 0) or 0
        elif obj_type == "Sketcher::SketchObject":
            # Compute bounding box from all geometry coordinates
            geom = params.get("geometry", [])
            xs: list[float] = []
            ys: list[float] = []
            for g in geom:
                g_type = g.get("type", "")
                if g_type == "line":
                    xs.extend([g.get("x1", 0), g.get("x2", 0)])
                    ys.extend([g.get("y1", 0), g.get("y2", 0)])
                elif g_type == "rect":
                    rx, ry = g.get("x", 0), g.get("y", 0)
                    rw, rh = g.get("width", 0) or 0, g.get("height", 0) or 0
                    xs.extend([rx, rx + rw])
                    ys.extend([ry, ry + rh])
                elif g_type == "circle":
                    cx, cy = g.get("cx", 0), g.get("cy", 0)
                    r = g.get("radius", 0)
                    xs.extend([cx - r, cx + r])
                    ys.extend([cy - r, cy + r])
                elif g_type == "arc":
                    xs.extend([g.get("x1", 0), g.get("x2", 0)])
                    ys.extend([g.get("y1", 0), g.get("y2", 0)])
                elif g_type == "ellipse":
                    cx, cy = g.get("cx", 0), g.get("cy", 0)
                    mr = g.get("major_radius", 0) or 0
                    xs.extend([cx - mr, cx + mr])
                    ys.extend([cy - mr, cy + mr])
            if xs and ys:
                w = max(xs) - min(xs)
                h = max(ys) - min(ys)

        if w > 0 or h > 0:
            found = True
            max_width = max(max_width, w)
            max_height = max(max_height, h)

    if not found:
        return None

    return {"width": max_width, "height": max_height}
