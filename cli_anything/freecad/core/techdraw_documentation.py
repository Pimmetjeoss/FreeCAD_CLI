"""TechDraw BOM and balloon operations for manufacturing documentation.

Implements Bill of Materials (BOM) and balloon callouts for assembly
drawings and manufacturing documentation workflows.
"""

from __future__ import annotations

import os
from typing import Any

from cli_anything.freecad.utils.freecad_backend import run_script


def create_bom(
    page_name: str,
    objects: list[str] | None = None,
    template: str = "default",
    name: str | None = None,
) -> dict[str, Any]:
    """Create a Bill of Materials table on a TechDraw page.
    
    TechDraw::BOM generates a parts list table for assembly documentation,
    essential for manufacturing and procurement workflows.
    
    Args:
        page_name: Name of the TechDraw page to add BOM to.
        objects: Optional list of object names to include (None = all).
        template: BOM template style ("default", "detailed", "minimal").
        name: Name for the BOM object (auto-generated if None).
        
    Returns:
        Dict with BOM creation results.
    """
    if name is None:
        name = f"BOM_{page_name}"
    
    # Build object filter code
    if objects:
        obj_filter = f"objects = [{', '.join(f'doc.getObject({obj!r})' for obj in objects)}]"
    else:
        obj_filter = "objects = [obj for obj in doc.Objects if hasattr(obj, 'Shape') and obj.Shape.isValid()]"
    
    script = f"""
import FreeCAD
import TechDraw
import Spreadsheet

# Ensure we have an active document
if FreeCAD.ActiveDocument is None:
    _cli_result['error'] = 'No active document'
else:
    doc = FreeCAD.ActiveDocument
    
    # Find the page
    page_obj = doc.getObject({page_name!r})
    if page_obj is None:
        _cli_result['error'] = 'Page {page_name} not found'
    else:
        try:
            # Create BOM spreadsheet
            bom_sheet = doc.addObject('Spreadsheet::Sheet', {name!r})
            
            # Set up BOM headers based on template
            headers = ['Item', 'Part Number', 'Description', 'Material', 'Quantity', 'Unit', 'Notes']
            if {template!r} == 'detailed':
                headers.extend(['Weight', 'Supplier', 'Cost'])
            elif {template!r} == 'minimal':
                headers = ['Item', 'Description', 'Quantity']
            
            # Write headers
            for col_idx, header in enumerate(headers, 1):
                cell = 'A' + str(col_idx)
                bom_sheet.set(cell, header)
                bom_sheet.setStyle(cell, 'bold')
            
            # Get objects for BOM
            {obj_filter}
            
            # Populate BOM data
            row = 2
            for i, obj in enumerate(objects, 1):
                if hasattr(obj, 'Label'):
                    bom_sheet.set('A' + str(row), str(i))
                    bom_sheet.set('B' + str(row), getattr(obj, 'PartNumber', obj.Name))
                    bom_sheet.set('C' + str(row), obj.Label)
                    bom_sheet.set('D' + str(row), getattr(obj, 'Material', 'Unknown'))
                    bom_sheet.set('E' + str(row), '1')  # Quantity
                    bom_sheet.set('F' + str(row), 'EA')  # Unit
                    
                    if {template!r} == 'detailed':
                        if hasattr(obj, 'Shape'):
                            volume = obj.Shape.Volume
                            bom_sheet.set('G' + str(row), f'{{volume:.2f}}')  # Weight (simplified)
                        bom_sheet.set('H' + str(row), '')  # Supplier
                        bom_sheet.set('I' + str(row), '')  # Cost
                    
                    row += 1
            
            # Auto-size columns
            for col in ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I']:
                bom_sheet.setColumnWidth(col, 10000)
            
            # Recompute document
            doc.recompute()
            
            _cli_result['success'] = True
            _cli_result['object_name'] = bom_sheet.Name
            _cli_result['page_name'] = {page_name!r}
            _cli_result['template'] = {template!r}
            _cli_result['item_count'] = len(objects)
            _cli_result['headers'] = headers
            _cli_result['rows'] = row - 2  # Subtract header rows
            
        except Exception as e:
            _cli_result['error'] = f'BOM creation failed: {{str(e)}}'
            import traceback
            _cli_result['traceback'] = traceback.format_exc()
"""

    return run_script(script)


def add_balloon(
    page_name: str,
    view_name: str,
    x: float = 50.0,
    y: float = 50.0,
    text: str = "1",
    symbol: str = "circle",
    name: str | None = None,
) -> dict[str, Any]:
    """Add a balloon callout to a TechDraw view.
    
    TechDraw::Balloon creates numbered callouts for part identification
    on assembly drawings, essential for manufacturing documentation.
    
    Args:
        page_name: Name of the TechDraw page.
        view_name: Name of the view to add balloon to.
        x: X position on page (mm).
        y: Y position on page (mm).
        text: Balloon text/number.
        symbol: Balloon symbol type ("circle", "square", "triangle").
        name: Name for the balloon object (auto-generated if None).
        
    Returns:
        Dict with balloon creation results.
    """
    if name is None:
        name = f"Balloon_{view_name}_{text}"
    
    script = f"""
import FreeCAD
import TechDraw

# Ensure we have an active document
if FreeCAD.ActiveDocument is None:
    _cli_result['error'] = 'No active document'
else:
    doc = FreeCAD.ActiveDocument
    
    # Find the page and view
    page_obj = doc.getObject({page_name!r})
    view_obj = doc.getObject({view_name!r})
    
    if page_obj is None:
        _cli_result['error'] = 'Page {page_name} not found'
    elif view_obj is None:
        _cli_result['error'] = 'View {view_name} not found'
    else:
        try:
            # Create balloon object
            balloon_obj = doc.addObject('TechDraw::DrawViewBalloon', {name!r})
            
            # Set balloon parameters
            balloon_obj.SourceView = view_obj
            balloon_obj.X = {x}
            balloon_obj.Y = {y}
            balloon_obj.Text = {text!r}
            balloon_obj.Symbol = {symbol!r}
            
            # Add balloon to page
            page_obj.addView(balloon_obj)
            
            # Recompute document
            doc.recompute()
            
            _cli_result['success'] = True
            _cli_result['object_name'] = balloon_obj.Name
            _cli_result['page_name'] = {page_name!r}
            _cli_result['view_name'] = {view_name!r}
            _cli_result['x'] = {x}
            _cli_result['y'] = {y}
            _cli_result['text'] = {text!r}
            _cli_result['symbol'] = {symbol!r}
            
        except Exception as e:
            _cli_result['error'] = f'Balloon creation failed: {{str(e)}}'
            import traceback
            _cli_result['traceback'] = traceback.format_exc()
"""

    return run_script(script)


def auto_balloon(
    page_name: str,
    view_name: str,
    start_number: int = 1,
    symbol: str = "circle",
    spacing: float = 20.0,
) -> dict[str, Any]:
    """Automatically add balloons to all parts in a view.
    
    Creates numbered balloon callouts for all visible parts,
    useful for assembly documentation and parts identification.
    
    Args:
        page_name: Name of the TechDraw page.
        view_name: Name of the view to add balloons to.
        start_number: Starting number for balloons.
        symbol: Balloon symbol type.
        spacing: Spacing between balloons (mm).
        
    Returns:
        Dict with auto-balloon results.
    """
    script = f"""
import FreeCAD
import TechDraw

# Ensure we have an active document
if FreeCAD.ActiveDocument is None:
    _cli_result['error'] = 'No active document'
else:
    doc = FreeCAD.ActiveDocument
    
    # Find the page and view
    page_obj = doc.getObject({page_name!r})
    view_obj = doc.getObject({view_name!r})
    
    if page_obj is None:
        _cli_result['error'] = 'Page {page_name} not found'
    elif view_obj is None:
        _cli_result['error'] = 'View {view_name} not found'
    else:
        try:
            balloons_created = []
            current_number = {start_number}
            current_x = 50.0  # Start position
            current_y = 50.0
            
            # Get visible objects from view
            visible_objects = []
            if hasattr(view_obj, 'Source'):
                source = view_obj.Source
                if hasattr(source, 'Group'):
                    visible_objects = [obj for obj in source.Group if hasattr(obj, 'Shape')]
                else:
                    visible_objects = [source]
            
            # Create balloons for each object
            for i, obj in enumerate(visible_objects):
                balloon_name = f"Balloon_{{view_obj.Name}}_{{current_number}}"
                balloon_obj = doc.addObject('TechDraw::DrawViewBalloon', balloon_name)
                
                # Set balloon parameters
                balloon_obj.SourceView = view_obj
                balloon_obj.X = current_x
                balloon_obj.Y = current_y
                balloon_obj.Text = str(current_number)
                balloon_obj.Symbol = {symbol!r}
                
                # Add balloon to page
                page_obj.addView(balloon_obj)
                
                balloons_created.append({{
                    'name': balloon_obj.Name,
                    'number': current_number,
                    'x': current_x,
                    'y': current_y,
                    'object': obj.Name if hasattr(obj, 'Name') else f'Object_{{i}}'
                }})
                
                # Update position for next balloon
                current_x += {spacing}
                if current_x > 200:  # Wrap to next row
                    current_x = 50.0
                    current_y += {spacing}
                
                current_number += 1
            
            # Recompute document
            doc.recompute()
            
            _cli_result['success'] = True
            _cli_result['page_name'] = {page_name!r}
            _cli_result['view_name'] = {view_name!r}
            _cli_result['balloons_created'] = balloons_created
            _cli_result['total_balloons'] = len(balloons_created)
            _cli_result['start_number'] = {start_number}
            _cli_result['end_number'] = current_number - 1
            _cli_result['symbol'] = {symbol!r}
            
        except Exception as e:
            _cli_result['error'] = f'Auto-balloon failed: {{str(e)}}'
            import traceback
            _cli_result['traceback'] = traceback.format_exc()
"""

    return run_script(script)


def bom_balloon_info(page_name: str) -> dict[str, Any]:
    """List all BOMs and balloons on a TechDraw page.
    
    Args:
        page_name: Name of the page to list documentation for.
        
    Returns:
        Dict with BOM and balloon information.
    """
    script = f"""
import FreeCAD

# Ensure we have an active document
if FreeCAD.ActiveDocument is None:
    _cli_result['error'] = 'No active document'
else:
    doc = FreeCAD.ActiveDocument
    
    # Find the page
    page_obj = doc.getObject({page_name!r})
    if page_obj is None:
        _cli_result['error'] = 'Page {page_name} not found'
    else:
        try:
            boms = []
            balloons = []
            
            # Check all objects for BOMs and balloons
            for obj in doc.Objects:
                if hasattr(obj, 'TypeId'):
                    if 'Spreadsheet' in obj.TypeId and hasattr(obj, 'Name') and 'BOM' in obj.Name:
                        bom_info = {{
                            'name': obj.Name,
                            'label': obj.Label,
                            'type': 'BOM',
                        }}
                        if hasattr(obj, 'rowCount'):
                            bom_info['rows'] = obj.rowCount()
                        if hasattr(obj, 'columnCount'):
                            bom_info['columns'] = obj.columnCount()
                        boms.append(bom_info)
                    
                    elif 'DrawViewBalloon' in obj.TypeId:
                        balloon_info = {{
                            'name': obj.Name,
                            'label': obj.Label,
                            'type': 'Balloon',
                        }}
                        if hasattr(obj, 'X'):
                            balloon_info['x'] = obj.X
                        if hasattr(obj, 'Y'):
                            balloon_info['y'] = obj.Y
                        if hasattr(obj, 'Text'):
                            balloon_info['text'] = obj.Text
                        if hasattr(obj, 'Symbol'):
                            balloon_info['symbol'] = obj.Symbol
                        balloons.append(balloon_info)
            
            _cli_result['success'] = True
            _cli_result['page_name'] = page_obj.Name
            _cli_result['boms'] = boms
            _cli_result['balloons'] = balloons
            _cli_result['bom_count'] = len(boms)
            _cli_result['balloon_count'] = len(balloons)
                
        except Exception as e:
            _cli_result['error'] = f'BOM/Balloon info failed: {{str(e)}}'
            import traceback
            _cli_result['traceback'] = traceback.format_exc()
"""

    return run_script(script)