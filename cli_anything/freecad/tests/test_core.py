"""Unit tests for cli-anything-freecad core modules.

Tests use synthetic data — no FreeCAD backend required.
"""

from __future__ import annotations

import json
import os
import tempfile

import pytest
from click.testing import CliRunner

from cli_anything.freecad.core.project import (
    create_project,
    get_project_info,
    load_project,
    save_project,
    _build_project_script,
    _object_to_script,
)
from cli_anything.freecad.core.session import Session
from cli_anything.freecad.core.export import list_formats, EXPORT_FORMATS
from cli_anything.freecad.core.project import _placement_script
from cli_anything.freecad.core.techdraw import (
    create_drawing,
    add_view,
    add_projection_group,
    add_section_view,
    add_dimension,
    add_annotation,
    _build_techdraw_script,
    _project_object_2d,
    export_drawing_svg,
    PAPER_SIZES,
    VIEW_DIRECTIONS,
)
from cli_anything.freecad.freecad_cli import cli


# ── Fixtures ─────────────────────────────────────────────────────────

@pytest.fixture
def tmp_dir():
    with tempfile.TemporaryDirectory(prefix="fc_test_") as d:
        yield d


@pytest.fixture
def sample_project(tmp_dir):
    path = os.path.join(tmp_dir, "test.json")
    proj = create_project(name="TestProject", output_path=path)
    return proj


@pytest.fixture
def session_with_project(tmp_dir):
    s = Session()
    path = os.path.join(tmp_dir, "session_test.json")
    s.new_project(name="SessionTest", path=path)
    return s


# ── project.py tests ────────────────────────────────────────────────

class TestCreateProject:
    def test_create_project_defaults(self):
        proj = create_project()
        assert proj["name"] == "Untitled"
        assert proj["objects"] == []
        assert proj["modified"] is False
        assert proj["fcstd_path"] is None

    def test_create_project_with_name(self):
        proj = create_project(name="MyPart")
        assert proj["name"] == "MyPart"

    def test_create_project_with_output(self, tmp_dir):
        path = os.path.join(tmp_dir, "out.json")
        proj = create_project(name="Saved", output_path=path)
        assert os.path.exists(path)
        with open(path) as f:
            loaded = json.load(f)
        assert loaded["name"] == "Saved"

    def test_load_project(self, tmp_dir):
        path = os.path.join(tmp_dir, "load.json")
        create_project(name="LoadMe", output_path=path)
        proj = load_project(path)
        assert proj["name"] == "LoadMe"
        assert proj["project_path"] == os.path.abspath(path)

    def test_save_project(self, sample_project, tmp_dir):
        path = os.path.join(tmp_dir, "saved.json")
        result = save_project(sample_project, path)
        assert result == os.path.abspath(path)
        assert os.path.exists(path)

    def test_get_project_info_empty(self, sample_project):
        info = get_project_info(sample_project)
        assert info["name"] == "TestProject"
        assert info["object_count"] == 0
        assert info["objects"] == []

    def test_get_project_info_with_objects(self, sample_project):
        sample_project["objects"].append({
            "name": "Box", "type": "Part::Box", "label": "Box",
            "params": {"length": 10, "width": 10, "height": 10},
        })
        info = get_project_info(sample_project)
        assert info["object_count"] == 1
        assert info["objects"][0]["name"] == "Box"


class TestBuildProjectScript:
    def test_empty_project(self):
        proj = create_project(name="Empty")
        script = _build_project_script(proj)
        assert "FreeCAD.newDocument" in script
        assert "'Empty'" in script
        assert "doc.recompute()" in script

    def test_box_object_script(self):
        obj = {
            "name": "MyBox",
            "type": "Part::Box",
            "params": {"length": 20, "width": 15, "height": 10},
        }
        script = _object_to_script(obj)
        assert "Part::Box" in script
        assert "MyBox" in script
        assert ".Length = 20" in script
        assert ".Width = 15" in script
        assert ".Height = 10" in script

    def test_cylinder_object_script(self):
        obj = {
            "name": "Cyl",
            "type": "Part::Cylinder",
            "params": {"radius": 5, "height": 20, "angle": 360},
        }
        script = _object_to_script(obj)
        assert "Part::Cylinder" in script
        assert ".Radius = 5" in script
        assert ".Height = 20" in script

    def test_sphere_object_script(self):
        obj = {"name": "Sph", "type": "Part::Sphere", "params": {"radius": 7}}
        script = _object_to_script(obj)
        assert "Part::Sphere" in script
        assert ".Radius = 7" in script

    def test_fuse_object_script(self):
        obj = {
            "name": "Fused",
            "type": "Part::Fuse",
            "params": {"base": "Box", "tool": "Cyl"},
        }
        script = _object_to_script(obj)
        assert "Part::Fuse" in script
        assert "'Box'" in script
        assert "'Cyl'" in script

    def test_cut_object_script(self):
        obj = {
            "name": "Cut1",
            "type": "Part::Cut",
            "params": {"base": "Box", "tool": "Cyl"},
        }
        script = _object_to_script(obj)
        assert "Part::Cut" in script

    def test_sketch_object_script(self):
        obj = {
            "name": "Sketch",
            "type": "Sketcher::SketchObject",
            "params": {
                "plane": "XY",
                "geometry": [{"type": "line", "x1": 0, "y1": 0, "x2": 10, "y2": 0}],
                "constraints": [],
            },
        }
        script = _object_to_script(obj)
        assert "Sketcher::SketchObject" in script
        assert "LineSegment" in script

    def test_unknown_type(self):
        obj = {"name": "Unknown", "type": "Foo::Bar", "params": {}}
        script = _object_to_script(obj)
        assert "Unknown object type" in script


# ── session.py tests ─────────────────────────────────────────────────

class TestSession:
    def test_new_session(self):
        s = Session()
        assert not s.has_project
        assert not s.is_modified
        assert s.project_name == ""

    def test_new_project(self, tmp_dir):
        s = Session()
        path = os.path.join(tmp_dir, "s.json")
        proj = s.new_project(name="Test", path=path)
        assert s.has_project
        assert s.project_name == "Test"
        assert not s.is_modified

    def test_open_project(self, tmp_dir):
        path = os.path.join(tmp_dir, "open.json")
        create_project(name="OpenMe", output_path=path)
        s = Session()
        proj = s.open_project(path)
        assert s.project_name == "OpenMe"

    def test_save(self, session_with_project, tmp_dir):
        path = os.path.join(tmp_dir, "saved_session.json")
        result = session_with_project.save(path)
        assert os.path.exists(path)

    def test_add_object(self, session_with_project):
        obj = {"name": "B", "type": "Part::Box", "params": {"length": 5, "width": 5, "height": 5}}
        session_with_project.add_object(obj, "add box")
        assert len(session_with_project.project["objects"]) == 1
        # After auto-save, modified is False (changes persisted)
        assert not session_with_project.is_modified

    def test_remove_object(self, session_with_project):
        obj = {"name": "B", "type": "Part::Box", "params": {}}
        session_with_project.add_object(obj, "add")
        removed = session_with_project.remove_object("B")
        assert removed is not None
        assert removed["name"] == "B"
        assert len(session_with_project.project["objects"]) == 0

    def test_remove_nonexistent(self, session_with_project):
        result = session_with_project.remove_object("DoesNotExist")
        assert result is None

    def test_undo(self, session_with_project):
        obj = {"name": "B", "type": "Part::Box", "params": {}}
        session_with_project.add_object(obj, "add box B")
        result = session_with_project.undo()
        assert result is not None
        assert result["undone"] == "add box B"
        assert len(session_with_project.project["objects"]) == 0

    def test_redo(self, session_with_project):
        obj = {"name": "B", "type": "Part::Box", "params": {}}
        session_with_project.add_object(obj, "add box B")
        session_with_project.undo()
        result = session_with_project.redo()
        assert result is not None
        assert len(session_with_project.project["objects"]) == 1

    def test_history(self, session_with_project):
        session_with_project.add_object({"name": "A", "type": "Part::Box", "params": {}}, "add A")
        session_with_project.add_object({"name": "B", "type": "Part::Cylinder", "params": {}}, "add B")
        history = session_with_project.history()
        assert len(history) == 2
        assert history[0] == "add A"
        assert history[1] == "add B"

    def test_status(self, session_with_project):
        status = session_with_project.status()
        assert status["has_project"] is True
        assert status["project_name"] == "SessionTest"
        assert isinstance(status["undo_available"], int)

    def test_list_objects(self, session_with_project):
        session_with_project.add_object({"name": "X", "type": "Part::Box", "params": {}}, "add")
        objects = session_with_project.list_objects()
        assert len(objects) == 1
        assert objects[0]["name"] == "X"

    def test_get_object(self, session_with_project):
        session_with_project.add_object({"name": "Y", "type": "Part::Sphere", "params": {}}, "add")
        obj = session_with_project.get_object("Y")
        assert obj is not None
        assert obj["type"] == "Part::Sphere"
        assert session_with_project.get_object("Z") is None


# ── export.py tests ──────────────────────────────────────────────────

class TestExport:
    def test_list_formats(self):
        fmts = list_formats()
        assert len(fmts) >= 5
        names = [f["name"] for f in fmts]
        assert "step" in names
        assert "stl" in names
        assert "obj" in names

    def test_export_no_overwrite(self, tmp_dir):
        from cli_anything.freecad.core.export import export
        proj = create_project(name="Test")
        proj["objects"].append({"name": "Box", "type": "Part::Box", "params": {"length": 10, "width": 10, "height": 10}})
        # Create a file to block overwrite
        path = os.path.join(tmp_dir, "existing.step")
        with open(path, "w") as f:
            f.write("dummy")
        result = export(proj, path, preset="step", overwrite=False)
        assert result["success"] is False
        assert "exists" in result["error"].lower()

    def test_format_registry(self):
        assert "step" in EXPORT_FORMATS
        assert "stl" in EXPORT_FORMATS
        assert ".step" in EXPORT_FORMATS["step"]["extensions"]
        assert ".stl" in EXPORT_FORMATS["stl"]["extensions"]

    def test_format_registry_dxf_svg_pdf(self):
        assert "dxf" in EXPORT_FORMATS
        assert "svg" in EXPORT_FORMATS
        assert "pdf" in EXPORT_FORMATS
        assert ".dxf" in EXPORT_FORMATS["dxf"]["extensions"]
        assert ".svg" in EXPORT_FORMATS["svg"]["extensions"]
        assert ".pdf" in EXPORT_FORMATS["pdf"]["extensions"]


# ── techdraw.py tests ──────────────────────────────────────────────

class TestTechDraw:
    def test_create_drawing(self):
        proj = create_project(name="TD")
        page = create_drawing(proj, page_name="Sheet1", template="A3_Landscape", scale=2.0)
        assert page["name"] == "Sheet1"
        assert page["type"] == "TechDraw::DrawPage"
        assert page["params"]["template"] == "A3_Landscape"
        assert page["params"]["scale"] == 2.0
        assert page["params"]["views"] == []
        assert page["params"]["dimensions"] == []
        assert page["params"]["annotations"] == []

    def test_create_drawing_defaults(self):
        proj = create_project()
        page = create_drawing(proj)
        assert page["name"] == "Page"
        assert page["params"]["template"] == "A4_Landscape"
        assert page["params"]["scale"] == 1.0

    def test_add_view(self):
        proj = create_project()
        page = create_drawing(proj)
        view = add_view(page, "Box", view_name="FrontView", direction="front", x=120, y=80)
        assert view["name"] == "FrontView"
        assert view["type"] == "TechDraw::DrawViewPart"
        assert view["source"] == "Box"
        assert view["direction"] == (0, 0, 1)
        assert view["x"] == 120
        assert view["y"] == 80
        assert len(page["params"]["views"]) == 1

    def test_add_view_iso(self):
        page = create_drawing(create_project())
        view = add_view(page, "Box", direction="iso")
        assert view["direction"] == (1, -1, 1)

    def test_add_view_custom_direction(self):
        page = create_drawing(create_project())
        view = add_view(page, "Box", direction="1,2,3")
        assert view["direction"] == (1.0, 2.0, 3.0)

    def test_add_projection_group(self):
        page = create_drawing(create_project())
        pg = add_projection_group(page, "Box", group_name="PG1",
                                  projections=["Front", "Top", "Right", "Left"])
        assert pg["name"] == "PG1"
        assert pg["type"] == "TechDraw::DrawProjGroup"
        assert pg["source"] == "Box"
        assert pg["projections"] == ["Front", "Top", "Right", "Left"]
        assert len(page["params"]["views"]) == 1

    def test_add_projection_group_defaults(self):
        page = create_drawing(create_project())
        pg = add_projection_group(page, "Cyl")
        assert pg["projections"] == ["Front", "Top", "Right"]

    def test_add_section_view(self):
        page = create_drawing(create_project())
        sv = add_section_view(page, "Box", "FrontView",
                              section_name="SectionA", normal=(1, 0, 0),
                              origin=(5, 0, 0), x=250, y=100)
        assert sv["name"] == "SectionA"
        assert sv["type"] == "TechDraw::DrawViewSection"
        assert sv["source"] == "Box"
        assert sv["base_view"] == "FrontView"
        assert sv["section_normal"] == (1, 0, 0)
        assert sv["section_origin"] == (5, 0, 0)

    def test_add_dimension(self):
        page = create_drawing(create_project())
        dim = add_dimension(page, "FrontView", dim_type="Distance",
                            edge_ref="Edge1", dim_name="Length1",
                            x=80, y=40, format_spec="%.1f")
        assert dim["name"] == "Length1"
        assert dim["type"] == "TechDraw::DrawViewDimension"
        assert dim["view"] == "FrontView"
        assert dim["dim_type"] == "Distance"
        assert dim["references"] == ["Edge1"]
        assert dim["format_spec"] == "%.1f"
        assert len(page["params"]["dimensions"]) == 1

    def test_add_dimension_radius(self):
        page = create_drawing(create_project())
        dim = add_dimension(page, "V1", dim_type="Radius", edge_ref="Edge3")
        assert dim["dim_type"] == "Radius"

    def test_add_annotation(self):
        page = create_drawing(create_project())
        anno = add_annotation(page, ["Line 1", "Line 2"], anno_name="Note1",
                              x=30, y=250, font_size=4.0)
        assert anno["name"] == "Note1"
        assert anno["type"] == "TechDraw::DrawViewAnnotation"
        assert anno["text"] == ["Line 1", "Line 2"]
        assert anno["font_size"] == 4.0
        assert len(page["params"]["annotations"]) == 1

    def test_paper_sizes(self):
        assert "A4_Landscape" in PAPER_SIZES
        assert PAPER_SIZES["A4_Landscape"] == (297, 210)
        assert "A3_Landscape" in PAPER_SIZES

    def test_view_directions(self):
        assert "front" in VIEW_DIRECTIONS
        assert "iso" in VIEW_DIRECTIONS
        assert VIEW_DIRECTIONS["front"] == (0, 0, 1)
        assert VIEW_DIRECTIONS["top"] == (0, -1, 0)

    def test_build_techdraw_script_basic(self):
        proj = create_project(name="TDTest")
        proj["objects"].append({
            "name": "Box", "type": "Part::Box",
            "params": {"length": 20, "width": 15, "height": 10},
        })
        page = create_drawing(proj, page_name="Sheet1")
        add_view(page, "Box", view_name="FrontView", direction="front")
        add_dimension(page, "FrontView", dim_type="Distance", edge_ref="Edge0")
        add_annotation(page, ["Test note"])
        proj["objects"].append(page)

        script = _build_techdraw_script(proj, "Sheet1")
        assert "TechDraw::DrawPage" in script
        assert "TechDraw::DrawViewPart" in script
        assert "'FrontView'" in script
        assert "'Box'" in script
        assert "TechDraw::DrawViewDimension" in script
        assert "TechDraw::DrawViewAnnotation" in script

    def test_build_techdraw_script_projection(self):
        proj = create_project(name="ProjTest")
        proj["objects"].append({
            "name": "Cyl", "type": "Part::Cylinder",
            "params": {"radius": 5, "height": 20, "angle": 360},
        })
        page = create_drawing(proj, page_name="P1")
        add_projection_group(page, "Cyl", projections=["Front", "Top"])
        proj["objects"].append(page)

        script = _build_techdraw_script(proj, "P1")
        assert "TechDraw::DrawProjGroup" in script
        assert "addProjection" in script

    def test_build_techdraw_script_section(self):
        proj = create_project(name="SecTest")
        proj["objects"].append({
            "name": "Box", "type": "Part::Box",
            "params": {"length": 30, "width": 30, "height": 10},
        })
        page = create_drawing(proj, page_name="S1")
        add_view(page, "Box", view_name="V1")
        add_section_view(page, "Box", "V1", section_name="Sec1")
        proj["objects"].append(page)

        script = _build_techdraw_script(proj, "S1")
        assert "TechDraw::DrawViewSection" in script
        assert "'Sec1'" in script

    def test_build_techdraw_script_page_not_found(self):
        proj = create_project(name="Empty")
        script = _build_techdraw_script(proj, "NonExistent")
        assert "not found" in script


class TestTechDrawCLI:
    def test_techdraw_page_json(self, tmp_dir):
        runner = CliRunner()
        path = os.path.join(tmp_dir, "td_test.json")
        runner.invoke(cli, ["--json", "project", "new", "-o", path])
        # Add a box first
        runner.invoke(cli, ["--json", "--project", path, "part", "box", "-l", "20"])
        # Create a drawing page
        result = runner.invoke(cli, ["--json", "--project", path, "techdraw", "page", "-t", "A3_Landscape"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["type"] == "TechDraw::DrawPage"
        assert data["params"]["template"] == "A3_Landscape"

    def test_techdraw_view_json(self, tmp_dir):
        runner = CliRunner()
        path = os.path.join(tmp_dir, "td_view.json")
        runner.invoke(cli, ["--json", "project", "new", "-o", path])
        runner.invoke(cli, ["--json", "--project", path, "part", "box", "-n", "MyBox"])
        runner.invoke(cli, ["--json", "--project", path, "techdraw", "page", "-n", "Page"])
        result = runner.invoke(cli, ["--json", "--project", path, "techdraw", "view", "Page", "MyBox", "-d", "top"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["type"] == "TechDraw::DrawViewPart"
        assert data["source"] == "MyBox"

    def test_techdraw_dimension_json(self, tmp_dir):
        runner = CliRunner()
        path = os.path.join(tmp_dir, "td_dim.json")
        runner.invoke(cli, ["--json", "project", "new", "-o", path])
        runner.invoke(cli, ["--json", "--project", path, "part", "box", "-n", "B1"])
        runner.invoke(cli, ["--json", "--project", path, "techdraw", "page", "-n", "P1"])
        runner.invoke(cli, ["--json", "--project", path, "techdraw", "view", "P1", "B1", "-n", "V1"])
        result = runner.invoke(cli, ["--json", "--project", path, "techdraw", "dimension",
                                     "P1", "V1", "-t", "Distance", "-e", "Edge0"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["type"] == "TechDraw::DrawViewDimension"
        assert data["dim_type"] == "Distance"

    def test_techdraw_annotate_json(self, tmp_dir):
        runner = CliRunner()
        path = os.path.join(tmp_dir, "td_anno.json")
        runner.invoke(cli, ["--json", "project", "new", "-o", path])
        runner.invoke(cli, ["--json", "--project", path, "techdraw", "page", "-n", "P1"])
        result = runner.invoke(cli, ["--json", "--project", path, "techdraw", "annotate",
                                     "P1", "Material:", "Steel"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["type"] == "TechDraw::DrawViewAnnotation"
        assert data["text"] == ["Material:", "Steel"]

    def test_techdraw_list_json(self, tmp_dir):
        runner = CliRunner()
        path = os.path.join(tmp_dir, "td_list.json")
        runner.invoke(cli, ["--json", "project", "new", "-o", path])
        runner.invoke(cli, ["--json", "--project", path, "part", "box", "-n", "Box"])
        runner.invoke(cli, ["--json", "--project", path, "techdraw", "page", "-n", "P1"])
        runner.invoke(cli, ["--json", "--project", path, "techdraw", "view", "P1", "Box"])
        runner.invoke(cli, ["--json", "--project", path, "techdraw", "annotate", "P1", "Note"])
        result = runner.invoke(cli, ["--json", "--project", path, "techdraw", "list", "P1"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["page"] == "P1"
        assert len(data["views"]) == 1
        assert len(data["annotations"]) == 1

    def test_export_formats_includes_dxf_svg_pdf(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["--json", "export", "formats"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        names = [f["name"] for f in data["formats"]]
        assert "dxf" in names
        assert "svg" in names
        assert "pdf" in names


# ── freecad_backend.py tests ────────────────────────────────────────

class TestBackend:
    def test_find_freecadcmd(self):
        from cli_anything.freecad.utils.freecad_backend import find_freecadcmd
        path = find_freecadcmd()
        assert os.path.exists(path)

    def test_get_version(self):
        from cli_anything.freecad.utils.freecad_backend import get_version
        version = get_version()
        assert "FreeCAD" in version or "freecad" in version.lower()

    def test_run_script_basic(self):
        from cli_anything.freecad.utils.freecad_backend import run_script
        result = run_script(
            "import FreeCAD\n"
            "_cli_result['version'] = FreeCAD.Version()[0] + '.' + FreeCAD.Version()[1]\n"
        )
        assert result["success"] is True
        assert "version" in result["result"]


# ── CLI tests (Click test runner) ───────────────────────────────────

class TestCLI:
    def test_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "cli-anything-freecad" in result.output

    def test_version(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["--json", "--version"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "version" in data

    def test_project_new_json(self, tmp_dir):
        runner = CliRunner()
        path = os.path.join(tmp_dir, "cli_test.json")
        result = runner.invoke(cli, ["--json", "project", "new", "-n", "CLITest", "-o", path])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["name"] == "CLITest"

    def test_part_box_json(self, tmp_dir):
        runner = CliRunner()
        path = os.path.join(tmp_dir, "box_test.json")
        # Create project first
        runner.invoke(cli, ["--json", "project", "new", "-o", path])
        result = runner.invoke(cli, ["--json", "--project", path, "part", "box", "-l", "30"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["type"] == "Part::Box"
        assert data["params"]["length"] == 30.0

    def test_export_formats_json(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["--json", "export", "formats"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "formats" in data
        assert len(data["formats"]) >= 5


# ── Placement tests ─────────────────────────────────────────────────

class TestPlacement:
    """Tests for placement support on all primitives."""

    def test_placement_script_helper(self):
        params = {"placement": {"x": 10, "y": 20, "z": 30}}
        script = _placement_script(params)
        assert "FreeCAD.Placement" in script
        assert "Vector(10, 20, 30)" in script

    def test_placement_script_no_placement(self):
        params = {"length": 10}
        script = _placement_script(params)
        assert script == ""

    def test_box_with_placement_script(self):
        obj = {
            "name": "PlacedBox",
            "type": "Part::Box",
            "params": {"length": 50, "width": 30, "height": 20, "placement": {"x": 100, "y": 0, "z": 50}},
        }
        script = _object_to_script(obj)
        assert "Part::Box" in script
        assert ".Length = 50" in script
        assert "FreeCAD.Placement" in script
        assert "Vector(100, 0, 50)" in script

    def test_cylinder_with_placement_script(self):
        obj = {
            "name": "PlacedCyl",
            "type": "Part::Cylinder",
            "params": {"radius": 10, "height": 50, "angle": 360, "placement": {"x": 5, "y": 10, "z": 15}},
        }
        script = _object_to_script(obj)
        assert "Part::Cylinder" in script
        assert "FreeCAD.Placement" in script
        assert "Vector(5, 10, 15)" in script

    def test_sphere_with_placement_script(self):
        obj = {
            "name": "PlacedSph",
            "type": "Part::Sphere",
            "params": {"radius": 25, "placement": {"x": 0, "y": 100, "z": 0}},
        }
        script = _object_to_script(obj)
        assert "Part::Sphere" in script
        assert "FreeCAD.Placement" in script
        assert "Vector(0, 100, 0)" in script

    def test_cone_with_placement_script(self):
        obj = {
            "name": "PlacedCone",
            "type": "Part::Cone",
            "params": {"radius1": 10, "radius2": 5, "height": 30, "placement": {"x": 20, "y": 20, "z": 0}},
        }
        script = _object_to_script(obj)
        assert "Part::Cone" in script
        assert "FreeCAD.Placement" in script
        assert "Vector(20, 20, 0)" in script

    def test_torus_with_placement_script(self):
        obj = {
            "name": "PlacedTor",
            "type": "Part::Torus",
            "params": {"radius1": 20, "radius2": 5, "placement": {"x": 0, "y": 0, "z": 100}},
        }
        script = _object_to_script(obj)
        assert "Part::Torus" in script
        assert "FreeCAD.Placement" in script
        assert "Vector(0, 0, 100)" in script

    def test_box_without_placement_no_placement_line(self):
        obj = {
            "name": "NoPlacement",
            "type": "Part::Box",
            "params": {"length": 10, "width": 10, "height": 10},
        }
        script = _object_to_script(obj)
        assert "FreeCAD.Placement" not in script


class TestPlacementCLI:
    """CLI tests for placement options on primitives."""

    def test_box_placement_json(self, tmp_dir):
        runner = CliRunner()
        path = os.path.join(tmp_dir, "place_test.json")
        runner.invoke(cli, ["--json", "project", "new", "-o", path])
        result = runner.invoke(cli, [
            "--json", "--project", path, "part", "box",
            "-l", "100", "-w", "50", "-H", "30",
            "--px", "10", "--py", "20", "--pz", "30",
        ])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["params"]["placement"] == {"x": 10.0, "y": 20.0, "z": 30.0}

    def test_cylinder_placement_json(self, tmp_dir):
        runner = CliRunner()
        path = os.path.join(tmp_dir, "cyl_place.json")
        runner.invoke(cli, ["--json", "project", "new", "-o", path])
        result = runner.invoke(cli, [
            "--json", "--project", path, "part", "cylinder",
            "-r", "10", "-H", "50", "--px", "5", "--pz", "100",
        ])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["params"]["placement"]["x"] == 5.0
        assert data["params"]["placement"]["z"] == 100.0

    def test_sphere_placement_json(self, tmp_dir):
        runner = CliRunner()
        path = os.path.join(tmp_dir, "sph_place.json")
        runner.invoke(cli, ["--json", "project", "new", "-o", path])
        result = runner.invoke(cli, [
            "--json", "--project", path, "part", "sphere",
            "-r", "25", "--py", "50",
        ])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["params"]["placement"]["y"] == 50.0

    def test_no_placement_when_all_zero(self, tmp_dir):
        runner = CliRunner()
        path = os.path.join(tmp_dir, "zero_place.json")
        runner.invoke(cli, ["--json", "project", "new", "-o", path])
        result = runner.invoke(cli, [
            "--json", "--project", path, "part", "box", "-l", "10",
        ])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "placement" not in data["params"]


class TestPartMove:
    """Tests for the part move command."""

    def test_move_object(self, tmp_dir):
        runner = CliRunner()
        path = os.path.join(tmp_dir, "move_test.json")
        runner.invoke(cli, ["--json", "project", "new", "-o", path])
        runner.invoke(cli, ["--json", "--project", path, "part", "box", "-n", "Target"])
        result = runner.invoke(cli, [
            "--json", "--project", path, "part", "move", "Target",
            "--px", "100", "--py", "200", "--pz", "300",
        ])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["params"]["placement"] == {"x": 100.0, "y": 200.0, "z": 300.0}

    def test_move_nonexistent(self, tmp_dir):
        runner = CliRunner()
        path = os.path.join(tmp_dir, "move_err.json")
        runner.invoke(cli, ["--json", "project", "new", "-o", path])
        result = runner.invoke(cli, [
            "--project", path, "part", "move", "NoSuch",
            "--px", "0", "--py", "0", "--pz", "0",
        ])
        assert result.exit_code != 0
        assert "not found" in result.output

    def test_move_persists(self, tmp_dir):
        runner = CliRunner()
        path = os.path.join(tmp_dir, "move_persist.json")
        runner.invoke(cli, ["--json", "project", "new", "-o", path])
        runner.invoke(cli, ["--json", "--project", path, "part", "box", "-n", "MovMe"])
        runner.invoke(cli, [
            "--json", "--project", path, "part", "move", "MovMe",
            "--px", "50", "--py", "0", "--pz", "75",
        ])
        # Reload and verify
        with open(path) as f:
            proj = json.load(f)
        obj = [o for o in proj["objects"] if o["name"] == "MovMe"][0]
        assert obj["params"]["placement"]["x"] == 50.0
        assert obj["params"]["placement"]["z"] == 75.0


# ── 2D projection tests ─────────────────────────────────────────────

class TestProjectObject2D:
    """Tests for _project_object_2d — 2D projection of 3D objects."""

    def test_box_front_elevation(self):
        obj = {"type": "Part::Box", "params": {"length": 904, "width": 504, "height": 1800}}
        result = _project_object_2d(obj, (0, -1, 0))
        assert result == (0, 0, 904, 1800)

    def test_box_side_elevation(self):
        obj = {"type": "Part::Box", "params": {"length": 904, "width": 504, "height": 1800}}
        result = _project_object_2d(obj, (1, 0, 0))
        assert result == (0, 0, 504, 1800)

    def test_box_plan_view(self):
        obj = {"type": "Part::Box", "params": {"length": 904, "width": 504, "height": 1800}}
        result = _project_object_2d(obj, (0, 0, 1))
        assert result == (0, 0, 904, 504)

    def test_box_with_placement(self):
        obj = {
            "type": "Part::Box",
            "params": {"length": 100, "width": 50, "height": 200, "placement": {"x": 10, "y": 20, "z": 30}},
        }
        result = _project_object_2d(obj, (0, -1, 0))
        assert result == (10, 30, 100, 200)

    def test_cylinder_front_elevation(self):
        obj = {"type": "Part::Cylinder", "params": {"radius": 25, "height": 100}}
        result = _project_object_2d(obj, (0, -1, 0))
        assert result == (0, 0, 50, 100)  # 2*r width, h height

    def test_cylinder_plan_view(self):
        obj = {"type": "Part::Cylinder", "params": {"radius": 25, "height": 100}}
        result = _project_object_2d(obj, (0, 0, 1))
        assert result == (0, 0, 50, 50)  # 2*r x 2*r from above

    def test_cylinder_with_placement(self):
        obj = {
            "type": "Part::Cylinder",
            "params": {"radius": 10, "height": 50, "placement": {"x": 5, "y": 0, "z": 100}},
        }
        result = _project_object_2d(obj, (0, -1, 0))
        assert result == (5, 100, 20, 50)

    def test_sphere_front_elevation(self):
        obj = {"type": "Part::Sphere", "params": {"radius": 30}}
        result = _project_object_2d(obj, (0, -1, 0))
        assert result == (0, 0, 60, 60)

    def test_cone_front_elevation(self):
        obj = {"type": "Part::Cone", "params": {"radius1": 20, "radius2": 5, "height": 40}}
        result = _project_object_2d(obj, (0, -1, 0))
        assert result == (0, 0, 40, 40)  # max(r1,r2)*2 width

    def test_unknown_type_returns_none(self):
        obj = {"type": "Part::Fuse", "params": {"base": "A", "tool": "B"}}
        result = _project_object_2d(obj, (0, -1, 0))
        assert result is None


# ── SVG export tests ─────────────────────────────────────────────────

class TestExportDrawingSVG:
    """Tests for the direct SVG export (no FreeCAD required)."""

    def _make_project_with_drawing(self):
        """Helper: project with box + cylinder + TechDraw page."""
        proj = create_project(name="SVGTest")
        proj["objects"].append({
            "name": "MainBox",
            "type": "Part::Box",
            "label": "MainBox",
            "params": {"length": 200, "width": 100, "height": 300},
        })
        proj["objects"].append({
            "name": "Hole",
            "type": "Part::Cylinder",
            "label": "Hole",
            "params": {"radius": 15, "height": 110, "placement": {"x": 100, "y": 50, "z": 0}},
        })
        page = create_drawing(proj, "Sheet1", template="A3_Landscape", scale=0.5)
        proj["objects"].append(page)  # Must add page to project objects
        add_view(page, "MainBox", "BoxFront", direction="front-elevation", x=100, y=150)
        add_view(page, "Hole", "HoleFront", direction="front-elevation", x=100, y=150)
        add_view(page, "MainBox", "BoxSide", direction="side-elevation", x=300, y=150)
        add_dimension(page, "BoxFront", dim_type="DistanceX", edge_ref="Edge0", dim_name="W200", x=100, y=20)
        add_dimension(page, "BoxFront", dim_type="DistanceY", edge_ref="Edge1", dim_name="H300", x=20, y=150)
        add_annotation(page, ["Test Drawing", "Scale: 1:2"], anno_name="Title", x=300, y=270)
        return proj

    def test_svg_export_creates_file(self, tmp_dir):
        proj = self._make_project_with_drawing()
        out = os.path.join(tmp_dir, "test.svg")
        result = export_drawing_svg(proj, "Sheet1", out)
        assert result["success"] is True
        assert os.path.exists(out)
        assert result["result"]["file_size"] > 0

    def test_svg_contains_rects(self, tmp_dir):
        proj = self._make_project_with_drawing()
        out = os.path.join(tmp_dir, "rects.svg")
        export_drawing_svg(proj, "Sheet1", out)
        with open(out) as f:
            svg = f.read()
        assert "<rect" in svg
        # At least: MainBox front + Hole front + MainBox side = 3+ rects (plus border)
        assert svg.count("<rect") >= 4

    def test_svg_contains_dimensions(self, tmp_dir):
        proj = self._make_project_with_drawing()
        out = os.path.join(tmp_dir, "dims.svg")
        export_drawing_svg(proj, "Sheet1", out)
        with open(out) as f:
            svg = f.read()
        assert "200 mm" in svg  # DistanceX of MainBox = 200
        assert "300 mm" in svg  # DistanceY of MainBox = 300

    def test_svg_contains_annotations(self, tmp_dir):
        proj = self._make_project_with_drawing()
        out = os.path.join(tmp_dir, "anno.svg")
        export_drawing_svg(proj, "Sheet1", out)
        with open(out) as f:
            svg = f.read()
        assert "Test Drawing" in svg
        assert "Scale: 1:2" in svg

    def test_svg_page_not_found(self, tmp_dir):
        proj = create_project(name="Empty")
        out = os.path.join(tmp_dir, "err.svg")
        result = export_drawing_svg(proj, "NoSuchPage", out)
        assert result["success"] is False

    def test_svg_viewbox_matches_template(self, tmp_dir):
        proj = self._make_project_with_drawing()
        out = os.path.join(tmp_dir, "vb.svg")
        export_drawing_svg(proj, "Sheet1", out)
        with open(out) as f:
            svg = f.read()
        assert 'viewBox="0 0 420 297"' in svg  # A3_Landscape


# ── View direction alias tests ───────────────────────────────────────

class TestViewDirectionAliases:
    """Tests for engineering-convention view direction aliases."""

    def test_front_elevation_alias(self):
        assert VIEW_DIRECTIONS["front-elevation"] == (0, -1, 0)

    def test_side_elevation_alias(self):
        assert VIEW_DIRECTIONS["side-elevation"] == (1, 0, 0)

    def test_plan_alias(self):
        assert VIEW_DIRECTIONS["plan"] == (0, 0, 1)

    def test_rear_elevation_alias(self):
        assert VIEW_DIRECTIONS["rear-elevation"] == (0, 1, 0)

    def test_original_names_preserved(self):
        assert VIEW_DIRECTIONS["front"] == (0, 0, 1)
        assert VIEW_DIRECTIONS["top"] == (0, -1, 0)
        assert VIEW_DIRECTIONS["right"] == (1, 0, 0)
