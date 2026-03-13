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

        with open(svg_path) as f:
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
