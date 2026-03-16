"""PartDesign operations — parametric modeling with sketches.

Implements PartDesign::Pad (extrusion) and PartDesign::Pocket (cutout)
for parametric workflows where sketches define 2D profiles that are
extruded or cut to create 3D geometry.
"""

from __future__ import annotations

import os
from typing import Any

from cli_anything.freecad.utils.freecad_backend import run_script


def pad(
    sketch_name: str,
    name: str | None = None,
    length: float = 10.0,
    symmetric: bool = False,
    reverse: bool = False,
    up_to_face: str | None = None,
) -> dict[str, Any]:
    """Create a parametric pad (extrusion) from a sketch.
    
    PartDesign::Pad extrudes a 2D sketch profile along its normal
    direction to create solid 3D geometry. Essential for parametric design.
    
    Args:
        sketch_name: Name of the sketch to extrude.
        name: Name for the pad object (auto-generated if None).
        length: Extrusion length in mm.
        symmetric: Whether to extrude symmetrically from sketch plane.
        reverse: Whether to reverse extrusion direction.
        up_to_face: Optional face name to extrude up to (instead of length).
        
    Returns:
        Dict with pad creation results.
    """
    if name is None:
        name = f"Pad_{sketch_name}"
    
    # Build direction parameters
    direction_code = ""
    if symmetric:
        direction_code = f"pad_obj.Symmetric = True"
    elif reverse:
        direction_code = f"pad_obj.Reversed = True"
    
    # Build length/upto parameters
    if up_to_face:
        length_code = f"pad_obj.Type = 'UpToFace'\npad_obj.UpToFace = {up_to_face!r}"
    else:
        length_code = f"pad_obj.Length = {length}"
    
    script = f"""
import FreeCAD
import PartDesign
import PartDesignGui

# Ensure we have an active document
if FreeCAD.ActiveDocument is None:
    _cli_result['error'] = 'No active document'
else:
    doc = FreeCAD.ActiveDocument
    
    # Find the sketch
    sketch_obj = doc.getObject({sketch_name!r})
    if sketch_obj is None:
        _cli_result['error'] = f'Sketch {{ {sketch_name!r} }} not found'
    else:
        try:
            # Create PartDesign::Pad object
            pad_obj = doc.addObject("PartDesign::Pad", {name!r})
            
            # Set sketch as profile
            pad_obj.Profile = sketch_obj
            
            # Set pad parameters
            {length_code}
            {direction_code}
            
            # Recompute to generate geometry
            doc.recompute()
            
            # Verify pad was created successfully
            if hasattr(pad_obj, 'Shape') and pad_obj.Shape.isValid():
                _cli_result['success'] = True
                _cli_result['object_name'] = pad_obj.Name
                _cli_result['volume'] = pad_obj.Shape.Volume
                _cli_result['area'] = pad_obj.Shape.Area
                _cli_result['length'] = getattr(pad_obj, 'Length', {length})
                _cli_result['symmetric'] = getattr(pad_obj, 'Symmetric', False)
                _cli_result['reversed'] = getattr(pad_obj, 'Reversed', False)
            else:
                _cli_result['error'] = 'Pad creation failed - invalid geometry'
                
        except Exception as e:
            _cli_result['error'] = f'Pad creation failed: {{str(e)}}'
            import traceback
            _cli_result['traceback'] = traceback.format_exc()
"""

    return run_script(script)


def pocket(
    sketch_name: str,
    name: str | None = None,
    length: float = 10.0,
    symmetric: bool = False,
    reverse: bool = False,
    up_to_face: str | None = None,
    pocket_type: str = "Length",
) -> dict[str, Any]:
    """Create a parametric pocket (cutout) from a sketch.
    
    PartDesign::Pocket removes material from a solid body using a
    2D sketch profile. Works with Pad to create complex features.
    
    Args:
        sketch_name: Name of the sketch to use for cutting.
        name: Name for the pocket object (auto-generated if None).
        length: Cut depth in mm.
        symmetric: Whether to cut symmetrically from sketch plane.
        reverse: Whether to reverse cut direction.
        up_to_face: Optional face name to cut up to.
        pocket_type: Type of pocket operation ("Length", "ThroughAll", "UpToFace").
        
    Returns:
        Dict with pocket creation results.
    """
    if name is None:
        name = f"Pocket_{sketch_name}"
    
    # Build direction parameters
    direction_code = ""
    if symmetric:
        direction_code = f"pocket_obj.Symmetric = True"
    elif reverse:
        direction_code = f"pocket_obj.Reversed = True"
    
    # Build type/length parameters
    if pocket_type == "ThroughAll":
        type_code = f"pocket_obj.Type = 'ThroughAll'"
    elif pocket_type == "UpToFace" and up_to_face:
        type_code = f"pocket_obj.Type = 'UpToFace'\npocket_obj.UpToFace = {up_to_face!r}"
    else:
        type_code = f"pocket_obj.Type = 'Length'\npocket_obj.Length = {length}"
    
    script = f"""
import FreeCAD
import PartDesign
import PartDesignGui

# Ensure we have an active document
if FreeCAD.ActiveDocument is None:
    _cli_result['error'] = 'No active document'
else:
    doc = FreeCAD.ActiveDocument
    
    # Find the sketch
    sketch_obj = doc.getObject({sketch_name!r})
    if sketch_obj is None:
        _cli_result['error'] = f'Sketch {{ {sketch_name!r} }} not found'
    else:
        try:
            # Create PartDesign::Pocket object
            pocket_obj = doc.addObject("PartDesign::Pocket", {name!r})
            
            # Set sketch as profile
            pocket_obj.Profile = sketch_obj
            
            # Set pocket parameters
            {type_code}
            {direction_code}
            
            # Recompute to generate geometry
            doc.recompute()
            
            # Verify pocket was created successfully
            if hasattr(pocket_obj, 'Shape'):
                _cli_result['success'] = True
                _cli_result['object_name'] = pocket_obj.Name
                _cli_result['type'] = pocket_type
                if hasattr(pocket_obj, 'Length'):
                    _cli_result['length'] = pocket_obj.Length
                _cli_result['symmetric'] = getattr(pocket_obj, 'Symmetric', False)
                _cli_result['reversed'] = getattr(pocket_obj, 'Reversed', False)
                
                # If we have a body, get the resulting shape info
                if hasattr(pocket_obj, 'Shape') and pocket_obj.Shape.isValid():
                    _cli_result['volume_removed'] = pocket_obj.Shape.Volume
                    _cli_result['area'] = pocket_obj.Shape.Area
            else:
                _cli_result['error'] = 'Pocket creation failed - no shape generated'
                
        except Exception as e:
            _cli_result['error'] = f'Pocket creation failed: {{str(e)}}'
            import traceback
            _cli_result['traceback'] = traceback.format_exc()
"""

    return run_script(script)


def body_create(
    name: str | None = None,
    base_feature: str | None = None,
) -> dict[str, Any]:
    """Create a PartDesign::Body container for parametric modeling.
    
    Bodies are containers that group parametric features (Pad, Pocket, etc.)
    and maintain a single contiguous solid shape.
    
    Args:
        name: Name for the body object (auto-generated if None).
        base_feature: Optional name of existing object to use as base feature.
        
    Returns:
        Dict with body creation results.
    """
    if name is None:
        name = "Body"
    
    script = f"""
import FreeCAD
import PartDesign
import PartDesignGui

# Ensure we have an active document
if FreeCAD.ActiveDocument is None:
    _cli_result['error'] = 'No active document'
else:
    doc = FreeCAD.ActiveDocument
    
    try:
        # Create PartDesign::Body
        body_obj = doc.addObject("PartDesign::Body", {name!r})
        
        # Set base feature if provided
        if {base_feature!r}:
            base_obj = doc.getObject({base_feature!r})
            if base_obj:
                body_obj.BaseFeature = base_obj
        
        # Recompute document
        doc.recompute()
        
        _cli_result['success'] = True
        _cli_result['object_name'] = body_obj.Name
        _cli_result['features_count'] = len(body_obj.Group) if hasattr(body_obj, 'Group') else 0
        
    except Exception as e:
        _cli_result['error'] = f'Body creation failed: {{str(e)}}'
        import traceback
        _cli_result['traceback'] = traceback.format_exc()
"""

    return run_script(script)


def feature_list(body_name: str) -> dict[str, Any]:
    """List features in a PartDesign body.
    
    Args:
        body_name: Name of the body to list features for.
        
    Returns:
        Dict with feature list and body info.
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
            features = []
            if hasattr(body_obj, 'Group'):
                for feature in body_obj.Group:
                    feature_info = {{
                        'name': feature.Name,
                        'type': feature.TypeId,
                        'label': feature.Label,
                    }}
                    
                    # Add specific info based on feature type
                    if hasattr(feature, 'Profile') and feature.Profile:
                        feature_info['sketch'] = feature.Profile.Name
                    if hasattr(feature, 'Length'):
                        feature_info['length'] = feature.Length
                    if hasattr(feature, 'Type'):
                        feature_info['pad_pocket_type'] = feature.Type
                        
                    features.append(feature_info)
            
            _cli_result['success'] = True
            _cli_result['body_name'] = body_obj.Name
            _cli_result['features'] = features
            _cli_result['feature_count'] = len(features)
            
            # Get final shape info if available
            if hasattr(body_obj, 'Shape') and body_obj.Shape.isValid():
                _cli_result['volume'] = body_obj.Shape.Volume
                _cli_result['area'] = body_obj.Shape.Area
                _cli_result['is_valid'] = True
            else:
                _cli_result['is_valid'] = False
                
        except Exception as e:
            _cli_result['error'] = f'Feature list failed: {{str(e)}}'
            import traceback
            _cli_result['traceback'] = traceback.format_exc()
"""

    return run_script(script)