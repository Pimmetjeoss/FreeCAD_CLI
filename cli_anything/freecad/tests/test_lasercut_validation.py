"""Unit tests for lasercut validation module.

Tests use synthetic data — no FreeCAD backend required.
Validates contour closure, duplicate detection, feature sizing,
plate fit, and kerf advisory checks.
"""

from __future__ import annotations

import json
import os
import tempfile

import pytest
from click.testing import CliRunner

from cli_anything.freecad.core.project import create_project
from cli_anything.freecad.core.session import Session
from cli_anything.freecad.core.lasercut_validation import (
    validate_project_for_lasercut,
    check_sketch_closure,
    check_duplicate_geometry,
    check_min_feature_size,
    check_plate_fit,
    report_dimensions,
    check_kerf_advisory,
    generate_validation_script,
    DEFAULT_CLOSURE_TOLERANCE_MM,
    DEFAULT_MIN_FEATURE_SIZE_MM,
    DEFAULT_KERF_WIDTH_MM,
)
from cli_anything.freecad.freecad_cli import cli


# ── Fixtures ─────────────────────────────────────────────────────────


@pytest.fixture
def tmp_dir():
    with tempfile.TemporaryDirectory(prefix="fc_laser_test_") as d:
        yield d


@pytest.fixture
def project_with_box(tmp_dir):
    path = os.path.join(tmp_dir, "test.json")
    proj = create_project(name="LaserTest", output_path=path)
    proj["objects"] = [
        {
            "name": "Plate",
            "type": "Part::Box",
            "label": "Plate",
            "params": {"length": 200, "width": 100, "height": 3},
        }
    ]
    return proj


@pytest.fixture
def project_with_closed_sketch(tmp_dir):
    path = os.path.join(tmp_dir, "test.json")
    proj = create_project(name="SketchTest", output_path=path)
    proj["objects"] = [
        {
            "name": "Profile",
            "type": "Sketcher::SketchObject",
            "label": "Profile",
            "params": {
                "plane": "XY",
                "closed": True,
                "geometry": [
                    {"type": "line", "x1": 0, "y1": 0, "x2": 100, "y2": 0},
                    {"type": "line", "x1": 100, "y1": 0, "x2": 100, "y2": 50},
                    {"type": "line", "x1": 100, "y1": 50, "x2": 0, "y2": 50},
                    {"type": "line", "x1": 0, "y1": 50, "x2": 0, "y2": 0},
                ],
            },
        }
    ]
    return proj


@pytest.fixture
def project_with_open_sketch(tmp_dir):
    path = os.path.join(tmp_dir, "test.json")
    proj = create_project(name="OpenTest", output_path=path)
    proj["objects"] = [
        {
            "name": "OpenProfile",
            "type": "Sketcher::SketchObject",
            "label": "OpenProfile",
            "params": {
                "plane": "XY",
                "closed": False,
                "geometry": [
                    {"type": "line", "x1": 0, "y1": 0, "x2": 100, "y2": 0},
                    {"type": "line", "x1": 100, "y1": 0, "x2": 100, "y2": 50},
                    # Missing: line back to origin — contour is open
                ],
            },
        }
    ]
    return proj


@pytest.fixture
def project_with_svg(tmp_dir):
    path = os.path.join(tmp_dir, "test.json")
    proj = create_project(name="SVGTest", output_path=path)
    proj["objects"] = [
        {
            "name": "Logo",
            "type": "ImportSVG",
            "label": "Logo",
            "params": {
                "filepath": "/fake/logo.svg",
                "target_units": "mm",
                "scale": 1.0,
                "svg_width": 300,
                "svg_height": 200,
                "svg_unit": "mm",
            },
        }
    ]
    return proj


@pytest.fixture
def project_with_duplicates(tmp_dir):
    path = os.path.join(tmp_dir, "test.json")
    proj = create_project(name="DupTest", output_path=path)
    proj["objects"] = [
        {
            "name": "BadProfile",
            "type": "Sketcher::SketchObject",
            "label": "BadProfile",
            "params": {
                "plane": "XY",
                "closed": True,
                "geometry": [
                    {"type": "line", "x1": 0, "y1": 0, "x2": 100, "y2": 0},
                    {"type": "line", "x1": 0, "y1": 0, "x2": 100, "y2": 0},  # duplicate!
                    {"type": "line", "x1": 100, "y1": 0, "x2": 100, "y2": 50},
                ],
            },
        }
    ]
    return proj


@pytest.fixture
def project_with_tiny_feature(tmp_dir):
    path = os.path.join(tmp_dir, "test.json")
    proj = create_project(name="TinyTest", output_path=path)
    proj["objects"] = [
        {
            "name": "TinyHole",
            "type": "Sketcher::SketchObject",
            "label": "TinyHole",
            "params": {
                "plane": "XY",
                "geometry": [
                    {"type": "circle", "cx": 50, "cy": 25, "radius": 0.1},
                ],
            },
        }
    ]
    return proj


@pytest.fixture
def runner():
    return CliRunner()


# ── Contour Closure Tests ────────────────────────────────────────────


class TestContourClosure:
    def test_closed_sketch_passes(self, project_with_closed_sketch):
        result = check_sketch_closure(project_with_closed_sketch["objects"])
        assert result["passed"] is True
        assert result["details"]["closed_count"] == 1
        assert result["details"]["open_count"] == 0

    def test_open_sketch_fails(self, project_with_open_sketch):
        result = check_sketch_closure(project_with_open_sketch["objects"])
        assert result["passed"] is False
        assert result["details"]["open_count"] == 1
        assert "OpenProfile" in result["details"]["open_profiles"]

    def test_solid_primitive_passes(self, project_with_box):
        result = check_sketch_closure(project_with_box["objects"])
        assert result["passed"] is True
        assert "solid primitive" in result["message"]

    def test_svg_import_skipped_needs_backend(self, project_with_svg):
        """SVG closure check is skipped in local mode — needs FreeCAD backend."""
        result = check_sketch_closure(project_with_svg["objects"])
        assert result["passed"] is True  # No open profiles = pass
        assert result["details"]["skipped_svg_count"] == 1
        assert result["details"]["closed_count"] == 0
        assert len(result.get("warnings", [])) > 0
        assert "backend" in result["warnings"][0].lower()

    def test_circle_always_closed(self, tmp_dir):
        proj = create_project(name="CircleTest", output_path=os.path.join(tmp_dir, "t.json"))
        proj["objects"] = [
            {
                "name": "Ring",
                "type": "Sketcher::SketchObject",
                "label": "Ring",
                "params": {
                    "plane": "XY",
                    "closed": False,  # closed flag is False but circle is inherently closed
                    "geometry": [{"type": "circle", "cx": 0, "cy": 0, "radius": 25}],
                },
            }
        ]
        result = check_sketch_closure(proj["objects"])
        assert result["passed"] is True

    def test_empty_project_fails(self):
        result = check_sketch_closure([])
        assert result["passed"] is False


# ── Duplicate Edge Tests ─────────────────────────────────────────────


class TestDuplicateEdges:
    def test_no_duplicates(self, project_with_closed_sketch):
        result = check_duplicate_geometry(project_with_closed_sketch["objects"])
        assert result["passed"] is True
        assert result["details"]["duplicate_count"] == 0

    def test_detects_duplicates(self, project_with_duplicates):
        result = check_duplicate_geometry(project_with_duplicates["objects"])
        assert result["passed"] is False
        assert result["details"]["duplicate_count"] > 0

    def test_reversed_duplicate_detected(self, tmp_dir):
        """Edges in opposite direction should also be detected as duplicates."""
        proj = create_project(name="RevTest", output_path=os.path.join(tmp_dir, "t.json"))
        proj["objects"] = [
            {
                "name": "RevDup",
                "type": "Sketcher::SketchObject",
                "label": "RevDup",
                "params": {
                    "geometry": [
                        {"type": "line", "x1": 0, "y1": 0, "x2": 50, "y2": 0},
                        {"type": "line", "x1": 50, "y1": 0, "x2": 0, "y2": 0},  # reversed duplicate
                    ],
                },
            }
        ]
        result = check_duplicate_geometry(proj["objects"])
        assert result["passed"] is False
        assert result["details"]["duplicate_count"] == 1


# ── Minimum Feature Size Tests ───────────────────────────────────────


class TestMinFeatureSize:
    def test_normal_features_pass(self, project_with_box):
        result = check_min_feature_size(project_with_box["objects"])
        assert result["passed"] is True

    def test_tiny_feature_fails(self, project_with_tiny_feature):
        result = check_min_feature_size(project_with_tiny_feature["objects"], min_size_mm=0.5)
        assert result["passed"] is False
        assert result["details"]["violation_count"] > 0

    def test_custom_minimum(self, project_with_box):
        # Box with 3mm height should fail with 5mm minimum
        result = check_min_feature_size(project_with_box["objects"], min_size_mm=5.0)
        assert result["passed"] is False

    def test_zero_minimum_always_passes(self, project_with_tiny_feature):
        result = check_min_feature_size(project_with_tiny_feature["objects"], min_size_mm=0.0)
        assert result["passed"] is True

    def test_line_length_check(self, tmp_dir):
        proj = create_project(name="LineTest", output_path=os.path.join(tmp_dir, "t.json"))
        proj["objects"] = [
            {
                "name": "ShortLine",
                "type": "Sketcher::SketchObject",
                "label": "ShortLine",
                "params": {
                    "geometry": [
                        {"type": "line", "x1": 0, "y1": 0, "x2": 0.2, "y2": 0},
                    ],
                },
            }
        ]
        result = check_min_feature_size(proj["objects"], min_size_mm=0.5)
        assert result["passed"] is False


# ── Plate Fit Tests ──────────────────────────────────────────────────


class TestPlateFit:
    def test_fits_on_plate(self, project_with_box):
        result = check_plate_fit(
            project_with_box["objects"],
            plate_width_mm=500,
            plate_height_mm=300,
        )
        assert result["passed"] is True

    def test_too_wide_for_plate(self, project_with_box):
        # Box is 200mm wide, plate is 150mm
        result = check_plate_fit(
            project_with_box["objects"],
            plate_width_mm=150,
            plate_height_mm=300,
        )
        assert result["passed"] is False
        assert any("exceeds" in e.lower() or "Width" in e for e in result["errors"])

    def test_too_tall_for_plate(self, project_with_box):
        # Box height dimension in 2D top view = width param = 100mm
        result = check_plate_fit(
            project_with_box["objects"],
            plate_width_mm=500,
            plate_height_mm=2,  # Way too small
        )
        assert result["passed"] is False

    def test_kerf_margin_included(self, project_with_box):
        # Box is 200x100mm, plate is 200.5x100.5mm — fails because kerf adds margin
        result = check_plate_fit(
            project_with_box["objects"],
            plate_width_mm=200.1,
            plate_height_mm=100.1,
            kerf_width_mm=0.15,
        )
        assert result["passed"] is False

    def test_svg_dimensions(self, project_with_svg):
        result = check_plate_fit(
            project_with_svg["objects"],
            plate_width_mm=400,
            plate_height_mm=300,
        )
        assert result["passed"] is True
        assert result["details"]["geometry_width_mm"] == 300
        assert result["details"]["geometry_height_mm"] == 200


# ── Dimension Report Tests ───────────────────────────────────────────


class TestDimensionReport:
    def test_reports_box_dimensions(self, project_with_box):
        result = report_dimensions(project_with_box["objects"])
        assert result["passed"] is True
        assert result["details"]["width"] > 0
        assert result["details"]["height"] > 0

    def test_reports_svg_dimensions(self, project_with_svg):
        result = report_dimensions(project_with_svg["objects"])
        assert result["passed"] is True
        assert "300" in result["message"] or result["details"]["width"] == 300

    def test_empty_project(self):
        result = report_dimensions([])
        assert result["passed"] is True
        assert result["details"] == {}


# ── Kerf Advisory Tests ──────────────────────────────────────────────


class TestKerfAdvisory:
    def test_simple_plate_no_advisory(self, project_with_box):
        result = check_kerf_advisory(project_with_box["objects"])
        assert result["passed"] is True  # Advisory never fails

    def test_boolean_cut_triggers_advisory(self, tmp_dir):
        proj = create_project(name="CutTest", output_path=os.path.join(tmp_dir, "t.json"))
        proj["objects"] = [
            {"name": "Base", "type": "Part::Box", "params": {"length": 100, "width": 100, "height": 3}},
            {"name": "Hole", "type": "Part::Cylinder", "params": {"radius": 5, "height": 10}},
            {"name": "Result", "type": "Part::Cut", "params": {"base": "Base", "tool": "Hole"}},
        ]
        result = check_kerf_advisory(proj["objects"])
        assert result["details"]["has_internal_features"] is True
        assert len(result["warnings"]) > 0
        assert "kerf" in result["warnings"][0].lower()

    def test_small_circle_triggers_advisory(self, tmp_dir):
        proj = create_project(name="SmallCircle", output_path=os.path.join(tmp_dir, "t.json"))
        proj["objects"] = [
            {
                "name": "Drill",
                "type": "Sketcher::SketchObject",
                "params": {
                    "geometry": [{"type": "circle", "cx": 0, "cy": 0, "radius": 0.5}],
                },
            }
        ]
        result = check_kerf_advisory(proj["objects"])
        assert result["details"]["has_internal_features"] is True


# ── Full Validation Tests ────────────────────────────────────────────


class TestFullValidation:
    def test_good_project_passes(self, project_with_closed_sketch):
        report = validate_project_for_lasercut(project_with_closed_sketch)
        assert report["passed"] is True
        assert report["failed_count"] == 0

    def test_open_sketch_fails_validation(self, project_with_open_sketch):
        report = validate_project_for_lasercut(project_with_open_sketch)
        assert report["passed"] is False
        assert len(report["errors"]) > 0

    def test_with_plate_dimensions(self, project_with_closed_sketch):
        report = validate_project_for_lasercut(
            project_with_closed_sketch,
            plate_width_mm=500,
            plate_height_mm=300,
        )
        assert report["passed"] is True

    def test_nonexistent_object(self, project_with_box):
        report = validate_project_for_lasercut(
            project_with_box, object_name="Nonexistent"
        )
        assert report["passed"] is False
        assert any("not found" in e.lower() for e in report["errors"])

    def test_empty_project(self, tmp_dir):
        proj = create_project(name="Empty", output_path=os.path.join(tmp_dir, "t.json"))
        report = validate_project_for_lasercut(proj)
        assert report["passed"] is False

    def test_report_structure(self, project_with_box):
        report = validate_project_for_lasercut(project_with_box)
        assert "passed" in report
        assert "checks" in report
        assert "errors" in report
        assert "warnings" in report
        assert "summary" in report
        assert "check_count" in report
        assert "passed_count" in report
        assert "failed_count" in report

    def test_specific_object_validation(self, tmp_dir):
        proj = create_project(name="MultiObj", output_path=os.path.join(tmp_dir, "t.json"))
        proj["objects"] = [
            {"name": "Good", "type": "Part::Box", "params": {"length": 100, "width": 50, "height": 3}},
            {"name": "Bad", "type": "Part::Box", "params": {"length": 0.1, "width": 0.1, "height": 0.1}},
        ]
        # Validate only the good object
        report = validate_project_for_lasercut(proj, object_name="Good")
        assert report["passed"] is True


# ── Backend Script Generation Tests ──────────────────────────────────


class TestBackendScriptGeneration:
    def test_generates_valid_python(self):
        script = generate_validation_script("/tmp/test.FCStd")
        assert "import FreeCAD" in script
        assert "import Part" in script
        assert "FreeCAD.openDocument" in script

    def test_includes_wire_closure_check(self):
        script = generate_validation_script("/tmp/test.FCStd")
        assert "wire.isClosed()" in script
        assert "wires_closed" in script
        assert "wires_open" in script

    def test_includes_duplicate_detection(self):
        script = generate_validation_script("/tmp/test.FCStd")
        assert "duplicate_edges" in script

    def test_includes_bounding_box(self):
        script = generate_validation_script("/tmp/test.FCStd")
        assert "BoundBox" in script
        assert "bounding_box" in script

    def test_includes_small_feature_check(self):
        script = generate_validation_script("/tmp/test.FCStd")
        assert "small_features" in script
        assert "MIN_FEAT" in script

    def test_custom_parameters(self):
        script = generate_validation_script(
            "/tmp/test.FCStd",
            object_name="MyPart",
            closure_tolerance=0.05,
            min_feature_mm=1.0,
        )
        assert "MyPart" in script
        assert "0.05" in script
        assert "1.0" in script

    def test_object_filter_all(self):
        script = generate_validation_script("/tmp/test.FCStd")
        assert "hasattr(o, 'Shape')" in script

    def test_object_filter_specific(self):
        script = generate_validation_script("/tmp/test.FCStd", object_name="CutProfile")
        assert "doc.getObject('CutProfile')" in script


# ── CLI Command Tests ────────────────────────────────────────────────


class TestValidateLasercutCLI:
    def test_validate_json_output(self, runner, tmp_dir):
        proj_path = os.path.join(tmp_dir, "test.json")
        # Create project with box via CLI
        result = runner.invoke(cli, ["--json", "project", "new", "-o", proj_path])
        assert result.exit_code == 0

        result = runner.invoke(cli, [
            "--json", "--project", proj_path,
            "part", "box", "-n", "Plate", "-l", "200", "-w", "100", "-H", "3",
        ])
        assert result.exit_code == 0

        # Run validation
        result = runner.invoke(cli, [
            "--json", "--project", proj_path,
            "validate-lasercut",
        ])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "passed" in data
        assert "checks" in data

    def test_validate_with_plate(self, runner, tmp_dir):
        proj_path = os.path.join(tmp_dir, "test.json")
        result = runner.invoke(cli, ["--json", "project", "new", "-o", proj_path])
        assert result.exit_code == 0

        result = runner.invoke(cli, [
            "--json", "--project", proj_path,
            "part", "box", "-n", "Part1", "-l", "100", "-w", "50", "-H", "3",
        ])
        assert result.exit_code == 0

        result = runner.invoke(cli, [
            "--json", "--project", proj_path,
            "validate-lasercut",
            "--plate-width", "500",
            "--plate-height", "300",
        ])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["passed"] is True

    def test_validate_human_output(self, runner, tmp_dir):
        proj_path = os.path.join(tmp_dir, "test.json")
        result = runner.invoke(cli, ["project", "new", "-o", proj_path])
        assert result.exit_code == 0

        result = runner.invoke(cli, [
            "--project", proj_path,
            "part", "box", "-n", "Plate", "-l", "200", "-w", "100", "-H", "3",
        ])
        assert result.exit_code == 0

        result = runner.invoke(cli, [
            "--project", proj_path,
            "validate-lasercut",
        ])
        assert result.exit_code == 0
        assert "Lasercut Validation" in result.output

    def test_validate_no_project_errors(self, runner):
        """Without a project loaded, validation should error or return failure."""
        # Note: In CliRunner context, global session may carry state from
        # previous tests. In a fresh CLI invocation, this errors with exit 1.
        # We test both scenarios: either error (no project) or failed validation.
        import cli_anything.freecad.freecad_cli as cli_mod
        old_session = cli_mod._session
        cli_mod._session = Session()  # Fresh session, no project
        try:
            result = runner.invoke(cli, ["--json", "validate-lasercut"])
            data = json.loads(result.output)
            if result.exit_code != 0:
                assert "error" in data
            else:
                assert data["passed"] is False
        finally:
            cli_mod._session = old_session

    def test_validate_with_min_feature(self, runner, tmp_dir):
        proj_path = os.path.join(tmp_dir, "test.json")
        result = runner.invoke(cli, ["--json", "project", "new", "-o", proj_path])
        assert result.exit_code == 0

        result = runner.invoke(cli, [
            "--json", "--project", proj_path,
            "part", "box", "-n", "P", "-l", "2", "-w", "2", "-H", "2",
        ])
        assert result.exit_code == 0

        # With very high minimum, should flag features
        result = runner.invoke(cli, [
            "--json", "--project", proj_path,
            "validate-lasercut",
            "--min-feature", "5.0",
        ])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["passed"] is False


# ── Constants Tests ──────────────────────────────────────────────────


class TestObjectNameValidation:
    def test_valid_names(self):
        script = generate_validation_script("/tmp/t.FCStd", object_name="MyPart")
        assert "MyPart" in script

    def test_valid_name_with_dots(self):
        script = generate_validation_script("/tmp/t.FCStd", object_name="Part.001")
        assert "Part.001" in script

    def test_invalid_name_injection(self):
        with pytest.raises(ValueError, match="Invalid object name"):
            generate_validation_script("/tmp/t.FCStd", object_name="x\nmalicious()")

    def test_invalid_name_quotes(self):
        with pytest.raises(ValueError, match="Invalid object name"):
            generate_validation_script("/tmp/t.FCStd", object_name="x'; import os; os.system('rm -rf /')")

    def test_invalid_name_spaces(self):
        with pytest.raises(ValueError, match="Invalid object name"):
            generate_validation_script("/tmp/t.FCStd", object_name="My Part")


class TestConstants:
    def test_default_closure_tolerance(self):
        assert DEFAULT_CLOSURE_TOLERANCE_MM == 0.01

    def test_default_min_feature(self):
        assert DEFAULT_MIN_FEATURE_SIZE_MM == 0.5

    def test_default_kerf_width(self):
        assert DEFAULT_KERF_WIDTH_MM == 0.15
