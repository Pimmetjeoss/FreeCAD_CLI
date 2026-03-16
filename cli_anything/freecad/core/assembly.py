"""Assembly workbench operations for multi-part products.

Implements Assembly creation, constraints, exploded views, and
assembly-level BOM generation for manufacturing multi-part products.
"""

from __future__ import annotations

import os
from typing import Any

from cli_anything.freecad.utils.freecad_backend import run_script


def create_assembly(
    name: str | None = None,
    parts: list[str] | None = None,
) -> dict[str, Any]:
    """Create an assembly container for multi-part products.
    
    Assembly::AssemblyObject groups multiple parts into a single
    product assembly for manufacturing and documentation.
    
    Args:
        name: Name for the assembly object (auto-generated if None).
        parts: Optional list of part names to add to assembly.
        
    Returns:
        Dict with assembly creation results.
    """
    if name is None:
        name = "Assembly"
    
    # Build parts addition code
    if parts:
        parts_code = "\n".join([
            f"    part_obj = doc.getObject({part!r})"
            f"\n    if part_obj:"
            f"\n        assembly.addObject(part_obj)"
            f"\n        parts_added.append({part!r})"
            for part in parts
        ])
    else:
        parts_code = "    # No parts specified - empty assembly created"
    
    script = f"""
import FreeCAD
import Assembly

# Ensure we have an active document
if FreeCAD.ActiveDocument is None:
    _cli_result['error'] = 'No active document'
else:
    doc = FreeCAD.ActiveDocument
    
    try:
        # Create Assembly object
        assembly = doc.addObject('Assembly::AssemblyObject', {name!r})
        
        # Add parts if specified
        parts_added = []
{parts_code}
        
        # Recompute document
        doc.recompute()
        
        _cli_result['success'] = True
        _cli_result['object_name'] = assembly.Name
        _cli_result['parts_added'] = parts_added
        _cli_result['part_count'] = len(parts_added)
        
    except Exception as e:
        _cli_result['error'] = f'Assembly creation failed: {{str(e)}}'
        import traceback
        _cli_result['traceback'] = traceback.format_exc()
"""

    return run_script(script)


def add_part_to_assembly(
    assembly_name: str,
    part_name: str,
    placement: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Add a part to an assembly with optional placement.
    
    Args:
        assembly_name: Name of the assembly.
        part_name: Name of the part to add.
        placement: Optional placement dict with x, y, z, rotation.
        
    Returns:
        Dict with operation results.
    """
    placement_code = ""
    if placement:
        x = placement.get('x', 0)
        y = placement.get('y', 0)
        z = placement.get('z', 0)
        rotation = placement.get('rotation', 0)
        placement_code = f"""
        # Set placement
        from FreeCAD import Placement, Rotation, Vector
        part_obj.Placement = Placement(Vector({x}, {y}, {z}), Rotation(Vector(0, 0, 1), {rotation}))
"""
    
    script = f"""
import FreeCAD

# Ensure we have an active document
if FreeCAD.ActiveDocument is None:
    _cli_result['error'] = 'No active document'
else:
    doc = FreeCAD.ActiveDocument
    
    # Find assembly and part
    assembly = doc.getObject({assembly_name!r})
    part_obj = doc.getObject({part_name!r})
    
    if assembly is None:
        _cli_result['error'] = 'Assembly {assembly_name} not found'
    elif part_obj is None:
        _cli_result['error'] = 'Part {part_name} not found'
    else:
        try:
            # Add part to assembly
            assembly.addObject(part_obj)
            {placement_code}
            # Recompute
            doc.recompute()
            
            _cli_result['success'] = True
            _cli_result['assembly_name'] = assembly.Name
            _cli_result['part_name'] = part_obj.Name
            _cli_result['total_parts'] = len(assembly.Group) if hasattr(assembly, 'Group') else 1
            
        except Exception as e:
            _cli_result['error'] = f'Add part failed: {{str(e)}}'
            import traceback
            _cli_result['traceback'] = traceback.format_exc()
"""

    return run_script(script)


def assembly_constraint(
    assembly_name: str,
    part1_name: str,
    part2_name: str,
    constraint_type: str = " coincident",
    name: str | None = None,
) -> dict[str, Any]:
    """Add constraint between parts in an assembly.
    
    Args:
        assembly_name: Name of the assembly.
        part1_name: Name of first part.
        part2_name: Name of second part.
        constraint_type: Type of constraint ("coincident", "parallel", "perpendicular", "distance").
        name: Name for constraint object.
        
    Returns:
        Dict with constraint creation results.
    """
    if name is None:
        name = f"Constraint_{part1_name}_{part2_name}"
    
    script = f"""
import FreeCAD
import Assembly

# Ensure we have an active document
if FreeCAD.ActiveDocument is None:
    _cli_result['error'] = 'No active document'
else:
    doc = FreeCAD.ActiveDocument
    
    # Find assembly and parts
    assembly = doc.getObject({assembly_name!r})
    part1 = doc.getObject({part1_name!r})
    part2 = doc.getObject({part2_name!r})
    
    if assembly is None:
        _cli_result['error'] = 'Assembly {assembly_name} not found'
    elif part1 is None:
        _cli_result['error'] = 'Part {part1_name} not found'
    elif part2 is None:
        _cli_result['error'] = 'Part {part2_name} not found'
    else:
        try:
            # Create constraint object
            constraint = doc.addObject('Assembly::Constraint', {name!r})
            
            # Set constraint type and parts
            constraint.Type = {constraint_type!r}
            constraint.Part1 = part1
            constraint.Part2 = part2
            
            # Add constraint to assembly
            assembly.addObject(constraint)
            
            # Recompute
            doc.recompute()
            
            _cli_result['success'] = True
            _cli_result['object_name'] = constraint.Name
            _cli_result['assembly_name'] = assembly.Name
            _cli_result['part1'] = part1.Name
            _cli_result['part2'] = part2.Name
            _cli_result['constraint_type'] = {constraint_type!r}
            
        except Exception as e:
            _cli_result['error'] = f'Constraint creation failed: {{str(e)}}'
            import traceback
            _cli_result['traceback'] = traceback.format_exc()
"""

    return run_script(script)


def create_exploded_view(
    assembly_name: str,
    explode_factor: float = 1.5,
    name: str | None = None,
) -> dict[str, Any]:
    """Create an exploded view of an assembly.
    
    Args:
        assembly_name: Name of the assembly to explode.
        explode_factor: Factor to explode parts by (1.0 = normal, >1 = exploded).
        name: Name for exploded view object.
        
    Returns:
        Dict with exploded view results.
    """
    if name is None:
        name = f"Exploded_{assembly_name}"
    
    script = f"""
import FreeCAD
import Assembly

# Ensure we have an active document
if FreeCAD.ActiveDocument is None:
    _cli_result['error'] = 'No active document'
else:
    doc = FreeCAD.ActiveDocument
    
    # Find assembly
    assembly = doc.getObject({assembly_name!r})
    if assembly is None:
        _cli_result['error'] = 'Assembly {assembly_name} not found'
    else:
        try:
            # Create exploded view object
            exploded = doc.addObject('Assembly::ExplodedView', {name!r})
            
            # Set assembly reference
            exploded.Assembly = assembly
            
            # Set explode factor
            exploded.ExplodeFactor = {explode_factor}
            
            # Recompute
            doc.recompute()
            
            _cli_result['success'] = True
            _cli_result['object_name'] = exploded.Name
            _cli_result['assembly_name'] = assembly.Name
            _cli_result['explode_factor'] = {explode_factor}
            _cli_result['parts_count'] = len(assembly.Group) if hasattr(assembly, 'Group') else 0
            
        except Exception as e:
            _cli_result['error'] = f'Exploded view creation failed: {{str(e)}}'
            import traceback
            _cli_result['traceback'] = traceback.format_exc()
"""

    return run_script(script)


def assembly_info(assembly_name: str) -> dict[str, Any]:
    """Get information about an assembly.
    
    Args:
        assembly_name: Name of the assembly.
        
    Returns:
        Dict with assembly information.
    """
    script = f"""
import FreeCAD

# Ensure we have an active document
if FreeCAD.ActiveDocument is None:
    _cli_result['error'] = 'No active document'
else:
    doc = FreeCAD.ActiveDocument
    
    # Find assembly
    assembly = doc.getObject({assembly_name!r})
    if assembly is None:
        _cli_result['error'] = 'Assembly {assembly_name} not found'
    else:
        try:
            parts = []
            constraints = []
            
            if hasattr(assembly, 'Group'):
                for obj in assembly.Group:
                    if hasattr(obj, 'TypeId'):
                        if 'Constraint' in obj.TypeId:
                            constraint_info = {{
                                'name': obj.Name,
                                'type': obj.TypeId,
                                'label': obj.Label,
                            }}
                            if hasattr(obj, 'Type'):
                                constraint_info['constraint_type'] = obj.Type
                            if hasattr(obj, 'Part1'):
                                constraint_info['part1'] = obj.Part1.Name if obj.Part1 else None
                            if hasattr(obj, 'Part2'):
                                constraint_info['part2'] = obj.Part2.Name if obj.Part2 else None
                            constraints.append(constraint_info)
                        else:
                            part_info = {{
                                'name': obj.Name,
                                'type': obj.TypeId,
                                'label': obj.Label,
                            }}
                            if hasattr(obj, 'Shape'):
                                part_info['volume'] = obj.Shape.Volume
                                part_info['area'] = obj.Shape.Area
                            parts.append(part_info)
            
            # Calculate total assembly properties
            total_volume = sum(p.get('volume', 0) for p in parts)
            total_area = sum(p.get('area', 0) for p in parts)
            
            _cli_result['success'] = True
            _cli_result['assembly_name'] = assembly.Name
            _cli_result['parts'] = parts
            _cli_result['constraints'] = constraints
            _cli_result['part_count'] = len(parts)
            _cli_result['constraint_count'] = len(constraints)
            _cli_result['total_volume'] = total_volume
            _cli_result['total_area'] = total_area
            
        except Exception as e:
            _cli_result['error'] = f'Assembly info failed: {{str(e)}}'
            import traceback
            _cli_result['traceback'] = traceback.format_exc()
"""

    return run_script(script)