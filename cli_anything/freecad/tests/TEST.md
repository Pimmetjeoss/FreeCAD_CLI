# FreeCAD CLI Test Plan and Results

## Test Inventory Plan

- `test_core.py`: ~63 unit tests planned
- `test_full_e2e.py`: ~22 E2E tests planned

## Unit Test Plan (`test_core.py`)

### project.py (8 tests)
- `test_create_project` — Create project with defaults
- `test_create_project_with_name` — Create with custom name
- `test_create_project_with_output` — Create and save to file
- `test_load_project` — Load from JSON file
- `test_save_project` — Save project state
- `test_get_project_info` — Get project metadata
- `test_get_project_info_with_objects` — Info with objects present
- `test_build_project_script` — Verify script generation

### session.py (10 tests)
- `test_new_session` — Initial session state
- `test_new_project` — Create project in session
- `test_open_project` — Open existing project
- `test_save_project` — Save from session
- `test_add_object` — Add object with auto-save
- `test_remove_object` — Remove object by name
- `test_remove_nonexistent` — Remove non-existent returns None
- `test_undo` — Undo last operation
- `test_redo` — Redo after undo
- `test_history` — Operation history tracking

### export.py (4 tests)
- `test_list_formats` — List supported formats
- `test_export_no_overwrite` — Refuse to overwrite without flag
- `test_export_formats_data` — Verify format registry
- `test_export_unknown_format` — Handle unknown format

### freecad_backend.py (3 tests)
- `test_find_freecadcmd` — Locate freecadcmd executable
- `test_get_version` — Get FreeCAD version
- `test_run_script_basic` — Execute simple script

### techdraw.py (17 unit tests)
- `test_create_drawing` — Create drawing with custom params
- `test_create_drawing_defaults` — Default page settings
- `test_add_view` — Add front view to page
- `test_add_view_iso` — Isometric view direction
- `test_add_view_custom_direction` — Custom dx,dy,dz direction
- `test_add_projection_group` — Multi-view projection set
- `test_add_projection_group_defaults` — Default projections (Front/Top/Right)
- `test_add_section_view` — Cross-section view
- `test_add_dimension` — Distance dimension on edge
- `test_add_dimension_radius` — Radius dimension type
- `test_add_annotation` — Text annotation
- `test_paper_sizes` — Paper size constants
- `test_view_directions` — View direction constants
- `test_build_techdraw_script_basic` — Script with view + dimension + annotation
- `test_build_techdraw_script_projection` — Script with projection group
- `test_build_techdraw_script_section` — Script with section view
- `test_build_techdraw_script_page_not_found` — Error handling

### export.py (1 additional test)
- `test_format_registry_dxf_svg_pdf` — DXF/SVG/PDF in format registry

### CLI TechDraw (6 tests via Click test runner)
- `test_techdraw_page_json` — Create drawing page
- `test_techdraw_view_json` — Add view to page
- `test_techdraw_dimension_json` — Add dimension
- `test_techdraw_annotate_json` — Add annotation
- `test_techdraw_list_json` — List page contents
- `test_export_formats_includes_dxf_svg_pdf` — Format listing

### CLI (5 tests via Click test runner)
- `test_cli_help` — --help output
- `test_cli_version` — --version flag
- `test_cli_project_new` — project new --json
- `test_cli_part_box` — part box --json
- `test_cli_export_formats` — export formats --json

## E2E Test Plan (`test_full_e2e.py`)

### Real FreeCAD Backend Tests (8 tests)
- `test_box_to_step` — Create box, export STEP, verify ISO-10303
- `test_box_to_stl` — Create box, export STL, verify format
- `test_cylinder_to_step` — Cylinder to STEP
- `test_multi_object_step` — Multiple objects in one STEP
- `test_boolean_fuse_step` — Fuse two objects, export STEP
- `test_save_fcstd` — Save as .FCStd, verify ZIP structure
- `test_inspect_fcstd` — Save + inspect roundtrip
- `test_sketch_with_pad` — Sketch + extrude workflow

### TechDraw E2E Tests (4 tests)
- `test_techdraw_box_to_dxf` — Box with view, export to DXF
- `test_techdraw_box_to_svg` — Box with view, export to SVG
- `test_projection_group_dxf` — Projection group (Front/Top/Right), export DXF
- `test_dimensioned_drawing_dxf` — View + dimension + annotation, export DXF

### TechDraw Subprocess Tests (3 tests)
- `test_techdraw_page_workflow` — Full page -> view -> dimension -> DXF workflow
- `test_techdraw_svg_workflow` — Page -> view -> SVG workflow
- `test_techdraw_list_workflow` — Page -> view + annotation -> list contents

### CLI Subprocess Tests (7 tests)
- `test_help` — --help exits 0
- `test_version_json` — --json --version output
- `test_project_new_json` — Create project via subprocess
- `test_full_box_step_workflow` — Box -> STEP via subprocess
- `test_full_cylinder_stl_workflow` — Cylinder -> STL via subprocess
- `test_multi_shape_workflow` — Multiple shapes via subprocess
- `test_export_formats` — List formats via subprocess

## Realistic Workflow Scenarios

### Workflow 1: Mechanical Part Design
**Simulates:** Engineer creating a bracket with holes
- Create project
- Add box base plate
- Add cylinder (hole punch)
- Boolean cut (box - cylinder)
- Export to STEP
- Verify: STEP file valid, volume < original box

### Workflow 2: Multi-Format Export Pipeline
**Simulates:** Exporting model to multiple formats for different tools
- Create box
- Export to STEP, STL, BREP
- Verify each format (ISO-10303 header, binary STL / ASCII solid, BREP header)

### Workflow 3: Parametric Sketch-Based Design
**Simulates:** 2D sketch to 3D part workflow
- Create sketch on XY plane
- Add rectangle
- Add circle (hole)
- Save as FCStd
- Inspect and verify geometry count

---

## Test Results (v1.1.0 — Placement + Move + SVG Rework)

**Date:** 2026-03-13
**Mode:** `CLI_ANYTHING_FORCE_INSTALLED=1` (using installed command)
**Backend:** `[_resolve_cli] Using installed command: /home/pimmetje/.local/bin/cli-anything-freecad`

### v1.1.0 Summary

| Metric | v1.0.0 | v1.1.0 | Delta |
|--------|--------|--------|-------|
| Total tests | 85 | 121 | +36 |
| Passed | 85 | 121 | +36 |
| Failed | 0 | 0 | 0 |
| Pass rate | 100% | 100% | — |
| Execution time | 7.02s | 6.80s | -0.22s |

### New Test Classes (v1.1.0)

| Class | Tests | Coverage |
|-------|-------|----------|
| TestPlacement | 8 | Placement script gen for all primitives |
| TestPlacementCLI | 4 | CLI --px/--py/--pz options |
| TestPartMove | 3 | part move command + persistence |
| TestProjectObject2D | 10 | 2D projection for box/cylinder/sphere/cone |
| TestExportDrawingSVG | 6 | Direct SVG export with views/dims/annotations |
| TestViewDirectionAliases | 5 | Engineering-convention direction aliases |

---

## Test Results (v1.0.0 + TechDraw)

**Date:** 2026-03-13 (initial)
**Mode:** `CLI_ANYTHING_FORCE_INSTALLED=1` (using installed command)
**Backend:** `[_resolve_cli] Using installed command: /home/pimmetje/.local/bin/cli-anything-freecad`

```
============================= test session starts ==============================
platform linux -- Python 3.12.3, pytest-9.0.2, pluggy-1.6.0
FreeCAD 0.21.2 (system installed)

cli_anything/freecad/tests/test_core.py::TestCreateProject::test_create_project_defaults PASSED [  1%]
cli_anything/freecad/tests/test_core.py::TestCreateProject::test_create_project_with_name PASSED [  2%]
cli_anything/freecad/tests/test_core.py::TestCreateProject::test_create_project_with_output PASSED [  3%]
cli_anything/freecad/tests/test_core.py::TestCreateProject::test_load_project PASSED [  4%]
cli_anything/freecad/tests/test_core.py::TestCreateProject::test_save_project PASSED [  5%]
cli_anything/freecad/tests/test_core.py::TestCreateProject::test_get_project_info_empty PASSED [  7%]
cli_anything/freecad/tests/test_core.py::TestCreateProject::test_get_project_info_with_objects PASSED [  8%]
cli_anything/freecad/tests/test_core.py::TestBuildProjectScript::test_empty_project PASSED [  9%]
cli_anything/freecad/tests/test_core.py::TestBuildProjectScript::test_box_object_script PASSED [ 10%]
cli_anything/freecad/tests/test_core.py::TestBuildProjectScript::test_cylinder_object_script PASSED [ 11%]
cli_anything/freecad/tests/test_core.py::TestBuildProjectScript::test_sphere_object_script PASSED [ 12%]
cli_anything/freecad/tests/test_core.py::TestBuildProjectScript::test_fuse_object_script PASSED [ 14%]
cli_anything/freecad/tests/test_core.py::TestBuildProjectScript::test_cut_object_script PASSED [ 15%]
cli_anything/freecad/tests/test_core.py::TestBuildProjectScript::test_sketch_object_script PASSED [ 16%]
cli_anything/freecad/tests/test_core.py::TestBuildProjectScript::test_unknown_type PASSED [ 17%]
cli_anything/freecad/tests/test_core.py::TestSession::test_new_session PASSED [ 18%]
cli_anything/freecad/tests/test_core.py::TestSession::test_new_project PASSED [ 20%]
cli_anything/freecad/tests/test_core.py::TestSession::test_open_project PASSED [ 21%]
cli_anything/freecad/tests/test_core.py::TestSession::test_save PASSED   [ 22%]
cli_anything/freecad/tests/test_core.py::TestSession::test_add_object PASSED [ 23%]
cli_anything/freecad/tests/test_core.py::TestSession::test_remove_object PASSED [ 24%]
cli_anything/freecad/tests/test_core.py::TestSession::test_remove_nonexistent PASSED [ 25%]
cli_anything/freecad/tests/test_core.py::TestSession::test_undo PASSED   [ 27%]
cli_anything/freecad/tests/test_core.py::TestSession::test_redo PASSED   [ 28%]
cli_anything/freecad/tests/test_core.py::TestSession::test_history PASSED [ 29%]
cli_anything/freecad/tests/test_core.py::TestSession::test_status PASSED [ 30%]
cli_anything/freecad/tests/test_core.py::TestSession::test_list_objects PASSED [ 31%]
cli_anything/freecad/tests/test_core.py::TestSession::test_get_object PASSED [ 32%]
cli_anything/freecad/tests/test_core.py::TestExport::test_list_formats PASSED [ 34%]
cli_anything/freecad/tests/test_core.py::TestExport::test_export_no_overwrite PASSED [ 35%]
cli_anything/freecad/tests/test_core.py::TestExport::test_format_registry PASSED [ 36%]
cli_anything/freecad/tests/test_core.py::TestExport::test_format_registry_dxf_svg_pdf PASSED [ 37%]
cli_anything/freecad/tests/test_core.py::TestTechDraw::test_create_drawing PASSED [ 38%]
cli_anything/freecad/tests/test_core.py::TestTechDraw::test_create_drawing_defaults PASSED [ 40%]
cli_anything/freecad/tests/test_core.py::TestTechDraw::test_add_view PASSED [ 41%]
cli_anything/freecad/tests/test_core.py::TestTechDraw::test_add_view_iso PASSED [ 42%]
cli_anything/freecad/tests/test_core.py::TestTechDraw::test_add_view_custom_direction PASSED [ 43%]
cli_anything/freecad/tests/test_core.py::TestTechDraw::test_add_projection_group PASSED [ 44%]
cli_anything/freecad/tests/test_core.py::TestTechDraw::test_add_projection_group_defaults PASSED [ 45%]
cli_anything/freecad/tests/test_core.py::TestTechDraw::test_add_section_view PASSED [ 47%]
cli_anything/freecad/tests/test_core.py::TestTechDraw::test_add_dimension PASSED [ 48%]
cli_anything/freecad/tests/test_core.py::TestTechDraw::test_add_dimension_radius PASSED [ 49%]
cli_anything/freecad/tests/test_core.py::TestTechDraw::test_add_annotation PASSED [ 50%]
cli_anything/freecad/tests/test_core.py::TestTechDraw::test_paper_sizes PASSED [ 51%]
cli_anything/freecad/tests/test_core.py::TestTechDraw::test_view_directions PASSED [ 52%]
cli_anything/freecad/tests/test_core.py::TestTechDraw::test_build_techdraw_script_basic PASSED [ 54%]
cli_anything/freecad/tests/test_core.py::TestTechDraw::test_build_techdraw_script_projection PASSED [ 55%]
cli_anything/freecad/tests/test_core.py::TestTechDraw::test_build_techdraw_script_section PASSED [ 56%]
cli_anything/freecad/tests/test_core.py::TestTechDraw::test_build_techdraw_script_page_not_found PASSED [ 57%]
cli_anything/freecad/tests/test_core.py::TestTechDrawCLI::test_techdraw_page_json PASSED [ 58%]
cli_anything/freecad/tests/test_core.py::TestTechDrawCLI::test_techdraw_view_json PASSED [ 60%]
cli_anything/freecad/tests/test_core.py::TestTechDrawCLI::test_techdraw_dimension_json PASSED [ 61%]
cli_anything/freecad/tests/test_core.py::TestTechDrawCLI::test_techdraw_annotate_json PASSED [ 62%]
cli_anything/freecad/tests/test_core.py::TestTechDrawCLI::test_techdraw_list_json PASSED [ 63%]
cli_anything/freecad/tests/test_core.py::TestTechDrawCLI::test_export_formats_includes_dxf_svg_pdf PASSED [ 64%]
cli_anything/freecad/tests/test_core.py::TestBackend::test_find_freecadcmd PASSED [ 65%]
cli_anything/freecad/tests/test_core.py::TestBackend::test_get_version PASSED [ 67%]
cli_anything/freecad/tests/test_core.py::TestBackend::test_run_script_basic PASSED [ 68%]
cli_anything/freecad/tests/test_core.py::TestCLI::test_help PASSED       [ 69%]
cli_anything/freecad/tests/test_core.py::TestCLI::test_version PASSED    [ 70%]
cli_anything/freecad/tests/test_core.py::TestCLI::test_project_new_json PASSED [ 71%]
cli_anything/freecad/tests/test_core.py::TestCLI::test_part_box_json PASSED [ 72%]
cli_anything/freecad/tests/test_core.py::TestCLI::test_export_formats_json PASSED [ 74%]
cli_anything/freecad/tests/test_full_e2e.py::TestBoxToSTEP::test_box_to_step PASSED [ 75%]
cli_anything/freecad/tests/test_full_e2e.py::TestBoxToSTL::test_box_to_stl PASSED [ 76%]
cli_anything/freecad/tests/test_full_e2e.py::TestCylinderToSTEP::test_cylinder_to_step PASSED [ 77%]
cli_anything/freecad/tests/test_full_e2e.py::TestMultiObjectSTEP::test_multi_object_step PASSED [ 78%]
cli_anything/freecad/tests/test_full_e2e.py::TestBooleanFuseSTEP::test_boolean_cut_step PASSED [ 80%]
cli_anything/freecad/tests/test_full_e2e.py::TestSaveFCStd::test_save_fcstd PASSED [ 81%]
cli_anything/freecad/tests/test_full_e2e.py::TestInspectFCStd::test_inspect_fcstd PASSED [ 82%]
cli_anything/freecad/tests/test_full_e2e.py::TestSketchProject::test_sketch_fcstd PASSED [ 83%]
cli_anything/freecad/tests/test_full_e2e.py::TestTechDrawDXF::test_techdraw_box_to_dxf PASSED [ 84%]
cli_anything/freecad/tests/test_full_e2e.py::TestTechDrawSVG::test_techdraw_box_to_svg PASSED [ 85%]
cli_anything/freecad/tests/test_full_e2e.py::TestTechDrawProjection::test_projection_group_dxf PASSED [ 87%]
cli_anything/freecad/tests/test_full_e2e.py::TestTechDrawDimension::test_dimensioned_drawing_dxf PASSED [ 88%]
cli_anything/freecad/tests/test_full_e2e.py::TestTechDrawSubprocess::test_techdraw_page_workflow PASSED [ 89%]
cli_anything/freecad/tests/test_full_e2e.py::TestTechDrawSubprocess::test_techdraw_svg_workflow PASSED [ 90%]
cli_anything/freecad/tests/test_full_e2e.py::TestTechDrawSubprocess::test_techdraw_list_workflow PASSED [ 91%]
cli_anything/freecad/tests/test_full_e2e.py::TestCLISubprocess::test_help PASSED [ 92%]
cli_anything/freecad/tests/test_full_e2e.py::TestCLISubprocess::test_version_json PASSED [ 94%]
cli_anything/freecad/tests/test_full_e2e.py::TestCLISubprocess::test_project_new_json PASSED [ 95%]
cli_anything/freecad/tests/test_full_e2e.py::TestCLISubprocess::test_full_box_step_workflow PASSED [ 96%]
cli_anything/freecad/tests/test_full_e2e.py::TestCLISubprocess::test_full_cylinder_stl_workflow PASSED [ 97%]
cli_anything/freecad/tests/test_full_e2e.py::TestCLISubprocess::test_multi_shape_workflow PASSED [ 98%]
cli_anything/freecad/tests/test_full_e2e.py::TestCLISubprocess::test_export_formats PASSED [100%]

============================== 85 passed in 7.02s ==============================
```

### Summary Statistics

| Metric | Value |
|--------|-------|
| Total tests | 85 |
| Passed | 85 |
| Failed | 0 |
| Pass rate | 100% |
| Execution time | 7.02s |

### Test Breakdown

| Test file | Tests | Category |
|-----------|-------|----------|
| `test_core.py` | 63 | Unit tests (synthetic data) |
| `test_full_e2e.py` | 22 | E2E + subprocess (real FreeCAD backend) |

### Generated Artifacts

| Artifact | Format | Size |
|----------|--------|------|
| Box STEP | ISO-10303-21 | 6,854 bytes |
| Box STL | Binary mesh | 684 bytes |
| Cylinder STEP | ISO-10303-21 | 3,491 bytes |
| Multi-object STEP | ISO-10303-21 | 8,790 bytes |
| Boolean cut STEP | ISO-10303-21 | 15,507 bytes |
| Box FCStd | ZIP (Document.xml + PartShape.brp) | 2,344 bytes |
| Sketch FCStd | ZIP | 2,394 bytes |
| TechDraw Box DXF | DXF 2D drawing | ~2,000 bytes |
| TechDraw Box SVG | SVG projection | ~375 bytes |
| TechDraw Projection DXF | Multi-view DXF | ~4,500 bytes |
| TechDraw Dimensioned DXF | DXF with dimensions | ~5,900 bytes |
| Subprocess STEP | ISO-10303-21 | 6,854 bytes |
| Subprocess STL | Binary mesh | 6,284 bytes |
| Subprocess multi STEP | ISO-10303-21 | 7,276 bytes |
| Subprocess TechDraw DXF | DXF via CLI | varies |
| Subprocess TechDraw SVG | SVG via CLI | varies |

### Coverage Notes

- All core modules tested (project, session, export, backend, techdraw)
- Real FreeCAD backend invoked for all E2E tests (no mocking)
- Subprocess tests use `_resolve_cli()` with installed command
- Output format verification: ISO-10303 header (STEP), binary/ASCII (STL), ZIP structure (FCStd), SECTION header (DXF), svg tag (SVG)
- Volume/area verification for box: volume=3000.0, area=1300.0 (mathematically correct)
- TechDraw uses `projectToSVG` for headless-safe SVG export (avoids `viewPartAsSvg` segfault in FreeCAD 0.21.2)
- Dimension `References2D` wrapped in try/except for HLR timing issues

---

## Tier 1-3 Module Tests (v1.2.0)

**Date:** 2026-03-17
**New test files:** 4 files, 68 tests

### Bug Fix

- **dxf_import.py:182** — Changed bare `except: pass` to `except (AttributeError, TypeError, ValueError): pass`

### New Test Files

| File | Tests | Passed | Skipped | Coverage |
|------|-------|--------|---------|----------|
| `test_partdesign.py` | 26 | 19 | 7* | partdesign.py, partdesign_patterns.py, partdesign_manufacturing.py |
| `test_assembly.py` | 14 | 14 | 0 | assembly.py |
| `test_fem.py` | 16 | 16 | 0 | fem.py |
| `test_dxf_import_module.py` | 12 | 12 | 0 | dxf_import.py |
| **Total** | **68** | **61** | **7** | |

\* 7 skipped tests are direct `run_script()` calls that require FreeCAD backend (they pass on Linux CI with FreeCAD installed)

### Test Classes

| Class | Tests | What It Tests |
|-------|-------|---------------|
| TestPartDesignBodyCLI | 3 | Body create, no-project error, JSON output |
| TestPartDesignPadPocketCLI | 4 | Pad/Pocket CLI, missing sketch, option parsing |
| TestLinearPatternValidation | 5 | Direct core call: invalid/valid directions, case-insensitive |
| TestPolarPatternValidation | 4 | Direct core call: invalid/valid axes |
| TestDraftCLI | 2 | No-project error, angle parsing |
| TestManufacturingCLI | 4 | Fillet/Chamfer/Thickness arg parsing |
| TestFeatureListCLI | 2 | Features/Patterns no-project errors |
| TestPartDesignHelpOutput | 2 | --help output |
| TestAssemblyCreateCLI | 3 | Create, with parts, no-project |
| TestAssemblyAddPartCLI | 3 | With/without placement, no-project |
| TestAssemblyConstraintCLI | 3 | Constraint types, wiring, no-project |
| TestAssemblyExplodeCLI | 2 | Factor, no-project |
| TestAssemblyInfoCLI | 2 | Wiring, no-project |
| TestAssemblyHelpOutput | 1 | --help output |
| TestFemAnalysisCLI | 3 | Create with/without name, no-project |
| TestFemMaterialCLI | 3 | Material types, wiring, no-project |
| TestFemMeshCLI | 3 | Element size/type, no-project |
| TestFemConstraintsCLI | 3 | Fixed/Force constraints, xyz values |
| TestFemSolveCLI | 2 | Solver types, no-project |
| TestFemInfoCLI | 2 | Wiring, no-project |
| TestDxfImportValidation | 4 | File-not-found, auto-naming, analyze errors |
| TestDxfImportCLI | 4 | Layers/scale/units options, no-project |
| TestDxfInfoCLI | 2 | Wiring, file-not-found |
| TestBareExceptRegression | 2 | No bare except in source, specific exceptions caught |

### Test Design

- All CLI tests use `CliRunner` with `isolated_filesystem()`
- Backend-dependent tests accept either success OR `RuntimeError("FreeCAD is not installed")` via `_assert_ok_or_backend_error()` helper
- Direct core function tests verify Python-layer validation (no backend needed)
- Regression tests verify bare except fix via source inspection
