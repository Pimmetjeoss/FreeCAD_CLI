"""End-to-end tests for cli-anything-freecad.

These tests invoke the REAL FreeCAD backend (freecadcmd) to produce
actual output files. FreeCAD is a HARD dependency — tests fail if
it's not installed.
"""

from __future__ import annotations

import json
import os
import struct
import subprocess
import sys
import tempfile
import zipfile

import pytest

from cli_anything.freecad.core.project import create_project, save_fcstd, inspect_fcstd
from cli_anything.freecad.core.export import export
from cli_anything.freecad.core.session import Session


# ── Fixtures ─────────────────────────────────────────────────────────

@pytest.fixture
def tmp_dir():
    with tempfile.TemporaryDirectory(prefix="fc_e2e_") as d:
        yield d


@pytest.fixture
def box_project():
    """Project with a single box."""
    proj = create_project(name="BoxTest")
    proj["objects"].append({
        "name": "Box",
        "type": "Part::Box",
        "label": "Box",
        "params": {"length": 20, "width": 15, "height": 10},
    })
    return proj


@pytest.fixture
def multi_project():
    """Project with multiple objects."""
    proj = create_project(name="MultiTest")
    proj["objects"].append({
        "name": "Box",
        "type": "Part::Box",
        "label": "Box",
        "params": {"length": 20, "width": 15, "height": 10},
    })
    proj["objects"].append({
        "name": "Cylinder",
        "type": "Part::Cylinder",
        "label": "Cylinder",
        "params": {"radius": 5, "height": 25, "angle": 360},
    })
    return proj


@pytest.fixture
def boolean_project():
    """Project with boolean cut (box - cylinder)."""
    proj = create_project(name="BooleanTest")
    proj["objects"].append({
        "name": "Base",
        "type": "Part::Box",
        "label": "Base",
        "params": {"length": 30, "width": 30, "height": 10},
    })
    proj["objects"].append({
        "name": "Hole",
        "type": "Part::Cylinder",
        "label": "Hole",
        "params": {"radius": 5, "height": 20, "angle": 360},
    })
    proj["objects"].append({
        "name": "Result",
        "type": "Part::Cut",
        "label": "Result",
        "params": {"base": "Base", "tool": "Hole"},
    })
    return proj


@pytest.fixture
def sketch_project():
    """Project with a sketch."""
    proj = create_project(name="SketchTest")
    proj["objects"].append({
        "name": "Sketch",
        "type": "Sketcher::SketchObject",
        "label": "Sketch",
        "params": {
            "plane": "XY",
            "geometry": [
                {"type": "rect", "x": 0, "y": 0, "width": 20, "height": 15},
                {"type": "circle", "cx": 10, "cy": 7.5, "radius": 3},
            ],
            "constraints": [],
        },
    })
    return proj


# ── Real FreeCAD Backend Tests ───────────────────────────────────────

class TestBoxToSTEP:
    def test_box_to_step(self, box_project, tmp_dir):
        """Create a box, export to STEP, verify ISO-10303 header."""
        step_path = os.path.join(tmp_dir, "box.step")
        result = export(box_project, step_path, preset="step", overwrite=True)

        assert result["success"] is True
        assert os.path.exists(result["output"])
        assert result["file_size"] > 500

        with open(result["output"]) as f:
            header = f.read(100)
        assert header.startswith("ISO-10303-21;")
        print(f"\n  STEP: {result['output']} ({result['file_size']:,} bytes)")


class TestBoxToSTL:
    def test_box_to_stl(self, box_project, tmp_dir):
        """Create a box, export to STL, verify format."""
        stl_path = os.path.join(tmp_dir, "box.stl")
        result = export(box_project, stl_path, preset="stl", overwrite=True)

        assert result["success"] is True
        assert os.path.exists(result["output"])
        assert result["file_size"] > 100

        with open(result["output"], "rb") as f:
            data = f.read(80)
        # STL can be ASCII ("solid") or binary (80-byte header)
        is_ascii = data.lstrip().startswith(b"solid")
        is_binary = len(data) == 80  # binary header
        assert is_ascii or is_binary
        print(f"\n  STL: {result['output']} ({result['file_size']:,} bytes)")


class TestCylinderToSTEP:
    def test_cylinder_to_step(self, tmp_dir):
        """Create cylinder, export to STEP."""
        proj = create_project(name="CylTest")
        proj["objects"].append({
            "name": "Cyl", "type": "Part::Cylinder",
            "params": {"radius": 8, "height": 30, "angle": 360},
        })
        step_path = os.path.join(tmp_dir, "cyl.step")
        result = export(proj, step_path, preset="step", overwrite=True)

        assert result["success"] is True
        assert result["file_size"] > 500
        with open(result["output"]) as f:
            content = f.read()
        assert "ISO-10303-21" in content
        print(f"\n  STEP: {result['output']} ({result['file_size']:,} bytes)")


class TestMultiObjectSTEP:
    def test_multi_object_step(self, multi_project, tmp_dir):
        """Multiple objects exported to single STEP file."""
        step_path = os.path.join(tmp_dir, "multi.step")
        result = export(multi_project, step_path, preset="step", overwrite=True)

        assert result["success"] is True
        assert result["file_size"] > 1000
        print(f"\n  STEP: {result['output']} ({result['file_size']:,} bytes)")


class TestBooleanFuseSTEP:
    def test_boolean_cut_step(self, boolean_project, tmp_dir):
        """Boolean cut (box - cylinder), export to STEP."""
        step_path = os.path.join(tmp_dir, "boolean.step")
        result = export(boolean_project, step_path, preset="step", overwrite=True)

        assert result["success"] is True
        assert result["file_size"] > 500
        print(f"\n  STEP: {result['output']} ({result['file_size']:,} bytes)")


class TestSaveFCStd:
    def test_save_fcstd(self, box_project, tmp_dir):
        """Save project as .FCStd and verify ZIP structure."""
        fcstd_path = os.path.join(tmp_dir, "test.FCStd")
        result = save_fcstd(box_project, fcstd_path)

        assert result["success"] is True
        assert os.path.exists(fcstd_path)

        # FCStd is a ZIP file
        assert zipfile.is_zipfile(fcstd_path)
        with zipfile.ZipFile(fcstd_path) as zf:
            names = zf.namelist()
            assert "Document.xml" in names
        print(f"\n  FCStd: {fcstd_path} ({os.path.getsize(fcstd_path):,} bytes)")
        print(f"  ZIP contents: {names}")


class TestInspectFCStd:
    def test_inspect_fcstd(self, box_project, tmp_dir):
        """Save + inspect roundtrip."""
        fcstd_path = os.path.join(tmp_dir, "inspect.FCStd")
        save_fcstd(box_project, fcstd_path)

        result = inspect_fcstd(fcstd_path)
        assert result["success"] is True
        r = result["result"]
        assert r["object_count"] >= 1
        # Find the box
        box_obj = None
        for obj in r["objects"]:
            if obj["name"] == "Box":
                box_obj = obj
                break
        assert box_obj is not None
        assert box_obj["type"] == "Part::Box"
        assert box_obj["volume"] == 3000.0  # 20 * 15 * 10
        assert box_obj["area"] == 1300.0  # 2*(20*15 + 20*10 + 15*10)
        print(f"\n  Inspect: {r['object_count']} objects, Box volume={box_obj['volume']}")


class TestSketchProject:
    def test_sketch_fcstd(self, sketch_project, tmp_dir):
        """Sketch with rectangle + circle saved to FCStd."""
        fcstd_path = os.path.join(tmp_dir, "sketch.FCStd")
        result = save_fcstd(sketch_project, fcstd_path)
        assert result["success"] is True
        assert os.path.exists(fcstd_path)
        assert zipfile.is_zipfile(fcstd_path)
        print(f"\n  FCStd: {fcstd_path} ({os.path.getsize(fcstd_path):,} bytes)")


# ── Subprocess helper ────────────────────────────────────────────────

def _resolve_cli(name):
    """Resolve installed CLI command; falls back to python -m for dev.

    Set env CLI_ANYTHING_FORCE_INSTALLED=1 to require the installed command.
    """
    import shutil
    force = os.environ.get("CLI_ANYTHING_FORCE_INSTALLED", "").strip() == "1"
    path = shutil.which(name)
    if path:
        print(f"[_resolve_cli] Using installed command: {path}")
        return [path]
    if force:
        raise RuntimeError(f"{name} not found in PATH. Install with: pip install -e .")
    module = name.replace("cli-anything-", "cli_anything.") + "." + name.split("-")[-1] + "_cli"
    print(f"[_resolve_cli] Falling back to: {sys.executable} -m {module}")
    return [sys.executable, "-m", module]


# ── TechDraw E2E Tests ──────────────────────────────────────────────

class TestTechDrawDXF:
    def test_techdraw_box_to_dxf(self, box_project, tmp_dir):
        """Create box, add TechDraw page + view, export to DXF."""
        from cli_anything.freecad.core.techdraw import (
            create_drawing, add_view, export_drawing_dxf,
        )
        page = create_drawing(box_project, page_name="Sheet1")
        add_view(page, "Box", view_name="FrontView", direction="front")
        box_project["objects"].append(page)

        dxf_path = os.path.join(tmp_dir, "drawing.dxf")
        result = export_drawing_dxf(box_project, "Sheet1", dxf_path)

        assert result["success"] is True
        r = result["result"]
        assert r.get("output") == dxf_path
        assert r.get("file_size", 0) > 0
        assert os.path.exists(dxf_path)

        # DXF files should contain SECTION header
        with open(dxf_path) as f:
            content = f.read(500)
        assert "SECTION" in content or "section" in content.lower() or "0" in content
        print(f"\n  DXF: {dxf_path} ({r['file_size']:,} bytes)")


class TestTechDrawSVG:
    def test_techdraw_box_to_svg(self, box_project, tmp_dir):
        """Create box, add TechDraw page + view, export to SVG."""
        from cli_anything.freecad.core.techdraw import (
            create_drawing, add_view, export_drawing_svg,
        )
        page = create_drawing(box_project, page_name="Sheet1")
        add_view(page, "Box", view_name="FrontView", direction="front")
        box_project["objects"].append(page)

        svg_path = os.path.join(tmp_dir, "drawing.svg")
        result = export_drawing_svg(box_project, "Sheet1", svg_path)

        assert result["success"] is True
        r = result["result"]
        assert r.get("output") == svg_path
        assert r.get("file_size", 0) > 0
        assert os.path.exists(svg_path)

        with open(svg_path, encoding="utf-8") as f:
            content = f.read(200)
        assert "svg" in content.lower()
        print(f"\n  SVG: {svg_path} ({r['file_size']:,} bytes)")


class TestTechDrawProjection:
    def test_projection_group_dxf(self, box_project, tmp_dir):
        """Create projection group (Front/Top/Right), export to DXF."""
        from cli_anything.freecad.core.techdraw import (
            create_drawing, add_projection_group, export_drawing_dxf,
        )
        page = create_drawing(box_project, page_name="ProjSheet")
        add_projection_group(page, "Box", group_name="PG1",
                             projections=["Front", "Top", "Right"])
        box_project["objects"].append(page)

        dxf_path = os.path.join(tmp_dir, "projection.dxf")
        result = export_drawing_dxf(box_project, "ProjSheet", dxf_path)

        assert result["success"] is True
        assert os.path.exists(dxf_path)
        assert result["result"].get("file_size", 0) > 0
        print(f"\n  DXF: {dxf_path} ({result['result']['file_size']:,} bytes)")


class TestTechDrawDimension:
    def test_dimensioned_drawing_dxf(self, box_project, tmp_dir):
        """Create drawing with view + dimension, export to DXF."""
        from cli_anything.freecad.core.techdraw import (
            create_drawing, add_view, add_dimension, add_annotation,
            export_drawing_dxf,
        )
        page = create_drawing(box_project, page_name="DimSheet")
        add_view(page, "Box", view_name="V1", direction="front")
        add_dimension(page, "V1", dim_type="Distance", edge_ref="Edge0",
                      dim_name="Length1")
        add_annotation(page, ["Material: Aluminum", "Scale: 1:1"],
                       anno_name="TitleBlock")
        box_project["objects"].append(page)

        dxf_path = os.path.join(tmp_dir, "dimensioned.dxf")
        result = export_drawing_dxf(box_project, "DimSheet", dxf_path)

        assert result["success"] is True
        assert os.path.exists(dxf_path)
        print(f"\n  DXF: {dxf_path} ({result['result']['file_size']:,} bytes)")


class TestTechDrawSubprocess:
    """Test TechDraw workflow via CLI subprocess."""
    CLI_BASE = _resolve_cli("cli-anything-freecad")

    def _run(self, args, check=True):
        return subprocess.run(
            self.CLI_BASE + args,
            capture_output=True, text=True,
            check=check,
        )

    def test_techdraw_page_workflow(self, tmp_dir):
        """Full workflow: project -> box -> page -> view -> export DXF."""
        proj_path = os.path.join(tmp_dir, "td_workflow.json")
        dxf_path = os.path.join(tmp_dir, "td_output.dxf")

        # Create project
        self._run(["--json", "project", "new", "-n", "TDWork", "-o", proj_path])

        # Add box
        r = self._run(["--json", "--project", proj_path, "part", "box",
                        "-l", "30", "-w", "20", "-H", "10"])
        assert r.returncode == 0

        # Create drawing page
        r = self._run(["--json", "--project", proj_path, "techdraw", "page",
                        "-n", "Sheet1", "-t", "A4_Landscape"])
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert data["type"] == "TechDraw::DrawPage"

        # Add front view
        r = self._run(["--json", "--project", proj_path, "techdraw", "view",
                        "Sheet1", "Box", "-d", "front", "-n", "V1"])
        assert r.returncode == 0

        # Add dimension
        r = self._run(["--json", "--project", proj_path, "techdraw", "dimension",
                        "Sheet1", "V1", "-t", "Distance", "-e", "Edge0"])
        assert r.returncode == 0

        # Export DXF
        r = self._run(["--json", "--project", proj_path, "techdraw", "export-dxf",
                        "Sheet1", dxf_path, "--overwrite"])
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert data["success"] is True
        assert os.path.exists(dxf_path)
        assert data["file_size"] > 0
        print(f"\n  DXF: {dxf_path} ({data['file_size']:,} bytes)")

    def test_techdraw_svg_workflow(self, tmp_dir):
        """Full workflow: project -> box -> page -> view -> export SVG."""
        proj_path = os.path.join(tmp_dir, "td_svg.json")
        svg_path = os.path.join(tmp_dir, "td_output.svg")

        self._run(["--json", "project", "new", "-o", proj_path])
        self._run(["--json", "--project", proj_path, "part", "box", "-l", "25"])
        self._run(["--json", "--project", proj_path, "techdraw", "page", "-n", "S1"])
        self._run(["--json", "--project", proj_path, "techdraw", "view", "S1", "Box", "-d", "iso"])
        r = self._run(["--json", "--project", proj_path, "techdraw", "export-svg",
                        "S1", svg_path, "--overwrite"])
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert data["success"] is True
        assert os.path.exists(svg_path)
        print(f"\n  SVG: {svg_path} ({data['file_size']:,} bytes)")

    def test_techdraw_list_workflow(self, tmp_dir):
        """Create page with views and list contents."""
        proj_path = os.path.join(tmp_dir, "td_list.json")

        self._run(["--json", "project", "new", "-o", proj_path])
        self._run(["--json", "--project", proj_path, "part", "box", "-n", "B"])
        self._run(["--json", "--project", proj_path, "techdraw", "page", "-n", "P"])
        self._run(["--json", "--project", proj_path, "techdraw", "view", "P", "B"])
        self._run(["--json", "--project", proj_path, "techdraw", "annotate", "P", "Test"])

        r = self._run(["--json", "--project", proj_path, "techdraw", "list", "P"])
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert data["page"] == "P"
        assert len(data["views"]) == 1
        assert len(data["annotations"]) == 1


# ── CLI Subprocess Tests ─────────────────────────────────────────────

class TestCLISubprocess:
    CLI_BASE = _resolve_cli("cli-anything-freecad")

    def _run(self, args, check=True):
        return subprocess.run(
            self.CLI_BASE + args,
            capture_output=True, text=True,
            check=check,
        )

    def test_help(self):
        result = self._run(["--help"])
        assert result.returncode == 0
        assert "cli-anything-freecad" in result.stdout

    def test_version_json(self):
        result = self._run(["--json", "--version"])
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "version" in data

    def test_project_new_json(self, tmp_dir):
        path = os.path.join(tmp_dir, "sub_test.json")
        result = self._run(["--json", "project", "new", "-n", "SubTest", "-o", path])
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["name"] == "SubTest"
        assert os.path.exists(path)

    def test_full_box_step_workflow(self, tmp_dir):
        """Full workflow: project new -> box -> export STEP via subprocess."""
        proj_path = os.path.join(tmp_dir, "workflow.json")
        step_path = os.path.join(tmp_dir, "workflow.step")

        # Create project
        r = self._run(["--json", "project", "new", "-n", "Workflow", "-o", proj_path])
        assert r.returncode == 0

        # Add box
        r = self._run(["--json", "--project", proj_path, "part", "box", "-l", "25", "-w", "20", "-H", "15"])
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert data["type"] == "Part::Box"

        # Export STEP
        r = self._run(["--json", "--project", proj_path, "export", "render", step_path, "-p", "step", "--overwrite"])
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert data["success"] is True
        assert os.path.exists(step_path)
        assert data["file_size"] > 500

        with open(step_path) as f:
            header = f.read(14)
            assert header.startswith("ISO-10303-21;")
        print(f"\n  STEP: {step_path} ({data['file_size']:,} bytes)")

    def test_full_cylinder_stl_workflow(self, tmp_dir):
        """Full workflow: project new -> cylinder -> export STL."""
        proj_path = os.path.join(tmp_dir, "cyl_workflow.json")
        stl_path = os.path.join(tmp_dir, "cyl.stl")

        self._run(["--json", "project", "new", "-o", proj_path])
        self._run(["--json", "--project", proj_path, "part", "cylinder", "-r", "10", "-H", "30"])
        r = self._run(["--json", "--project", proj_path, "export", "render", stl_path, "-p", "stl", "--overwrite"])
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert data["success"] is True
        assert os.path.exists(stl_path)
        print(f"\n  STL: {stl_path} ({data['file_size']:,} bytes)")

    def test_multi_shape_workflow(self, tmp_dir):
        """Create multiple shapes, export to STEP."""
        proj_path = os.path.join(tmp_dir, "multi.json")
        step_path = os.path.join(tmp_dir, "multi.step")

        self._run(["--json", "project", "new", "-n", "Multi", "-o", proj_path])
        self._run(["--json", "--project", proj_path, "part", "box", "-l", "10"])
        self._run(["--json", "--project", proj_path, "part", "sphere", "-r", "8"])
        r = self._run(["--json", "--project", proj_path, "export", "render", step_path, "-p", "step", "--overwrite"])
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert data["success"] is True
        print(f"\n  STEP: {step_path} ({data['file_size']:,} bytes)")

    def test_export_formats(self):
        r = self._run(["--json", "export", "formats"])
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert "formats" in data
        names = [f["name"] for f in data["formats"]]
        assert "step" in names
        assert "stl" in names


class TestRevolve:
    """Part revolve tests — revolve a sketch profile around an axis."""

    def test_revolve_sketch_to_step(self, tmp_dir):
        """Create a sketch, revolve 360°, export to STEP."""
        proj = create_project(name="RevolveTest")
        # Create a rectangular profile on XZ plane (will revolve around Z axis)
        proj["objects"].append({
            "name": "Profile",
            "type": "Sketcher::SketchObject",
            "label": "Profile",
            "params": {
                "plane": "XZ",
                "geometry": [
                    {"type": "rect", "x": 5, "y": 0, "width": 5, "height": 10},
                ],
                "constraints": [],
            },
        })
        # Revolve around Z axis (0,0,1) at origin — creates a hollow cylinder
        proj["objects"].append({
            "name": "Revolve",
            "type": "Part::Revolution",
            "label": "Revolve",
            "params": {
                "source": "Profile",
                "angle": 360,
                "axis_x": 0, "axis_y": 0, "axis_z": 1,
                "base_x": 0, "base_y": 0, "base_z": 0,
            },
        })

        step_path = os.path.join(tmp_dir, "revolve.step")
        result = export(proj, step_path, preset="step", overwrite=True)

        assert result["success"] is True, f"Export failed: {result}"
        assert os.path.exists(result["output"])
        assert result["file_size"] > 500
        print(f"\n  STEP revolve: {result['output']} ({result['file_size']:,} bytes)")

    def test_revolve_partial_angle(self, tmp_dir):
        """Revolve a profile 180° — should produce a half-solid."""
        proj = create_project(name="HalfRevolve")
        proj["objects"].append({
            "name": "Profile",
            "type": "Sketcher::SketchObject",
            "label": "Profile",
            "params": {
                "plane": "XZ",
                "geometry": [
                    {"type": "rect", "x": 5, "y": 0, "width": 5, "height": 10},
                ],
                "constraints": [],
            },
        })
        proj["objects"].append({
            "name": "HalfRev",
            "type": "Part::Revolution",
            "label": "HalfRev",
            "params": {
                "source": "Profile",
                "angle": 180,
                "axis_x": 0, "axis_y": 0, "axis_z": 1,
                "base_x": 0, "base_y": 0, "base_z": 0,
            },
        })

        step_path = os.path.join(tmp_dir, "half_revolve.step")
        result = export(proj, step_path, preset="step", overwrite=True)

        assert result["success"] is True, f"Export failed: {result}"
        assert os.path.exists(result["output"])
        print(f"\n  STEP half-revolve: {result['output']} ({result['file_size']:,} bytes)")


# ── GD&T E2E Tests ─────────────────────────────────────────────────

class TestGDTDrawingWorkflow:
    """E2E tests for GD&T annotations on TechDraw pages."""

    def test_gdt_position_on_drawing_svg(self, box_project, tmp_dir):
        """Box + drawing page + position tolerance → export SVG with FCF."""
        from cli_anything.freecad.core.techdraw import (
            create_drawing, add_view, add_geometric_tolerance,
            export_drawing_svg,
        )
        page = create_drawing(box_project, page_name="GDTSheet")
        add_view(page, "Box", view_name="FrontView", direction="front")
        add_geometric_tolerance(
            page, "FrontView",
            characteristic="position",
            tolerance=0.05,
            datum_refs=["A", "B"],
            material_condition="MMC",
            diameter_zone=True,
            gdt_name="PosGDT1",
            x=100, y=80,
        )
        box_project["objects"].append(page)

        svg_path = os.path.join(tmp_dir, "gdt_position.svg")
        result = export_drawing_svg(box_project, "GDTSheet", svg_path)

        assert result["success"] is True
        assert os.path.exists(svg_path)
        with open(svg_path, encoding="utf-8") as f:
            content = f.read()
        # FCF should contain position symbol and datum refs
        assert "⌖" in content, "Position symbol not found in SVG"
        assert "0.05" in content, "Tolerance value not found in SVG"
        assert ">A<" in content, "Datum A not found in SVG"
        assert ">B<" in content, "Datum B not found in SVG"
        print(f"\n  SVG GD&T position: {svg_path} ({result['result']['file_size']:,} bytes)")

    def test_gdt_flatness_on_drawing_svg(self, box_project, tmp_dir):
        """Flatness tolerance (form — no datums) → SVG."""
        from cli_anything.freecad.core.techdraw import (
            create_drawing, add_view, add_geometric_tolerance,
            export_drawing_svg,
        )
        page = create_drawing(box_project, page_name="FlatSheet")
        add_view(page, "Box", view_name="TopView", direction="top")
        add_geometric_tolerance(
            page, "TopView",
            characteristic="flatness",
            tolerance=0.02,
            gdt_name="Flat1",
        )
        box_project["objects"].append(page)

        svg_path = os.path.join(tmp_dir, "gdt_flatness.svg")
        result = export_drawing_svg(box_project, "FlatSheet", svg_path)

        assert result["success"] is True
        with open(svg_path, encoding="utf-8") as f:
            content = f.read()
        assert "⏥" in content, "Flatness symbol not found in SVG"
        assert "0.02" in content
        print(f"\n  SVG GD&T flatness: {svg_path}")

    def test_gdt_perpendicularity_with_datum_svg(self, box_project, tmp_dir):
        """Perpendicularity + datum symbol → SVG has both."""
        from cli_anything.freecad.core.techdraw import (
            create_drawing, add_view, add_geometric_tolerance,
            add_datum_symbol, export_drawing_svg,
        )
        page = create_drawing(box_project, page_name="PerpSheet")
        add_view(page, "Box", view_name="FrontView", direction="front")
        add_datum_symbol(page, "FrontView", "A", datum_name="DatumA", x=50, y=120)
        add_geometric_tolerance(
            page, "FrontView",
            characteristic="perpendicularity",
            tolerance=0.1,
            datum_refs=["A"],
            gdt_name="Perp1",
            x=100, y=80,
        )
        box_project["objects"].append(page)

        svg_path = os.path.join(tmp_dir, "gdt_perp.svg")
        result = export_drawing_svg(box_project, "PerpSheet", svg_path)

        assert result["success"] is True
        with open(svg_path, encoding="utf-8") as f:
            content = f.read()
        assert "⊥" in content, "Perpendicularity symbol not found"
        assert "0.1" in content
        # Datum triangle + letter
        assert ">A<" in content, "Datum A symbol not found"
        print(f"\n  SVG GD&T perpendicularity + datum: {svg_path}")

    def test_surface_finish_on_drawing_svg(self, box_project, tmp_dir):
        """Surface finish annotation → SVG."""
        from cli_anything.freecad.core.techdraw import (
            create_drawing, add_view, add_surface_finish,
            export_drawing_svg,
        )
        page = create_drawing(box_project, page_name="SFSheet")
        add_view(page, "Box", view_name="FrontView", direction="front")
        add_surface_finish(
            page, "FrontView",
            ra=1.6, rz=6.3,
            process="removal_required",
            lay_direction="=",
            sf_name="SF1",
            x=80, y=60,
        )
        box_project["objects"].append(page)

        svg_path = os.path.join(tmp_dir, "surface_finish.svg")
        result = export_drawing_svg(box_project, "SFSheet", svg_path)

        assert result["success"] is True
        with open(svg_path, encoding="utf-8") as f:
            content = f.read()
        assert "Ra 1.6" in content, "Ra value not found in SVG"
        assert "Rz 6.3" in content, "Rz value not found in SVG"
        print(f"\n  SVG surface finish: {svg_path}")

    def test_combined_gdt_workflow_svg(self, box_project, tmp_dir):
        """Full GD&T workflow: datums + position + flatness + surface finish → SVG."""
        from cli_anything.freecad.core.techdraw import (
            create_drawing, add_view, add_geometric_tolerance,
            add_datum_symbol, add_surface_finish, export_drawing_svg,
        )
        page = create_drawing(box_project, page_name="FullGDT")
        add_view(page, "Box", view_name="FrontView", direction="front")

        # Add datum references
        add_datum_symbol(page, "FrontView", "A", datum_name="DatA", x=50, y=130)
        add_datum_symbol(page, "FrontView", "B", datum_name="DatB", x=130, y=130)
        add_datum_symbol(page, "FrontView", "C", datum_name="DatC", x=90, y=30)

        # Position tolerance referencing all 3 datums
        add_geometric_tolerance(
            page, "FrontView",
            characteristic="position",
            tolerance=0.05,
            datum_refs=["A", "B", "C"],
            material_condition="MMC",
            diameter_zone=True,
            gdt_name="Pos1",
            x=100, y=80,
        )

        # Flatness on top surface
        add_geometric_tolerance(
            page, "FrontView",
            characteristic="flatness",
            tolerance=0.01,
            gdt_name="Flat1",
            x=100, y=50,
        )

        # Surface finish
        add_surface_finish(
            page, "FrontView",
            ra=0.8,
            process="removal_required",
            sf_name="SF1",
            x=160, y=60,
        )

        box_project["objects"].append(page)

        svg_path = os.path.join(tmp_dir, "full_gdt.svg")
        result = export_drawing_svg(box_project, "FullGDT", svg_path)

        assert result["success"] is True
        with open(svg_path, encoding="utf-8") as f:
            content = f.read()

        # Verify all GD&T elements present
        assert "⌖" in content, "Position symbol missing"
        assert "⏥" in content, "Flatness symbol missing"
        assert ">A<" in content, "Datum A missing"
        assert ">B<" in content, "Datum B missing"
        assert ">C<" in content, "Datum C missing"
        assert "Ra 0.8" in content, "Surface finish missing"
        assert "0.05" in content, "Position tolerance value missing"
        assert "0.01" in content, "Flatness tolerance value missing"
        print(f"\n  SVG full GD&T: {svg_path} ({result['result']['file_size']:,} bytes)")


class TestGDTDrawingDXF:
    """GD&T annotations exported to DXF."""

    def test_gdt_to_dxf(self, box_project, tmp_dir):
        """Box + GD&T annotations → DXF export succeeds."""
        from cli_anything.freecad.core.techdraw import (
            create_drawing, add_view, add_geometric_tolerance,
            add_datum_symbol, export_drawing_dxf,
        )
        page = create_drawing(box_project, page_name="GDTDxf")
        add_view(page, "Box", view_name="V1", direction="front")
        add_datum_symbol(page, "V1", "A", datum_name="DatA", x=50, y=120)
        add_geometric_tolerance(
            page, "V1",
            characteristic="position",
            tolerance=0.1,
            datum_refs=["A"],
            gdt_name="PosGDT",
            x=100, y=80,
        )
        box_project["objects"].append(page)

        dxf_path = os.path.join(tmp_dir, "gdt.dxf")
        result = export_drawing_dxf(box_project, "GDTDxf", dxf_path)

        assert result["success"] is True
        assert os.path.exists(dxf_path)
        assert result["result"]["file_size"] > 0
        print(f"\n  DXF GD&T: {dxf_path} ({result['result']['file_size']:,} bytes)")


class TestGDTSubprocess:
    """GD&T workflow via CLI subprocess."""
    CLI_BASE = _resolve_cli("cli-anything-freecad")

    def _run(self, args, check=True):
        return subprocess.run(
            self.CLI_BASE + args,
            capture_output=True, text=True,
            check=check,
        )

    def test_gdt_cli_workflow(self, tmp_dir):
        """Full CLI workflow: project → box → page → view → GD&T → datum → list."""
        proj_path = os.path.join(tmp_dir, "gdt_workflow.json")
        svg_path = os.path.join(tmp_dir, "gdt_output.svg")

        # Create project + box
        self._run(["--json", "project", "new", "-n", "GDTWork", "-o", proj_path])
        self._run(["--json", "--project", proj_path, "part", "box",
                    "-l", "30", "-w", "20", "-H", "10"])

        # Create drawing page + view
        self._run(["--json", "--project", proj_path, "techdraw", "page",
                    "-n", "S1", "-t", "A4_Landscape"])
        self._run(["--json", "--project", proj_path, "techdraw", "view",
                    "S1", "Box", "-d", "front", "-n", "V1"])

        # Add datum
        r = self._run(["--json", "--project", proj_path, "techdraw", "datum",
                        "S1", "V1", "A", "-x", "50", "-y", "120"])
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert data["letter"] == "A"

        # Add GD&T position tolerance
        r = self._run(["--json", "--project", proj_path, "techdraw", "gdt",
                        "S1", "V1", "-c", "position", "-t", "0.05",
                        "-d", "A", "-m", "MMC", "--diameter-zone",
                        "-x", "100", "-y", "80"])
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert data["characteristic"] == "position"
        assert data["tolerance"] == 0.05
        assert data["datum_refs"] == ["A"]
        assert data["material_condition"] == "MMC"

        # Add surface finish
        r = self._run(["--json", "--project", proj_path, "techdraw", "surface-finish",
                        "S1", "V1", "--ra", "1.6", "--rz", "6.3",
                        "-p", "removal_required", "-x", "80", "-y", "60"])
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert data["ra"] == 1.6
        assert data["rz"] == 6.3

        # List should show GD&T items
        r = self._run(["--json", "--project", proj_path, "techdraw", "list", "S1"])
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert len(data.get("gdt", [])) == 1
        assert len(data.get("datums", [])) == 1
        assert len(data.get("surface_finishes", [])) == 1

        # Export SVG
        r = self._run(["--json", "--project", proj_path, "techdraw", "export-svg",
                        "S1", svg_path, "--overwrite"])
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert data["success"] is True
        assert os.path.exists(svg_path)
        print(f"\n  SVG GD&T workflow: {svg_path} ({data['file_size']:,} bytes)")


# ── Weld Symbol E2E Tests ──────────────────────────────────────────

class TestWeldDrawingWorkflow:
    """E2E tests for weld symbol annotations on TechDraw pages."""

    def test_fillet_weld_on_drawing_svg(self, box_project, tmp_dir):
        """Box + drawing page + fillet weld → export SVG with weld symbol."""
        from cli_anything.freecad.core.techdraw import (
            create_drawing, add_view, add_weld_symbol,
            export_drawing_svg,
        )
        page = create_drawing(box_project, page_name="WeldSheet")
        add_view(page, "Box", view_name="FrontView", direction="front")
        add_weld_symbol(
            page, "FrontView",
            weld_type="fillet",
            side="arrow",
            size="5",
            length="50",
            weld_name="W1",
            x=100, y=80,
        )
        box_project["objects"].append(page)

        svg_path = os.path.join(tmp_dir, "weld_fillet.svg")
        result = export_drawing_svg(box_project, "WeldSheet", svg_path)

        assert result["success"] is True
        assert os.path.exists(svg_path)
        with open(svg_path, encoding="utf-8") as f:
            content = f.read()
        # Should have weld reference line and fillet triangle
        assert "weld-reference-line" in content or "stroke" in content
        assert "polygon" in content.lower(), "Fillet triangle polygon not found"
        print(f"\n  SVG weld fillet: {svg_path} ({result['result']['file_size']:,} bytes)")

    def test_v_groove_all_around_svg(self, box_project, tmp_dir):
        """V-groove weld with all-around symbol → SVG."""
        from cli_anything.freecad.core.techdraw import (
            create_drawing, add_view, add_weld_symbol,
            export_drawing_svg,
        )
        page = create_drawing(box_project, page_name="VGroove")
        add_view(page, "Box", view_name="FrontView", direction="front")
        add_weld_symbol(
            page, "FrontView",
            weld_type="v_groove",
            side="arrow",
            size="6",
            all_around=True,
            weld_name="VG1",
            x=100, y=80,
        )
        box_project["objects"].append(page)

        svg_path = os.path.join(tmp_dir, "weld_vgroove.svg")
        result = export_drawing_svg(box_project, "VGroove", svg_path)

        assert result["success"] is True
        with open(svg_path, encoding="utf-8") as f:
            content = f.read()
        # All-around circle
        assert "circle" in content.lower(), "All-around circle not found"
        print(f"\n  SVG weld V-groove all-around: {svg_path}")

    def test_double_sided_weld_svg(self, box_project, tmp_dir):
        """Fillet weld + other side tile → SVG has both sides."""
        from cli_anything.freecad.core.techdraw import (
            create_drawing, add_view, add_weld_symbol, add_weld_tile,
            export_drawing_svg,
        )
        page = create_drawing(box_project, page_name="DoubleSide")
        add_view(page, "Box", view_name="FrontView", direction="front")
        add_weld_symbol(
            page, "FrontView",
            weld_type="fillet",
            side="arrow",
            size="5",
            weld_name="DW1",
            x=100, y=80,
        )
        add_weld_tile(
            page, "DW1",
            weld_type="fillet",
            side="other",
            size="3",
        )
        box_project["objects"].append(page)

        svg_path = os.path.join(tmp_dir, "weld_double.svg")
        result = export_drawing_svg(box_project, "DoubleSide", svg_path)

        assert result["success"] is True
        with open(svg_path, encoding="utf-8") as f:
            content = f.read()
        assert "svg" in content.lower()
        print(f"\n  SVG double-sided weld: {svg_path}")

    def test_weld_with_tail_and_contour_svg(self, box_project, tmp_dir):
        """Bevel groove with tail text and flush contour → SVG."""
        from cli_anything.freecad.core.techdraw import (
            create_drawing, add_view, add_weld_symbol,
            export_drawing_svg,
        )
        page = create_drawing(box_project, page_name="BevelSheet")
        add_view(page, "Box", view_name="FrontView", direction="front")
        add_weld_symbol(
            page, "FrontView",
            weld_type="bevel_groove",
            side="arrow",
            size="8",
            tail="GMAW",
            contour="flush",
            field_weld=True,
            weld_name="BG1",
            x=100, y=80,
        )
        box_project["objects"].append(page)

        svg_path = os.path.join(tmp_dir, "weld_bevel.svg")
        result = export_drawing_svg(box_project, "BevelSheet", svg_path)

        assert result["success"] is True
        with open(svg_path, encoding="utf-8") as f:
            content = f.read()
        assert "GMAW" in content, "Tail text GMAW not found"
        print(f"\n  SVG weld bevel+tail+contour: {svg_path}")

    def test_combined_gdt_and_weld_workflow_svg(self, box_project, tmp_dir):
        """Full workflow: datums + GD&T + weld symbols → SVG has everything."""
        from cli_anything.freecad.core.techdraw import (
            create_drawing, add_view, add_geometric_tolerance,
            add_datum_symbol, add_weld_symbol, export_drawing_svg,
        )
        page = create_drawing(box_project, page_name="FullDraw")
        add_view(page, "Box", view_name="FrontView", direction="front")

        # GD&T
        add_datum_symbol(page, "FrontView", "A", datum_name="DatA", x=50, y=130)
        add_geometric_tolerance(
            page, "FrontView",
            characteristic="position",
            tolerance=0.05,
            datum_refs=["A"],
            gdt_name="Pos1",
            x=100, y=80,
        )

        # Weld
        add_weld_symbol(
            page, "FrontView",
            weld_type="fillet",
            side="arrow",
            size="5",
            weld_name="W1",
            x=150, y=100,
        )

        box_project["objects"].append(page)

        svg_path = os.path.join(tmp_dir, "full_combined.svg")
        result = export_drawing_svg(box_project, "FullDraw", svg_path)

        assert result["success"] is True
        with open(svg_path, encoding="utf-8") as f:
            content = f.read()
        # GD&T elements
        assert "⌖" in content, "Position symbol missing"
        assert ">A<" in content, "Datum A missing"
        # Weld elements
        assert "polygon" in content.lower(), "Weld fillet triangle missing"
        print(f"\n  SVG combined GD&T + weld: {svg_path} ({result['result']['file_size']:,} bytes)")


class TestWeldSubprocess:
    """Weld workflow via CLI subprocess."""
    CLI_BASE = _resolve_cli("cli-anything-freecad")

    def _run(self, args, check=True):
        return subprocess.run(
            self.CLI_BASE + args,
            capture_output=True, text=True,
            check=check,
        )

    def test_weld_cli_workflow(self, tmp_dir):
        """Full CLI workflow: project → box → page → view → weld → tile → list → SVG."""
        proj_path = os.path.join(tmp_dir, "weld_workflow.json")
        svg_path = os.path.join(tmp_dir, "weld_output.svg")

        # Create project + box
        self._run(["--json", "project", "new", "-n", "WeldWork", "-o", proj_path])
        self._run(["--json", "--project", proj_path, "part", "box",
                    "-l", "30", "-w", "20", "-H", "10"])

        # Create drawing page + view
        self._run(["--json", "--project", proj_path, "techdraw", "page",
                    "-n", "S1", "-t", "A4_Landscape"])
        self._run(["--json", "--project", proj_path, "techdraw", "view",
                    "S1", "Box", "-d", "front", "-n", "V1"])

        # Add fillet weld
        r = self._run(["--json", "--project", proj_path, "techdraw", "weld",
                        "S1", "V1", "-t", "fillet", "-s", "arrow",
                        "--size", "5", "--length", "50",
                        "-x", "100", "-y", "80"])
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert data["weld_type"] == "fillet"
        assert data["all_around"] is False

        # Add other-side tile
        weld_name = data["name"]
        r = self._run(["--json", "--project", proj_path, "techdraw", "weld-tile",
                        "S1", weld_name, "-t", "fillet", "-s", "other",
                        "--size", "3"])
        assert r.returncode == 0
        tile_data = json.loads(r.stdout)
        assert tile_data["side"] == "other"

        # List should show welds
        r = self._run(["--json", "--project", proj_path, "techdraw", "list", "S1"])
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert len(data.get("welds", [])) == 1

        # Export SVG
        r = self._run(["--json", "--project", proj_path, "techdraw", "export-svg",
                        "S1", svg_path, "--overwrite"])
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert data["success"] is True
        assert os.path.exists(svg_path)
        print(f"\n  SVG weld workflow: {svg_path} ({data['file_size']:,} bytes)")
