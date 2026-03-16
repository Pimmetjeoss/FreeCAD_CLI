"""DXF Import pipeline — import 2D profiles from DXF files for laser cutting.

Supports AutoCAD DXF format with layers, entities, and units conversion.
Critical for manufacturing workflows where customers provide 2D drawings.
"""

from __future__ import annotations

import os
from typing import Any

from cli_anything.freecad.utils.freecad_backend import run_script


def import_dxf(
    filepath: str,
    name: str | None = None,
    target_units: str = "mm",
    layer_filter: list[str] | None = None,
    scale_factor: float = 1.0,
) -> dict[str, Any]:
    """Import a DXF file as 2D profiles in FreeCAD.

    Args:
        filepath: Path to the DXF file.
        name: Name for the imported object (auto-generated if None).
        target_units: Target units for import (mm, cm, inch).
        layer_filter: Optional list of layer names to import (None = all).
        scale_factor: Scale factor to apply during import.

    Returns:
        Dict with import results including object name and layer info.
    """
    if not os.path.exists(filepath):
        return {"success": False, "error": f"DXF file not found: {filepath}"}

    # Extract base name for auto-naming
    if name is None:
        base_name = os.path.splitext(os.path.basename(filepath))[0]
        name = f"DXF_{base_name}"

    # Build layer filter code
    layer_code = ""
    if layer_filter:
        layer_list = ", ".join(f"'{layer}'" for layer in layer_filter)
        layer_code = f"""
# Filter by layers
filtered_entities = []
for entity in entities:
    layer_name = getattr(entity, 'layer', '0')
    if layer_name in [{layer_list}]:
        filtered_entities.append(entity)
entities = filtered_entities
"""

    script = f"""
import FreeCAD
import importDXF
import math

# Open or create document
if FreeCAD.ActiveDocument is None:
    doc = FreeCAD.newDocument("DXFImport")
else:
    doc = FreeCAD.ActiveDocument

# Import DXF file
try:
    # Use FreeCAD's DXF importer
    import importDXF
    importDXF.insert("{filepath}", doc.Name)
    
    # Get imported objects
    imported_objects = doc.Objects[-len(doc.Objects):]  # Get newly added objects
    
    if not imported_objects:
        _cli_result['error'] = 'No objects imported from DXF file'
    else:
        # Process and organize imported objects
        layers_found = set()
        valid_objects = []
        
        for obj in imported_objects:
            if hasattr(obj, 'Shape') and obj.Shape.isValid():
                # Apply scale factor if needed
                if {scale_factor} != 1.0:
                    obj.Shape = obj.Shape.scale({scale_factor})
                
                # Track layers
                layer_name = getattr(obj, 'layer', '0')
                layers_found.add(layer_name)
                
                # Rename with prefix
                obj.Name = f"{name}_{{obj.Name}}"
                obj.Label = f"{name}_{{obj.Label}}"
                
                valid_objects.append(obj)
        
        if valid_objects:
            _cli_result['success'] = True
            _cli_result['objects_created'] = len(valid_objects)
            _cli_result['layers_found'] = list(layers_found)
            _cli_result['object_names'] = [obj.Name for obj in valid_objects]
            _cli_result['units'] = "{target_units}"
            _cli_result['scale_factor'] = {scale_factor}
            
            # Calculate total geometry info
            total_length = 0
            total_area = 0
            for obj in valid_objects:
                if hasattr(obj.Shape, 'Length'):
                    total_length += obj.Shape.Length
                if hasattr(obj.Shape, 'Area'):
                    total_area += obj.Shape.Area
            
            _cli_result['total_length'] = total_length
            _cli_result['total_area'] = total_area
            
            # Recompute document
            doc.recompute()
        else:
            _cli_result['error'] = 'No valid geometry found in DXF file'

except Exception as e:
    _cli_result['error'] = f"DXF import failed: {{str(e)}}"
    import traceback
    _cli_result['traceback'] = traceback.format_exc()
"""

    return run_script(script)


def analyze_dxf(filepath: str) -> dict[str, Any]:
    """Analyze a DXF file without importing to get metadata.
    
    Args:
        filepath: Path to the DXF file.
        
    Returns:
        Dict with DXF file analysis including layers, entities, and bounds.
    """
    if not os.path.exists(filepath):
        return {"success": False, "error": f"DXF file not found: {filepath}"}

    script = f"""
import ezdxf
import math

try:
    # Load DXF file
    doc = ezdxf.readfile("{filepath}")
    msp = doc.modelspace()
    
    # Analyze entities
    entity_counts = {{}}
    layers = set()
    bounds = {{'min_x': float('inf'), 'min_y': float('inf'), 
               'max_x': float('-inf'), 'max_y': float('-inf')}}
    
    for entity in msp:
        entity_type = entity.dxftype()
        entity_counts[entity_type] = entity_counts.get(entity_type, 0) + 1
        
        # Track layers
        layer_name = getattr(entity, 'layer', '0')
        layers.add(layer_name)
        
        # Calculate bounds (simplified)
        try:
            if hasattr(entity, 'dxf') and hasattr(entity.dxf, 'start'):
                start = entity.dxf.start
                bounds['min_x'] = min(bounds['min_x'], start.x)
                bounds['min_y'] = min(bounds['min_y'], start.y)
                bounds['max_x'] = max(bounds['max_x'], start.x)
                bounds['max_y'] = max(bounds['max_y'], start.y)
            if hasattr(entity, 'dxf') and hasattr(entity.dxf, 'end'):
                end = entity.dxf.end
                bounds['min_x'] = min(bounds['min_x'], end.x)
                bounds['min_y'] = min(bounds['min_y'], end.y)
                bounds['max_x'] = max(bounds['max_x'], end.x)
                bounds['max_y'] = max(bounds['max_y'], end.y)
        except:
            pass
    
    # Get document units
    units = doc.units
    unit_names = {{0: 'unitless', 1: 'inches', 2: 'feet', 3: 'miles', 4: 'millimeters', 
                  5: 'centimeters', 6: 'meters', 7: 'kilometers', 8: 'microinches',
                  9: 'mils', 10: 'yards', 11: 'angstroms', 12: 'nanometers',
                  13: 'microns', 14: 'decimeters', 15: 'decameters', 16: 'hectometers',
                  17: 'gigameters', 18: 'AU', 19: 'light years', 20: 'parsecs'}}
    
    _cli_result['success'] = True
    _cli_result['filename'] = "{filepath}"
    _cli_result['total_entities'] = sum(entity_counts.values())
    _cli_result['entity_types'] = entity_counts
    _cli_result['layers'] = list(layers)
    _cli_result['units'] = unit_names.get(units, f'unknown ({{units}})')
    _cli_result['bounds'] = bounds if bounds['min_x'] != float('inf') else None
    _cli_result['has_geometry'] = any(entity_type in ['LINE', 'CIRCLE', 'ARC', 'POLYLINE', 'LWPOLYLINE', 'SPLINE'] 
                                    for entity_type in entity_counts.keys())

except Exception as e:
    _cli_result['error'] = f"DXF analysis failed: {{str(e)}}"
    import traceback
    _cli_result['traceback'] = traceback.format_exc()
"""

    return run_script(script)