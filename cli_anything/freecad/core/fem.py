"""FEM workbench operations for stress and thermal analysis.

Implements Finite Element Method analysis for manufacturing validation
including material assignment, meshing, boundary conditions, and solving.
"""

from __future__ import annotations

import os
from typing import Any

from cli_anything.freecad.utils.freecad_backend import run_script


def create_analysis(
    name: str | None = None,
) -> dict[str, Any]:
    """Create a FEM analysis container.
    
    FEM::Analysis groups all FEM objects for a complete
    finite element analysis workflow.
    
    Args:
        name: Name for the analysis object (auto-generated if None).
        
    Returns:
        Dict with analysis creation results.
    """
    if name is None:
        name = "FEMAnalysis"
    
    script = f"""
import FreeCAD
import Fem

# Ensure we have an active document
if FreeCAD.ActiveDocument is None:
    _cli_result['error'] = 'No active document'
else:
    doc = FreeCAD.ActiveDocument
    
    try:
        # Create Analysis object
        analysis = doc.addObject('Fem::FemAnalysis', {name!r})
        
        # Recompute document
        doc.recompute()
        
        _cli_result['success'] = True
        _cli_result['object_name'] = analysis.Name
        
    except Exception as e:
        _cli_result['error'] = f'Analysis creation failed: {{str(e)}}'
        import traceback
        _cli_result['traceback'] = traceback.format_exc()
"""

    return run_script(script)


def add_material(
    analysis_name: str,
    object_name: str,
    material: str = "Steel",
    name: str | None = None,
) -> dict[str, Any]:
    """Add material properties to an object for FEM analysis.
    
    FEM::Material assigns material properties essential for
    accurate stress and thermal calculations.
    
    Args:
        analysis_name: Name of the FEM analysis.
        object_name: Name of the object to assign material to.
        material: Material type ("Steel", "Aluminum", "Concrete", "Custom").
        name: Name for material object.
        
    Returns:
        Dict with material assignment results.
    """
    if name is None:
        name = f"Material_{object_name}"
    
    # Material properties database
    materials = {
        "Steel": {
            "YoungsModulus": "200000",  # MPa
            "PoissonRatio": "0.30",
            "Density": "7850",  # kg/m³
            "ThermalExpansionCoefficient": "12e-6",
            "ThermalConductivity": "50",
            "SpecificHeat": "460",
        },
        "Aluminum": {
            "YoungsModulus": "70000",
            "PoissonRatio": "0.33",
            "Density": "2700",
            "ThermalExpansionCoefficient": "23e-6",
            "ThermalConductivity": "237",
            "SpecificHeat": "900",
        },
        "Concrete": {
            "YoungsModulus": "30000",
            "PoissonRatio": "0.20",
            "Density": "2400",
            "ThermalExpansionCoefficient": "10e-6",
            "ThermalConductivity": "1.7",
            "SpecificHeat": "880",
        },
    }
    
    mat_props = materials.get(material, materials["Steel"])
    
    script = f"""
import FreeCAD
import Fem

# Ensure we have an active document
if FreeCAD.ActiveDocument is None:
    _cli_result['error'] = 'No active document'
else:
    doc = FreeCAD.ActiveDocument
    
    # Find analysis and object
    analysis = doc.getObject({analysis_name!r})
    obj = doc.getObject({object_name!r})
    
    if analysis is None:
        _cli_result['error'] = 'Analysis {analysis_name} not found'
    elif obj is None:
        _cli_result['error'] = 'Object {object_name} not found'
    else:
        try:
            # Create Material object
            material_obj = doc.addObject('Fem::Material', {name!r})
            
            # Set material properties
            material_obj.Material = {{
                'Name': {material!r},
                'YoungsModulus': '{mat_props['YoungsModulus']} MPa',
                'PoissonRatio': '{mat_props['PoissonRatio']}',
                'Density': '{mat_props['Density']} kg/m^3',
                'ThermalExpansionCoefficient': '{mat_props['ThermalExpansionCoefficient']} m/m/K',
                'ThermalConductivity': '{mat_props['ThermalConductivity']} W/m/K',
                'SpecificHeat': '{mat_props['SpecificHeat']} J/kg/K',
            }}
            
            # Add material to analysis
            analysis.addObject(material_obj)
            
            # Recompute
            doc.recompute()
            
            _cli_result['success'] = True
            _cli_result['object_name'] = material_obj.Name
            _cli_result['analysis_name'] = analysis.Name
            _cli_result['target_object'] = obj.Name
            _cli_result['material'] = {material!r}
            _cli_result['properties'] = {mat_props}
            
        except Exception as e:
            _cli_result['error'] = f'Material assignment failed: {{str(e)}}'
            import traceback
            _cli_result['traceback'] = traceback.format_exc()
"""

    return run_script(script)


def create_mesh(
    analysis_name: str,
    object_name: str,
    element_size: float = 5.0,
    element_type: str = "Tetrahedron",
    name: str | None = None,
) -> dict[str, Any]:
    """Create a finite element mesh for analysis.
    
    FEM::FemMeshMesh generates the mesh required for
    finite element calculations.
    
    Args:
        analysis_name: Name of the FEM analysis.
        object_name: Name of the object to mesh.
        element_size: Mesh element size in mm (smaller = more accurate).
        element_type: Type of mesh elements ("Tetrahedron", "Hexahedron").
        name: Name for mesh object.
        
    Returns:
        Dict with mesh creation results.
    """
    if name is None:
        name = f"Mesh_{object_name}"
    
    script = f"""
import FreeCAD
import Fem
import Mesh

# Ensure we have an active document
if FreeCAD.ActiveDocument is None:
    _cli_result['error'] = 'No active document'
else:
    doc = FreeCAD.ActiveDocument
    
    # Find analysis and object
    analysis = doc.getObject({analysis_name!r})
    obj = doc.getObject({object_name!r})
    
    if analysis is None:
        _cli_result['error'] = 'Analysis {analysis_name} not found'
    elif obj is None:
        _cli_result['error'] = 'Object {object_name} not found'
    else:
        try:
            # Create Mesh object
            mesh_obj = doc.addObject('Fem::FemMeshMesh', {name!r})
            
            # Set mesh parameters
            mesh_obj.Shape = obj
            mesh_obj.ElementSize = {element_size}
            mesh_obj.ElementType = {element_type!r}
            
            # Add mesh to analysis
            analysis.addObject(mesh_obj)
            
            # Generate mesh
            mesh_obj.createMesh()
            
            # Recompute
            doc.recompute()
            
            # Get mesh statistics
            if hasattr(mesh_obj, 'FemMesh'):
                fem_mesh = mesh_obj.FemMesh
                node_count = fem_mesh.NodeCount
                element_count = fem_mesh.ElementCount
            else:
                node_count = 0
                element_count = 0
            
            _cli_result['success'] = True
            _cli_result['object_name'] = mesh_obj.Name
            _cli_result['analysis_name'] = analysis.Name
            _cli_result['target_object'] = obj.Name
            _cli_result['element_size'] = {element_size}
            _cli_result['element_type'] = {element_type!r}
            _cli_result['node_count'] = node_count
            _cli_result['element_count'] = element_count
            
        except Exception as e:
            _cli_result['error'] = f'Mesh creation failed: {{str(e)}}'
            import traceback
            _cli_result['traceback'] = traceback.format_exc()
"""

    return run_script(script)


def add_constraint_fixed(
    analysis_name: str,
    object_name: str,
    face_name: str | None = None,
    name: str | None = None,
) -> dict[str, Any]:
    """Add fixed constraint (boundary condition) to analysis.
    
    FEM::ConstraintFixed defines where the structure is
    constrained from movement.
    
    Args:
        analysis_name: Name of the FEM analysis.
        object_name: Name of the object.
        face_name: Optional specific face to fix (None = entire object).
        name: Name for constraint object.
        
    Returns:
        Dict with constraint creation results.
    """
    if name is None:
        name = f"Fixed_{object_name}"
    
    face_code = ""
    if face_name:
        face_code = f"constraint.Face = {face_name!r}"
    
    script = f"""
import FreeCAD
import Fem

# Ensure we have an active document
if FreeCAD.ActiveDocument is None:
    _cli_result['error'] = 'No active document'
else:
    doc = FreeCAD.ActiveDocument
    
    # Find analysis and object
    analysis = doc.getObject({analysis_name!r})
    obj = doc.getObject({object_name!r})
    
    if analysis is None:
        _cli_result['error'] = 'Analysis {analysis_name} not found'
    elif obj is None:
        _cli_result['error'] = 'Object {object_name} not found'
    else:
        try:
            # Create Fixed constraint
            constraint = doc.addObject('Fem::ConstraintFixed', {name!r})
            
            # Set constraint reference
            constraint.References = [(obj, ('', ))]
            {face_code}
            
            # Add constraint to analysis
            analysis.addObject(constraint)
            
            # Recompute
            doc.recompute()
            
            _cli_result['success'] = True
            _cli_result['object_name'] = constraint.Name
            _cli_result['analysis_name'] = analysis.Name
            _cli_result['target_object'] = obj.Name
            _cli_result['face'] = {face_name!r}
            
        except Exception as e:
            _cli_result['error'] = f'Fixed constraint failed: {{str(e)}}'
            import traceback
            _cli_result['traceback'] = traceback.format_exc()
"""

    return run_script(script)


def add_constraint_force(
    analysis_name: str,
    object_name: str,
    force_x: float = 0.0,
    force_y: float = 0.0,
    force_z: float = -1000.0,
    face_name: str | None = None,
    name: str | None = None,
) -> dict[str, Any]:
    """Add force constraint (load) to analysis.
    
    FEM::ConstraintForce applies forces to the structure
    for stress analysis.
    
    Args:
        analysis_name: Name of the FEM analysis.
        object_name: Name of the object.
        force_x: Force in X direction (N).
        force_y: Force in Y direction (N).
        force_z: Force in Z direction (N, default downward).
        face_name: Optional specific face to apply force to.
        name: Name for constraint object.
        
    Returns:
        Dict with constraint creation results.
    """
    if name is None:
        name = f"Force_{object_name}"
    
    face_code = ""
    if face_name:
        face_code = f"constraint.Face = {face_name!r}"
    
    script = f"""
import FreeCAD
import Fem

# Ensure we have an active document
if FreeCAD.ActiveDocument is None:
    _cli_result['error'] = 'No active document'
else:
    doc = FreeCAD.ActiveDocument
    
    # Find analysis and object
    analysis = doc.getObject({analysis_name!r})
    obj = doc.getObject({object_name!r})
    
    if analysis is None:
        _cli_result['error'] = 'Analysis {analysis_name} not found'
    elif obj is None:
        _cli_result['error'] = 'Object {object_name} not found'
    else:
        try:
            # Create Force constraint
            constraint = doc.addObject('Fem::ConstraintForce', {name!r})
            
            # Set constraint reference
            constraint.References = [(obj, ('', ))]
            
            # Set force values
            constraint.ForceX = {force_x}
            constraint.ForceY = {force_y}
            constraint.ForceZ = {force_z}
            
            {face_code}
            
            # Add constraint to analysis
            analysis.addObject(constraint)
            
            # Recompute
            doc.recompute()
            
            # Calculate resultant force
            import math
            resultant = math.sqrt({force_x}**2 + {force_y}**2 + {force_z}**2)
            
            _cli_result['success'] = True
            _cli_result['object_name'] = constraint.Name
            _cli_result['analysis_name'] = analysis.Name
            _cli_result['target_object'] = obj.Name
            _cli_result['force_x'] = {force_x}
            _cli_result['force_y'] = {force_y}
            _cli_result['force_z'] = {force_z}
            _cli_result['resultant_force'] = resultant
            _cli_result['face'] = {face_name!r}
            
        except Exception as e:
            _cli_result['error'] = f'Force constraint failed: {{str(e)}}'
            import traceback
            _cli_result['traceback'] = traceback.format_exc()
"""

    return run_script(script)


def run_solver(
    analysis_name: str,
    solver_type: str = "CalculiX",
    analysis_type: str = "static",
    name: str | None = None,
) -> dict[str, Any]:
    """Run FEM solver to calculate stresses and displacements.
    
    FEM::Solver runs the finite element calculation using
    external solvers like CalculiX.
    
    Args:
        analysis_name: Name of the FEM analysis.
        solver_type: Solver to use ("CalculiX", "Elmer", "Z88").
        analysis_type: Type of analysis ("static", "thermal", "modal").
        name: Name for solver object.
        
    Returns:
        Dict with solver results.
    """
    if name is None:
        name = f"Solver_{analysis_name}"
    
    script = f"""
import FreeCAD
import Fem

# Ensure we have an active document
if FreeCAD.ActiveDocument is None:
    _cli_result['error'] = 'No active document'
else:
    doc = FreeCAD.ActiveDocument
    
    # Find analysis
    analysis = doc.getObject({analysis_name!r})
    if analysis is None:
        _cli_result['error'] = 'Analysis {analysis_name} not found'
    else:
        try:
            # Create Solver object
            solver = doc.addObject('Fem::FemSolverObject', {name!r})
            
            # Set solver parameters
            solver.SolverType = {solver_type!r}
            solver.AnalysisType = {analysis_type!r}
            
            # Add solver to analysis
            analysis.addObject(solver)
            
            # Run solver
            solver.run()
            
            # Recompute
            doc.recompute()
            
            # Get results if available
            results_available = False
            max_displacement = 0
            max_stress = 0
            
            if hasattr(solver, 'Results'):
                results = solver.Results
                if results:
                    results_available = True
                    # Try to extract key results
                    for result in results:
                        if hasattr(result, 'MaxDisplacement'):
                            max_displacement = max(max_displacement, result.MaxDisplacement)
                        if hasattr(result, 'MaxVonMisesStress'):
                            max_stress = max(max_stress, result.MaxVonMisesStress)
            
            _cli_result['success'] = True
            _cli_result['object_name'] = solver.Name
            _cli_result['analysis_name'] = analysis.Name
            _cli_result['solver_type'] = {solver_type!r}
            _cli_result['analysis_type'] = {analysis_type!r}
            _cli_result['results_available'] = results_available
            _cli_result['max_displacement'] = max_displacement
            _cli_result['max_stress'] = max_stress
            
        except Exception as e:
            _cli_result['error'] = f'Solver failed: {{str(e)}}'
            import traceback
            _cli_result['traceback'] = traceback.format_exc()
"""

    return run_script(script)


def analysis_info(analysis_name: str) -> dict[str, Any]:
    """Get information about a FEM analysis.
    
    Args:
        analysis_name: Name of the analysis.
        
    Returns:
        Dict with analysis information.
    """
    script = f"""
import FreeCAD

# Ensure we have an active document
if FreeCAD.ActiveDocument is None:
    _cli_result['error'] = 'No active document'
else:
    doc = FreeCAD.ActiveDocument
    
    # Find analysis
    analysis = doc.getObject({analysis_name!r})
    if analysis is None:
        _cli_result['error'] = 'Analysis {analysis_name} not found'
    else:
        try:
            materials = []
            meshes = []
            constraints = []
            solvers = []
            
            if hasattr(analysis, 'Group'):
                for obj in analysis.Group:
                    if hasattr(obj, 'TypeId'):
                        obj_info = {{
                            'name': obj.Name,
                            'type': obj.TypeId,
                            'label': obj.Label,
                        }}
                        
                        if 'Material' in obj.TypeId:
                            if hasattr(obj, 'Material'):
                                obj_info['material_name'] = obj.Material.get('Name', 'Unknown')
                            materials.append(obj_info)
                        elif 'Mesh' in obj.TypeId:
                            if hasattr(obj, 'ElementCount'):
                                obj_info['element_count'] = obj.ElementCount
                            if hasattr(obj, 'NodeCount'):
                                obj_info['node_count'] = obj.NodeCount
                            meshes.append(obj_info)
                        elif 'Constraint' in obj.TypeId:
                            constraints.append(obj_info)
                        elif 'Solver' in obj.TypeId:
                            if hasattr(obj, 'SolverType'):
                                obj_info['solver_type'] = obj.SolverType
                            if hasattr(obj, 'AnalysisType'):
                                obj_info['analysis_type'] = obj.AnalysisType
                            solvers.append(obj_info)
            
            _cli_result['success'] = True
            _cli_result['analysis_name'] = analysis.Name
            _cli_result['materials'] = materials
            _cli_result['meshes'] = meshes
            _cli_result['constraints'] = constraints
            _cli_result['solvers'] = solvers
            _cli_result['material_count'] = len(materials)
            _cli_result['mesh_count'] = len(meshes)
            _cli_result['constraint_count'] = len(constraints)
            _cli_result['solver_count'] = len(solvers)
            
        except Exception as e:
            _cli_result['error'] = f'Analysis info failed: {{str(e)}}'
            import traceback
            _cli_result['traceback'] = traceback.format_exc()
"""

    return run_script(script)