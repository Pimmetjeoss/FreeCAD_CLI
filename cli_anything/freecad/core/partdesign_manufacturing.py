"""PartDesign manufacturing edge treatment operations.

Implements Fillet, Chamfer, and Thickness operations for manufacturing
workflows requiring edge treatment, deburring, and shell structures.
"""

from __future__ import annotations

import os
from typing import Any

from cli_anything.freecad.utils.freecad_backend import run_script


def partdesign_fillet(
    edge_name: str,
    radius: float = 1.0,
    name: str | None = None,
) -> dict[str, Any]:
    """Apply fillet (round) to edges of a PartDesign body.
    
    PartDesign::Fillet rounds edges for manufacturing requirements
    like stress reduction, assembly clearance, and finishing.
    
    Args:
        edge_name: Name of the edge to fillet.
        radius: Fillet radius in mm.
        name: Name for the fillet object (auto-generated if None).
        
    Returns:
        Dict with fillet creation results.
    """
    if name is None:
        name = f"Fillet_{edge_name}"
    
    script = f"""
import FreeCAD
import PartDesign

# Ensure we have an active document
if FreeCAD.ActiveDocument is None:
    _cli_result['error'] = 'No active document'
else:
    doc = FreeCAD.ActiveDocument
    
    # Find the edge to fillet
    edge_obj = doc.getObject({edge_name!r})
    if edge_obj is None:
        _cli_result['error'] = 'Edge {edge_name} not found'
    else:
        try:
            # Create Fillet object
            fillet_obj = doc.addObject("PartDesign::Fillet", {name!r})
            
            # Set base object and edge
            fillet_obj.Base = edge_obj
            
            # Set fillet radius
            fillet_obj.Radius = {radius}
            
            # Recompute to apply fillet
            doc.recompute()
            
            # Verify fillet was created successfully
            if hasattr(fillet_obj, 'Shape') and fillet_obj.Shape.isValid():
                _cli_result['success'] = True
                _cli_result['object_name'] = fillet_obj.Name
                _cli_result['radius'] = {radius}
                _cli_result['volume'] = fillet_obj.Shape.Volume
                _cli_result['area'] = fillet_obj.Shape.Area
            else:
                _cli_result['error'] = 'Fillet creation failed - invalid geometry'
                
        except Exception as e:
            _cli_result['error'] = f'Fillet creation failed: {{str(e)}}'
            import traceback
            _cli_result['traceback'] = traceback.format_exc()
"""

    return run_script(script)


def partdesign_chamfer(
    edge_name: str,
    size: float = 1.0,
    angle: float = 45.0,
    name: str | None = None,
) -> dict[str, Any]:
    """Apply chamfer to edges of a PartDesign body.
    
    PartDesign::Chamfer creates angled cuts for manufacturing
    deburring, assembly clearance, and aesthetic finishing.
    
    Args:
        edge_name: Name of the edge to chamfer.
        size: Chamfer size in mm.
        angle: Chamfer angle in degrees (default 45°).
        name: Name for the chamfer object (auto-generated if None).
        
    Returns:
        Dict with chamfer creation results.
    """
    if name is None:
        name = f"Chamfer_{edge_name}"
    
    script = f"""
import FreeCAD
import PartDesign
import math

# Ensure we have an active document
if FreeCAD.ActiveDocument is None:
    _cli_result['error'] = 'No active document'
else:
    doc = FreeCAD.ActiveDocument
    
    # Find the edge to chamfer
    edge_obj = doc.getObject({edge_name!r})
    if edge_obj is None:
        _cli_result['error'] = 'Edge {edge_name} not found'
    else:
        try:
            # Create Chamfer object
            chamfer_obj = doc.addObject("PartDesign::Chamfer", {name!r})
            
            # Set base object and edge
            chamfer_obj.Base = edge_obj
            
            # Set chamfer size and angle
            chamfer_obj.Size = {size}
            chamfer_obj.Angle = math.radians({angle})
            
            # Recompute to apply chamfer
            doc.recompute()
            
            # Verify chamfer was created successfully
            if hasattr(chamfer_obj, 'Shape') and chamfer_obj.Shape.isValid():
                _cli_result['success'] = True
                _cli_result['object_name'] = chamfer_obj.Name
                _cli_result['size'] = {size}
                _cli_result['angle'] = {angle}
                _cli_result['volume'] = chamfer_obj.Shape.Volume
                _cli_result['area'] = chamfer_obj.Shape.Area
            else:
                _cli_result['error'] = 'Chamfer creation failed - invalid geometry'
                
        except Exception as e:
            _cli_result['error'] = f'Chamfer creation failed: {{str(e)}}'
            import traceback
            _cli_result['traceback'] = traceback.format_exc()
"""

    return run_script(script)


def partdesign_thickness(
    face_name: str,
    thickness: float = 2.0,
    mode: str = "thickness",
    join: str = "arc",
    name: str | None = None,
) -> dict[str, Any]:
    """Create shell structure by applying thickness to faces.
    
    PartDesign::Thickness creates hollow structures from solid bodies,
    essential for sheet metal, enclosures, and lightweight parts.
    
    Args:
        face_name: Name of the face to remove for shell creation.
        thickness: Wall thickness in mm.
        mode: Thickness mode ("thickness", "offset", "skin").
        join: Join type for corners ("arc", "intersection").
        name: Name for the thickness object (auto-generated if None).
        
    Returns:
        Dict with thickness operation results.
    """
    if name is None:
        name = f"Thickness_{face_name}"
    
    script = f"""
import FreeCAD
import PartDesign

# Ensure we have an active document
if FreeCAD.ActiveDocument is None:
    _cli_result['error'] = 'No active document'
else:
    doc = FreeCAD.ActiveDocument
    
    # Find the face to remove
    face_obj = doc.getObject({face_name!r})
    if face_obj is None:
        _cli_result['error'] = 'Face {face_name} not found'
    else:
        try:
            # Create Thickness object
            thickness_obj = doc.addObject("PartDesign::Thickness", {name!r})
            
            # Set base object and face
            thickness_obj.Base = face_obj
            
            # Set thickness parameters
            thickness_obj.Thickness = {thickness}
            thickness_obj.Mode = {mode!r}
            thickness_obj.Join = {join!r}
            
            # Recompute to apply thickness
            doc.recompute()
            
            # Verify thickness was created successfully
            if hasattr(thickness_obj, 'Shape') and thickness_obj.Shape.isValid():
                _cli_result['success'] = True
                _cli_result['object_name'] = thickness_obj.Name
                _cli_result['thickness'] = {thickness}
                _cli_result['mode'] = {mode!r}
                _cli_result['join'] = {join!r}
                _cli_result['volume'] = thickness_obj.Shape.Volume
                _cli_result['area'] = thickness_obj.Shape.Area
                
                # Calculate wall volume (approximate)
                if hasattr(face_obj, 'Shape') and hasattr(face_obj.Shape, 'Area'):
                    wall_volume = face_obj.Shape.Area * {thickness}
                    _cli_result['wall_volume'] = wall_volume
            else:
                _cli_result['error'] = 'Thickness creation failed - invalid geometry'
                
        except Exception as e:
            _cli_result['error'] = f'Thickness creation failed: {{str(e)}}'
            import traceback
            _cli_result['traceback'] = traceback.format_exc()
"""

    return run_script(script)


def partdesign_fillet_chamfer_info(body_name: str) -> dict[str, Any]:
    """List all fillets and chamfers in a PartDesign body.
    
    Args:
        body_name: Name of the body to list edge treatments for.
        
    Returns:
        Dict with fillet/chamfer list and body info.
    """
    script = f"""
import FreeCAD

# Ensure we have an active document
if FreeCAD.ActiveDocument is None:
    _cli_result['error'] = 'No active document'
else:
    doc = FreeCAD.ActiveDocument
    
    # Find the body
    body_obj = doc.getObject({body_name!r})
    if body_obj is None:
        _cli_result['error'] = 'Body {body_name} not found'
    else:
        try:
            edge_treatments = []
            if hasattr(body_obj, 'Group'):
                for feature in body_obj.Group:
                    # Check if feature is fillet or chamfer
                    if hasattr(feature, 'TypeId') and ('Fillet' in feature.TypeId or 'Chamfer' in feature.TypeId):
                        treatment_info = {{
                            'name': feature.Name,
                            'type': feature.TypeId,
                            'label': feature.Label,
                        }}
                        
                        # Add specific info based on type
                        if 'Fillet' in feature.TypeId and hasattr(feature, 'Radius'):
                            treatment_info['radius'] = feature.Radius
                        elif 'Chamfer' in feature.TypeId:
                            if hasattr(feature, 'Size'):
                                treatment_info['size'] = feature.Size
                            if hasattr(feature, 'Angle'):
                                treatment_info['angle'] = feature.Angle
                            
                        edge_treatments.append(treatment_info)
            
            _cli_result['success'] = True
            _cli_result['body_name'] = body_obj.Name
            _cli_result['edge_treatments'] = edge_treatments
            _cli_result['treatment_count'] = len(edge_treatments)
                
        except Exception as e:
            _cli_result['error'] = f'Edge treatment list failed: {{str(e)}}'
            import traceback
            _cli_result['traceback'] = traceback.format_exc()
"""

    return run_script(script)