"""SVG import and unit conversion utilities."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from typing import Any


# ── Unit Conversion Constants ────────────────────────────────────────

UNIT_TO_MM = {
    "mm": 1.0,
    "cm": 10.0,
    "m": 1000.0,
    "in": 25.4,
    "inch": 25.4,
    "inches": 25.4,
    "pt": 0.352778,  # 1 pt = 1/72 inch
    "pc": 4.233333,  # 1 pica = 12 pt
    "px": None,  # Depends on DPI, assume 96 DPI = 0.264583 mm
}

DEFAULT_DPI = 96
PX_TO_MM = 25.4 / DEFAULT_DPI  # 0.264583 mm per pixel at 96 DPI


def parse_svg_units(svg_content: str) -> dict[str, Any]:
    """Parse SVG file to extract dimensions and units.
    
    Args:
        svg_content: SVG file content as string.
        
    Returns:
        Dict with width, height, unit, and optional viewBox info.
    """
    try:
        root = ET.fromstring(svg_content)
    except ET.ParseError:
        # Try to find SVG element with regex if XML parsing fails
        match = re.search(r'<svg[^>]*>', svg_content)
        if not match:
            raise ValueError("Invalid SVG: no <svg> element found")
        svg_tag = match.group(0)
    else:
        svg_tag = ET.tostring(root, encoding='unicode')
    
    result = {
        "width": None,
        "height": None,
        "unit": None,
        "viewbox_width": None,
        "viewbox_height": None,
    }
    
    # Parse width
    width_match = re.search(r'width="([^"]*)"', svg_tag)
    if width_match:
        width_str = width_match.group(1)
        parsed = _parse_dimension(width_str)
        result["width"] = parsed["value"]
        if parsed["unit"]:
            result["unit"] = parsed["unit"]
    
    # Parse height
    height_match = re.search(r'height="([^"]*)"', svg_tag)
    if height_match:
        height_str = height_match.group(1)
        parsed = _parse_dimension(height_str)
        result["height"] = parsed["value"]
        if parsed["unit"] and not result["unit"]:
            result["unit"] = parsed["unit"]
    
    # Parse viewBox
    viewbox_match = re.search(r'viewBox="([^"]*)"', svg_tag)
    if viewbox_match:
        viewbox_str = viewbox_match.group(1)
        parts = viewbox_str.split()
        if len(parts) == 4:
            result["viewbox_width"] = float(parts[2])
            result["viewbox_height"] = float(parts[3])
    
    return result


def _parse_dimension(dim_str: str) -> dict[str, Any]:
    """Parse a dimension string like '100mm', '5in', '200'.
    
    Args:
        dim_str: Dimension string.
        
    Returns:
        Dict with value and unit.
    """
    dim_str = dim_str.strip()
    
    # Match number followed by optional unit
    match = re.match(r'^([\d.]+)\s*([a-zA-Z]*)$', dim_str)
    if not match:
        raise ValueError(f"Invalid dimension: {dim_str}")
    
    value = float(match.group(1))
    unit = match.group(2).lower() if match.group(2) else None
    
    return {"value": value, "unit": unit}


def convert_units(value: float, from_unit: str, to_unit: str) -> float:
    """Convert a value from one unit to another.
    
    Args:
        value: The value to convert.
        from_unit: Source unit (mm, cm, in, etc.).
        to_unit: Target unit.
        
    Returns:
        Converted value.
    """
    from_unit = from_unit.lower()
    to_unit = to_unit.lower()
    
    if from_unit == to_unit:
        return value
    
    if from_unit not in UNIT_TO_MM:
        raise ValueError(f"Unknown unit: {from_unit}")
    if to_unit not in UNIT_TO_MM:
        raise ValueError(f"Unknown unit: {to_unit}")
    
    # Convert to mm first, then to target unit
    value_in_mm = value * UNIT_TO_MM[from_unit]
    if from_unit == "px":
        value_in_mm = value * PX_TO_MM
    
    result = value_in_mm / UNIT_TO_MM[to_unit]
    if to_unit == "px":
        result = value_in_mm / PX_TO_MM
    
    return result


def apply_scale(value: float, scale: float) -> float:
    """Apply scale factor to a value.
    
    Args:
        value: Original value.
        scale: Scale factor.
        
    Returns:
        Scaled value.
    """
    return value * scale


def convert_and_scale(value: float, from_unit: str, to_unit: str, scale: float) -> float:
    """Convert units and apply scale factor.
    
    Args:
        value: Original value.
        from_unit: Source unit.
        to_unit: Target unit.
        scale: Scale factor.
        
    Returns:
        Converted and scaled value.
    """
    converted = convert_units(value, from_unit, to_unit)
    return apply_scale(converted, scale)


def calculate_scale_to_fit(
    current_width: float,
    current_height: float,
    target_width: float | None = None,
    target_height: float | None = None,
    maintain_aspect: bool = True,
) -> float:
    """Calculate scale factor to fit dimensions to target size.
    
    Args:
        current_width: Current width.
        current_height: Current height.
        target_width: Target width (optional).
        target_height: Target height (optional).
        maintain_aspect: Maintain aspect ratio.
        
    Returns:
        Scale factor.
    """
    if target_width and target_height:
        if maintain_aspect:
            # Use the smaller scale to fit within bounds
            scale_w = target_width / current_width
            scale_h = target_height / current_height
            return min(scale_w, scale_h)
        else:
            # Return average scale
            return (target_width / current_width + target_height / current_height) / 2
    elif target_width:
        return target_width / current_width
    elif target_height:
        return target_height / current_height
    else:
        return 1.0


def generate_svg_import_script(
    filepath: str,
    target_units: str = "mm",
    scale: float = 1.0,
) -> str:
    """Generate FreeCAD Python script for SVG import.
    
    Args:
        filepath: Path to SVG file.
        target_units: Target unit system.
        scale: Scale factor.
        
    Returns:
        FreeCAD Python script.
    """
    return (
        f"import importSVG\n"
        f"import FreeCAD\n"
        f"\n"
        f"# Import SVG\n"
        f"importSVG.insert({filepath!r}, doc.Name)\n"
        f"\n"
        f"# Apply scale if needed\n"
        f"if {scale} != 1.0:\n"
        f"    for obj in doc.Objects:\n"
        f"        if hasattr(obj, 'Shape'):\n"
        f"            obj.Shape = obj.Shape.scale({scale})\n"
        f"\n"
        f"# Set document units\n"
        f"FreeCAD.ParamGet('User parameter:BaseApp/Preferences/Units').SetInt('UserSchema', 3)  # mm\n"
    )
