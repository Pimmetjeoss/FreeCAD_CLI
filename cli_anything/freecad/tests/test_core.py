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
    set_title_block,
    add_detail_view,
    add_centerline,
    add_hatch,
    add_leader_line,
    add_balloon,
    add_bom,
    add_cosmetic_edge,
    add_center_mark,
    add_clip_group,
    add_view_to_clip,
    add_geometric_tolerance,
    add_datum_symbol,
    add_surface_finish,
    _build_techdraw_script,
    _compute_dimension_value,
    _project_object_2d,
    export_drawing_svg,
    GDT_SYMBOLS,
    MATERIAL_CONDITIONS,
    SURFACE_FINISH_SYMBOLS,
    LINE_STYLES,
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

    def test_revolve_object_script(self):
        obj = {
            "name": "Rev",
            "type": "Part::Revolution",
            "params": {
                "source": "Sketch",
                "angle": 360,
                "axis_x": 0, "axis_y": 0, "axis_z": 1,
                "base_x": 0, "base_y": 0, "base_z": 0,
            },
        }
        script = _object_to_script(obj)
        assert "Part::Revolution" in script
        assert "'Sketch'" in script
        assert ".Axis = FreeCAD.Vector(0, 0, 1)" in script
        assert ".Base = FreeCAD.Vector(0, 0, 0)" in script
        assert ".Angle = 360" in script

    def test_revolve_partial_angle(self):
        obj = {
            "name": "HalfRev",
            "type": "Part::Revolution",
            "params": {
                "source": "Profile",
                "angle": 180,
                "axis_x": 1, "axis_y": 0, "axis_z": 0,
                "base_x": 10, "base_y": 0, "base_z": 0,
            },
        }
        script = _object_to_script(obj)
        assert "Part::Revolution" in script
        assert ".Angle = 180" in script
        assert ".Axis = FreeCAD.Vector(1, 0, 0)" in script
        assert ".Base = FreeCAD.Vector(10, 0, 0)" in script

    def test_sweep_object_script(self):
        obj = {
            "name": "Sweep1",
            "type": "Part::Sweep",
            "params": {"profile": "Circle", "path": "Helix", "solid": True, "frenet": True},
        }
        script = _object_to_script(obj)
        assert "Part::Sweep" in script
        assert "'Circle'" in script
        assert "'Helix'" in script
        assert ".Solid = True" in script
        assert ".Frenet = True" in script

    def test_sweep_shell_script(self):
        obj = {
            "name": "ShellSweep",
            "type": "Part::Sweep",
            "params": {"profile": "Rect", "path": "Spline", "solid": False, "frenet": False},
        }
        script = _object_to_script(obj)
        assert ".Solid = False" in script
        assert ".Frenet = False" in script

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

    def test_part_revolve_json(self, tmp_dir):
        runner = CliRunner()
        path = os.path.join(tmp_dir, "revolve_test.json")
        # Create project + sketch source
        runner.invoke(cli, ["--json", "project", "new", "-o", path])
        runner.invoke(cli, ["--json", "--project", path, "sketch", "new", "-n", "Profile"])
        result = runner.invoke(cli, [
            "--json", "--project", path, "part", "revolve", "Profile",
            "-a", "360", "--axis-z", "1",
        ])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["type"] == "Part::Revolution"
        assert data["params"]["source"] == "Profile"
        assert data["params"]["angle"] == 360

    def test_part_revolve_partial_json(self, tmp_dir):
        runner = CliRunner()
        path = os.path.join(tmp_dir, "revolve_half.json")
        runner.invoke(cli, ["--json", "project", "new", "-o", path])
        runner.invoke(cli, ["--json", "--project", path, "sketch", "new", "-n", "Prof"])
        result = runner.invoke(cli, [
            "--json", "--project", path, "part", "revolve", "Prof",
            "-a", "180", "--axis-x", "1", "--base-x", "5",
        ])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["params"]["angle"] == 180
        assert data["params"]["axis_x"] == 1
        assert data["params"]["base_x"] == 5

    def test_part_revolve_missing_source(self, tmp_dir):
        runner = CliRunner()
        path = os.path.join(tmp_dir, "revolve_err.json")
        runner.invoke(cli, ["--json", "project", "new", "-o", path])
        result = runner.invoke(cli, [
            "--json", "--project", path, "part", "revolve", "NonExistent",
        ])
        assert result.exit_code != 0

    def test_part_sweep_json(self, tmp_dir):
        runner = CliRunner()
        path = os.path.join(tmp_dir, "sweep_test.json")
        runner.invoke(cli, ["--json", "project", "new", "-o", path])
        runner.invoke(cli, ["--json", "--project", path, "sketch", "new", "-n", "Profile"])
        runner.invoke(cli, ["--json", "--project", path, "sketch", "new", "-n", "Path"])
        result = runner.invoke(cli, [
            "--json", "--project", path, "part", "sweep", "Profile", "Path",
        ])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["type"] == "Part::Sweep"
        assert data["params"]["profile"] == "Profile"
        assert data["params"]["path"] == "Path"
        assert data["params"]["solid"] is True

    def test_part_sweep_missing_profile(self, tmp_dir):
        runner = CliRunner()
        path = os.path.join(tmp_dir, "sweep_err.json")
        runner.invoke(cli, ["--json", "project", "new", "-o", path])
        result = runner.invoke(cli, [
            "--json", "--project", path, "part", "sweep", "Missing", "Also",
        ])
        assert result.exit_code != 0

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
        with open(out, encoding="utf-8") as f:
            svg = f.read()
        assert "<rect" in svg
        # At least: MainBox front + Hole front + MainBox side = 3+ rects (plus border)
        assert svg.count("<rect") >= 4

    def test_svg_contains_dimensions(self, tmp_dir):
        proj = self._make_project_with_drawing()
        out = os.path.join(tmp_dir, "dims.svg")
        export_drawing_svg(proj, "Sheet1", out)
        with open(out, encoding="utf-8") as f:
            svg = f.read()
        assert "200 mm" in svg  # DistanceX of MainBox = 200
        assert "300 mm" in svg  # DistanceY of MainBox = 300

    def test_svg_contains_annotations(self, tmp_dir):
        proj = self._make_project_with_drawing()
        out = os.path.join(tmp_dir, "anno.svg")
        export_drawing_svg(proj, "Sheet1", out)
        with open(out, encoding="utf-8") as f:
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
        with open(out, encoding="utf-8") as f:
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


# ── Title Block tests ───────────────────────────────────────────────

class TestTitleBlock:
    def test_set_title_block(self):
        page = create_drawing(create_project())
        fields = {"title": "Dressoir", "author": "Pim", "date": "2026-03-13",
                   "material": "Eiken", "scale": "1:10"}
        tb = set_title_block(page, fields)
        assert tb["type"] == "TitleBlock"
        assert tb["title"] == "Dressoir"
        assert tb["material"] == "Eiken"
        assert page["params"]["title_block"] is tb

    def test_set_title_block_partial(self):
        page = create_drawing(create_project())
        tb = set_title_block(page, {"title": "Only Title"})
        assert tb["title"] == "Only Title"
        assert "author" not in tb

    def test_set_title_block_overwrites(self):
        page = create_drawing(create_project())
        set_title_block(page, {"title": "First"})
        tb2 = set_title_block(page, {"title": "Second", "revision": "B"})
        assert page["params"]["title_block"]["title"] == "Second"
        assert tb2["revision"] == "B"

    def test_build_techdraw_script_title_block(self):
        proj = create_project(name="TBTest")
        proj["objects"].append({
            "name": "Box", "type": "Part::Box",
            "params": {"length": 20, "width": 15, "height": 10},
        })
        page = create_drawing(proj, page_name="P1")
        set_title_block(page, {"title": "Bouwtekening", "author": "Claude"})
        proj["objects"].append(page)
        script = _build_techdraw_script(proj, "P1")
        assert "Title Block" in script
        assert "'Bouwtekening'" in script


# ── Detail View tests ───────────────────────────────────────────────

class TestDetailView:
    def test_add_detail_view(self):
        page = create_drawing(create_project())
        detail = add_detail_view(page, "Box", "FrontView",
                                  detail_name="DetailA", anchor_x=10, anchor_y=5,
                                  radius=15, scale=3.0, x=300, y=60)
        assert detail["name"] == "DetailA"
        assert detail["type"] == "TechDraw::DrawViewDetail"
        assert detail["source"] == "Box"
        assert detail["base_view"] == "FrontView"
        assert detail["anchor_x"] == 10
        assert detail["anchor_y"] == 5
        assert detail["radius"] == 15
        assert detail["scale"] == 3.0
        assert len(page["params"]["views"]) == 1

    def test_detail_view_defaults(self):
        page = create_drawing(create_project())
        detail = add_detail_view(page, "Cyl", "V1")
        assert detail["radius"] == 20
        assert detail["scale"] == 2.0

    def test_build_techdraw_script_detail(self):
        proj = create_project(name="DetTest")
        proj["objects"].append({
            "name": "Box", "type": "Part::Box",
            "params": {"length": 20, "width": 15, "height": 10},
        })
        page = create_drawing(proj, page_name="P1")
        add_view(page, "Box", view_name="V1")
        add_detail_view(page, "Box", "V1", detail_name="DetailB", anchor_x=5, anchor_y=3)
        proj["objects"].append(page)
        script = _build_techdraw_script(proj, "P1")
        assert "TechDraw::DrawViewDetail" in script
        assert "'DetailB'" in script
        assert "AnchorPoint" in script
        assert "Radius" in script


# ── Centerline tests ────────────────────────────────────────────────

class TestCenterline:
    def test_add_centerline(self):
        page = create_drawing(create_project())
        cl = add_centerline(page, "FrontView", cl_name="CL1",
                            orientation="vertical", position=50,
                            extent_low=-100, extent_high=100)
        assert cl["name"] == "CL1"
        assert cl["type"] == "TechDraw::CenterLine"
        assert cl["view"] == "FrontView"
        assert cl["orientation"] == "vertical"
        assert cl["position"] == 50
        assert page["params"]["centerlines"] == [cl]

    def test_add_centerline_horizontal(self):
        page = create_drawing(create_project())
        cl = add_centerline(page, "V1", orientation="horizontal", position=25)
        assert cl["orientation"] == "horizontal"
        assert cl["position"] == 25

    def test_multiple_centerlines(self):
        page = create_drawing(create_project())
        add_centerline(page, "V1", cl_name="CL1")
        add_centerline(page, "V1", cl_name="CL2")
        assert len(page["params"]["centerlines"]) == 2


# ── Hatch tests ─────────────────────────────────────────────────────

class TestHatch:
    def test_add_hatch(self):
        page = create_drawing(create_project())
        h = add_hatch(page, "Section1", face_ref="Face0",
                      hatch_name="H1", pattern="ansi31",
                      scale=1.5, rotation=45, color="#FF0000")
        assert h["name"] == "H1"
        assert h["type"] == "TechDraw::DrawHatch"
        assert h["view"] == "Section1"
        assert h["face_ref"] == "Face0"
        assert h["pattern"] == "ansi31"
        assert h["scale"] == 1.5
        assert h["rotation"] == 45
        assert h["color"] == "#FF0000"
        assert page["params"]["hatches"] == [h]

    def test_hatch_defaults(self):
        page = create_drawing(create_project())
        h = add_hatch(page, "V1")
        assert h["pattern"] == "ansi31"
        assert h["scale"] == 1.0
        assert h["rotation"] == 0
        assert h["color"] == "#000000"


# ── Leader Line tests ───────────────────────────────────────────────

class TestLeaderLine:
    def test_add_leader_line(self):
        page = create_drawing(create_project())
        ld = add_leader_line(page, "V1", leader_name="LD1",
                             start_x=10, start_y=20, end_x=60, end_y=70,
                             text="Detail A", arrow_style="filled")
        assert ld["name"] == "LD1"
        assert ld["type"] == "TechDraw::DrawLeaderLine"
        assert ld["view"] == "V1"
        assert ld["start_x"] == 10
        assert ld["end_x"] == 60
        assert ld["text"] == "Detail A"
        assert ld["arrow_style"] == "filled"
        assert page["params"]["leaders"] == [ld]

    def test_leader_line_defaults(self):
        page = create_drawing(create_project())
        ld = add_leader_line(page, "V1")
        assert ld["text"] == ""
        assert ld["arrow_style"] == "filled"


# ── Balloon tests ───────────────────────────────────────────────────

class TestBalloon:
    def test_add_balloon(self):
        page = create_drawing(create_project())
        bl = add_balloon(page, "V1", balloon_name="BL1",
                         origin_x=10, origin_y=20, text="3",
                         shape="circular", x=80, y=30)
        assert bl["name"] == "BL1"
        assert bl["type"] == "TechDraw::DrawViewBalloon"
        assert bl["view"] == "V1"
        assert bl["text"] == "3"
        assert bl["shape"] == "circular"
        assert bl["x"] == 80
        assert bl["y"] == 30
        assert page["params"]["balloons"] == [bl]

    def test_balloon_shapes(self):
        page = create_drawing(create_project())
        for shape in ["circular", "rectangular", "triangle", "hexagon", "none"]:
            bl = add_balloon(page, "V1", balloon_name=f"BL_{shape}", shape=shape)
            assert bl["shape"] == shape

    def test_multiple_balloons(self):
        page = create_drawing(create_project())
        add_balloon(page, "V1", balloon_name="BL1", text="1")
        add_balloon(page, "V1", balloon_name="BL2", text="2")
        add_balloon(page, "V1", balloon_name="BL3", text="3")
        assert len(page["params"]["balloons"]) == 3


# ── BOM tests ───────────────────────────────────────────────────────

class TestBOM:
    def test_add_bom(self):
        page = create_drawing(create_project())
        items = [
            {"item": "1", "name": "Zijpaneel", "material": "Eiken", "quantity": "2"},
            {"item": "2", "name": "Bovenpaneel", "material": "Eiken", "quantity": "1"},
        ]
        bom = add_bom(page, items, bom_name="BOM1", x=150, y=200)
        assert bom["name"] == "BOM1"
        assert bom["type"] == "BOM"
        assert len(bom["items"]) == 2
        assert bom["columns"] == ["item", "name", "material", "quantity"]
        assert page["params"]["bom"] == [bom]

    def test_bom_custom_columns(self):
        page = create_drawing(create_project())
        bom = add_bom(page, [], columns=["pos", "description", "qty"])
        assert bom["columns"] == ["pos", "description", "qty"]

    def test_bom_empty_items(self):
        page = create_drawing(create_project())
        bom = add_bom(page, [])
        assert bom["items"] == []


# ── CLI tests for new TechDraw commands ─────────────────────────────

class TestTitleBlockCLI:
    def test_title_block_json(self, tmp_dir):
        runner = CliRunner()
        path = os.path.join(tmp_dir, "tb_test.json")
        runner.invoke(cli, ["--json", "project", "new", "-o", path])
        runner.invoke(cli, ["--json", "--project", path, "techdraw", "page", "-n", "P1"])
        result = runner.invoke(cli, [
            "--json", "--project", path, "techdraw", "title-block", "P1",
            "--title", "Bouwtekening Dressoir",
            "--author", "Pim",
            "--material", "Eiken massief",
            "--scale", "1:10",
        ])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["type"] == "TitleBlock"
        assert data["title"] == "Bouwtekening Dressoir"
        assert data["material"] == "Eiken massief"

    def test_title_block_no_fields(self, tmp_dir):
        runner = CliRunner()
        path = os.path.join(tmp_dir, "tb_err.json")
        runner.invoke(cli, ["--json", "project", "new", "-o", path])
        runner.invoke(cli, ["--json", "--project", path, "techdraw", "page", "-n", "P1"])
        result = runner.invoke(cli, ["--project", path, "techdraw", "title-block", "P1"])
        assert result.exit_code != 0
        assert "at least one" in result.output.lower()


class TestDetailViewCLI:
    def test_detail_view_json(self, tmp_dir):
        runner = CliRunner()
        path = os.path.join(tmp_dir, "det_test.json")
        runner.invoke(cli, ["--json", "project", "new", "-o", path])
        runner.invoke(cli, ["--json", "--project", path, "part", "box", "-n", "Box"])
        runner.invoke(cli, ["--json", "--project", path, "techdraw", "page", "-n", "P1"])
        runner.invoke(cli, ["--json", "--project", path, "techdraw", "view", "P1", "Box", "-n", "V1"])
        result = runner.invoke(cli, [
            "--json", "--project", path, "techdraw", "detail",
            "P1", "Box", "V1", "--ax", "10", "--ay", "5", "-r", "15", "-s", "3.0",
        ])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["type"] == "TechDraw::DrawViewDetail"
        assert data["anchor_x"] == 10
        assert data["scale"] == 3.0


class TestCenterlineCLI:
    def test_centerline_json(self, tmp_dir):
        runner = CliRunner()
        path = os.path.join(tmp_dir, "cl_test.json")
        runner.invoke(cli, ["--json", "project", "new", "-o", path])
        runner.invoke(cli, ["--json", "--project", path, "part", "box", "-n", "Box"])
        runner.invoke(cli, ["--json", "--project", path, "techdraw", "page", "-n", "P1"])
        runner.invoke(cli, ["--json", "--project", path, "techdraw", "view", "P1", "Box", "-n", "V1"])
        result = runner.invoke(cli, [
            "--json", "--project", path, "techdraw", "centerline",
            "P1", "V1", "-o", "vertical", "-p", "50",
        ])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["type"] == "TechDraw::CenterLine"
        assert data["orientation"] == "vertical"
        assert data["position"] == 50


class TestHatchCLI:
    def test_hatch_json(self, tmp_dir):
        runner = CliRunner()
        path = os.path.join(tmp_dir, "h_test.json")
        runner.invoke(cli, ["--json", "project", "new", "-o", path])
        runner.invoke(cli, ["--json", "--project", path, "part", "box", "-n", "Box"])
        runner.invoke(cli, ["--json", "--project", path, "techdraw", "page", "-n", "P1"])
        runner.invoke(cli, ["--json", "--project", path, "techdraw", "view", "P1", "Box", "-n", "V1"])
        result = runner.invoke(cli, [
            "--json", "--project", path, "techdraw", "hatch",
            "P1", "V1", "-f", "Face0", "-p", "ansi32",
        ])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["type"] == "TechDraw::DrawHatch"
        assert data["pattern"] == "ansi32"


class TestLeaderCLI:
    def test_leader_json(self, tmp_dir):
        runner = CliRunner()
        path = os.path.join(tmp_dir, "ld_test.json")
        runner.invoke(cli, ["--json", "project", "new", "-o", path])
        runner.invoke(cli, ["--json", "--project", path, "part", "box", "-n", "Box"])
        runner.invoke(cli, ["--json", "--project", path, "techdraw", "page", "-n", "P1"])
        runner.invoke(cli, ["--json", "--project", path, "techdraw", "view", "P1", "Box", "-n", "V1"])
        result = runner.invoke(cli, [
            "--json", "--project", path, "techdraw", "leader",
            "P1", "V1", "--sx", "10", "--sy", "20", "--ex", "60", "--ey", "70",
            "-t", "Zie detail A",
        ])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["type"] == "TechDraw::DrawLeaderLine"
        assert data["text"] == "Zie detail A"


class TestBalloonCLI:
    def test_balloon_json(self, tmp_dir):
        runner = CliRunner()
        path = os.path.join(tmp_dir, "bl_test.json")
        runner.invoke(cli, ["--json", "project", "new", "-o", path])
        runner.invoke(cli, ["--json", "--project", path, "part", "box", "-n", "Box"])
        runner.invoke(cli, ["--json", "--project", path, "techdraw", "page", "-n", "P1"])
        runner.invoke(cli, ["--json", "--project", path, "techdraw", "view", "P1", "Box", "-n", "V1"])
        result = runner.invoke(cli, [
            "--json", "--project", path, "techdraw", "balloon",
            "P1", "V1", "-t", "5", "-s", "circular", "-x", "80", "-y", "30",
        ])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["type"] == "TechDraw::DrawViewBalloon"
        assert data["text"] == "5"
        assert data["shape"] == "circular"


class TestBOMCLI:
    def test_bom_json(self, tmp_dir):
        runner = CliRunner()
        path = os.path.join(tmp_dir, "bom_test.json")
        runner.invoke(cli, ["--json", "project", "new", "-o", path])
        runner.invoke(cli, ["--json", "--project", path, "techdraw", "page", "-n", "P1"])
        result = runner.invoke(cli, [
            "--json", "--project", path, "techdraw", "bom", "P1",
            "-i", "item=1,name=Zijpaneel,material=Eiken,quantity=2",
            "-i", "item=2,name=Bovenpaneel,material=Eiken,quantity=1",
        ])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["type"] == "BOM"
        assert len(data["items"]) == 2
        assert data["items"][0]["name"] == "Zijpaneel"

    def test_bom_custom_columns_json(self, tmp_dir):
        runner = CliRunner()
        path = os.path.join(tmp_dir, "bom_cols.json")
        runner.invoke(cli, ["--json", "project", "new", "-o", path])
        runner.invoke(cli, ["--json", "--project", path, "techdraw", "page", "-n", "P1"])
        result = runner.invoke(cli, [
            "--json", "--project", path, "techdraw", "bom", "P1",
            "--columns", "pos,omschrijving,stuks",
            "-i", "pos=1,omschrijving=Plank,stuks=4",
        ])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["columns"] == ["pos", "omschrijving", "stuks"]


# ── SVG export with new features tests ──────────────────────────────

class TestExportSVGNewFeatures:
    def _make_project_with_all_features(self):
        proj = create_project(name="FullTest")
        proj["objects"].append({
            "name": "MainBox", "type": "Part::Box", "label": "MainBox",
            "params": {"length": 200, "width": 100, "height": 300},
        })
        page = create_drawing(proj, "Sheet1", template="A3_Landscape", scale=0.5)
        proj["objects"].append(page)
        add_view(page, "MainBox", "BoxFront", direction="front-elevation", x=100, y=150)
        set_title_block(page, {"title": "Test Drawing", "author": "Claude", "material": "Steel"})
        add_centerline(page, "BoxFront", cl_name="CL1", orientation="vertical", position=0)
        add_hatch(page, "BoxFront", face_ref="Face0", hatch_name="H1")
        add_leader_line(page, "BoxFront", leader_name="LD1", start_x=10, start_y=20,
                        end_x=60, end_y=70, text="See detail")
        add_balloon(page, "BoxFront", balloon_name="BL1", text="1", x=80, y=30)
        add_bom(page, [
            {"item": "1", "name": "Box", "material": "Steel", "quantity": "1"},
        ], bom_name="BOM1", x=300, y=250)
        return proj

    def test_svg_has_title_block(self, tmp_dir):
        proj = self._make_project_with_all_features()
        out = os.path.join(tmp_dir, "full.svg")
        result = export_drawing_svg(proj, "Sheet1", out)
        assert result["success"] is True
        with open(out, encoding="utf-8") as f:
            svg = f.read()
        assert "Test Drawing" in svg
        assert "Claude" in svg

    def test_svg_has_centerline(self, tmp_dir):
        proj = self._make_project_with_all_features()
        out = os.path.join(tmp_dir, "cl.svg")
        export_drawing_svg(proj, "Sheet1", out)
        with open(out, encoding="utf-8") as f:
            svg = f.read()
        assert "stroke-dasharray" in svg

    def test_svg_has_hatch(self, tmp_dir):
        proj = self._make_project_with_all_features()
        out = os.path.join(tmp_dir, "hatch.svg")
        export_drawing_svg(proj, "Sheet1", out)
        with open(out, encoding="utf-8") as f:
            svg = f.read()
        # Hatch generates many lines with opacity
        assert 'opacity="0.5"' in svg

    def test_svg_has_leader(self, tmp_dir):
        proj = self._make_project_with_all_features()
        out = os.path.join(tmp_dir, "leader.svg")
        export_drawing_svg(proj, "Sheet1", out)
        with open(out, encoding="utf-8") as f:
            svg = f.read()
        assert "See detail" in svg

    def test_svg_has_balloon(self, tmp_dir):
        proj = self._make_project_with_all_features()
        out = os.path.join(tmp_dir, "balloon.svg")
        export_drawing_svg(proj, "Sheet1", out)
        with open(out, encoding="utf-8") as f:
            svg = f.read()
        assert "<circle" in svg
        assert 'text-anchor="middle"' in svg

    def test_svg_has_bom_table(self, tmp_dir):
        proj = self._make_project_with_all_features()
        out = os.path.join(tmp_dir, "bom.svg")
        export_drawing_svg(proj, "Sheet1", out)
        with open(out, encoding="utf-8") as f:
            svg = f.read()
        assert "ITEM" in svg
        assert "NAME" in svg
        assert "Steel" in svg

    def test_svg_list_shows_new_types(self, tmp_dir):
        runner = CliRunner()
        path = os.path.join(tmp_dir, "list_new.json")
        runner.invoke(cli, ["--json", "project", "new", "-o", path])
        runner.invoke(cli, ["--json", "--project", path, "part", "box", "-n", "Box"])
        runner.invoke(cli, ["--json", "--project", path, "techdraw", "page", "-n", "P1"])
        runner.invoke(cli, ["--json", "--project", path, "techdraw", "view", "P1", "Box", "-n", "V1"])
        runner.invoke(cli, ["--json", "--project", path, "techdraw", "centerline", "P1", "V1"])
        runner.invoke(cli, ["--json", "--project", path, "techdraw", "balloon", "P1", "V1", "-t", "1"])
        result = runner.invoke(cli, ["--json", "--project", path, "techdraw", "list", "P1"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data["centerlines"]) == 1
        assert len(data["balloons"]) == 1


# ── Dimension types & format tests ───────────────────────────────────

class TestDimensionTypes:
    """Tests for all dimension types: Distance, DistanceX, DistanceY, Radius, Diameter, Angle."""

    def test_add_dimension_distance_x(self):
        page = create_drawing(create_project())
        dim = add_dimension(page, "V1", dim_type="DistanceX", edge_ref="Edge0")
        assert dim["dim_type"] == "DistanceX"
        assert dim["prefix"] == ""
        assert dim["suffix"] == ""

    def test_add_dimension_distance_y(self):
        page = create_drawing(create_project())
        dim = add_dimension(page, "V1", dim_type="DistanceY", edge_ref="Edge1")
        assert dim["dim_type"] == "DistanceY"

    def test_add_dimension_radius_auto_prefix(self):
        page = create_drawing(create_project())
        dim = add_dimension(page, "V1", dim_type="Radius", edge_ref="Edge3")
        assert dim["dim_type"] == "Radius"
        assert dim["prefix"] == "R"

    def test_add_dimension_diameter_auto_prefix(self):
        page = create_drawing(create_project())
        dim = add_dimension(page, "V1", dim_type="Diameter", edge_ref="Edge2")
        assert dim["dim_type"] == "Diameter"
        assert dim["prefix"] == "∅"

    def test_add_dimension_angle(self):
        page = create_drawing(create_project())
        dim = add_dimension(page, "V1", dim_type="Angle",
                            edge_ref="Edge0", edge_ref2="Edge1")
        assert dim["dim_type"] == "Angle"
        assert dim["references"] == ["Edge0", "Edge1"]

    def test_add_dimension_custom_prefix_overrides_auto(self):
        """User-supplied prefix overrides auto R/∅."""
        page = create_drawing(create_project())
        dim = add_dimension(page, "V1", dim_type="Radius", prefix="2xR")
        assert dim["prefix"] == "2xR"

    def test_add_dimension_suffix(self):
        page = create_drawing(create_project())
        dim = add_dimension(page, "V1", dim_type="Diameter", suffix=" H7")
        assert dim["suffix"] == " H7"
        assert dim["prefix"] == "∅"

    def test_add_dimension_tolerance(self):
        page = create_drawing(create_project())
        dim = add_dimension(page, "V1", dim_type="Distance",
                            tolerance_upper=0.1, tolerance_lower=-0.05)
        assert dim["tolerance_upper"] == 0.1
        assert dim["tolerance_lower"] == -0.05

    def test_add_dimension_no_tolerance_omits_keys(self):
        page = create_drawing(create_project())
        dim = add_dimension(page, "V1", dim_type="Distance")
        assert "tolerance_upper" not in dim
        assert "tolerance_lower" not in dim

    def test_dimension_edge_ref2_none_when_not_angle(self):
        page = create_drawing(create_project())
        dim = add_dimension(page, "V1", dim_type="Distance")
        assert dim["references"] == ["Edge0"]  # Only one ref

    def test_all_six_types_accepted(self):
        """All six dimension types can be created without error."""
        page = create_drawing(create_project())
        for dt in ["Distance", "DistanceX", "DistanceY", "Radius", "Diameter", "Angle"]:
            dim = add_dimension(page, "V1", dim_type=dt, dim_name=f"D_{dt}")
            assert dim["dim_type"] == dt
        assert len(page["params"]["dimensions"]) == 6


class TestDimensionScript:
    """Tests for _build_techdraw_script dimension rendering."""

    def _make_project_with_dims(self):
        proj = create_project(name="DimScript")
        proj["objects"].append({
            "name": "Box", "type": "Part::Box",
            "params": {"length": 50, "width": 30, "height": 20},
        })
        page = create_drawing(proj, "Sheet1")
        add_view(page, "Box", "V1", direction="front")
        proj["objects"].append(page)
        return proj, page

    def test_script_has_distance_type(self):
        proj, page = self._make_project_with_dims()
        add_dimension(page, "V1", dim_type="Distance")
        script = _build_techdraw_script(proj, "Sheet1")
        assert "'Distance'" in script

    def test_script_has_radius_type(self):
        proj, page = self._make_project_with_dims()
        add_dimension(page, "V1", dim_type="Radius")
        script = _build_techdraw_script(proj, "Sheet1")
        assert "'Radius'" in script

    def test_script_has_diameter_type(self):
        proj, page = self._make_project_with_dims()
        add_dimension(page, "V1", dim_type="Diameter")
        script = _build_techdraw_script(proj, "Sheet1")
        assert "'Diameter'" in script

    def test_script_has_angle_type(self):
        proj, page = self._make_project_with_dims()
        add_dimension(page, "V1", dim_type="Angle", edge_ref="Edge0", edge_ref2="Edge1")
        script = _build_techdraw_script(proj, "Sheet1")
        assert "'Angle'" in script
        # Both edge refs should be in References2D
        assert "'Edge0'" in script
        assert "'Edge1'" in script

    def test_script_prefix_in_format_spec(self):
        proj, page = self._make_project_with_dims()
        add_dimension(page, "V1", dim_type="Diameter", suffix=" H7")
        script = _build_techdraw_script(proj, "Sheet1")
        # FormatSpec should contain the prefix and suffix
        assert "∅" in script
        assert "H7" in script

    def test_script_tolerance_fields(self):
        proj, page = self._make_project_with_dims()
        add_dimension(page, "V1", dim_type="Distance",
                      tolerance_upper=0.1, tolerance_lower=-0.05)
        script = _build_techdraw_script(proj, "Sheet1")
        assert "FormatSpecOverTolerance" in script
        assert "FormatSpecUnderTolerance" in script

    def test_script_no_tolerance_when_none(self):
        proj, page = self._make_project_with_dims()
        add_dimension(page, "V1", dim_type="Distance")
        script = _build_techdraw_script(proj, "Sheet1")
        assert "FormatSpecOverTolerance" not in script


class TestComputeDimensionValue:
    """Tests for _compute_dimension_value helper."""

    def _make_views_and_objects(self, obj_type="Part::Box", params=None):
        if params is None:
            params = {"length": 100, "width": 60, "height": 40}
        obj = {"name": "Obj", "type": obj_type, "params": params}
        views = [{
            "name": "V1", "type": "TechDraw::DrawViewPart",
            "source": "Obj", "direction": (0, -1, 0),  # front elevation
        }]
        obj_map = {"Obj": obj}
        return views, obj_map

    def test_distance_x_box(self):
        views, obj_map = self._make_views_and_objects()
        val = _compute_dimension_value("DistanceX", "V1", views, obj_map)
        assert val == 100  # length (X dimension in front elevation)

    def test_distance_y_box(self):
        views, obj_map = self._make_views_and_objects()
        val = _compute_dimension_value("DistanceY", "V1", views, obj_map)
        assert val == 40  # height (Z dimension in front elevation)

    def test_radius_cylinder(self):
        views, obj_map = self._make_views_and_objects(
            "Part::Cylinder", {"radius": 15, "height": 50})
        val = _compute_dimension_value("Radius", "V1", views, obj_map)
        assert val == 15

    def test_diameter_cylinder(self):
        views, obj_map = self._make_views_and_objects(
            "Part::Cylinder", {"radius": 15, "height": 50})
        val = _compute_dimension_value("Diameter", "V1", views, obj_map)
        assert val == 30

    def test_radius_sphere(self):
        views, obj_map = self._make_views_and_objects(
            "Part::Sphere", {"radius": 25})
        val = _compute_dimension_value("Radius", "V1", views, obj_map)
        assert val == 25

    def test_diameter_sphere(self):
        views, obj_map = self._make_views_and_objects(
            "Part::Sphere", {"radius": 25})
        val = _compute_dimension_value("Diameter", "V1", views, obj_map)
        assert val == 50

    def test_angle_box_is_90(self):
        views, obj_map = self._make_views_and_objects()
        val = _compute_dimension_value("Angle", "V1", views, obj_map)
        assert val == 90.0

    def test_angle_cone(self):
        import math
        views, obj_map = self._make_views_and_objects(
            "Part::Cone", {"radius1": 10, "radius2": 5, "height": 20})
        val = _compute_dimension_value("Angle", "V1", views, obj_map)
        expected = math.degrees(math.atan2(5, 20))
        assert abs(val - expected) < 0.01

    def test_unknown_view_returns_none(self):
        views, obj_map = self._make_views_and_objects()
        val = _compute_dimension_value("DistanceX", "NoSuchView", views, obj_map)
        assert val is None

    def test_radius_unknown_type_returns_none(self):
        """Radius on a Part::Box returns None (no radius concept)."""
        views, obj_map = self._make_views_and_objects()
        val = _compute_dimension_value("Radius", "V1", views, obj_map)
        assert val is None


class TestDimensionSVGExport:
    """Tests for SVG export with all dimension types."""

    def _make_box_drawing_with_dim(self, dim_type, **kwargs):
        proj = create_project(name="DimSVG")
        proj["objects"].append({
            "name": "Box", "type": "Part::Box",
            "params": {"length": 80, "width": 50, "height": 30},
        })
        page = create_drawing(proj, "Sheet1", template="A4_Landscape", scale=1.0)
        proj["objects"].append(page)
        add_view(page, "Box", "V1", direction="front-elevation", x=150, y=100)
        add_dimension(page, "V1", dim_type=dim_type, dim_name="TestDim",
                      x=150, y=30, **kwargs)
        return proj

    def _make_cylinder_drawing_with_dim(self, dim_type, **kwargs):
        proj = create_project(name="CylDimSVG")
        proj["objects"].append({
            "name": "Cyl", "type": "Part::Cylinder",
            "params": {"radius": 12, "height": 40},
        })
        page = create_drawing(proj, "Sheet1", template="A4_Landscape", scale=1.0)
        proj["objects"].append(page)
        add_view(page, "Cyl", "V1", direction="front-elevation", x=150, y=100)
        add_dimension(page, "V1", dim_type=dim_type, dim_name="TestDim",
                      x=150, y=30, **kwargs)
        return proj

    def test_svg_distance_x_value(self, tmp_dir):
        proj = self._make_box_drawing_with_dim("DistanceX")
        out = os.path.join(tmp_dir, "dx.svg")
        export_drawing_svg(proj, "Sheet1", out)
        with open(out, encoding="utf-8") as f:
            svg = f.read()
        assert "80" in svg  # length = 80

    def test_svg_distance_y_value(self, tmp_dir):
        proj = self._make_box_drawing_with_dim("DistanceY")
        out = os.path.join(tmp_dir, "dy.svg")
        export_drawing_svg(proj, "Sheet1", out)
        with open(out, encoding="utf-8") as f:
            svg = f.read()
        assert "30" in svg  # height = 30

    def test_svg_radius_with_prefix(self, tmp_dir):
        proj = self._make_cylinder_drawing_with_dim("Radius")
        out = os.path.join(tmp_dir, "rad.svg")
        export_drawing_svg(proj, "Sheet1", out)
        with open(out, encoding="utf-8") as f:
            svg = f.read()
        assert "R12" in svg  # auto-prefix R + radius 12

    def test_svg_diameter_with_prefix(self, tmp_dir):
        proj = self._make_cylinder_drawing_with_dim("Diameter")
        out = os.path.join(tmp_dir, "dia.svg")
        export_drawing_svg(proj, "Sheet1", out)
        with open(out, encoding="utf-8") as f:
            svg = f.read()
        assert "∅24" in svg  # auto-prefix ∅ + diameter 24

    def test_svg_dimension_with_suffix(self, tmp_dir):
        proj = self._make_cylinder_drawing_with_dim("Diameter", suffix=" H7")
        out = os.path.join(tmp_dir, "suffix.svg")
        export_drawing_svg(proj, "Sheet1", out)
        with open(out, encoding="utf-8") as f:
            svg = f.read()
        assert "∅24 H7" in svg

    def test_svg_dimension_with_tolerance(self, tmp_dir):
        proj = self._make_box_drawing_with_dim(
            "DistanceX", tolerance_upper=0.1, tolerance_lower=-0.05)
        out = os.path.join(tmp_dir, "tol.svg")
        export_drawing_svg(proj, "Sheet1", out)
        with open(out, encoding="utf-8") as f:
            svg = f.read()
        assert "+0.1" in svg
        assert "-0.05" in svg

    def test_svg_angle_box_90(self, tmp_dir):
        proj = self._make_box_drawing_with_dim("Angle")
        out = os.path.join(tmp_dir, "angle.svg")
        export_drawing_svg(proj, "Sheet1", out)
        with open(out, encoding="utf-8") as f:
            svg = f.read()
        assert "90" in svg


class TestDimensionCLI:
    """CLI tests for all dimension types and new options."""

    def test_cli_dimension_radius(self, tmp_dir):
        runner = CliRunner()
        path = os.path.join(tmp_dir, "cli_rad.json")
        runner.invoke(cli, ["--json", "project", "new", "-o", path])
        runner.invoke(cli, ["--json", "--project", path, "part", "cylinder", "-n", "C1"])
        runner.invoke(cli, ["--json", "--project", path, "techdraw", "page", "-n", "P1"])
        runner.invoke(cli, ["--json", "--project", path, "techdraw", "view", "P1", "C1", "-n", "V1"])
        result = runner.invoke(cli, [
            "--json", "--project", path, "techdraw", "dimension",
            "P1", "V1", "-t", "Radius", "-e", "Edge0",
        ])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["dim_type"] == "Radius"
        assert data["prefix"] == "R"

    def test_cli_dimension_diameter(self, tmp_dir):
        runner = CliRunner()
        path = os.path.join(tmp_dir, "cli_dia.json")
        runner.invoke(cli, ["--json", "project", "new", "-o", path])
        runner.invoke(cli, ["--json", "--project", path, "part", "box", "-n", "B"])
        runner.invoke(cli, ["--json", "--project", path, "techdraw", "page", "-n", "P1"])
        runner.invoke(cli, ["--json", "--project", path, "techdraw", "view", "P1", "B", "-n", "V1"])
        result = runner.invoke(cli, [
            "--json", "--project", path, "techdraw", "dimension",
            "P1", "V1", "-t", "Diameter",
        ])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["dim_type"] == "Diameter"
        assert data["prefix"] == "∅"

    def test_cli_dimension_angle_with_edge2(self, tmp_dir):
        runner = CliRunner()
        path = os.path.join(tmp_dir, "cli_angle.json")
        runner.invoke(cli, ["--json", "project", "new", "-o", path])
        runner.invoke(cli, ["--json", "--project", path, "part", "box", "-n", "B"])
        runner.invoke(cli, ["--json", "--project", path, "techdraw", "page", "-n", "P1"])
        runner.invoke(cli, ["--json", "--project", path, "techdraw", "view", "P1", "B", "-n", "V1"])
        result = runner.invoke(cli, [
            "--json", "--project", path, "techdraw", "dimension",
            "P1", "V1", "-t", "Angle", "-e", "Edge0", "-e2", "Edge1",
        ])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["dim_type"] == "Angle"
        assert data["references"] == ["Edge0", "Edge1"]

    def test_cli_dimension_with_tolerance(self, tmp_dir):
        runner = CliRunner()
        path = os.path.join(tmp_dir, "cli_tol.json")
        runner.invoke(cli, ["--json", "project", "new", "-o", path])
        runner.invoke(cli, ["--json", "--project", path, "part", "box", "-n", "B"])
        runner.invoke(cli, ["--json", "--project", path, "techdraw", "page", "-n", "P1"])
        runner.invoke(cli, ["--json", "--project", path, "techdraw", "view", "P1", "B", "-n", "V1"])
        result = runner.invoke(cli, [
            "--json", "--project", path, "techdraw", "dimension",
            "P1", "V1", "-t", "Distance", "--tol-upper", "0.1", "--tol-lower", "-0.05",
        ])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["tolerance_upper"] == 0.1
        assert data["tolerance_lower"] == -0.05

    def test_cli_dimension_with_suffix(self, tmp_dir):
        runner = CliRunner()
        path = os.path.join(tmp_dir, "cli_suffix.json")
        runner.invoke(cli, ["--json", "project", "new", "-o", path])
        runner.invoke(cli, ["--json", "--project", path, "part", "box", "-n", "B"])
        runner.invoke(cli, ["--json", "--project", path, "techdraw", "page", "-n", "P1"])
        runner.invoke(cli, ["--json", "--project", path, "techdraw", "view", "P1", "B", "-n", "V1"])
        result = runner.invoke(cli, [
            "--json", "--project", path, "techdraw", "dimension",
            "P1", "V1", "-t", "Diameter", "--suffix", " THRU",
        ])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["suffix"] == " THRU"
        assert data["prefix"] == "∅"

    def test_cli_all_six_dim_types(self, tmp_dir):
        """All six dimension types accepted by CLI."""
        runner = CliRunner()
        path = os.path.join(tmp_dir, "cli_all6.json")
        runner.invoke(cli, ["--json", "project", "new", "-o", path])
        runner.invoke(cli, ["--json", "--project", path, "part", "box", "-n", "B"])
        runner.invoke(cli, ["--json", "--project", path, "techdraw", "page", "-n", "P1"])
        runner.invoke(cli, ["--json", "--project", path, "techdraw", "view", "P1", "B", "-n", "V1"])
        for dt in ["Distance", "DistanceX", "DistanceY", "Radius", "Diameter", "Angle"]:
            result = runner.invoke(cli, [
                "--json", "--project", path, "techdraw", "dimension",
                "P1", "V1", "-t", dt, "-n", f"D_{dt}",
            ])
            assert result.exit_code == 0, f"Failed for type {dt}: {result.output}"
            data = json.loads(result.output)
            assert data["dim_type"] == dt


# ── Cosmetic Edge & Center Mark tests ────────────────────────────────

class TestCosmeticEdge:
    """Tests for cosmetic edge (artificial line) functionality."""

    def test_add_cosmetic_edge_defaults(self):
        page = create_drawing(create_project())
        edge = add_cosmetic_edge(page, "V1")
        assert edge["type"] == "TechDraw::CosmeticEdge"
        assert edge["view"] == "V1"
        assert edge["x1"] == 0
        assert edge["y1"] == 0
        assert edge["x2"] == 50
        assert edge["y2"] == 0
        assert edge["style"] == "dashed"
        assert edge["color"] == "#000000"
        assert edge["weight"] == 0.2
        assert len(page["params"]["cosmetic_edges"]) == 1

    def test_add_cosmetic_edge_custom(self):
        page = create_drawing(create_project())
        edge = add_cosmetic_edge(
            page, "V1", x1=-20, y1=10, x2=20, y2=10,
            edge_name="FoldLine", style="dashdot", color="#FF0000", weight=0.3,
        )
        assert edge["name"] == "FoldLine"
        assert edge["x1"] == -20
        assert edge["x2"] == 20
        assert edge["style"] == "dashdot"
        assert edge["color"] == "#FF0000"
        assert edge["weight"] == 0.3

    def test_add_multiple_cosmetic_edges(self):
        page = create_drawing(create_project())
        add_cosmetic_edge(page, "V1", edge_name="E1")
        add_cosmetic_edge(page, "V1", edge_name="E2")
        add_cosmetic_edge(page, "V1", edge_name="E3")
        assert len(page["params"]["cosmetic_edges"]) == 3

    def test_all_line_styles(self):
        """All line styles can be used."""
        page = create_drawing(create_project())
        for style in ["solid", "dashed", "dashdot", "dotted", "phantom"]:
            edge = add_cosmetic_edge(page, "V1", style=style, edge_name=f"E_{style}")
            assert edge["style"] == style
        assert len(page["params"]["cosmetic_edges"]) == 5

    def test_line_styles_dict(self):
        """LINE_STYLES has expected entries with dash patterns."""
        assert "solid" in LINE_STYLES
        assert "dashed" in LINE_STYLES
        assert "dashdot" in LINE_STYLES
        assert "dotted" in LINE_STYLES
        assert "phantom" in LINE_STYLES
        # Solid has no dash pattern
        assert LINE_STYLES["solid"]["dash_pattern"] == ""
        # Others have patterns
        assert LINE_STYLES["dashed"]["dash_pattern"] != ""


class TestCenterMark:
    """Tests for center mark (crosshair) functionality."""

    def test_add_center_mark_defaults(self):
        page = create_drawing(create_project())
        mark = add_center_mark(page, "V1")
        assert mark["type"] == "TechDraw::CenterMark"
        assert mark["view"] == "V1"
        assert mark["cx"] == 0
        assert mark["cy"] == 0
        assert mark["size"] == 5
        assert mark["style"] == "dashdot"
        assert mark["weight"] == 0.15
        assert len(page["params"]["cosmetic_edges"]) == 1

    def test_add_center_mark_custom(self):
        page = create_drawing(create_project())
        mark = add_center_mark(
            page, "V1", cx=15, cy=-10, mark_name="HoleCenter",
            size=8, color="#0000FF",
        )
        assert mark["name"] == "HoleCenter"
        assert mark["cx"] == 15
        assert mark["cy"] == -10
        assert mark["size"] == 8
        assert mark["color"] == "#0000FF"

    def test_cosmetic_edges_and_center_marks_share_list(self):
        """Both types are stored in the same cosmetic_edges list."""
        page = create_drawing(create_project())
        add_cosmetic_edge(page, "V1", edge_name="E1")
        add_center_mark(page, "V1", mark_name="M1")
        edges = page["params"]["cosmetic_edges"]
        assert len(edges) == 2
        assert edges[0]["type"] == "TechDraw::CosmeticEdge"
        assert edges[1]["type"] == "TechDraw::CenterMark"


class TestCosmeticEdgeScript:
    """Tests for FreeCAD script generation with cosmetic edges."""

    def _make_project(self):
        proj = create_project(name="CEScript")
        proj["objects"].append({
            "name": "Box", "type": "Part::Box",
            "params": {"length": 50, "width": 30, "height": 20},
        })
        page = create_drawing(proj, "Sheet1")
        add_view(page, "Box", "V1", direction="front")
        proj["objects"].append(page)
        return proj, page

    def test_script_has_cosmetic_line(self):
        proj, page = self._make_project()
        add_cosmetic_edge(page, "V1", x1=-10, y1=5, x2=10, y2=5)
        script = _build_techdraw_script(proj, "Sheet1")
        assert "makeCosmeticLine" in script
        assert "-10" in script

    def test_script_has_center_mark(self):
        proj, page = self._make_project()
        add_center_mark(page, "V1", cx=25, cy=10, size=6)
        script = _build_techdraw_script(proj, "Sheet1")
        # Center mark generates two cosmetic lines (horizontal + vertical)
        assert script.count("makeCosmeticLine") == 2


class TestCosmeticEdgeSVG:
    """Tests for SVG export with cosmetic edges and center marks."""

    def _make_project_with_edges(self):
        proj = create_project(name="CESVG")
        proj["objects"].append({
            "name": "Box", "type": "Part::Box",
            "params": {"length": 80, "width": 50, "height": 30},
        })
        page = create_drawing(proj, "Sheet1", template="A4_Landscape", scale=1.0)
        proj["objects"].append(page)
        add_view(page, "Box", "V1", direction="front-elevation", x=150, y=100)
        return proj, page

    def test_svg_has_cosmetic_edge_line(self, tmp_dir):
        proj, page = self._make_project_with_edges()
        add_cosmetic_edge(page, "V1", x1=-30, y1=0, x2=30, y2=0, style="dashed")
        out = os.path.join(tmp_dir, "ce.svg")
        export_drawing_svg(proj, "Sheet1", out)
        with open(out, encoding="utf-8") as f:
            svg = f.read()
        # Should have a dashed line
        assert 'stroke-dasharray="6,3"' in svg

    def test_svg_has_center_mark_crosshair(self, tmp_dir):
        proj, page = self._make_project_with_edges()
        add_center_mark(page, "V1", cx=10, cy=5, size=7)
        out = os.path.join(tmp_dir, "cm.svg")
        export_drawing_svg(proj, "Sheet1", out)
        with open(out, encoding="utf-8") as f:
            svg = f.read()
        # Center mark is two lines with dashdot pattern
        assert 'stroke-dasharray="8,2,2,2"' in svg
        # Should produce 2 line elements for the crosshair
        lines = [l for l in svg.split("\n") if "stroke-dasharray" in l and "<line" in l]
        assert len(lines) >= 2

    def test_svg_solid_style_no_dash(self, tmp_dir):
        proj, page = self._make_project_with_edges()
        add_cosmetic_edge(page, "V1", x1=0, y1=0, x2=40, y2=0, style="solid")
        out = os.path.join(tmp_dir, "solid.svg")
        export_drawing_svg(proj, "Sheet1", out)
        with open(out, encoding="utf-8") as f:
            svg = f.read()
        # Solid lines should NOT have stroke-dasharray on the cosmetic edge line
        cosmetic_lines = [l for l in svg.split("\n")
                          if 'stroke-width="0.2"' in l and "<line" in l]
        assert len(cosmetic_lines) >= 1
        for line in cosmetic_lines:
            assert "stroke-dasharray" not in line

    def test_svg_phantom_style(self, tmp_dir):
        proj, page = self._make_project_with_edges()
        add_cosmetic_edge(page, "V1", style="phantom")
        out = os.path.join(tmp_dir, "phantom.svg")
        export_drawing_svg(proj, "Sheet1", out)
        with open(out, encoding="utf-8") as f:
            svg = f.read()
        assert 'stroke-dasharray="10,2,2,2,2,2"' in svg

    def test_svg_custom_color(self, tmp_dir):
        proj, page = self._make_project_with_edges()
        add_cosmetic_edge(page, "V1", color="#FF0000")
        out = os.path.join(tmp_dir, "color.svg")
        export_drawing_svg(proj, "Sheet1", out)
        with open(out, encoding="utf-8") as f:
            svg = f.read()
        assert 'stroke="#FF0000"' in svg


class TestCosmeticEdgeCLI:
    """CLI tests for cosmetic-edge and center-mark commands."""

    def test_cli_cosmetic_edge(self, tmp_dir):
        runner = CliRunner()
        path = os.path.join(tmp_dir, "cli_ce.json")
        runner.invoke(cli, ["--json", "project", "new", "-o", path])
        runner.invoke(cli, ["--json", "--project", path, "part", "box", "-n", "B"])
        runner.invoke(cli, ["--json", "--project", path, "techdraw", "page", "-n", "P1"])
        runner.invoke(cli, ["--json", "--project", path, "techdraw", "view", "P1", "B", "-n", "V1"])
        result = runner.invoke(cli, [
            "--json", "--project", path, "techdraw", "cosmetic-edge",
            "P1", "V1", "--x1", "-20", "--y1", "5", "--x2", "20", "--y2", "5",
            "-s", "dashed",
        ])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["type"] == "TechDraw::CosmeticEdge"
        assert data["x1"] == -20.0
        assert data["style"] == "dashed"

    def test_cli_center_mark(self, tmp_dir):
        runner = CliRunner()
        path = os.path.join(tmp_dir, "cli_cm.json")
        runner.invoke(cli, ["--json", "project", "new", "-o", path])
        runner.invoke(cli, ["--json", "--project", path, "part", "box", "-n", "B"])
        runner.invoke(cli, ["--json", "--project", path, "techdraw", "page", "-n", "P1"])
        runner.invoke(cli, ["--json", "--project", path, "techdraw", "view", "P1", "B", "-n", "V1"])
        result = runner.invoke(cli, [
            "--json", "--project", path, "techdraw", "center-mark",
            "P1", "V1", "--cx", "10", "--cy", "-5", "--size", "8",
        ])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["type"] == "TechDraw::CenterMark"
        assert data["cx"] == 10.0
        assert data["cy"] == -5.0
        assert data["size"] == 8.0

    def test_cli_cosmetic_edge_all_styles(self, tmp_dir):
        """All line styles accepted by CLI."""
        runner = CliRunner()
        path = os.path.join(tmp_dir, "cli_styles.json")
        runner.invoke(cli, ["--json", "project", "new", "-o", path])
        runner.invoke(cli, ["--json", "--project", path, "part", "box", "-n", "B"])
        runner.invoke(cli, ["--json", "--project", path, "techdraw", "page", "-n", "P1"])
        runner.invoke(cli, ["--json", "--project", path, "techdraw", "view", "P1", "B", "-n", "V1"])
        for style in ["solid", "dashed", "dashdot", "dotted", "phantom"]:
            result = runner.invoke(cli, [
                "--json", "--project", path, "techdraw", "cosmetic-edge",
                "P1", "V1", "-s", style, "-n", f"E_{style}",
            ])
            assert result.exit_code == 0, f"Failed for style {style}: {result.output}"

    def test_cli_list_shows_cosmetic_edges(self, tmp_dir):
        runner = CliRunner()
        path = os.path.join(tmp_dir, "cli_list_ce.json")
        runner.invoke(cli, ["--json", "project", "new", "-o", path])
        runner.invoke(cli, ["--json", "--project", path, "part", "box", "-n", "B"])
        runner.invoke(cli, ["--json", "--project", path, "techdraw", "page", "-n", "P1"])
        runner.invoke(cli, ["--json", "--project", path, "techdraw", "view", "P1", "B", "-n", "V1"])
        runner.invoke(cli, [
            "--json", "--project", path, "techdraw", "cosmetic-edge", "P1", "V1",
        ])
        runner.invoke(cli, [
            "--json", "--project", path, "techdraw", "center-mark", "P1", "V1",
        ])
        result = runner.invoke(cli, [
            "--json", "--project", path, "techdraw", "list", "P1",
        ])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data["cosmetic_edges"]) == 2
        types = [ce["type"] for ce in data["cosmetic_edges"]]
        assert "TechDraw::CosmeticEdge" in types
        assert "TechDraw::CenterMark" in types


# ── DrawViewClip tests ───────────────────────────────────────────────

class TestClipGroup:
    """Tests for clip group (view clipping/masking) functionality."""

    def test_add_clip_group_defaults(self):
        page = create_drawing(create_project())
        clip = add_clip_group(page)
        assert clip["type"] == "TechDraw::DrawViewClip"
        assert clip["name"] == "Clip"
        assert clip["x"] == 100
        assert clip["y"] == 100
        assert clip["width"] == 80
        assert clip["height"] == 60
        assert clip["show_frame"] is True
        assert clip["views"] == []
        assert len(page["params"]["clips"]) == 1

    def test_add_clip_group_custom(self):
        page = create_drawing(create_project())
        clip = add_clip_group(
            page, clip_name="DetailClip", x=200, y=150,
            width=120, height=90, show_frame=False,
        )
        assert clip["name"] == "DetailClip"
        assert clip["x"] == 200
        assert clip["y"] == 150
        assert clip["width"] == 120
        assert clip["height"] == 90
        assert clip["show_frame"] is False

    def test_add_multiple_clips(self):
        page = create_drawing(create_project())
        add_clip_group(page, clip_name="C1")
        add_clip_group(page, clip_name="C2")
        assert len(page["params"]["clips"]) == 2

    def test_add_view_to_clip(self):
        proj = create_project()
        page = create_drawing(proj)
        add_view(page, "Box", view_name="V1", direction="front")
        add_clip_group(page, clip_name="C1")
        result = add_view_to_clip(page, "C1", "V1")
        assert result is not None
        assert "V1" in result["views"]

    def test_add_view_to_clip_idempotent(self):
        """Adding the same view twice doesn't duplicate it."""
        proj = create_project()
        page = create_drawing(proj)
        add_view(page, "Box", view_name="V1")
        add_clip_group(page, clip_name="C1")
        add_view_to_clip(page, "C1", "V1")
        add_view_to_clip(page, "C1", "V1")
        clips = page["params"]["clips"]
        assert len(clips[0]["views"]) == 1

    def test_add_view_to_nonexistent_clip_returns_none(self):
        page = create_drawing(create_project())
        add_view(page, "Box", view_name="V1")
        result = add_view_to_clip(page, "NoSuchClip", "V1")
        assert result is None

    def test_add_nonexistent_view_to_clip_returns_none(self):
        page = create_drawing(create_project())
        add_clip_group(page, clip_name="C1")
        result = add_view_to_clip(page, "C1", "NoSuchView")
        assert result is None

    def test_add_multiple_views_to_clip(self):
        proj = create_project()
        page = create_drawing(proj)
        add_view(page, "Box", view_name="V1")
        add_view(page, "Cyl", view_name="V2")
        add_clip_group(page, clip_name="C1")
        add_view_to_clip(page, "C1", "V1")
        add_view_to_clip(page, "C1", "V2")
        clip = page["params"]["clips"][0]
        assert clip["views"] == ["V1", "V2"]


class TestClipGroupScript:
    """Tests for FreeCAD script generation with clip groups."""

    def _make_project(self):
        proj = create_project(name="ClipScript")
        proj["objects"].append({
            "name": "Box", "type": "Part::Box",
            "params": {"length": 50, "width": 30, "height": 20},
        })
        page = create_drawing(proj, "Sheet1")
        add_view(page, "Box", "V1", direction="front")
        proj["objects"].append(page)
        return proj, page

    def test_script_has_clip_object(self):
        proj, page = self._make_project()
        add_clip_group(page, clip_name="C1")
        script = _build_techdraw_script(proj, "Sheet1")
        assert "TechDraw::DrawViewClip" in script
        assert "'C1'" in script

    def test_script_has_clip_dimensions(self):
        proj, page = self._make_project()
        add_clip_group(page, clip_name="C1", width=120, height=90)
        script = _build_techdraw_script(proj, "Sheet1")
        assert "_clip.Width = 120" in script
        assert "_clip.Height = 90" in script

    def test_script_adds_view_to_clip(self):
        proj, page = self._make_project()
        add_clip_group(page, clip_name="C1")
        add_view_to_clip(page, "C1", "V1")
        script = _build_techdraw_script(proj, "Sheet1")
        assert "_clip.addView" in script
        assert "'V1'" in script

    def test_script_show_frame(self):
        proj, page = self._make_project()
        add_clip_group(page, clip_name="C1", show_frame=False)
        script = _build_techdraw_script(proj, "Sheet1")
        assert "_clip.ShowFrame = False" in script


class TestClipGroupSVG:
    """Tests for SVG export with clip groups."""

    def _make_project_with_clip(self, show_frame=True):
        proj = create_project(name="ClipSVG")
        proj["objects"].append({
            "name": "Box", "type": "Part::Box",
            "params": {"length": 80, "width": 50, "height": 30},
        })
        page = create_drawing(proj, "Sheet1", template="A4_Landscape", scale=1.0)
        proj["objects"].append(page)
        add_view(page, "Box", "V1", direction="front-elevation", x=150, y=100)
        add_clip_group(page, clip_name="C1", x=150, y=100,
                       width=60, height=40, show_frame=show_frame)
        add_view_to_clip(page, "C1", "V1")
        return proj

    def test_svg_has_clip_path(self, tmp_dir):
        proj = self._make_project_with_clip()
        out = os.path.join(tmp_dir, "clip.svg")
        export_drawing_svg(proj, "Sheet1", out)
        with open(out, encoding="utf-8") as f:
            svg = f.read()
        assert "clipPath" in svg
        assert 'id="clip-C1"' in svg

    def test_svg_has_clipped_group(self, tmp_dir):
        proj = self._make_project_with_clip()
        out = os.path.join(tmp_dir, "clip_grp.svg")
        export_drawing_svg(proj, "Sheet1", out)
        with open(out, encoding="utf-8") as f:
            svg = f.read()
        assert 'clip-path="url(#clip-C1)"' in svg

    def test_svg_has_clip_frame(self, tmp_dir):
        proj = self._make_project_with_clip(show_frame=True)
        out = os.path.join(tmp_dir, "frame.svg")
        export_drawing_svg(proj, "Sheet1", out)
        with open(out, encoding="utf-8") as f:
            svg = f.read()
        # Frame is drawn with dash pattern
        assert 'stroke-dasharray="4,2"' in svg

    def test_svg_no_frame_when_disabled(self, tmp_dir):
        proj = self._make_project_with_clip(show_frame=False)
        out = os.path.join(tmp_dir, "noframe.svg")
        export_drawing_svg(proj, "Sheet1", out)
        with open(out, encoding="utf-8") as f:
            svg = f.read()
        # clipPath should exist but no dashed frame rect
        assert "clipPath" in svg
        assert 'stroke-dasharray="4,2"' not in svg

    def test_svg_clip_without_views(self, tmp_dir):
        """Empty clip group should still produce a frame."""
        proj = create_project(name="EmptyClip")
        proj["objects"].append({
            "name": "Box", "type": "Part::Box",
            "params": {"length": 40, "width": 20, "height": 10},
        })
        page = create_drawing(proj, "Sheet1", template="A4_Landscape")
        proj["objects"].append(page)
        add_clip_group(page, clip_name="Empty", x=200, y=100, width=50, height=30)
        out = os.path.join(tmp_dir, "empty_clip.svg")
        export_drawing_svg(proj, "Sheet1", out)
        with open(out, encoding="utf-8") as f:
            svg = f.read()
        assert "clipPath" in svg
        assert 'stroke-dasharray="4,2"' in svg  # frame visible


class TestClipGroupCLI:
    """CLI tests for clip and clip-add commands."""

    def test_cli_clip_create(self, tmp_dir):
        runner = CliRunner()
        path = os.path.join(tmp_dir, "cli_clip.json")
        runner.invoke(cli, ["--json", "project", "new", "-o", path])
        runner.invoke(cli, ["--json", "--project", path, "techdraw", "page", "-n", "P1"])
        result = runner.invoke(cli, [
            "--json", "--project", path, "techdraw", "clip",
            "P1", "-n", "C1", "-x", "200", "-y", "150",
            "-w", "100", "-H", "70",
        ])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["type"] == "TechDraw::DrawViewClip"
        assert data["width"] == 100.0
        assert data["height"] == 70.0

    def test_cli_clip_add_view(self, tmp_dir):
        runner = CliRunner()
        path = os.path.join(tmp_dir, "cli_clip_add.json")
        runner.invoke(cli, ["--json", "project", "new", "-o", path])
        runner.invoke(cli, ["--json", "--project", path, "part", "box", "-n", "B"])
        runner.invoke(cli, ["--json", "--project", path, "techdraw", "page", "-n", "P1"])
        runner.invoke(cli, ["--json", "--project", path, "techdraw", "view", "P1", "B", "-n", "V1"])
        runner.invoke(cli, ["--json", "--project", path, "techdraw", "clip", "P1", "-n", "C1"])
        result = runner.invoke(cli, [
            "--json", "--project", path, "techdraw", "clip-add", "P1", "C1", "V1",
        ])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "V1" in data["views"]

    def test_cli_clip_add_nonexistent_view_fails(self, tmp_dir):
        runner = CliRunner()
        path = os.path.join(tmp_dir, "cli_clip_fail.json")
        runner.invoke(cli, ["--json", "project", "new", "-o", path])
        runner.invoke(cli, ["--json", "--project", path, "techdraw", "page", "-n", "P1"])
        runner.invoke(cli, ["--json", "--project", path, "techdraw", "clip", "P1", "-n", "C1"])
        result = runner.invoke(cli, [
            "--json", "--project", path, "techdraw", "clip-add", "P1", "C1", "NoView",
        ])
        assert result.exit_code != 0

    def test_cli_clip_no_frame(self, tmp_dir):
        runner = CliRunner()
        path = os.path.join(tmp_dir, "cli_clip_nf.json")
        runner.invoke(cli, ["--json", "project", "new", "-o", path])
        runner.invoke(cli, ["--json", "--project", path, "techdraw", "page", "-n", "P1"])
        result = runner.invoke(cli, [
            "--json", "--project", path, "techdraw", "clip",
            "P1", "-n", "C1", "--no-frame",
        ])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["show_frame"] is False

    def test_cli_list_shows_clips(self, tmp_dir):
        runner = CliRunner()
        path = os.path.join(tmp_dir, "cli_list_clip.json")
        runner.invoke(cli, ["--json", "project", "new", "-o", path])
        runner.invoke(cli, ["--json", "--project", path, "part", "box", "-n", "B"])
        runner.invoke(cli, ["--json", "--project", path, "techdraw", "page", "-n", "P1"])
        runner.invoke(cli, ["--json", "--project", path, "techdraw", "view", "P1", "B", "-n", "V1"])
        runner.invoke(cli, ["--json", "--project", path, "techdraw", "clip", "P1", "-n", "C1"])
        runner.invoke(cli, ["--json", "--project", path, "techdraw", "clip-add", "P1", "C1", "V1"])
        result = runner.invoke(cli, [
            "--json", "--project", path, "techdraw", "list", "P1",
        ])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data["clips"]) == 1
        assert data["clips"][0]["name"] == "C1"
        assert "V1" in data["clips"][0]["views"]


# ── GD&T Constants tests ─────────────────────────────────────────────

class TestGDTConstants:
    def test_gdt_symbols_complete(self):
        expected = [
            "flatness", "straightness", "circularity", "cylindricity",
            "perpendicularity", "parallelism", "angularity",
            "position", "concentricity", "symmetry",
            "circular_runout", "total_runout",
            "profile_line", "profile_surface",
        ]
        for name in expected:
            assert name in GDT_SYMBOLS
            assert "symbol" in GDT_SYMBOLS[name]
            assert "category" in GDT_SYMBOLS[name]

    def test_gdt_categories(self):
        assert GDT_SYMBOLS["flatness"]["category"] == "form"
        assert GDT_SYMBOLS["perpendicularity"]["category"] == "orientation"
        assert GDT_SYMBOLS["position"]["category"] == "location"
        assert GDT_SYMBOLS["circular_runout"]["category"] == "runout"
        assert GDT_SYMBOLS["profile_line"]["category"] == "profile"

    def test_material_conditions(self):
        assert "MMC" in MATERIAL_CONDITIONS
        assert "LMC" in MATERIAL_CONDITIONS
        assert "RFS" in MATERIAL_CONDITIONS
        assert MATERIAL_CONDITIONS["MMC"]["symbol"] == "Ⓜ"
        assert MATERIAL_CONDITIONS["RFS"]["symbol"] == ""

    def test_surface_finish_symbols(self):
        assert "any" in SURFACE_FINISH_SYMBOLS
        assert "removal_required" in SURFACE_FINISH_SYMBOLS
        assert "removal_prohibited" in SURFACE_FINISH_SYMBOLS


# ── Geometric Tolerance tests ────────────────────────────────────────

class TestGeometricTolerance:
    def test_add_position_tolerance(self):
        page = create_drawing(create_project())
        gdt = add_geometric_tolerance(
            page, "V1", characteristic="position", tolerance=0.05,
            gdt_name="GDT1", datum_refs=["A", "B"], material_condition="MMC",
            diameter_zone=True, x=120, y=90,
        )
        assert gdt["name"] == "GDT1"
        assert gdt["type"] == "TechDraw::GeometricTolerance"
        assert gdt["characteristic"] == "position"
        assert gdt["symbol"] == "⌖"
        assert gdt["category"] == "location"
        assert gdt["tolerance"] == 0.05
        assert gdt["diameter_zone"] is True
        assert gdt["material_condition"] == "MMC"
        assert gdt["material_condition_symbol"] == "Ⓜ"
        assert gdt["datum_refs"] == ["A", "B"]
        assert gdt["x"] == 120
        assert gdt["y"] == 90
        assert page["params"]["gdt"] == [gdt]

    def test_add_flatness_tolerance(self):
        page = create_drawing(create_project())
        gdt = add_geometric_tolerance(
            page, "V1", characteristic="flatness", tolerance=0.01,
        )
        assert gdt["characteristic"] == "flatness"
        assert gdt["symbol"] == "⏥"
        assert gdt["category"] == "form"
        assert gdt["datum_refs"] == []
        assert gdt["material_condition"] == "RFS"
        assert gdt["diameter_zone"] is False

    def test_add_perpendicularity_tolerance(self):
        page = create_drawing(create_project())
        gdt = add_geometric_tolerance(
            page, "V1", characteristic="perpendicularity", tolerance=0.1,
            datum_refs=["A"],
        )
        assert gdt["characteristic"] == "perpendicularity"
        assert gdt["symbol"] == "⊥"
        assert gdt["datum_refs"] == ["A"]

    def test_add_parallelism_tolerance(self):
        page = create_drawing(create_project())
        gdt = add_geometric_tolerance(
            page, "V1", characteristic="parallelism", tolerance=0.02,
            datum_refs=["A", "B", "C"],
        )
        assert gdt["datum_refs"] == ["A", "B", "C"]

    def test_invalid_characteristic_raises(self):
        page = create_drawing(create_project())
        with pytest.raises(ValueError, match="Unknown GD&T characteristic"):
            add_geometric_tolerance(page, "V1", characteristic="nonexistent", tolerance=0.1)

    def test_multiple_gdt_on_page(self):
        page = create_drawing(create_project())
        add_geometric_tolerance(page, "V1", characteristic="flatness", tolerance=0.01, gdt_name="G1")
        add_geometric_tolerance(page, "V1", characteristic="position", tolerance=0.05, gdt_name="G2")
        assert len(page["params"]["gdt"]) == 2


# ── Datum Symbol tests ───────────────────────────────────────────────

class TestDatumSymbol:
    def test_add_datum_symbol(self):
        page = create_drawing(create_project())
        datum = add_datum_symbol(page, "V1", letter="A", datum_name="DatumA", x=50, y=120)
        assert datum["name"] == "DatumA"
        assert datum["type"] == "TechDraw::DatumSymbol"
        assert datum["view"] == "V1"
        assert datum["letter"] == "A"
        assert datum["x"] == 50
        assert datum["y"] == 120
        assert page["params"]["datums"] == [datum]

    def test_datum_uppercase(self):
        page = create_drawing(create_project())
        datum = add_datum_symbol(page, "V1", letter="b")
        assert datum["letter"] == "B"

    def test_datum_invalid_letter_raises(self):
        page = create_drawing(create_project())
        with pytest.raises(ValueError, match="1-2 characters"):
            add_datum_symbol(page, "V1", letter="ABC")

    def test_datum_empty_letter_raises(self):
        page = create_drawing(create_project())
        with pytest.raises(ValueError, match="1-2 characters"):
            add_datum_symbol(page, "V1", letter="")

    def test_multiple_datums(self):
        page = create_drawing(create_project())
        add_datum_symbol(page, "V1", letter="A", datum_name="D1")
        add_datum_symbol(page, "V1", letter="B", datum_name="D2")
        add_datum_symbol(page, "V1", letter="C", datum_name="D3")
        assert len(page["params"]["datums"]) == 3


# ── Surface Finish tests ─────────────────────────────────────────────

class TestSurfaceFinish:
    def test_add_surface_finish_ra(self):
        page = create_drawing(create_project())
        sf = add_surface_finish(page, "V1", ra=1.6, process="removal_required",
                                sf_name="SF1", x=80, y=100)
        assert sf["name"] == "SF1"
        assert sf["type"] == "TechDraw::SurfaceFinish"
        assert sf["view"] == "V1"
        assert sf["ra"] == 1.6
        assert sf["rz"] is None
        assert sf["process"] == "removal_required"
        assert sf["process_symbol"] == "▽"
        assert page["params"]["surface_finishes"] == [sf]

    def test_add_surface_finish_rz(self):
        page = create_drawing(create_project())
        sf = add_surface_finish(page, "V1", rz=6.3)
        assert sf["rz"] == 6.3
        assert sf["ra"] is None
        assert sf["process"] == "any"

    def test_add_surface_finish_both(self):
        page = create_drawing(create_project())
        sf = add_surface_finish(page, "V1", ra=1.6, rz=6.3)
        assert sf["ra"] == 1.6
        assert sf["rz"] == 6.3

    def test_add_surface_finish_lay_direction(self):
        page = create_drawing(create_project())
        sf = add_surface_finish(page, "V1", ra=0.8, lay_direction="⊥")
        assert sf["lay_direction"] == "⊥"

    def test_invalid_process_raises(self):
        page = create_drawing(create_project())
        with pytest.raises(ValueError, match="Unknown surface finish process"):
            add_surface_finish(page, "V1", ra=1.6, process="invalid")

    def test_removal_prohibited(self):
        page = create_drawing(create_project())
        sf = add_surface_finish(page, "V1", ra=3.2, process="removal_prohibited")
        assert sf["process_symbol"] == "▽̶"


# ── GD&T Script Generation tests ────────────────────────────────────

class TestGDTScriptGeneration:
    def _make_project_with_gdt(self):
        proj = create_project(name="GDTScript")
        proj["objects"].append({
            "name": "Box", "type": "Part::Box",
            "params": {"length": 50, "width": 30, "height": 20},
        })
        page = create_drawing(proj, "Sheet1")
        add_view(page, "Box", "V1", direction="front")
        proj["objects"].append(page)
        return proj, page

    def test_script_has_gdt_annotation(self):
        proj, page = self._make_project_with_gdt()
        add_geometric_tolerance(page, "V1", characteristic="position",
                                tolerance=0.05, gdt_name="G1", datum_refs=["A"])
        script = _build_techdraw_script(proj, "Sheet1")
        assert "'G1'" in script
        assert "⌖" in script
        assert "0.05" in script

    def test_script_has_datum_annotation(self):
        proj, page = self._make_project_with_gdt()
        add_datum_symbol(page, "V1", letter="A", datum_name="DatA")
        script = _build_techdraw_script(proj, "Sheet1")
        assert "'DatA'" in script
        assert "[A]" in script

    def test_script_has_surface_finish_annotation(self):
        proj, page = self._make_project_with_gdt()
        add_surface_finish(page, "V1", ra=1.6, sf_name="SF1")
        script = _build_techdraw_script(proj, "Sheet1")
        assert "'SF1'" in script
        assert "Ra 1.6" in script

    def test_script_gdt_with_diameter_zone(self):
        proj, page = self._make_project_with_gdt()
        add_geometric_tolerance(page, "V1", characteristic="position",
                                tolerance=0.1, diameter_zone=True, gdt_name="G2")
        script = _build_techdraw_script(proj, "Sheet1")
        assert "∅0.1" in script

    def test_script_gdt_with_mmc(self):
        proj, page = self._make_project_with_gdt()
        add_geometric_tolerance(page, "V1", characteristic="position",
                                tolerance=0.05, material_condition="MMC", gdt_name="G3")
        script = _build_techdraw_script(proj, "Sheet1")
        assert "Ⓜ" in script


# ── GD&T SVG Export tests ────────────────────────────────────────────

class TestGDTSVGExport:
    def _make_project_with_gdt_annotations(self):
        proj = create_project(name="GDTSvg")
        proj["objects"].append({
            "name": "Box", "type": "Part::Box", "label": "Box",
            "params": {"length": 100, "width": 50, "height": 200},
        })
        page = create_drawing(proj, "Sheet1", template="A3_Landscape", scale=0.5)
        proj["objects"].append(page)
        add_view(page, "Box", "V1", direction="front-elevation", x=100, y=150)
        add_geometric_tolerance(page, "V1", characteristic="position",
                                tolerance=0.05, datum_refs=["A", "B"],
                                diameter_zone=True, gdt_name="G1")
        add_geometric_tolerance(page, "V1", characteristic="flatness",
                                tolerance=0.01, gdt_name="G2")
        add_datum_symbol(page, "V1", letter="A", datum_name="DatA", x=80, y=180)
        add_datum_symbol(page, "V1", letter="B", datum_name="DatB", x=120, y=180)
        add_surface_finish(page, "V1", ra=1.6, process="removal_required",
                           sf_name="SF1", x=60, y=100)
        return proj

    def test_svg_has_gdt_frame(self, tmp_dir):
        proj = self._make_project_with_gdt_annotations()
        out = os.path.join(tmp_dir, "gdt.svg")
        result = export_drawing_svg(proj, "Sheet1", out)
        assert result["success"] is True
        with open(out, encoding="utf-8") as f:
            svg = f.read()
        # FCF frame boxes
        assert "⌖" in svg  # position symbol
        assert "⏥" in svg  # flatness symbol
        assert "0.05" in svg  # tolerance value
        assert "0.01" in svg

    def test_svg_has_datum_symbols(self, tmp_dir):
        proj = self._make_project_with_gdt_annotations()
        out = os.path.join(tmp_dir, "datum.svg")
        export_drawing_svg(proj, "Sheet1", out)
        with open(out, encoding="utf-8") as f:
            svg = f.read()
        assert "<polygon" in svg  # datum triangle
        assert ">A<" in svg  # datum letter
        assert ">B<" in svg

    def test_svg_has_surface_finish(self, tmp_dir):
        proj = self._make_project_with_gdt_annotations()
        out = os.path.join(tmp_dir, "sf.svg")
        export_drawing_svg(proj, "Sheet1", out)
        with open(out, encoding="utf-8") as f:
            svg = f.read()
        assert "<polyline" in svg  # checkmark
        assert "Ra 1.6" in svg

    def test_svg_gdt_datum_refs_in_frame(self, tmp_dir):
        proj = self._make_project_with_gdt_annotations()
        out = os.path.join(tmp_dir, "refs.svg")
        export_drawing_svg(proj, "Sheet1", out)
        with open(out, encoding="utf-8") as f:
            svg = f.read()
        # Datum refs A, B should appear in the FCF
        assert ">A<" in svg
        assert ">B<" in svg


# ── GD&T CLI tests ───────────────────────────────────────────────────

class TestGDTCLI:
    def _setup_page(self, runner, tmp_dir, name="gdt_test"):
        path = os.path.join(tmp_dir, f"{name}.json")
        runner.invoke(cli, ["--json", "project", "new", "-o", path])
        runner.invoke(cli, ["--json", "--project", path, "part", "box", "-n", "Box"])
        runner.invoke(cli, ["--json", "--project", path, "techdraw", "page", "-n", "P1"])
        runner.invoke(cli, ["--json", "--project", path, "techdraw", "view", "P1", "Box", "-n", "V1"])
        return path

    def test_gdt_position_json(self, tmp_dir):
        runner = CliRunner()
        path = self._setup_page(runner, tmp_dir, "gdt_pos")
        result = runner.invoke(cli, [
            "--json", "--project", path, "techdraw", "gdt", "P1", "V1",
            "-c", "position", "-t", "0.05", "-d", "A", "-d", "B", "-m", "MMC",
            "--diameter-zone",
        ])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["type"] == "TechDraw::GeometricTolerance"
        assert data["characteristic"] == "position"
        assert data["tolerance"] == 0.05
        assert data["datum_refs"] == ["A", "B"]
        assert data["material_condition"] == "MMC"
        assert data["diameter_zone"] is True

    def test_gdt_flatness_json(self, tmp_dir):
        runner = CliRunner()
        path = self._setup_page(runner, tmp_dir, "gdt_flat")
        result = runner.invoke(cli, [
            "--json", "--project", path, "techdraw", "gdt", "P1", "V1",
            "-c", "flatness", "-t", "0.01",
        ])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["characteristic"] == "flatness"
        assert data["tolerance"] == 0.01
        assert data["datum_refs"] == []

    def test_gdt_perpendicularity_json(self, tmp_dir):
        runner = CliRunner()
        path = self._setup_page(runner, tmp_dir, "gdt_perp")
        result = runner.invoke(cli, [
            "--json", "--project", path, "techdraw", "gdt", "P1", "V1",
            "-c", "perpendicularity", "-t", "0.1", "-d", "A",
        ])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["characteristic"] == "perpendicularity"
        assert data["datum_refs"] == ["A"]

    def test_datum_json(self, tmp_dir):
        runner = CliRunner()
        path = self._setup_page(runner, tmp_dir, "datum_cli")
        result = runner.invoke(cli, [
            "--json", "--project", path, "techdraw", "datum", "P1", "V1", "A",
            "-x", "50", "-y", "120",
        ])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["type"] == "TechDraw::DatumSymbol"
        assert data["letter"] == "A"
        assert data["x"] == 50

    def test_surface_finish_json(self, tmp_dir):
        runner = CliRunner()
        path = self._setup_page(runner, tmp_dir, "sf_cli")
        result = runner.invoke(cli, [
            "--json", "--project", path, "techdraw", "surface-finish", "P1", "V1",
            "--ra", "1.6", "-p", "removal_required",
        ])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["type"] == "TechDraw::SurfaceFinish"
        assert data["ra"] == 1.6
        assert data["process"] == "removal_required"

    def test_surface_finish_rz_json(self, tmp_dir):
        runner = CliRunner()
        path = self._setup_page(runner, tmp_dir, "sf_rz")
        result = runner.invoke(cli, [
            "--json", "--project", path, "techdraw", "surface-finish", "P1", "V1",
            "--rz", "6.3",
        ])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["rz"] == 6.3

    def test_surface_finish_no_value_fails(self, tmp_dir):
        runner = CliRunner()
        path = self._setup_page(runner, tmp_dir, "sf_err")
        result = runner.invoke(cli, [
            "--project", path, "techdraw", "surface-finish", "P1", "V1",
        ])
        assert result.exit_code != 0
        assert "ra" in result.output.lower() or "rz" in result.output.lower()

    def test_list_shows_gdt(self, tmp_dir):
        runner = CliRunner()
        path = self._setup_page(runner, tmp_dir, "list_gdt")
        runner.invoke(cli, [
            "--json", "--project", path, "techdraw", "gdt", "P1", "V1",
            "-c", "position", "-t", "0.05", "-d", "A",
        ])
        runner.invoke(cli, [
            "--json", "--project", path, "techdraw", "datum", "P1", "V1", "A",
        ])
        runner.invoke(cli, [
            "--json", "--project", path, "techdraw", "surface-finish", "P1", "V1",
            "--ra", "1.6",
        ])
        result = runner.invoke(cli, [
            "--json", "--project", path, "techdraw", "list", "P1",
        ])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data["gdt"]) == 1
        assert len(data["datums"]) == 1
        assert len(data["surface_finishes"]) == 1


# ── Weld Symbol Tests ──────────────────────────────────────────────

class TestWeldConstants:
    """Test weld symbol constants completeness."""

    def test_weld_types_complete(self):
        from cli_anything.freecad.core.techdraw import WELD_TYPES
        expected = {
            "fillet", "v_groove", "square_groove", "bevel_groove",
            "u_groove", "j_groove", "plug", "bead",
            "spot", "seam", "edge", "flare_v", "flare_bevel",
        }
        assert set(WELD_TYPES.keys()) == expected

    def test_weld_types_have_symbols(self):
        from cli_anything.freecad.core.techdraw import WELD_TYPES
        for name, info in WELD_TYPES.items():
            assert "symbol" in info, f"{name} missing symbol"
            assert "description" in info, f"{name} missing description"
            assert "svg_file_arrow" in info, f"{name} missing svg_file_arrow"
            assert "svg_file_other" in info, f"{name} missing svg_file_other"

    def test_weld_contours(self):
        from cli_anything.freecad.core.techdraw import WELD_CONTOURS
        assert "flush" in WELD_CONTOURS
        assert "convex" in WELD_CONTOURS
        assert "concave" in WELD_CONTOURS

    def test_weld_processes(self):
        from cli_anything.freecad.core.techdraw import WELD_PROCESSES
        assert "GMAW" in WELD_PROCESSES
        assert "SMAW" in WELD_PROCESSES
        assert "GTAW" in WELD_PROCESSES


class TestWeldSymbol:
    """Test add_weld_symbol core function."""

    def _make_page(self):
        from cli_anything.freecad.core.project import create_project
        from cli_anything.freecad.core.techdraw import create_drawing, add_view
        proj = create_project(name="WeldTest")
        proj["objects"].append({
            "name": "Box", "type": "Part::Box",
            "params": {"length": 20, "width": 15, "height": 10},
        })
        page = create_drawing(proj, page_name="Sheet1")
        add_view(page, "Box", view_name="V1", direction="front")
        proj["objects"].append(page)
        return proj, page

    def test_fillet_weld(self):
        from cli_anything.freecad.core.techdraw import add_weld_symbol
        _, page = self._make_page()
        weld = add_weld_symbol(page, "V1", weld_type="fillet", size="6")
        assert weld["weld_type"] == "fillet"
        assert weld["weld_symbol"] == "△"
        assert weld["side"] == "arrow"
        assert len(weld["tiles"]) == 1
        assert weld["tiles"][0]["left_text"] == "6"

    def test_v_groove_all_around(self):
        from cli_anything.freecad.core.techdraw import add_weld_symbol
        _, page = self._make_page()
        weld = add_weld_symbol(
            page, "V1", weld_type="v_groove",
            all_around=True, tail="GMAW",
        )
        assert weld["all_around"] is True
        assert weld["tail"] == "GMAW"
        assert weld["weld_type"] == "v_groove"

    def test_bevel_field_weld_flush(self):
        from cli_anything.freecad.core.techdraw import add_weld_symbol
        _, page = self._make_page()
        weld = add_weld_symbol(
            page, "V1", weld_type="bevel_groove",
            field_weld=True, contour="flush", length="50",
        )
        assert weld["field_weld"] is True
        assert weld["contour"] == "flush"
        assert weld["contour_symbol"] == "—"
        assert weld["tiles"][0]["right_text"] == "50"

    def test_invalid_weld_type_raises(self):
        from cli_anything.freecad.core.techdraw import add_weld_symbol
        _, page = self._make_page()
        with pytest.raises(ValueError, match="Unknown weld type"):
            add_weld_symbol(page, "V1", weld_type="nonexistent")

    def test_invalid_side_raises(self):
        from cli_anything.freecad.core.techdraw import add_weld_symbol
        _, page = self._make_page()
        with pytest.raises(ValueError, match="Side must be"):
            add_weld_symbol(page, "V1", weld_type="fillet", side="both")

    def test_invalid_contour_raises(self):
        from cli_anything.freecad.core.techdraw import add_weld_symbol
        _, page = self._make_page()
        with pytest.raises(ValueError, match="Unknown contour"):
            add_weld_symbol(page, "V1", weld_type="fillet", contour="wavy")

    def test_other_side(self):
        from cli_anything.freecad.core.techdraw import add_weld_symbol
        _, page = self._make_page()
        weld = add_weld_symbol(page, "V1", weld_type="fillet", side="other", size="4")
        assert weld["side"] == "other"
        assert weld["tiles"][0]["side"] == "other"
        assert weld["tiles"][0]["svg_file"] == "filletDown.svg"

    def test_multiple_welds_on_page(self):
        from cli_anything.freecad.core.techdraw import add_weld_symbol
        _, page = self._make_page()
        add_weld_symbol(page, "V1", weld_type="fillet", weld_name="W1")
        add_weld_symbol(page, "V1", weld_type="v_groove", weld_name="W2")
        assert len(page["params"]["welds"]) == 2


class TestWeldTile:
    """Test add_weld_tile for double-sided welds."""

    def _make_page_with_weld(self):
        from cli_anything.freecad.core.project import create_project
        from cli_anything.freecad.core.techdraw import (
            create_drawing, add_view, add_weld_symbol,
        )
        proj = create_project(name="WeldTileTest")
        proj["objects"].append({
            "name": "Box", "type": "Part::Box",
            "params": {"length": 20, "width": 15, "height": 10},
        })
        page = create_drawing(proj, page_name="Sheet1")
        add_view(page, "Box", view_name="V1", direction="front")
        proj["objects"].append(page)
        add_weld_symbol(page, "V1", weld_type="fillet", side="arrow",
                        size="6", weld_name="W1")
        return proj, page

    def test_add_other_side_tile(self):
        from cli_anything.freecad.core.techdraw import add_weld_tile
        _, page = self._make_page_with_weld()
        tile = add_weld_tile(page, "W1", weld_type="fillet", side="other", size="4")
        assert tile["side"] == "other"
        assert tile["left_text"] == "4"
        # Weld should now have 2 tiles
        weld = page["params"]["welds"][0]
        assert len(weld["tiles"]) == 2

    def test_tile_different_type(self):
        from cli_anything.freecad.core.techdraw import add_weld_tile
        _, page = self._make_page_with_weld()
        tile = add_weld_tile(page, "W1", weld_type="v_groove", side="other")
        assert tile["weld_type"] == "v_groove"

    def test_tile_nonexistent_weld_raises(self):
        from cli_anything.freecad.core.techdraw import add_weld_tile
        _, page = self._make_page_with_weld()
        with pytest.raises(ValueError, match="Weld symbol not found"):
            add_weld_tile(page, "NonExistent", weld_type="fillet")


class TestWeldScriptGeneration:
    """Test that _build_techdraw_script generates weld annotations."""

    def _make_page_with_weld(self):
        from cli_anything.freecad.core.project import create_project
        from cli_anything.freecad.core.techdraw import (
            create_drawing, add_view, add_weld_symbol,
        )
        proj = create_project(name="ScriptTest")
        proj["objects"].append({
            "name": "Box", "type": "Part::Box",
            "params": {"length": 20, "width": 15, "height": 10},
        })
        page = create_drawing(proj, page_name="Sheet1")
        add_view(page, "Box", view_name="V1", direction="front")
        proj["objects"].append(page)
        return proj, page

    def test_script_has_weld_annotation(self):
        from cli_anything.freecad.core.techdraw import (
            add_weld_symbol, _build_techdraw_script,
        )
        proj, page = self._make_page_with_weld()
        add_weld_symbol(page, "V1", weld_type="fillet", size="6", weld_name="W1")
        script = _build_techdraw_script(proj, "Sheet1")
        assert "DrawViewAnnotation" in script
        assert "'W1'" in script

    def test_script_weld_with_tail(self):
        from cli_anything.freecad.core.techdraw import (
            add_weld_symbol, _build_techdraw_script,
        )
        proj, page = self._make_page_with_weld()
        add_weld_symbol(page, "V1", weld_type="v_groove",
                        tail="GMAW", weld_name="W2")
        script = _build_techdraw_script(proj, "Sheet1")
        assert "GMAW" in script

    def test_script_weld_all_around(self):
        from cli_anything.freecad.core.techdraw import (
            add_weld_symbol, _build_techdraw_script,
        )
        proj, page = self._make_page_with_weld()
        add_weld_symbol(page, "V1", weld_type="fillet",
                        all_around=True, weld_name="W3")
        script = _build_techdraw_script(proj, "Sheet1")
        assert "○" in script


class TestWeldSVGExport:
    """Test SVG export includes weld symbols."""

    def _make_page_with_weld(self, tmp_path):
        from cli_anything.freecad.core.project import create_project
        from cli_anything.freecad.core.techdraw import (
            create_drawing, add_view, add_weld_symbol, export_drawing_svg,
        )
        proj = create_project(name="SVGTest")
        proj["objects"].append({
            "name": "Box", "type": "Part::Box",
            "params": {"length": 20, "width": 15, "height": 10},
        })
        page = create_drawing(proj, page_name="Sheet1")
        add_view(page, "Box", view_name="V1", direction="front")
        proj["objects"].append(page)
        return proj, page

    def test_svg_has_weld_reference_line(self, tmp_path):
        from cli_anything.freecad.core.techdraw import (
            add_weld_symbol, export_drawing_svg,
        )
        proj, page = self._make_page_with_weld(tmp_path)
        add_weld_symbol(page, "V1", weld_type="fillet", size="6")
        svg_path = str(tmp_path / "weld.svg")
        result = export_drawing_svg(proj, "Sheet1", svg_path)
        assert result["success"] is True
        with open(svg_path, encoding="utf-8") as f:
            content = f.read()
        # Reference line + arrow line
        assert "stroke-width=\"0.4\"" in content

    def test_svg_has_weld_fillet_triangle(self, tmp_path):
        from cli_anything.freecad.core.techdraw import (
            add_weld_symbol, export_drawing_svg,
        )
        proj, page = self._make_page_with_weld(tmp_path)
        add_weld_symbol(page, "V1", weld_type="fillet", size="6")
        svg_path = str(tmp_path / "weld_fillet.svg")
        result = export_drawing_svg(proj, "Sheet1", svg_path)
        assert result["success"] is True
        with open(svg_path, encoding="utf-8") as f:
            content = f.read()
        # Fillet weld renders as polygon (triangle)
        assert "<polygon" in content
        # Size text
        assert ">6<" in content

    def test_svg_has_all_around_circle(self, tmp_path):
        from cli_anything.freecad.core.techdraw import (
            add_weld_symbol, export_drawing_svg,
        )
        proj, page = self._make_page_with_weld(tmp_path)
        add_weld_symbol(page, "V1", weld_type="fillet", all_around=True)
        svg_path = str(tmp_path / "weld_allaround.svg")
        result = export_drawing_svg(proj, "Sheet1", svg_path)
        assert result["success"] is True
        with open(svg_path, encoding="utf-8") as f:
            content = f.read()
        # All-around circle (r=2.5)
        assert 'r="2.5"' in content

    def test_svg_has_tail_text(self, tmp_path):
        from cli_anything.freecad.core.techdraw import (
            add_weld_symbol, export_drawing_svg,
        )
        proj, page = self._make_page_with_weld(tmp_path)
        add_weld_symbol(page, "V1", weld_type="v_groove", tail="GTAW")
        svg_path = str(tmp_path / "weld_tail.svg")
        result = export_drawing_svg(proj, "Sheet1", svg_path)
        assert result["success"] is True
        with open(svg_path, encoding="utf-8") as f:
            content = f.read()
        assert "GTAW" in content


class TestWeldCLI:
    """Test weld CLI commands via CliRunner."""

    def test_weld_fillet_json(self, tmp_path):
        from click.testing import CliRunner
        from cli_anything.freecad.freecad_cli import cli
        runner = CliRunner()
        path = str(tmp_path / "weld_cli.json")
        runner.invoke(cli, ["--json", "project", "new", "-o", path])
        runner.invoke(cli, ["--json", "--project", path, "part", "box"])
        runner.invoke(cli, ["--json", "--project", path, "techdraw", "page", "-n", "P1"])
        runner.invoke(cli, ["--json", "--project", path, "techdraw", "view", "P1", "Box"])
        result = runner.invoke(cli, [
            "--json", "--project", path, "techdraw", "weld", "P1", "View",
            "-t", "fillet", "--size", "6", "--length", "50",
        ])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["weld_type"] == "fillet"
        assert data["tiles"][0]["left_text"] == "6"
        assert data["tiles"][0]["right_text"] == "50"

    def test_weld_v_groove_all_around_json(self, tmp_path):
        from click.testing import CliRunner
        from cli_anything.freecad.freecad_cli import cli
        runner = CliRunner()
        path = str(tmp_path / "weld_cli2.json")
        runner.invoke(cli, ["--json", "project", "new", "-o", path])
        runner.invoke(cli, ["--json", "--project", path, "part", "box"])
        runner.invoke(cli, ["--json", "--project", path, "techdraw", "page", "-n", "P1"])
        runner.invoke(cli, ["--json", "--project", path, "techdraw", "view", "P1", "Box"])
        result = runner.invoke(cli, [
            "--json", "--project", path, "techdraw", "weld", "P1", "View",
            "-t", "v_groove", "--all-around", "--tail", "GMAW",
        ])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["all_around"] is True
        assert data["tail"] == "GMAW"

    def test_weld_tile_json(self, tmp_path):
        from click.testing import CliRunner
        from cli_anything.freecad.freecad_cli import cli
        runner = CliRunner()
        path = str(tmp_path / "weld_tile_cli.json")
        runner.invoke(cli, ["--json", "project", "new", "-o", path])
        runner.invoke(cli, ["--json", "--project", path, "part", "box"])
        runner.invoke(cli, ["--json", "--project", path, "techdraw", "page", "-n", "P1"])
        runner.invoke(cli, ["--json", "--project", path, "techdraw", "view", "P1", "Box"])
        runner.invoke(cli, [
            "--json", "--project", path, "techdraw", "weld", "P1", "View",
            "-t", "fillet", "--size", "6", "-n", "W1",
        ])
        result = runner.invoke(cli, [
            "--json", "--project", path, "techdraw", "weld-tile", "P1", "W1",
            "-t", "fillet", "-s", "other", "--size", "4",
        ])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["side"] == "other"
        assert data["left_text"] == "4"

    def test_weld_with_contour_json(self, tmp_path):
        from click.testing import CliRunner
        from cli_anything.freecad.freecad_cli import cli
        runner = CliRunner()
        path = str(tmp_path / "weld_contour.json")
        runner.invoke(cli, ["--json", "project", "new", "-o", path])
        runner.invoke(cli, ["--json", "--project", path, "part", "box"])
        runner.invoke(cli, ["--json", "--project", path, "techdraw", "page", "-n", "P1"])
        runner.invoke(cli, ["--json", "--project", path, "techdraw", "view", "P1", "Box"])
        result = runner.invoke(cli, [
            "--json", "--project", path, "techdraw", "weld", "P1", "View",
            "-t", "bevel_groove", "--contour", "flush", "--field-weld",
        ])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["contour"] == "flush"
        assert data["field_weld"] is True

    def test_list_shows_welds(self, tmp_path):
        from click.testing import CliRunner
        from cli_anything.freecad.freecad_cli import cli
        runner = CliRunner()
        path = str(tmp_path / "weld_list.json")
        runner.invoke(cli, ["--json", "project", "new", "-o", path])
        runner.invoke(cli, ["--json", "--project", path, "part", "box"])
        runner.invoke(cli, ["--json", "--project", path, "techdraw", "page", "-n", "P1"])
        runner.invoke(cli, ["--json", "--project", path, "techdraw", "view", "P1", "Box"])
        runner.invoke(cli, [
            "--json", "--project", path, "techdraw", "weld", "P1", "View",
            "-t", "fillet", "--size", "6",
        ])
        result = runner.invoke(cli, [
            "--json", "--project", path, "techdraw", "list", "P1",
        ])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data["welds"]) == 1
        assert data["welds"][0]["weld_type"] == "fillet"
