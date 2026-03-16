"""PartDesign patterns and draft operations for manufacturing.

Implements Linear Pattern, Polar Pattern, and Draft operations
for manufacturing workflows requiring feature replication and
casting/molding angle requirements.
"""

from __future__ import annotations

import os
from typing import Any

from cli_anything.freecad.utils.freecad_backend import run_script


def linear_pattern(
    feature_name: str,
    direction: str = "X",
    length: float = 20.0,
    occurrences: int = 2,
    name: str | None = None,
) -> dict[str, Any]:
    """Create a linear pattern of a PartDesign feature.
    
    PartDesign::LinearPattern replicates features in a linear direction,
    essential for manufacturing arrays of holes, slots, or other features.
    
    Args:
        feature_name: Name of the feature to pattern.
        direction: Direction of pattern ("X", "Y", or "Z").
        length: Total length of the pattern in mm.
        occurrences: Number of instances in the pattern.
        name: Name for the pattern object (auto-generated if None).
        
    Returns:
        Dict with pattern creation results.
    """
    if name is None:
        name = f"LinearPattern_{feature_name}"
    
    # Map direction to vector
    direction_map = {
        "X": (1, 0, 0),
        "Y": (0, 1, 0),
        "Z": (0, 0, 1),
    }
    
    if direction.upper() not in direction_map:
        return {"success": False, "error": f"Invalid direction: {direction}. Use X, Y, or Z."}
    
    dir_vector = direction_map[direction.upper()]
    
    script = f"""
import FreeCAD
import PartDesign

# Ensure we have an active document
if FreeCAD.ActiveDocument is None:
    _cli_result['error'] = 'No active document'
else:
    doc = FreeCAD.ActiveDocument
    
    # Find the feature to pattern
    feature_obj = doc.getObject({feature_name!r})
    if feature_obj is None:
        _cli_result['error'] = 'Feature {feature_name} not found'
    else:
        try:
            # Create LinearPattern object
            pattern_obj = doc.addObject("PartDesign::LinearPattern", {name!r})
            
            # Set feature to pattern
            pattern_obj.Originals = [feature_obj]
            
            # Set pattern direction
            pattern_obj.Direction = FreeCAD.Vector({dir_vector[0]}, {dir_vector[1]}, {dir_vector[2]})
            
            # Set pattern parameters
            pattern_obj.Length = {length}
            pattern_obj.Occurrences = {occurrences}
            
            # Recompute to generate pattern
            doc.recompute()
            
            # Verify pattern was created successfully
            if hasattr(pattern_obj, 'Shape') and pattern_obj.Shape.isValid():
                _cli_result['success'] = True
                _cli_result['object_name'] = pattern_obj.Name
                _cli_result['direction'] = {direction!r}
                _cli_result['length'] = {length}
                _cli_result['occurrences'] = {occurrences}
                _cli_result['volume'] = pattern_obj.Shape.Volume
                _cli_result['area'] = pattern_obj.Shape.Area
                
                # Calculate spacing
                spacing = {length} / ({occurrences} - 1) if {occurrences} > 1 else 0
                _cli_result['spacing'] = spacing
            else:
                _cli_result['error'] = 'Pattern creation failed - invalid geometry'
                
        except Exception as e:
            _cli_result['error'] = f'Linear pattern creation failed: {{str(e)}}'
            import traceback
            _cli_result['traceback'] = traceback.format_exc()
"""

    return run_script(script)


def polar_pattern(
    feature_name: str,
    axis: str = "Z",
    angle: float = 360.0,
    occurrences: int = 6,
    reverse: bool = False,
    name: str | None = None,
) -> dict[str, Any]:
    """Create a polar pattern of a PartDesign feature.
    
    PartDesign::PolarPattern replicates features around an axis,
    essential for manufacturing bolt circles, radial features, etc.
    
    Args:
        feature_name: Name of the feature to pattern.
        axis: Axis of rotation ("X", "Y", or "Z").
        angle: Total angle of the pattern in degrees.
        occurrences: Number of instances in the pattern.
        reverse: Whether to reverse the direction.
        name: Name for the pattern object (auto-generated if None).
        
    Returns:
        Dict with pattern creation results.
    """
    if name is None:
        name = f"PolarPattern_{feature_name}"
    
    # Map axis to vector
    axis_map = {
        "X": (1, 0, 0),
        "Y": (0, 1, 0),
        "Z": (0, 0, 1),
    }
    
    if axis.upper() not in axis_map:
        return {"success": False, "error": f"Invalid axis: {axis}. Use X, Y, or Z."}
    
    axis_vector = axis_map[axis.upper()]
    
    script = f"""
import FreeCAD
import PartDesign

# Ensure we have an active document
if FreeCAD.ActiveDocument is None:
    _cli_result['error'] = 'No active document'
else:
    doc = FreeCAD.ActiveDocument
    
    # Find the feature to pattern
    feature_obj = doc.getObject({feature_name!r})
    if feature_obj is None:
        _cli_result['error'] = 'Feature {feature_name} not found'
    else:
        try:
            # Create PolarPattern object
            pattern_obj = doc.addObject("PartDesign::PolarPattern", {name!r})
            
            # Set feature to pattern
            pattern_obj.Originals = [feature_obj]
            
            # Set rotation axis
            pattern_obj.Axis = FreeCAD.Vector({axis_vector[0]}, {axis_vector[1]}, {axis_vector[2]})
            
            # Set pattern parameters
            pattern_obj.Angle = {angle}
            pattern_obj.Occurrences = {occurrences}
            pattern_obj.Reversed = {1 if reverse else 0}
            
            # Recompute to generate pattern
            doc.recompute()
            
            # Verify pattern was created successfully
            if hasattr(pattern_obj, 'Shape') and pattern_obj.Shape.isValid():
                _cli_result['success'] = True
                _cli_result['object_name'] = pattern_obj.Name
                _cli_result['axis'] = {axis!r}
                _cli_result['angle'] = {angle}
                _cli_result['occurrences'] = {occurrences}
                _cli_result['reversed'] = {reverse}
                _cli_result['volume'] = pattern_obj.Shape.Volume
                _cli_result['area'] = pattern_obj.Shape.Area
                
                # Calculate angular spacing
                angular_spacing = {angle} / ({occurrences} - 1) if {occurrences} > 1 else 0
                _cli_result['angular_spacing'] = angular_spacing
            else:
                _cli_result['error'] = 'Polar pattern creation failed - invalid geometry'
                
        except Exception as e:
            _cli_result['error'] = f'Polar pattern creation failed: {{str(e)}}'
            import traceback
            _cli_result['traceback'] = traceback.format_exc()
"""

    return run_script(script)


def draft(
    face_name: str,
    angle: float = 3.0,
    neutral_plane: str | None = None,
    reverse: bool = False,
    name: str | None = None,
) -> dict[str, Any]:
    """Apply draft angle to faces of a PartDesign body.
    
    PartDesign::Draft applies angular draft to selected faces,
    essential for casting, molding, and manufacturing processes.
    
    Args:
        face_name: Name of the face to apply draft to.
        angle: Draft angle in degrees.
        neutral_plane: Optional neutral plane name.
        reverse: Whether to reverse the draft direction.
        name: Name for the draft object (auto-generated if None).
        
    Returns:
        Dict with draft operation results.
    """
    if name is None:
        name = f"Draft_{face_name}"
    
    # Build neutral plane code
    neutral_code = ""
    if neutral_plane:
        neutral_code = f"draft_obj.NeutralPlane = doc.getObject({neutral_plane!r})"
    
    script = f"""
import FreeCAD
import PartDesign
import math

# Ensure we have an active document
if FreeCAD.ActiveDocument is None:
    _cli_result['error'] = 'No active document'
else:
    doc = FreeCAD.ActiveDocument
    
    # Find the face to draft
    face_obj = doc.getObject({face_name!r})
    if face_obj is None:
        _cli_result['error'] = f'Face {{ {face_name!r} }} not found'
    else:
        try:
            # Create Draft object
            draft_obj = doc.addObject("PartDesign::Draft", {name!r})
            
            # Set face to draft
            draft_obj.Base = face_obj
            
            # Set draft angle (convert to radians)
            angle_rad = math.radians({angle})
            draft_obj.Angle = angle_rad
            
            # Set draft direction
            draft_obj.Reversed = {1 if reverse else 0}
            
            # Set neutral plane if provided
            {neutral_code}
            
            # Recompute to apply draft
            doc.recompute()
            
            # Verify draft was created successfully
            if hasattr(draft_obj, 'Shape') and draft_obj.Shape.isValid():
                _cli_result['success'] = True
                _cli_result['object_name'] = draft_obj.Name
                _cli_result['angle'] = {angle}
                _cli_result['angle_rad'] = angle_rad
                _cli_result['reversed'] = {reverse}
                _cli_result['neutral_plane'] = {neutral_plane!r}
                _cli_result['volume'] = draft_obj.Shape.Volume
                _cli_result['area'] = draft_obj.Shape.Area
            else:
                _cli_result['error'] = 'Draft creation failed - invalid geometry'
                
        except Exception as e:
            _cli_result['error'] = f'Draft creation failed: {{str(e)}}'
            import traceback
            _cli_result['traceback'] = traceback.format_exc()
"""

    return run_script(script)


def feature_pattern_info(body_name: str) -> dict[str, Any]:
    """List all patterns in a PartDesign body.
    
    Args:
        body_name: Name of the body to list patterns for.
        
    Returns:
        Dict with pattern list and body info.
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
        _cli_result['error'] = f'Body {{ {body_name!r} }} not found'
    else:
        try:
            patterns = []
            if hasattr(body_obj, 'Group'):
                for feature in body_obj.Group:
                    # Check if feature is a pattern type
                    if hasattr(feature, 'TypeId') and 'Pattern' in feature.TypeId:
                        pattern_info = {{
                            'name': feature.Name,
                            'type': feature.TypeId,
                            'label': feature.Label,
                        }}
                        
                        # Add pattern-specific info
                        if hasattr(feature, 'Occurrences'):
                            pattern_info['occurrences'] = feature.Occurrences
                        if hasattr(feature, 'Length'):
                            pattern_info['length'] = feature.Length
                        if hasattr(feature, 'Angle'):
                            pattern_info['angle'] = feature.Angle
                        if hasattr(feature, 'Direction'):
                            pattern_info['direction'] = str(feature.Direction)
                        if hasattr(feature, 'Axis'):
                            pattern_info['axis'] = str(feature.Axis)
                            
                        patterns.append(pattern_info)
            
            _cli_result['success'] = True
            _cli_result['body_name'] = body_obj.Name
            _cli_result['patterns'] = patterns
            _cli_result['pattern_count'] = len(patterns)
                
        except Exception as e:
            _cli_result['error'] = f'Pattern list failed: {{str(e)}}'
            import traceback
            _cli_result['traceback'] = traceback.format_exc()
"""

    return run_script(script)