"""TechDraw module — 2D fabrication drawings, views, dimensions.

Creates TechDraw pages with views of 3D objects, dimensions, and
annotations, then exports to DXF/SVG/PDF via the real FreeCAD backend.
"""

from __future__ import annotations

import os
from typing import Any

from cli_anything.freecad.core.project import _build_project_script
from cli_anything.freecad.utils.freecad_backend import run_script


# Standard paper sizes (width x height in mm)
PAPER_SIZES = {
    "A4_Landscape": (297, 210),
    "A4_Portrait": (210, 297),
    "A3_Landscape": (420, 297),
    "A3_Portrait": (297, 420),
    "A2_Landscape": (594, 420),
    "A1_Landscape": (841, 594),
    "A0_Landscape": (1189, 841),
}

# View direction presets
# Engineering convention aliases added for clarity:
#   front-elevation = looking at front face (shows width x height)
#   side-elevation  = looking at side face (shows depth x height)
#   plan            = looking from above (shows width x depth)
VIEW_DIRECTIONS = {
    # Original FreeCAD-convention names (kept for backward compat)
    "front": (0, 0, 1),
    "back": (0, 0, -1),
    "top": (0, -1, 0),
    "bottom": (0, 1, 0),
    "left": (-1, 0, 0),
    "right": (1, 0, 0),
    "iso": (1, -1, 1),
    # Engineering-convention aliases
    "front-elevation": (0, -1, 0),  # Looking at front → X-Z (width x height)
    "side-elevation": (1, 0, 0),    # Looking at side → Y-Z (depth x height)
    "plan": (0, 0, 1),              # Looking from above → X-Y (width x depth)
    "rear-elevation": (0, 1, 0),    # Looking at back
}


def create_drawing(
    project: dict[str, Any],
    page_name: str = "Page",
    template: str = "A4_Landscape",
    scale: float = 1.0,
) -> dict[str, Any]:
    """Create a TechDraw page object in the project.

    Args:
        project: Project dict.
        page_name: Name for the page object.
        template: Paper size template name.
        scale: Drawing scale factor.

    Returns:
        Page object dict.
    """
    return {
        "name": page_name,
        "type": "TechDraw::DrawPage",
        "label": page_name,
        "params": {
            "template": template,
            "scale": scale,
            "views": [],
            "dimensions": [],
            "annotations": [],
        },
    }


def add_view(
    page_obj: dict[str, Any],
    source_name: str,
    view_name: str = "View",
    direction: str = "front",
    x: float = 100,
    y: float = 150,
    rotation: float = 0,
) -> dict[str, Any]:
    """Add a 2D view of a 3D object to a TechDraw page.

    Args:
        page_obj: Page object dict.
        source_name: Name of the 3D source object.
        view_name: Name for the view.
        direction: View direction preset or custom (dx,dy,dz).
        x: X position on page (mm).
        y: Y position on page (mm).
        rotation: View rotation (degrees).

    Returns:
        View dict.
    """
    if direction in VIEW_DIRECTIONS:
        dir_vec = VIEW_DIRECTIONS[direction]
    else:
        # Try to parse "dx,dy,dz" format
        try:
            parts = direction.split(",")
            dir_vec = tuple(float(p) for p in parts)
        except (ValueError, AttributeError):
            dir_vec = VIEW_DIRECTIONS["front"]

    view = {
        "name": view_name,
        "type": "TechDraw::DrawViewPart",
        "source": source_name,
        "direction": dir_vec,
        "x": x,
        "y": y,
        "rotation": rotation,
    }
    page_obj["params"]["views"].append(view)
    return view


def add_projection_group(
    page_obj: dict[str, Any],
    source_name: str,
    group_name: str = "ProjGroup",
    projections: list[str] | None = None,
    x: float = 150,
    y: float = 150,
    anchor_direction: str = "front",
) -> dict[str, Any]:
    """Add a projection group (multi-view orthogonal set) to a page.

    Args:
        page_obj: Page object dict.
        source_name: Name of the 3D source object.
        group_name: Name for the projection group.
        projections: List of projection types (Front, Left, Top, Right, Rear, Bottom).
        x: X position on page (mm).
        y: Y position on page (mm).
        anchor_direction: Anchor view direction.

    Returns:
        Projection group dict.
    """
    if projections is None:
        projections = ["Front", "Top", "Right"]

    proj_group = {
        "name": group_name,
        "type": "TechDraw::DrawProjGroup",
        "source": source_name,
        "projections": projections,
        "anchor_direction": anchor_direction,
        "x": x,
        "y": y,
    }
    page_obj["params"]["views"].append(proj_group)
    return proj_group


def add_section_view(
    page_obj: dict[str, Any],
    source_name: str,
    base_view_name: str,
    section_name: str = "Section",
    normal: tuple[float, float, float] = (0, 1, 0),
    origin: tuple[float, float, float] = (0, 0, 0),
    x: float = 200,
    y: float = 150,
) -> dict[str, Any]:
    """Add a cross-section view to a page.

    Args:
        page_obj: Page object dict.
        source_name: 3D source object name.
        base_view_name: Base view to section from.
        section_name: Name for the section view.
        normal: Section plane normal vector.
        origin: Point on the section plane.
        x: X position on page (mm).
        y: Y position on page (mm).

    Returns:
        Section view dict.
    """
    section = {
        "name": section_name,
        "type": "TechDraw::DrawViewSection",
        "source": source_name,
        "base_view": base_view_name,
        "section_normal": normal,
        "section_origin": origin,
        "x": x,
        "y": y,
    }
    page_obj["params"]["views"].append(section)
    return section


def add_dimension(
    page_obj: dict[str, Any],
    view_name: str,
    dim_type: str = "Distance",
    edge_ref: str = "Edge0",
    edge_ref2: str | None = None,
    dim_name: str = "Dim",
    x: float = 100,
    y: float = 50,
    format_spec: str = "%.2f",
    prefix: str = "",
    suffix: str = "",
    tolerance_upper: float | None = None,
    tolerance_lower: float | None = None,
) -> dict[str, Any]:
    """Add a dimension to a TechDraw page view.

    Args:
        page_obj: Page object dict.
        view_name: Name of the view to dimension.
        dim_type: Distance, DistanceX, DistanceY, Radius, Diameter, Angle.
        edge_ref: Edge or vertex reference (Edge0, Vertex0, etc.).
        edge_ref2: Second edge reference (required for Angle).
        dim_name: Name for the dimension object.
        x: X position of dimension text (mm).
        y: Y position of dimension text (mm).
        format_spec: Format string for dimension value.
        prefix: Text prefix (e.g. "2x", "∅").  Auto-set for Radius/Diameter
            if left empty.
        suffix: Text suffix (e.g. " H7", " THRU").
        tolerance_upper: Upper tolerance (e.g. +0.1).
        tolerance_lower: Lower tolerance (e.g. -0.1).

    Returns:
        Dimension dict.
    """
    # Auto-prefix for Radius and Diameter when caller leaves it empty
    if not prefix:
        if dim_type == "Radius":
            prefix = "R"
        elif dim_type == "Diameter":
            prefix = "∅"

    refs = [edge_ref]
    if edge_ref2:
        refs.append(edge_ref2)

    dim: dict[str, Any] = {
        "name": dim_name,
        "type": "TechDraw::DrawViewDimension",
        "view": view_name,
        "dim_type": dim_type,
        "references": refs,
        "x": x,
        "y": y,
        "format_spec": format_spec,
        "prefix": prefix,
        "suffix": suffix,
    }
    if tolerance_upper is not None:
        dim["tolerance_upper"] = tolerance_upper
    if tolerance_lower is not None:
        dim["tolerance_lower"] = tolerance_lower

    page_obj["params"]["dimensions"].append(dim)
    return dim


def add_annotation(
    page_obj: dict[str, Any],
    text: list[str],
    anno_name: str = "Anno",
    x: float = 50,
    y: float = 200,
    font_size: float = 5.0,
) -> dict[str, Any]:
    """Add a text annotation to a TechDraw page.

    Args:
        page_obj: Page object dict.
        text: List of text lines.
        anno_name: Name for the annotation.
        x: X position (mm).
        y: Y position (mm).
        font_size: Font size in mm.

    Returns:
        Annotation dict.
    """
    anno = {
        "name": anno_name,
        "type": "TechDraw::DrawViewAnnotation",
        "text": text,
        "x": x,
        "y": y,
        "font_size": font_size,
    }
    page_obj["params"]["annotations"].append(anno)
    return anno


def set_title_block(
    page_obj: dict[str, Any],
    fields: dict[str, str],
) -> dict[str, Any]:
    """Set title block fields on a TechDraw page.

    Supported fields: title, author, date, scale, material, revision,
    company, drawing_number, sheet, checked_by, approved_by.

    Args:
        page_obj: Page object dict.
        fields: Dict of field name → value.

    Returns:
        Title block dict.
    """
    title_block = {
        "type": "TitleBlock",
        **fields,
    }
    page_obj["params"]["title_block"] = title_block
    return title_block


def add_detail_view(
    page_obj: dict[str, Any],
    source_name: str,
    base_view_name: str,
    detail_name: str = "Detail",
    anchor_x: float = 0,
    anchor_y: float = 0,
    radius: float = 20,
    scale: float = 2.0,
    x: float = 250,
    y: float = 80,
) -> dict[str, Any]:
    """Add a detail (magnified) view to a TechDraw page.

    Args:
        page_obj: Page object dict.
        source_name: Name of the 3D source object.
        base_view_name: Name of the base view to zoom into.
        detail_name: Name for the detail view.
        anchor_x: X center of the detail circle on the base view.
        anchor_y: Y center of the detail circle on the base view.
        radius: Radius of the detail highlight circle (mm).
        scale: Detail view magnification scale.
        x: X position on page (mm).
        y: Y position on page (mm).

    Returns:
        Detail view dict.
    """
    detail = {
        "name": detail_name,
        "type": "TechDraw::DrawViewDetail",
        "source": source_name,
        "base_view": base_view_name,
        "anchor_x": anchor_x,
        "anchor_y": anchor_y,
        "radius": radius,
        "scale": scale,
        "x": x,
        "y": y,
    }
    page_obj["params"]["views"].append(detail)
    return detail


def add_centerline(
    page_obj: dict[str, Any],
    view_name: str,
    cl_name: str = "CenterLine",
    orientation: str = "vertical",
    position: float = 0,
    extent_low: float = -10,
    extent_high: float = 10,
) -> dict[str, Any]:
    """Add a centerline to a view on a TechDraw page.

    Args:
        page_obj: Page object dict.
        view_name: Name of the view to add the centerline to.
        cl_name: Name for the centerline object.
        orientation: 'vertical' or 'horizontal'.
        position: Position along the perpendicular axis (mm).
        extent_low: Start extent (mm).
        extent_high: End extent (mm).

    Returns:
        Centerline dict.
    """
    centerline = {
        "name": cl_name,
        "type": "TechDraw::CenterLine",
        "view": view_name,
        "orientation": orientation,
        "position": position,
        "extent_low": extent_low,
        "extent_high": extent_high,
    }
    page_obj["params"].setdefault("centerlines", []).append(centerline)
    return centerline


def add_hatch(
    page_obj: dict[str, Any],
    view_name: str,
    face_ref: str = "Face0",
    hatch_name: str = "Hatch",
    pattern: str = "ansi31",
    scale: float = 1.0,
    rotation: float = 0,
    color: str = "#000000",
) -> dict[str, Any]:
    """Add a hatch pattern to a face in a view.

    Args:
        page_obj: Page object dict.
        view_name: Name of the view containing the face.
        face_ref: Face reference (Face0, Face1, etc.).
        hatch_name: Name for the hatch object.
        pattern: Hatch pattern name (ansi31, ansi32, etc.).
        scale: Hatch pattern scale.
        rotation: Hatch pattern rotation (degrees).
        color: Hatch line color (hex string).

    Returns:
        Hatch dict.
    """
    hatch = {
        "name": hatch_name,
        "type": "TechDraw::DrawHatch",
        "view": view_name,
        "face_ref": face_ref,
        "pattern": pattern,
        "scale": scale,
        "rotation": rotation,
        "color": color,
    }
    page_obj["params"].setdefault("hatches", []).append(hatch)
    return hatch


def add_leader_line(
    page_obj: dict[str, Any],
    view_name: str,
    leader_name: str = "Leader",
    start_x: float = 0,
    start_y: float = 0,
    end_x: float = 50,
    end_y: float = 50,
    text: str = "",
    arrow_style: str = "filled",
) -> dict[str, Any]:
    """Add a leader line (reference line with text) to a view.

    Args:
        page_obj: Page object dict.
        view_name: Name of the view.
        leader_name: Name for the leader line object.
        start_x: Start X on the view (mm).
        start_y: Start Y on the view (mm).
        end_x: End X on the page (mm).
        end_y: End Y on the page (mm).
        text: Label text at the end of the leader.
        arrow_style: Arrow head style ('filled', 'open', 'tick', 'dot', 'none').

    Returns:
        Leader line dict.
    """
    leader = {
        "name": leader_name,
        "type": "TechDraw::DrawLeaderLine",
        "view": view_name,
        "start_x": start_x,
        "start_y": start_y,
        "end_x": end_x,
        "end_y": end_y,
        "text": text,
        "arrow_style": arrow_style,
    }
    page_obj["params"].setdefault("leaders", []).append(leader)
    return leader


def add_balloon(
    page_obj: dict[str, Any],
    view_name: str,
    balloon_name: str = "Balloon",
    origin_x: float = 0,
    origin_y: float = 0,
    text: str = "1",
    shape: str = "circular",
    x: float = 50,
    y: float = 50,
) -> dict[str, Any]:
    """Add a balloon (item number reference) to a view.

    Args:
        page_obj: Page object dict.
        view_name: Name of the view.
        balloon_name: Name for the balloon object.
        origin_x: Point on the object the balloon references (mm).
        origin_y: Point on the object the balloon references (mm).
        text: Balloon text (typically an item number).
        shape: Balloon shape ('circular', 'rectangular', 'triangle', 'hexagon', 'none').
        x: X position of balloon on page (mm).
        y: Y position of balloon on page (mm).

    Returns:
        Balloon dict.
    """
    balloon = {
        "name": balloon_name,
        "type": "TechDraw::DrawViewBalloon",
        "view": view_name,
        "origin_x": origin_x,
        "origin_y": origin_y,
        "text": text,
        "shape": shape,
        "x": x,
        "y": y,
    }
    page_obj["params"].setdefault("balloons", []).append(balloon)
    return balloon


def add_bom(
    page_obj: dict[str, Any],
    items: list[dict[str, str]],
    bom_name: str = "BOM",
    x: float = 200,
    y: float = 250,
    font_size: float = 3.5,
    columns: list[str] | None = None,
) -> dict[str, Any]:
    """Add a Bill of Materials (stuklijst) table to a drawing page.

    Each item is a dict with keys matching the column names.
    Default columns: item, name, material, quantity.

    Args:
        page_obj: Page object dict.
        items: List of BOM row dicts.
        bom_name: Name for the BOM object.
        x: X position on page (mm).
        y: Y position on page (mm).
        font_size: Font size for BOM text (mm).
        columns: Column header names (default: item, name, material, quantity).

    Returns:
        BOM dict.
    """
    if columns is None:
        columns = ["item", "name", "material", "quantity"]

    bom = {
        "name": bom_name,
        "type": "BOM",
        "items": items,
        "columns": columns,
        "x": x,
        "y": y,
        "font_size": font_size,
    }
    page_obj["params"].setdefault("bom", []).append(bom)
    return bom


def add_clip_group(
    page_obj: dict[str, Any],
    clip_name: str = "Clip",
    x: float = 100,
    y: float = 100,
    width: float = 80,
    height: float = 60,
    show_frame: bool = True,
) -> dict[str, Any]:
    """Add a clip group (rectangular mask) to a TechDraw page.

    A clip group defines a visible rectangle. Views added to it are
    masked to that area — anything outside the rectangle is hidden.

    Args:
        page_obj: Page object dict.
        clip_name: Name for the clip object.
        x: X position of the clip rectangle center (mm).
        y: Y position of the clip rectangle center (mm).
        width: Clip rectangle width (mm).
        height: Clip rectangle height (mm).
        show_frame: Whether to draw the clip boundary frame.

    Returns:
        Clip group dict.
    """
    clip = {
        "name": clip_name,
        "type": "TechDraw::DrawViewClip",
        "x": x,
        "y": y,
        "width": width,
        "height": height,
        "show_frame": show_frame,
        "views": [],
    }
    page_obj["params"].setdefault("clips", []).append(clip)
    return clip


def add_view_to_clip(
    page_obj: dict[str, Any],
    clip_name: str,
    view_name: str,
) -> dict[str, Any] | None:
    """Add an existing view to a clip group.

    The view must already exist in the page's views list. It will be
    referenced by the clip group so it renders within the clipped area.

    Args:
        page_obj: Page object dict.
        clip_name: Name of the target clip group.
        view_name: Name of the view to add.

    Returns:
        Updated clip dict, or None if clip/view not found.
    """
    params = page_obj.get("params", {})

    # Find the clip
    clip = None
    for c in params.get("clips", []):
        if c.get("name") == clip_name:
            clip = c
            break
    if clip is None:
        return None

    # Verify the view exists
    view_found = False
    for v in params.get("views", []):
        if v.get("name") == view_name:
            view_found = True
            break
    if not view_found:
        return None

    if view_name not in clip["views"]:
        clip["views"].append(view_name)
    return clip


# ── Line style presets ───────────────────────────────────────────────
LINE_STYLES = {
    "solid": {"dash_pattern": "", "description": "Continuous line"},
    "dashed": {"dash_pattern": "6,3", "description": "Dashed line (hidden edges)"},
    "dashdot": {"dash_pattern": "8,2,2,2", "description": "Dash-dot (center lines)"},
    "dotted": {"dash_pattern": "1,2", "description": "Dotted line"},
    "phantom": {"dash_pattern": "10,2,2,2,2,2", "description": "Phantom line (alternate positions)"},
}


def add_cosmetic_edge(
    page_obj: dict[str, Any],
    view_name: str,
    x1: float = 0,
    y1: float = 0,
    x2: float = 50,
    y2: float = 0,
    edge_name: str = "CosmeticEdge",
    style: str = "dashed",
    color: str = "#000000",
    weight: float = 0.2,
) -> dict[str, Any]:
    """Add a cosmetic (artificial) edge to a view.

    Cosmetic edges are lines that don't correspond to actual geometry.
    Common uses: fold lines, cut lines, phantom edges, reference lines.

    Args:
        page_obj: Page object dict.
        view_name: Name of the view to add the edge to.
        x1: Start X (mm, relative to view center).
        y1: Start Y (mm, relative to view center).
        x2: End X (mm, relative to view center).
        y2: End Y (mm, relative to view center).
        edge_name: Name for the cosmetic edge.
        style: Line style ('solid', 'dashed', 'dashdot', 'dotted', 'phantom').
        color: Line color (hex string).
        weight: Line weight in mm.

    Returns:
        Cosmetic edge dict.
    """
    edge = {
        "name": edge_name,
        "type": "TechDraw::CosmeticEdge",
        "view": view_name,
        "x1": x1,
        "y1": y1,
        "x2": x2,
        "y2": y2,
        "style": style,
        "color": color,
        "weight": weight,
    }
    page_obj["params"].setdefault("cosmetic_edges", []).append(edge)
    return edge


def add_center_mark(
    page_obj: dict[str, Any],
    view_name: str,
    cx: float = 0,
    cy: float = 0,
    mark_name: str = "CenterMark",
    size: float = 5,
    style: str = "dashdot",
    color: str = "#000000",
    weight: float = 0.15,
) -> dict[str, Any]:
    """Add a center mark (crosshair) to a view.

    Center marks indicate the center of holes, arcs, or circular features.
    Rendered as two perpendicular lines forming a + at the specified point.

    Args:
        page_obj: Page object dict.
        view_name: Name of the view.
        cx: Center X (mm, relative to view center).
        cy: Center Y (mm, relative to view center).
        mark_name: Name for the center mark.
        size: Half-length of each crosshair arm (mm).
        style: Line style (default 'dashdot' per ISO convention).
        color: Line color.
        weight: Line weight in mm.

    Returns:
        Center mark dict.
    """
    mark = {
        "name": mark_name,
        "type": "TechDraw::CenterMark",
        "view": view_name,
        "cx": cx,
        "cy": cy,
        "size": size,
        "style": style,
        "color": color,
        "weight": weight,
    }
    page_obj["params"].setdefault("cosmetic_edges", []).append(mark)
    return mark


# ── GD&T Constants ────────────────────────────────────────────────────

# ISO 1101 / ASME Y14.5 geometric characteristic symbols
GDT_SYMBOLS = {
    # Form tolerances
    "flatness": {"symbol": "⏥", "category": "form", "description": "Surface flatness"},
    "straightness": {"symbol": "⏤", "category": "form", "description": "Straightness of line/axis"},
    "circularity": {"symbol": "○", "category": "form", "description": "Circularity (roundness)"},
    "cylindricity": {"symbol": "⌭", "category": "form", "description": "Cylindricity"},
    # Orientation tolerances
    "perpendicularity": {"symbol": "⊥", "category": "orientation", "description": "Perpendicularity"},
    "parallelism": {"symbol": "∥", "category": "orientation", "description": "Parallelism"},
    "angularity": {"symbol": "∠", "category": "orientation", "description": "Angularity"},
    # Location tolerances
    "position": {"symbol": "⌖", "category": "location", "description": "True position"},
    "concentricity": {"symbol": "◎", "category": "location", "description": "Concentricity"},
    "symmetry": {"symbol": "⌯", "category": "location", "description": "Symmetry"},
    # Runout tolerances
    "circular_runout": {"symbol": "↗", "category": "runout", "description": "Circular runout"},
    "total_runout": {"symbol": "⇗", "category": "runout", "description": "Total runout"},
    # Profile tolerances
    "profile_line": {"symbol": "⌒", "category": "profile", "description": "Profile of a line"},
    "profile_surface": {"symbol": "⌓", "category": "profile", "description": "Profile of a surface"},
}

# Material condition modifiers (ASME Y14.5)
MATERIAL_CONDITIONS = {
    "MMC": {"symbol": "Ⓜ", "description": "Maximum Material Condition"},
    "LMC": {"symbol": "Ⓛ", "description": "Least Material Condition"},
    "RFS": {"symbol": "", "description": "Regardless of Feature Size (default)"},
}

# Surface finish symbols (ISO 1302)
SURFACE_FINISH_SYMBOLS = {
    "any": {"symbol": "√", "description": "Any manufacturing process"},
    "removal_required": {"symbol": "▽", "description": "Material removal required (machining)"},
    "removal_prohibited": {"symbol": "▽̶", "description": "Material removal prohibited (as-cast, as-forged)"},
}


def add_geometric_tolerance(
    page_obj: dict[str, Any],
    view_name: str,
    characteristic: str,
    tolerance: float,
    gdt_name: str = "GDT",
    datum_refs: list[str] | None = None,
    material_condition: str = "RFS",
    diameter_zone: bool = False,
    x: float = 100,
    y: float = 80,
) -> dict[str, Any]:
    """Add a geometric tolerance frame (Feature Control Frame) to a view.

    Creates an ISO 1101 / ASME Y14.5 compliant FCF annotation.

    Args:
        page_obj: Page object dict.
        view_name: Name of the view to annotate.
        characteristic: GD&T characteristic name (e.g. 'position', 'flatness').
        tolerance: Tolerance value in mm (or degrees for angularity).
        gdt_name: Name for the GD&T annotation object.
        datum_refs: List of datum reference letters (max 3), e.g. ['A', 'B'].
        material_condition: 'MMC', 'LMC', or 'RFS'.
        diameter_zone: If True, prefix tolerance with ∅ (diameter zone).
        x: X position on page (mm).
        y: Y position on page (mm).

    Returns:
        GD&T annotation dict.
    """
    if characteristic not in GDT_SYMBOLS:
        raise ValueError(
            f"Unknown GD&T characteristic: {characteristic!r}. "
            f"Valid: {', '.join(GDT_SYMBOLS.keys())}"
        )

    symbol_info = GDT_SYMBOLS[characteristic]
    mc_info = MATERIAL_CONDITIONS.get(material_condition, MATERIAL_CONDITIONS["RFS"])

    gdt: dict[str, Any] = {
        "name": gdt_name,
        "type": "TechDraw::GeometricTolerance",
        "view": view_name,
        "characteristic": characteristic,
        "symbol": symbol_info["symbol"],
        "category": symbol_info["category"],
        "tolerance": tolerance,
        "diameter_zone": diameter_zone,
        "material_condition": material_condition,
        "material_condition_symbol": mc_info["symbol"],
        "datum_refs": datum_refs or [],
        "x": x,
        "y": y,
    }
    page_obj["params"].setdefault("gdt", []).append(gdt)
    return gdt


def add_datum_symbol(
    page_obj: dict[str, Any],
    view_name: str,
    letter: str,
    datum_name: str = "Datum",
    x: float = 100,
    y: float = 100,
) -> dict[str, Any]:
    """Add a datum feature symbol to a view on a TechDraw page.

    Renders as a filled triangle with the datum letter in a box,
    per ISO 5459 / ASME Y14.5.

    Args:
        page_obj: Page object dict.
        view_name: Name of the view.
        letter: Datum letter (A, B, C, etc.).
        datum_name: Name for the datum object.
        x: X position on page (mm).
        y: Y position on page (mm).

    Returns:
        Datum symbol dict.
    """
    letter = letter.upper().strip()
    if not letter or len(letter) > 2:
        raise ValueError(f"Datum letter must be 1-2 characters, got: {letter!r}")

    datum: dict[str, Any] = {
        "name": datum_name,
        "type": "TechDraw::DatumSymbol",
        "view": view_name,
        "letter": letter,
        "x": x,
        "y": y,
    }
    page_obj["params"].setdefault("datums", []).append(datum)
    return datum


def add_surface_finish(
    page_obj: dict[str, Any],
    view_name: str,
    ra: float | None = None,
    rz: float | None = None,
    process: str = "any",
    sf_name: str = "SurfFinish",
    lay_direction: str = "",
    x: float = 100,
    y: float = 100,
) -> dict[str, Any]:
    """Add a surface finish (roughness) symbol to a view.

    Per ISO 1302 — specifies surface roughness requirements.

    Args:
        page_obj: Page object dict.
        view_name: Name of the view.
        ra: Ra roughness value in µm (arithmetic mean).
        rz: Rz roughness value in µm (mean peak-to-valley).
        process: 'any', 'removal_required', or 'removal_prohibited'.
        sf_name: Name for the surface finish object.
        lay_direction: Lay direction symbol ('=', '⊥', 'X', 'M', 'C', 'R').
        x: X position on page (mm).
        y: Y position on page (mm).

    Returns:
        Surface finish dict.
    """
    if process not in SURFACE_FINISH_SYMBOLS:
        raise ValueError(
            f"Unknown surface finish process: {process!r}. "
            f"Valid: {', '.join(SURFACE_FINISH_SYMBOLS.keys())}"
        )

    sf_info = SURFACE_FINISH_SYMBOLS[process]

    sf: dict[str, Any] = {
        "name": sf_name,
        "type": "TechDraw::SurfaceFinish",
        "view": view_name,
        "ra": ra,
        "rz": rz,
        "process": process,
        "process_symbol": sf_info["symbol"],
        "lay_direction": lay_direction,
        "x": x,
        "y": y,
    }
    page_obj["params"].setdefault("surface_finishes", []).append(sf)
    return sf


def _build_techdraw_script(project: dict[str, Any], page_name: str) -> str:
    """Build FreeCAD Python script for TechDraw page creation.

    Creates all 3D objects first, then builds the drawing page with
    views, dimensions, and annotations.

    Args:
        project: Project dict with objects.
        page_name: Name of the page object to build.

    Returns:
        Python script string.
    """
    # Start with 3D objects
    script = _build_project_script(project)

    # Find the page object
    page_obj = None
    for obj in project.get("objects", []):
        if obj.get("name") == page_name and obj.get("type") == "TechDraw::DrawPage":
            page_obj = obj
            break

    if not page_obj:
        return script + f"_cli_result['error'] = 'Page {page_name!r} not found'\n"

    params = page_obj.get("params", {})
    template = params.get("template", "A4_Landscape")
    scale = params.get("scale", 1.0)

    # Create page
    script += (
        f"\n# ── TechDraw Page ──\n"
        f"_page = doc.addObject('TechDraw::DrawPage', {page_name!r})\n"
        f"_template = doc.addObject('TechDraw::DrawSVGTemplate', 'Template')\n"
    )

    # Find template file
    script += (
        f"import os, glob\n"
        f"_td = os.path.join(FreeCAD.getResourceDir(), 'Mod', 'TechDraw', 'Templates')\n"
        f"_tmpl_pattern = {template!r}\n"
        f"_found = False\n"
        f"for _root, _dirs, _files in os.walk(_td):\n"
        f"    for _f in _files:\n"
        f"        if _tmpl_pattern.replace('_', ' ') in _f.replace('_', ' ') or "
        f"_tmpl_pattern.lower() in _f.lower():\n"
        f"            _template.Template = os.path.join(_root, _f)\n"
        f"            _found = True\n"
        f"            break\n"
        f"    if _found:\n"
        f"        break\n"
        f"if not _found:\n"
        f"    # Fallback: search for any A4 landscape\n"
        f"    for _root, _dirs, _files in os.walk(_td):\n"
        f"        for _f in _files:\n"
        f"            if 'A4' in _f and 'Landscape' in _f and _f.endswith('.svg'):\n"
        f"                _template.Template = os.path.join(_root, _f)\n"
        f"                _found = True\n"
        f"                break\n"
        f"        if _found:\n"
        f"            break\n"
        f"if _found:\n"
        f"    _page.Template = _template\n"
        f"_page.Scale = {scale}\n"
    )

    # Add views
    for view in params.get("views", []):
        vtype = view.get("type", "")
        vname = view.get("name", "View")
        source = view.get("source", "")

        if vtype == "TechDraw::DrawViewPart":
            dx, dy, dz = view.get("direction", (0, 0, 1))
            x, y = view.get("x", 100), view.get("y", 150)
            script += (
                f"\n_v = doc.addObject('TechDraw::DrawViewPart', {vname!r})\n"
                f"_v.Source = [doc.getObject({source!r})]\n"
                f"_v.Direction = FreeCAD.Vector({dx}, {dy}, {dz})\n"
                f"_v.X = {x}\n"
                f"_v.Y = {y}\n"
                f"_page.addView(_v)\n"
            )
            rotation = view.get("rotation", 0)
            if rotation:
                script += f"_v.Rotation = {rotation}\n"

        elif vtype == "TechDraw::DrawProjGroup":
            projections = view.get("projections", ["Front", "Top", "Right"])
            x, y = view.get("x", 150), view.get("y", 150)
            script += (
                f"\n_pg = doc.addObject('TechDraw::DrawProjGroup', {vname!r})\n"
                f"_pg.Source = [doc.getObject({source!r})]\n"
                f"_page.addView(_pg)\n"
            )
            for proj in projections:
                script += f"_pg.addProjection({proj!r})\n"
            script += (
                f"if _pg.Anchor is not None:\n"
                f"    _pg.Anchor.Direction = FreeCAD.Vector(0, 0, 1)\n"
                f"    _pg.Anchor.RotationVector = FreeCAD.Vector(1, 0, 0)\n"
                f"doc.recompute()\n"
                f"_pg.X = {x}\n"
                f"_pg.Y = {y}\n"
            )

        elif vtype == "TechDraw::DrawViewSection":
            base_view = view.get("base_view", "View")
            nx, ny, nz = view.get("section_normal", (0, 1, 0))
            ox, oy, oz = view.get("section_origin", (0, 0, 0))
            x, y = view.get("x", 200), view.get("y", 150)
            script += (
                f"\n_sv = doc.addObject('TechDraw::DrawViewSection', {vname!r})\n"
                f"_sv.Source = [doc.getObject({source!r})]\n"
                f"_sv.BaseView = doc.getObject({base_view!r})\n"
                f"_sv.SectionNormal = FreeCAD.Vector({nx}, {ny}, {nz})\n"
                f"_sv.SectionOrigin = FreeCAD.Vector({ox}, {oy}, {oz})\n"
                f"_sv.Direction = FreeCAD.Vector({nx}, {ny}, {nz})\n"
                f"_sv.X = {x}\n"
                f"_sv.Y = {y}\n"
                f"_page.addView(_sv)\n"
            )

        elif vtype == "TechDraw::DrawViewDetail":
            base_view = view.get("base_view", "View")
            ax = view.get("anchor_x", 0)
            ay = view.get("anchor_y", 0)
            r = view.get("radius", 20)
            detail_scale = view.get("scale", 2.0)
            x, y = view.get("x", 250), view.get("y", 80)
            script += (
                f"\n_dv = doc.addObject('TechDraw::DrawViewDetail', {vname!r})\n"
                f"_dv.Source = [doc.getObject({source!r})]\n"
                f"_dv.BaseView = doc.getObject({base_view!r})\n"
                f"_dv.AnchorPoint = FreeCAD.Vector({ax}, {ay}, 0)\n"
                f"_dv.Radius = {r}\n"
                f"_dv.Scale = {detail_scale}\n"
                f"_dv.X = {x}\n"
                f"_dv.Y = {y}\n"
                f"_page.addView(_dv)\n"
            )

    # Recompute before adding dimensions (views need to exist)
    script += "\ndoc.recompute()\n"

    # Add dimensions
    for dim in params.get("dimensions", []):
        dname = dim.get("name", "Dim")
        view_name = dim.get("view", "View")
        dim_type = dim.get("dim_type", "Distance")
        refs = dim.get("references", ["Edge0"])
        x, y = dim.get("x", 100), dim.get("y", 50)
        fmt = dim.get("format_spec", "%.2f")
        prefix = dim.get("prefix", "")
        suffix = dim.get("suffix", "")
        tol_upper = dim.get("tolerance_upper")
        tol_lower = dim.get("tolerance_lower")

        # Build FormatSpec with prefix/suffix: e.g. "∅%.2f H7"
        full_fmt = f"{prefix}{fmt}{suffix}" if (prefix or suffix) else fmt

        ref_str = ", ".join(f"(doc.getObject({view_name!r}), {r!r})" for r in refs)
        script += (
            f"\n_d = doc.addObject('TechDraw::DrawViewDimension', {dname!r})\n"
            f"_d.Type = {dim_type!r}\n"
            f"_d.MeasureType = 'Projected'\n"
            f"try:\n"
            f"    _d.References2D = [{ref_str}]\n"
            f"except (IndexError, RuntimeError):\n"
            f"    pass  # Edge refs may not be available until HLR finishes\n"
            f"_d.FormatSpec = {full_fmt!r}\n"
            f"_d.X = {x}\n"
            f"_d.Y = {y}\n"
        )
        # Set tolerances if specified
        if tol_upper is not None or tol_lower is not None:
            script += (
                f"try:\n"
                f"    _d.FormatSpecOverTolerance = '+{tol_upper or 0}'\n"
                f"    _d.FormatSpecUnderTolerance = '{tol_lower or 0}'\n"
                f"except AttributeError:\n"
                f"    pass  # Tolerance fields may not exist in older FreeCAD\n"
            )
        script += f"_page.addView(_d)\n"

    # Add annotations
    for anno in params.get("annotations", []):
        aname = anno.get("name", "Anno")
        text = anno.get("text", [""])
        x, y = anno.get("x", 50), anno.get("y", 200)
        font_size = anno.get("font_size", 5.0)

        script += (
            f"\n_a = doc.addObject('TechDraw::DrawViewAnnotation', {aname!r})\n"
            f"_a.Text = {text!r}\n"
            f"_a.X = {x}\n"
            f"_a.Y = {y}\n"
            f"_a.TextSize = {font_size}\n"
            f"_page.addView(_a)\n"
        )

    # Add title block fields to template
    title_block = params.get("title_block")
    if title_block:
        # Map our field names to common FreeCAD SVG template text fields
        field_map = {
            "title": ["FC:Title", "DRAWING TITLE", "Title"],
            "author": ["FC:Author", "AUTHOR", "Designed by"],
            "date": ["FC:Date", "DATE", "Date"],
            "scale": ["FC:Scale", "SCALE", "Scale"],
            "material": ["MATERIAL", "Material"],
            "revision": ["FC:Revision", "REVISION", "Revision"],
            "company": ["FC:Company", "COMPANY", "Company"],
            "drawing_number": ["FC:DrawingNumber", "DRAWING NUMBER", "Drawing number"],
            "sheet": ["FC:Sheet", "SHEET", "Sheet"],
            "checked_by": ["CHECKED BY", "Checked by"],
            "approved_by": ["APPROVED BY", "Approved by"],
        }
        script += "\n# ── Title Block ──\n"
        script += "try:\n"
        script += "    _tmpl = _page.Template\n"
        script += "    if _tmpl and hasattr(_tmpl, 'EditableTexts'):\n"
        script += "        _texts = _tmpl.EditableTexts.copy()\n"
        for field_name, svg_keys in field_map.items():
            value = title_block.get(field_name)
            if value:
                for svg_key in svg_keys:
                    script += (
                        f"        if {svg_key!r} in _texts:\n"
                        f"            _texts[{svg_key!r}] = {value!r}\n"
                    )
        script += "        _tmpl.EditableTexts = _texts\n"
        script += "except Exception:\n"
        script += "    pass  # Title block editing may not be available\n"

    # Add centerlines
    for cl in params.get("centerlines", []):
        cl_name = cl.get("name", "CenterLine")
        view_name = cl.get("view", "View")
        orientation = cl.get("orientation", "vertical")
        position = cl.get("position", 0)
        ext_low = cl.get("extent_low", -10)
        ext_high = cl.get("extent_high", 10)
        mode = 0 if orientation == "vertical" else 1
        script += (
            f"\ntry:\n"
            f"    _vw = doc.getObject({view_name!r})\n"
            f"    if _vw:\n"
            f"        _cl_idx = _vw.makeCenterLine([0], {mode})\n"
            f"except (AttributeError, RuntimeError):\n"
            f"    pass  # CenterLine API may vary by FreeCAD version\n"
        )

    # Add hatches
    for h in params.get("hatches", []):
        h_name = h.get("name", "Hatch")
        view_name = h.get("view", "View")
        face_ref = h.get("face_ref", "Face0")
        pattern = h.get("pattern", "ansi31")
        h_scale = h.get("scale", 1.0)
        h_rotation = h.get("rotation", 0)
        h_color = h.get("color", "#000000")
        script += (
            f"\ntry:\n"
            f"    import os as _os\n"
            f"    _hatch = doc.addObject('TechDraw::DrawHatch', {h_name!r})\n"
            f"    _hatch.Source = (doc.getObject({view_name!r}), [{face_ref!r}])\n"
            f"    _pat_dir = _os.path.join(FreeCAD.getResourceDir(), 'Mod', 'TechDraw', 'PAT')\n"
            f"    for _pf in _os.listdir(_pat_dir) if _os.path.isdir(_pat_dir) else []:\n"
            f"        if _pf.endswith('.pat'):\n"
            f"            _hatch.HatchPattern = _os.path.join(_pat_dir, _pf)\n"
            f"            break\n"
            f"    _hatch.HatchScale = {h_scale}\n"
            f"    _hatch.HatchRotation = {h_rotation}\n"
            f"    _page.addView(_hatch)\n"
            f"except Exception:\n"
            f"    pass  # Hatch may not be available in all FreeCAD builds\n"
        )

    # Add leader lines
    for ld in params.get("leaders", []):
        ld_name = ld.get("name", "Leader")
        view_name = ld.get("view", "View")
        sx = ld.get("start_x", 0)
        sy = ld.get("start_y", 0)
        ex = ld.get("end_x", 50)
        ey = ld.get("end_y", 50)
        ld_text = ld.get("text", "")
        script += (
            f"\ntry:\n"
            f"    _ld = doc.addObject('TechDraw::DrawLeaderLine', {ld_name!r})\n"
            f"    _ld.LeaderParent = doc.getObject({view_name!r})\n"
            f"    _ld.WayPoints = [FreeCAD.Vector({sx},{sy},0), FreeCAD.Vector({ex},{ey},0)]\n"
            f"    _page.addView(_ld)\n"
            f"except Exception:\n"
            f"    pass  # LeaderLine may not be available\n"
        )

    # Add balloons
    for bl in params.get("balloons", []):
        bl_name = bl.get("name", "Balloon")
        view_name = bl.get("view", "View")
        ox = bl.get("origin_x", 0)
        oy = bl.get("origin_y", 0)
        bl_text = bl.get("text", "1")
        bl_x = bl.get("x", 50)
        bl_y = bl.get("y", 50)
        bl_shape = bl.get("shape", "circular")
        shape_map = {
            "circular": 0, "rectangular": 1, "triangle": 2,
            "hexagon": 5, "none": 7,
        }
        shape_enum = shape_map.get(bl_shape, 0)
        script += (
            f"\ntry:\n"
            f"    _bl = doc.addObject('TechDraw::DrawViewBalloon', {bl_name!r})\n"
            f"    _bl.SourceView = doc.getObject({view_name!r})\n"
            f"    _bl.OriginIsSet = True\n"
            f"    _bl.ShapeIsSet = True\n"
            f"    _bl.Text = {bl_text!r}\n"
            f"    _bl.X = {bl_x}\n"
            f"    _bl.Y = {bl_y}\n"
            f"    _bl.EndType = {shape_enum}\n"
            f"    _page.addView(_bl)\n"
            f"except Exception:\n"
            f"    pass  # Balloon may not be available\n"
        )

    # Add clip groups
    for clip in params.get("clips", []):
        clip_name = clip.get("name", "Clip")
        cx = clip.get("x", 100)
        cy = clip.get("y", 100)
        cw = clip.get("width", 80)
        ch = clip.get("height", 60)
        show_frame = clip.get("show_frame", True)
        clip_views = clip.get("views", [])
        script += (
            f"\ntry:\n"
            f"    _clip = doc.addObject('TechDraw::DrawViewClip', {clip_name!r})\n"
            f"    _clip.X = {cx}\n"
            f"    _clip.Y = {cy}\n"
            f"    _clip.Width = {cw}\n"
            f"    _clip.Height = {ch}\n"
            f"    _clip.ShowFrame = {show_frame}\n"
            f"    _page.addView(_clip)\n"
        )
        for vn in clip_views:
            script += (
                f"    _cv = doc.getObject({vn!r})\n"
                f"    if _cv:\n"
                f"        _clip.addView(_cv)\n"
            )
        script += (
            f"except Exception:\n"
            f"    pass  # DrawViewClip may not be available\n"
        )

    # Add GD&T frames (as annotations with formatted text)
    for gdt in params.get("gdt", []):
        gdt_name = gdt.get("name", "GDT")
        view_name = gdt.get("view", "View")
        symbol = gdt.get("symbol", "⌖")
        tol = gdt.get("tolerance", 0)
        diameter_zone = gdt.get("diameter_zone", False)
        mc_symbol = gdt.get("material_condition_symbol", "")
        datum_refs = gdt.get("datum_refs", [])
        gdt_x = gdt.get("x", 100)
        gdt_y = gdt.get("y", 80)

        # Build FCF text: |symbol|∅tol MC|A|B|C|
        tol_str = f"∅{tol}" if diameter_zone else str(tol)
        fcf_text = f"{symbol} {tol_str}{mc_symbol}"
        if datum_refs:
            fcf_text += " " + " ".join(datum_refs[:3])

        script += (
            f"\ntry:\n"
            f"    _gdt = doc.addObject('TechDraw::DrawViewAnnotation', {gdt_name!r})\n"
            f"    _gdt.Text = [{fcf_text!r}]\n"
            f"    _gdt.TextSize = 4.0\n"
            f"    _gdt.X = {gdt_x}\n"
            f"    _gdt.Y = {gdt_y}\n"
            f"    _page.addView(_gdt)\n"
            f"except Exception:\n"
            f"    pass  # GD&T annotation may not render in all FreeCAD versions\n"
        )

    # Add datum symbols (as annotations)
    for dat in params.get("datums", []):
        dat_name = dat.get("name", "Datum")
        dat_letter = dat.get("letter", "A")
        dat_x = dat.get("x", 100)
        dat_y = dat.get("y", 100)
        script += (
            f"\ntry:\n"
            f"    _dat = doc.addObject('TechDraw::DrawViewAnnotation', {dat_name!r})\n"
            f"    _dat.Text = [{f'▼ [{dat_letter}]'!r}]\n"
            f"    _dat.TextSize = 5.0\n"
            f"    _dat.X = {dat_x}\n"
            f"    _dat.Y = {dat_y}\n"
            f"    _page.addView(_dat)\n"
            f"except Exception:\n"
            f"    pass  # Datum annotation may not render in all FreeCAD versions\n"
        )

    # Add surface finish symbols (as annotations)
    for sf in params.get("surface_finishes", []):
        sf_name = sf.get("name", "SurfFinish")
        sf_ra = sf.get("ra")
        sf_rz = sf.get("rz")
        sf_symbol = sf.get("process_symbol", "√")
        sf_lay = sf.get("lay_direction", "")
        sf_x = sf.get("x", 100)
        sf_y = sf.get("y", 100)

        # Build surface finish text
        sf_parts = [sf_symbol]
        if sf_ra is not None:
            sf_parts.append(f"Ra {sf_ra}")
        if sf_rz is not None:
            sf_parts.append(f"Rz {sf_rz}")
        if sf_lay:
            sf_parts.append(sf_lay)
        sf_text = " ".join(sf_parts)

        script += (
            f"\ntry:\n"
            f"    _sf = doc.addObject('TechDraw::DrawViewAnnotation', {sf_name!r})\n"
            f"    _sf.Text = [{sf_text!r}]\n"
            f"    _sf.TextSize = 3.5\n"
            f"    _sf.X = {sf_x}\n"
            f"    _sf.Y = {sf_y}\n"
            f"    _page.addView(_sf)\n"
            f"except Exception:\n"
            f"    pass  # Surface finish annotation may not render\n"
        )

    # Add cosmetic edges and center marks
    # FreeCAD line style enum: 1=dashed, 2=center, 3=dashdot
    _style_map = {"solid": 0, "dashed": 1, "dashdot": 3, "dotted": 4, "phantom": 5}
    for ce in params.get("cosmetic_edges", []):
        ce_type = ce.get("type", "TechDraw::CosmeticEdge")
        view_name = ce.get("view", "View")
        style = ce.get("style", "dashed")
        color = ce.get("color", "#000000")
        weight = ce.get("weight", 0.2)
        style_int = _style_map.get(style, 1)

        if ce_type == "TechDraw::CenterMark":
            cx = ce.get("cx", 0)
            cy = ce.get("cy", 0)
            size = ce.get("size", 5)
            script += (
                f"\ntry:\n"
                f"    _vw = doc.getObject({view_name!r})\n"
                f"    if _vw:\n"
                f"        import TechDraw\n"
                f"        _ce1 = _vw.makeCosmeticLine("
                f"FreeCAD.Vector({cx - size}, {cy}, 0), "
                f"FreeCAD.Vector({cx + size}, {cy}, 0))\n"
                f"        _ce2 = _vw.makeCosmeticLine("
                f"FreeCAD.Vector({cx}, {cy - size}, 0), "
                f"FreeCAD.Vector({cx}, {cy + size}, 0))\n"
                f"except (AttributeError, RuntimeError):\n"
                f"    pass  # CosmeticEdge API may vary by FreeCAD version\n"
            )
        else:
            x1, y1 = ce.get("x1", 0), ce.get("y1", 0)
            x2, y2 = ce.get("x2", 50), ce.get("y2", 0)
            script += (
                f"\ntry:\n"
                f"    _vw = doc.getObject({view_name!r})\n"
                f"    if _vw:\n"
                f"        import TechDraw\n"
                f"        _ce = _vw.makeCosmeticLine("
                f"FreeCAD.Vector({x1}, {y1}, 0), "
                f"FreeCAD.Vector({x2}, {y2}, 0))\n"
                f"except (AttributeError, RuntimeError):\n"
                f"    pass  # CosmeticEdge API may vary by FreeCAD version\n"
            )

    script += "\ndoc.recompute()\n"
    return script


def export_drawing_dxf(
    project: dict[str, Any],
    page_name: str,
    output_path: str,
) -> dict[str, Any]:
    """Export a TechDraw page to DXF via FreeCAD.

    Args:
        project: Project dict.
        page_name: Name of the TechDraw page.
        output_path: DXF output file path.

    Returns:
        Result dict.
    """
    output_path = os.path.abspath(output_path)
    script = _build_techdraw_script(project, page_name)
    script += (
        f"\nimport TechDraw\n"
        f"_page_obj = doc.getObject({page_name!r})\n"
        f"if _page_obj:\n"
        f"    TechDraw.writeDXFPage(_page_obj, {output_path!r})\n"
        f"    import os\n"
        f"    if os.path.exists({output_path!r}):\n"
        f"        _cli_result['output'] = {output_path!r}\n"
        f"        _cli_result['file_size'] = os.path.getsize({output_path!r})\n"
        f"        _cli_result['format'] = 'dxf'\n"
        f"    else:\n"
        f"        _cli_result['error'] = 'DXF export produced no file'\n"
        f"else:\n"
        f"    _cli_result['error'] = 'Page {page_name} not found in document'\n"
    )
    return run_script(script)


def _project_object_2d(
    obj: dict[str, Any],
    direction: tuple[float, float, float],
) -> tuple[float, float, float, float] | None:
    """Project a 3D object to a 2D bounding rectangle for a given view direction.

    Supports Part::Box and Part::Cylinder (cylinder projects as rectangle
    in elevation views, approximated as bounding rect in all views).

    Returns (x, y, width, height) in mm for the 2D projection, or None.
    Direction mapping (which model axes map to screen X, Y):
        (0,-1,0): front elevation → screen_x = model_X, screen_y = model_Z
        (0,0,1):  plan view       → screen_x = model_X, screen_y = model_Y
        (1,0,0):  side elevation  → screen_x = model_Y, screen_y = model_Z
    """
    obj_type = obj.get("type", "")
    params = obj.get("params", {})
    placement = params.get("placement", {})
    px = placement.get("x", 0)
    py = placement.get("y", 0)
    pz = placement.get("z", 0)

    # Determine 3D bounding box (size_x, size_y, size_z)
    if obj_type == "Part::Box":
        size_x = params.get("length", 10)
        size_y = params.get("width", 10)
        size_z = params.get("height", 10)
    elif obj_type == "Part::Cylinder":
        r = params.get("radius", 5)
        h = params.get("height", 10)
        # Cylinder axis along Z: bounding box is 2r x 2r x h
        size_x = r * 2
        size_y = r * 2
        size_z = h
    elif obj_type == "Part::Cone":
        r1 = params.get("radius1", 5)
        r2 = params.get("radius2", 2)
        h = params.get("height", 10)
        max_r = max(r1, r2)
        size_x = max_r * 2
        size_y = max_r * 2
        size_z = h
    elif obj_type == "Part::Sphere":
        r = params.get("radius", 5)
        size_x = r * 2
        size_y = r * 2
        size_z = r * 2
    else:
        return None

    dx, dy, dz = direction
    if abs(dy) > 0.5:
        # front/rear elevation: X, Z
        return (px, pz, size_x, size_z)
    elif abs(dz) > 0.5:
        # plan view: X, Y
        return (px, py, size_x, size_y)
    elif abs(dx) > 0.5:
        # side elevation: Y, Z
        return (py, pz, size_y, size_z)
    return None


# Backward-compatible alias
_project_box_2d = _project_object_2d


def _compute_dimension_value(
    dim_type: str,
    view_name: str,
    views: list[dict[str, Any]],
    obj_map: dict[str, dict[str, Any]],
    scale: float = 1.0,
) -> float | None:
    """Compute the actual dimension value from project geometry.

    Supports all dimension types for Part::Box, Part::Cylinder, Part::Sphere,
    Part::Cone, and Part::Torus.

    Args:
        dim_type: Distance, DistanceX, DistanceY, Radius, Diameter, Angle.
        view_name: Name of the view referencing the source object.
        views: List of view dicts from the page.
        obj_map: Object name -> object dict lookup.
        scale: Page scale (not applied to dimension value — real-world units).

    Returns:
        Dimension value in mm (or degrees for Angle), or None if unknown.
    """
    import math

    for v in views:
        if v.get("name") != view_name:
            continue
        src = obj_map.get(v.get("source", ""))
        if not src:
            return None
        src_type = src.get("type", "")
        params = src.get("params", {})
        direction = tuple(v.get("direction", (0, 0, 1)))
        rect = _project_object_2d(src, direction)

        if dim_type == "DistanceX":
            return rect[2] if rect else None
        elif dim_type == "DistanceY":
            return rect[3] if rect else None
        elif dim_type == "Distance":
            # Diagonal / general distance — use the larger projected dimension
            if rect:
                return math.sqrt(rect[2] ** 2 + rect[3] ** 2)
            return None
        elif dim_type == "Radius":
            if src_type == "Part::Cylinder":
                return params.get("radius", 5)
            elif src_type == "Part::Sphere":
                return params.get("radius", 5)
            elif src_type == "Part::Cone":
                return params.get("radius1", 5)
            elif src_type == "Part::Torus":
                return params.get("radius2", 2)
            return None
        elif dim_type == "Diameter":
            if src_type == "Part::Cylinder":
                return params.get("radius", 5) * 2
            elif src_type == "Part::Sphere":
                return params.get("radius", 5) * 2
            elif src_type == "Part::Cone":
                return params.get("radius1", 5) * 2
            elif src_type == "Part::Torus":
                return params.get("radius2", 2) * 2
            return None
        elif dim_type == "Angle":
            if src_type == "Part::Cone":
                r1 = params.get("radius1", 5)
                r2 = params.get("radius2", 2)
                h = params.get("height", 10)
                if h > 0:
                    return math.degrees(math.atan2(abs(r1 - r2), h))
            # Default: 90° for box corners
            if src_type == "Part::Box":
                return 90.0
            return None
        return None
    return None


def export_drawing_svg(
    project: dict[str, Any],
    page_name: str,
    output_path: str,
) -> dict[str, Any]:
    """Export a TechDraw page to SVG directly from project data.

    Generates clean 2D fabrication drawing SVG by projecting Part::Box
    objects geometrically, without requiring FreeCAD's TechDraw SVG export.

    Args:
        project: Project dict.
        page_name: Name of the TechDraw page.
        output_path: SVG output file path.

    Returns:
        Result dict with output path and file size.
    """
    output_path = os.path.abspath(output_path)

    # Find the TechDraw page
    page_obj = None
    for o in project.get("objects", []):
        if o.get("name") == page_name:
            page_obj = o
            break
    if not page_obj:
        return {"success": False, "result": {"error": f"Page '{page_name}' not found"}}

    page_params = page_obj.get("params", {})
    scale = page_params.get("scale", 1.0)
    template = page_params.get("template", "A2_Landscape")
    page_w, page_h = PAPER_SIZES.get(template, (594, 420))
    views = page_params.get("views", [])

    # Build object lookup
    obj_map: dict[str, dict[str, Any]] = {}
    for o in project.get("objects", []):
        obj_map[o["name"]] = o

    # Group views by (x, y, direction) to overlay objects at same position
    view_groups: dict[tuple[float, float, tuple[float, float, float]], list[str]] = {}
    for v in views:
        if v.get("type") == "TechDraw::DrawViewPart":
            key = (
                v.get("x", 100),
                v.get("y", 150),
                tuple(v.get("direction", (0, 0, 1))),
            )
            view_groups.setdefault(key, []).append(v.get("source", ""))

    svg_elements: list[str] = []

    # Generate SVG for each view group
    for (vx, vy, direction), sources in view_groups.items():
        group_rects: list[tuple[float, float, float, float]] = []
        for src_name in sources:
            src_obj = obj_map.get(src_name)
            if not src_obj:
                continue
            rect = _project_box_2d(src_obj, direction)
            if rect:
                group_rects.append(rect)

        if not group_rects:
            continue

        # Compute bounding box of all rects in this group
        all_x = [r[0] for r in group_rects] + [r[0] + r[2] for r in group_rects]
        all_y = [r[1] for r in group_rects] + [r[1] + r[3] for r in group_rects]
        min_x, max_x = min(all_x), max(all_x)
        min_y, max_y = min(all_y), max(all_y)
        bb_w = max_x - min_x
        bb_h = max_y - min_y

        # Center the view group at (vx, vy) on the page
        # SVG Y is flipped (Y-down), model Z is up → flip Y
        for rx, ry, rw, rh in group_rects:
            # Transform model coords to page coords
            sx = vx + (rx - min_x) * scale - (bb_w * scale / 2)
            # Flip Y: model_y increases upward, SVG y increases downward
            sy = vy - (ry - min_y + rh) * scale + (bb_h * scale / 2)
            sw = rw * scale
            sh = rh * scale
            svg_elements.append(
                f'  <rect x="{sx:.1f}" y="{sy:.1f}" width="{sw:.1f}" height="{sh:.1f}" '
                f'fill="none" stroke="black" stroke-width="0.3"/>'
            )

    # Add dimension lines with actual measured values
    dims = page_params.get("dimensions", [])
    for dim in dims:
        dim_x = dim.get("x", 0)
        dim_y = dim.get("y", 0)
        dim_name = dim.get("name", "")
        dim_view = dim.get("view", "")
        dim_type = dim.get("dim_type", dim.get("type", "Distance"))
        prefix = dim.get("prefix", "")
        suffix = dim.get("suffix", "")
        tol_upper = dim.get("tolerance_upper")
        tol_lower = dim.get("tolerance_lower")

        dim_value = _compute_dimension_value(
            dim_type, dim_view, views, obj_map, scale,
        )

        # Build label: prefix + value + unit + suffix + tolerance
        if dim_value is not None:
            val_str = f"{dim_value:.2f}".rstrip("0").rstrip(".")
            # Unit: mm for linear, ° for angle (omit for R/∅ prefixed)
            if dim_type == "Angle":
                unit = "°"
            elif dim_type in ("Distance", "DistanceX", "DistanceY"):
                unit = " mm"
            else:
                unit = ""
            label = f"{prefix}{val_str}{unit}{suffix}"
            if tol_upper is not None or tol_lower is not None:
                tol_u = f"+{tol_upper}" if tol_upper is not None else ""
                tol_l = str(tol_lower) if tol_lower is not None else ""
                if tol_u and tol_l:
                    label += f" {tol_u}/{tol_l}"
                elif tol_u:
                    label += f" {tol_u}"
                elif tol_l:
                    label += f" {tol_l}"
        else:
            label = f"{prefix}{dim_name}{suffix}"

        svg_elements.append(
            f'  <text x="{dim_x}" y="{dim_y}" font-size="4" '
            f'font-family="sans-serif" fill="black">{label}</text>'
        )

    # Add text annotations
    for ann in page_params.get("annotations", []):
        ann_x = ann.get("x", 0)
        ann_y = ann.get("y", 0)
        ann_size = ann.get("font_size", 5)
        for i, line in enumerate(ann.get("text", [])):
            ly = ann_y + i * (ann_size + 2)
            svg_elements.append(
                f'  <text x="{ann_x}" y="{ly}" font-size="{ann_size}" '
                f'font-family="sans-serif" fill="black">{line}</text>'
            )

    # Add centerlines (dash-dot pattern)
    for cl in page_params.get("centerlines", []):
        cl_view = cl.get("view", "")
        orientation = cl.get("orientation", "vertical")
        position = cl.get("position", 0)
        ext_low = cl.get("extent_low", -10)
        ext_high = cl.get("extent_high", 10)
        # Find the view position to place the centerline relative to
        for v in views:
            if v.get("name") == cl_view:
                vx_cl = v.get("x", 100)
                vy_cl = v.get("y", 150)
                if orientation == "vertical":
                    x1 = vx_cl + position * scale
                    y1 = vy_cl + ext_low * scale
                    x2 = x1
                    y2 = vy_cl + ext_high * scale
                else:
                    x1 = vx_cl + ext_low * scale
                    y1 = vy_cl + position * scale
                    x2 = vx_cl + ext_high * scale
                    y2 = y1
                svg_elements.append(
                    f'  <line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
                    f'stroke="black" stroke-width="0.15" stroke-dasharray="8,2,2,2"/>'
                )
                break

    # Add hatches (cross-hatch pattern lines)
    for h in page_params.get("hatches", []):
        h_view = h.get("view", "")
        h_color = h.get("color", "#000000")
        h_rotation = h.get("rotation", 0)
        h_scale_val = h.get("scale", 1.0)
        for v in views:
            if v.get("name") == h_view:
                vx_h = v.get("x", 100)
                vy_h = v.get("y", 150)
                # Draw hatch lines as a simple diagonal pattern
                spacing = 3 * h_scale_val
                for offset in range(-50, 51):
                    lx = vx_h - 25 + offset * spacing
                    svg_elements.append(
                        f'  <line x1="{lx:.1f}" y1="{vy_h - 25:.1f}" '
                        f'x2="{lx + 25:.1f}" y2="{vy_h + 0:.1f}" '
                        f'stroke="{h_color}" stroke-width="0.1" opacity="0.5"/>'
                    )
                break

    # Add leader lines (arrow + text)
    for ld in page_params.get("leaders", []):
        ld_view = ld.get("view", "")
        sx = ld.get("start_x", 0)
        sy = ld.get("start_y", 0)
        ex = ld.get("end_x", 50)
        ey = ld.get("end_y", 50)
        ld_text = ld.get("text", "")
        for v in views:
            if v.get("name") == ld_view:
                vx_ld = v.get("x", 100)
                vy_ld = v.get("y", 150)
                abs_sx = vx_ld + sx * scale
                abs_sy = vy_ld - sy * scale
                abs_ex = vx_ld + ex * scale
                abs_ey = vy_ld - ey * scale
                svg_elements.append(
                    f'  <line x1="{abs_sx:.1f}" y1="{abs_sy:.1f}" '
                    f'x2="{abs_ex:.1f}" y2="{abs_ey:.1f}" '
                    f'stroke="black" stroke-width="0.25" marker-end="url(#arrow)"/>'
                )
                if ld_text:
                    svg_elements.append(
                        f'  <text x="{abs_ex + 2:.1f}" y="{abs_ey:.1f}" '
                        f'font-size="3.5" font-family="sans-serif" fill="black">{ld_text}</text>'
                    )
                break

    # Add balloons (circle + number)
    for bl in page_params.get("balloons", []):
        bl_view = bl.get("view", "")
        bl_text = bl.get("text", "1")
        bl_x = bl.get("x", 50)
        bl_y = bl.get("y", 50)
        bl_ox = bl.get("origin_x", 0)
        bl_oy = bl.get("origin_y", 0)
        for v in views:
            if v.get("name") == bl_view:
                vx_bl = v.get("x", 100)
                vy_bl = v.get("y", 150)
                origin_abs_x = vx_bl + bl_ox * scale
                origin_abs_y = vy_bl - bl_oy * scale
                # Leader line from origin to balloon
                svg_elements.append(
                    f'  <line x1="{origin_abs_x:.1f}" y1="{origin_abs_y:.1f}" '
                    f'x2="{bl_x:.1f}" y2="{bl_y:.1f}" '
                    f'stroke="black" stroke-width="0.25"/>'
                )
                # Balloon circle
                svg_elements.append(
                    f'  <circle cx="{bl_x:.1f}" cy="{bl_y:.1f}" r="5" '
                    f'fill="white" stroke="black" stroke-width="0.3"/>'
                )
                # Balloon text
                svg_elements.append(
                    f'  <text x="{bl_x:.1f}" y="{bl_y + 1.5:.1f}" '
                    f'font-size="4" font-family="sans-serif" fill="black" '
                    f'text-anchor="middle">{bl_text}</text>'
                )
                break

    # Add BOM table
    for bom in page_params.get("bom", []):
        bom_x = bom.get("x", 200)
        bom_y = bom.get("y", 250)
        bom_fs = bom.get("font_size", 3.5)
        columns = bom.get("columns", ["item", "name", "material", "quantity"])
        items = bom.get("items", [])
        col_width = 30
        row_height = bom_fs + 3
        # Header row
        for ci, col in enumerate(columns):
            cx = bom_x + ci * col_width
            svg_elements.append(
                f'  <rect x="{cx:.1f}" y="{bom_y:.1f}" '
                f'width="{col_width}" height="{row_height:.1f}" '
                f'fill="#e0e0e0" stroke="black" stroke-width="0.2"/>'
            )
            svg_elements.append(
                f'  <text x="{cx + 1:.1f}" y="{bom_y + bom_fs + 1:.1f}" '
                f'font-size="{bom_fs}" font-family="sans-serif" '
                f'font-weight="bold" fill="black">{col.upper()}</text>'
            )
        # Data rows
        for ri, item in enumerate(items):
            ry = bom_y + (ri + 1) * row_height
            for ci, col in enumerate(columns):
                cx = bom_x + ci * col_width
                svg_elements.append(
                    f'  <rect x="{cx:.1f}" y="{ry:.1f}" '
                    f'width="{col_width}" height="{row_height:.1f}" '
                    f'fill="white" stroke="black" stroke-width="0.2"/>'
                )
                val = item.get(col, "")
                svg_elements.append(
                    f'  <text x="{cx + 1:.1f}" y="{ry + bom_fs + 1:.1f}" '
                    f'font-size="{bom_fs}" font-family="sans-serif" fill="black">{val}</text>'
                )

    # Add clip groups (rectangular clipping frames)
    for ci, clip in enumerate(page_params.get("clips", [])):
        clip_name = clip.get("name", f"Clip{ci}")
        cx = clip.get("x", 100)
        cy = clip.get("y", 100)
        cw = clip.get("width", 80)
        ch = clip.get("height", 60)
        show_frame = clip.get("show_frame", True)
        clip_views = set(clip.get("views", []))

        # Clip rectangle top-left corner (SVG coords)
        clip_left = cx - cw / 2
        clip_top = cy - ch / 2

        # Define SVG clipPath
        clip_id = f"clip-{clip_name}"
        svg_elements.append(
            f'  <defs><clipPath id="{clip_id}">'
            f'<rect x="{clip_left:.1f}" y="{clip_top:.1f}" '
            f'width="{cw:.1f}" height="{ch:.1f}"/>'
            f'</clipPath></defs>'
        )

        # Redraw clipped view content inside a clipped group
        clipped_rects: list[str] = []
        for v in views:
            if v.get("name") not in clip_views:
                continue
            if v.get("type") != "TechDraw::DrawViewPart":
                continue
            src_obj = obj_map.get(v.get("source", ""))
            if not src_obj:
                continue
            direction = tuple(v.get("direction", (0, 0, 1)))
            rect = _project_object_2d(src_obj, direction)
            if not rect:
                continue
            vx_c = v.get("x", 100)
            vy_c = v.get("y", 150)
            rx, ry, rw, rh = rect
            # Simple placement: center the object at the view position
            sx = vx_c - (rw * scale / 2)
            sy = vy_c - (rh * scale / 2)
            sw = rw * scale
            sh = rh * scale
            clipped_rects.append(
                f'    <rect x="{sx:.1f}" y="{sy:.1f}" width="{sw:.1f}" height="{sh:.1f}" '
                f'fill="none" stroke="black" stroke-width="0.3"/>'
            )
        if clipped_rects:
            svg_elements.append(f'  <g clip-path="url(#{clip_id})">')
            svg_elements.extend(clipped_rects)
            svg_elements.append('  </g>')

        # Draw clip frame border
        if show_frame:
            svg_elements.append(
                f'  <rect x="{clip_left:.1f}" y="{clip_top:.1f}" '
                f'width="{cw:.1f}" height="{ch:.1f}" '
                f'fill="none" stroke="black" stroke-width="0.2" '
                f'stroke-dasharray="4,2"/>'
            )

    # Add cosmetic edges and center marks
    for ce in page_params.get("cosmetic_edges", []):
        ce_type = ce.get("type", "TechDraw::CosmeticEdge")
        ce_view = ce.get("view", "")
        ce_style = ce.get("style", "dashed")
        ce_color = ce.get("color", "#000000")
        ce_weight = ce.get("weight", 0.2)
        dash = LINE_STYLES.get(ce_style, LINE_STYLES["dashed"])["dash_pattern"]
        dash_attr = f' stroke-dasharray="{dash}"' if dash else ""

        for v in views:
            if v.get("name") != ce_view:
                continue
            vx_ce = v.get("x", 100)
            vy_ce = v.get("y", 150)

            if ce_type == "TechDraw::CenterMark":
                cx = ce.get("cx", 0)
                cy = ce.get("cy", 0)
                sz = ce.get("size", 5)
                # Horizontal arm
                svg_elements.append(
                    f'  <line x1="{vx_ce + (cx - sz) * scale:.1f}" '
                    f'y1="{vy_ce - cy * scale:.1f}" '
                    f'x2="{vx_ce + (cx + sz) * scale:.1f}" '
                    f'y2="{vy_ce - cy * scale:.1f}" '
                    f'stroke="{ce_color}" stroke-width="{ce_weight}"{dash_attr}/>'
                )
                # Vertical arm
                svg_elements.append(
                    f'  <line x1="{vx_ce + cx * scale:.1f}" '
                    f'y1="{vy_ce - (cy - sz) * scale:.1f}" '
                    f'x2="{vx_ce + cx * scale:.1f}" '
                    f'y2="{vy_ce - (cy + sz) * scale:.1f}" '
                    f'stroke="{ce_color}" stroke-width="{ce_weight}"{dash_attr}/>'
                )
            else:
                x1 = ce.get("x1", 0)
                y1 = ce.get("y1", 0)
                x2 = ce.get("x2", 50)
                y2 = ce.get("y2", 0)
                svg_elements.append(
                    f'  <line x1="{vx_ce + x1 * scale:.1f}" '
                    f'y1="{vy_ce - y1 * scale:.1f}" '
                    f'x2="{vx_ce + x2 * scale:.1f}" '
                    f'y2="{vy_ce - y2 * scale:.1f}" '
                    f'stroke="{ce_color}" stroke-width="{ce_weight}"{dash_attr}/>'
                )
            break

    # Add GD&T feature control frames
    for gdt in page_params.get("gdt", []):
        gdt_x = gdt.get("x", 100)
        gdt_y = gdt.get("y", 80)
        symbol = gdt.get("symbol", "⌖")
        tol = gdt.get("tolerance", 0)
        diameter_zone = gdt.get("diameter_zone", False)
        mc_symbol = gdt.get("material_condition_symbol", "")
        datum_refs = gdt.get("datum_refs", [])

        # Build FCF cells: each cell is a box with text
        cell_w = 14
        cell_h = 7
        cells = []

        # Cell 1: characteristic symbol
        cells.append(symbol)
        # Cell 2: tolerance value (with optional ∅ prefix and MC suffix)
        tol_str = f"∅{tol}" if diameter_zone else str(tol)
        if mc_symbol:
            tol_str += mc_symbol
        cells.append(tol_str)
        # Cells 3-5: datum references
        for ref in datum_refs[:3]:
            cells.append(ref)

        # Draw frame boxes
        total_w = len(cells) * cell_w
        frame_x = gdt_x - total_w / 2
        svg_elements.append(
            f'  <rect x="{frame_x:.1f}" y="{gdt_y - cell_h / 2:.1f}" '
            f'width="{total_w:.1f}" height="{cell_h:.1f}" '
            f'fill="white" stroke="black" stroke-width="0.3"/>'
        )
        for ci, cell_text in enumerate(cells):
            cx = frame_x + ci * cell_w
            # Divider line between cells
            if ci > 0:
                svg_elements.append(
                    f'  <line x1="{cx:.1f}" y1="{gdt_y - cell_h / 2:.1f}" '
                    f'x2="{cx:.1f}" y2="{gdt_y + cell_h / 2:.1f}" '
                    f'stroke="black" stroke-width="0.3"/>'
                )
            # Cell text (centered)
            svg_elements.append(
                f'  <text x="{cx + cell_w / 2:.1f}" y="{gdt_y + 1.5:.1f}" '
                f'font-size="4" font-family="sans-serif" fill="black" '
                f'text-anchor="middle">{cell_text}</text>'
            )

    # Add datum symbols
    for dat in page_params.get("datums", []):
        dat_x = dat.get("x", 100)
        dat_y = dat.get("y", 100)
        dat_letter = dat.get("letter", "A")

        # Triangle pointing down
        tri_h = 6
        tri_w = 5
        svg_elements.append(
            f'  <polygon points="{dat_x:.1f},{dat_y:.1f} '
            f'{dat_x - tri_w / 2:.1f},{dat_y - tri_h:.1f} '
            f'{dat_x + tri_w / 2:.1f},{dat_y - tri_h:.1f}" '
            f'fill="black" stroke="black" stroke-width="0.3"/>'
        )
        # Letter box above triangle
        box_w = 8
        box_h = 6
        svg_elements.append(
            f'  <rect x="{dat_x - box_w / 2:.1f}" y="{dat_y - tri_h - box_h:.1f}" '
            f'width="{box_w:.1f}" height="{box_h:.1f}" '
            f'fill="white" stroke="black" stroke-width="0.3"/>'
        )
        svg_elements.append(
            f'  <text x="{dat_x:.1f}" y="{dat_y - tri_h - 1.5:.1f}" '
            f'font-size="4.5" font-family="sans-serif" fill="black" '
            f'text-anchor="middle" font-weight="bold">{dat_letter}</text>'
        )

    # Add surface finish symbols
    for sf in page_params.get("surface_finishes", []):
        sf_x = sf.get("x", 100)
        sf_y = sf.get("y", 100)
        sf_ra = sf.get("ra")
        sf_rz = sf.get("rz")
        sf_process = sf.get("process", "any")
        sf_lay = sf.get("lay_direction", "")

        # Draw the surface finish check mark
        svg_elements.append(
            f'  <polyline points="{sf_x:.1f},{sf_y:.1f} '
            f'{sf_x + 2:.1f},{sf_y + 4:.1f} '
            f'{sf_x + 4:.1f},{sf_y - 6:.1f}" '
            f'fill="none" stroke="black" stroke-width="0.3"/>'
        )
        # Horizontal line for removal_required
        if sf_process == "removal_required":
            svg_elements.append(
                f'  <line x1="{sf_x + 4:.1f}" y1="{sf_y - 6:.1f}" '
                f'x2="{sf_x + 14:.1f}" y2="{sf_y - 6:.1f}" '
                f'stroke="black" stroke-width="0.3"/>'
            )
        elif sf_process == "removal_prohibited":
            svg_elements.append(
                f'  <line x1="{sf_x + 4:.1f}" y1="{sf_y - 6:.1f}" '
                f'x2="{sf_x + 14:.1f}" y2="{sf_y - 6:.1f}" '
                f'stroke="black" stroke-width="0.3"/>'
            )
            # Circle (prohibition) on the check mark
            svg_elements.append(
                f'  <circle cx="{sf_x + 3:.1f}" cy="{sf_y - 1:.1f}" r="3" '
                f'fill="none" stroke="black" stroke-width="0.2"/>'
            )

        # Roughness values (text above the symbol)
        label_parts = []
        if sf_ra is not None:
            label_parts.append(f"Ra {sf_ra}")
        if sf_rz is not None:
            label_parts.append(f"Rz {sf_rz}")
        if sf_lay:
            label_parts.append(sf_lay)
        if label_parts:
            label = " ".join(label_parts)
            svg_elements.append(
                f'  <text x="{sf_x + 5:.1f}" y="{sf_y - 8:.1f}" '
                f'font-size="3" font-family="sans-serif" fill="black">{label}</text>'
            )

    # Add title block as SVG text in bottom-right
    title_block = page_params.get("title_block")
    if title_block:
        tb_x = page_w - 90
        tb_y = page_h - 30
        tb_fields = [
            ("title", "Titel"),
            ("drawing_number", "Tek.nr"),
            ("revision", "Rev"),
            ("scale", "Schaal"),
            ("date", "Datum"),
            ("author", "Getekend"),
            ("material", "Materiaal"),
            ("company", "Bedrijf"),
        ]
        row_i = 0
        for field_key, label in tb_fields:
            val = title_block.get(field_key)
            if val:
                ty = tb_y + row_i * 4
                svg_elements.append(
                    f'  <text x="{tb_x}" y="{ty}" font-size="2.5" '
                    f'font-family="sans-serif" fill="black">{label}: {val}</text>'
                )
                row_i += 1

    # Write SVG (UTF-8 for dimension symbols like ∅)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(
            f'<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'width="{page_w}mm" height="{page_h}mm" '
            f'viewBox="0 0 {page_w} {page_h}">\n'
        )
        f.write(
            f'<rect width="{page_w}" height="{page_h}" '
            f'fill="white" stroke="black" stroke-width="0.5"/>\n'
        )
        f.write("\n".join(svg_elements))
        f.write("\n</svg>")

    file_size = os.path.getsize(output_path)
    return {
        "success": True,
        "result": {"output": output_path, "file_size": file_size, "format": "svg"},
    }


def export_drawing_pdf(
    project: dict[str, Any],
    page_name: str,
    output_path: str,
) -> dict[str, Any]:
    """Export a TechDraw page to PDF via FreeCAD.

    Note: PDF export from TechDraw typically requires the GUI module.
    This attempts a headless export; if unavailable, falls back to
    SVG-based conversion.

    Args:
        project: Project dict.
        page_name: Name of the TechDraw page.
        output_path: PDF output file path.

    Returns:
        Result dict.
    """
    output_path = os.path.abspath(output_path)
    script = _build_techdraw_script(project, page_name)
    script += (
        f"\nimport os, TechDraw\n"
        f"_page_obj = doc.getObject({page_name!r})\n"
        f"if _page_obj:\n"
        f"    # Try TechDrawGui PDF export (only works if GUI module available)\n"
        f"    _exported = False\n"
        f"    try:\n"
        f"        import TechDrawGui\n"
        f"        TechDrawGui.exportPageAsPdf(_page_obj, {output_path!r})\n"
        f"        _exported = True\n"
        f"    except (ImportError, AttributeError):\n"
        f"        pass\n"
        f"    if not _exported:\n"
        f"        # Fallback: SVG projection then convert to PDF\n"
        f"        _svg_path = {output_path!r}.replace('.pdf', '.tmp.svg')\n"
        f"        _shapes = [o for o in doc.Objects if hasattr(o, 'Shape') "
        f"and not o.isDerivedFrom('TechDraw::DrawView') "
        f"and not o.isDerivedFrom('TechDraw::DrawPage')]\n"
        f"        _svg_parts = []\n"
        f"        for _s in _shapes:\n"
        f"            try:\n"
        f"                _svg_parts.append(TechDraw.projectToSVG(_s.Shape, FreeCAD.Vector(0,0,1)))\n"
        f"            except Exception:\n"
        f"                pass\n"
        f"        if _svg_parts:\n"
        f"            with open(_svg_path, 'w') as _f:\n"
        f"                _f.write('<svg xmlns=\"http://www.w3.org/2000/svg\">\\n')\n"
        f"                _f.write('\\n'.join(_svg_parts))\n"
        f"                _f.write('\\n</svg>')\n"
        f"            import subprocess, shutil\n"
        f"            _inkscape = shutil.which('inkscape')\n"
        f"            if _inkscape:\n"
        f"                subprocess.run([_inkscape, _svg_path, '--export-filename=' + {output_path!r}], capture_output=True)\n"
        f"            else:\n"
        f"                try:\n"
        f"                    import cairosvg\n"
        f"                    cairosvg.svg2pdf(url=_svg_path, write_to={output_path!r})\n"
        f"                except ImportError:\n"
        f"                    _cli_result['error'] = 'PDF export requires inkscape or cairosvg'\n"
        f"            if os.path.exists(_svg_path):\n"
        f"                os.remove(_svg_path)\n"
        f"    if os.path.exists({output_path!r}):\n"
        f"        _cli_result['output'] = {output_path!r}\n"
        f"        _cli_result['file_size'] = os.path.getsize({output_path!r})\n"
        f"        _cli_result['format'] = 'pdf'\n"
        f"    elif 'error' not in _cli_result:\n"
        f"        _cli_result['error'] = 'PDF export failed (requires inkscape or cairosvg for headless mode)'\n"
        f"else:\n"
        f"    _cli_result['error'] = 'Page {page_name} not found'\n"
    )
    return run_script(script)
