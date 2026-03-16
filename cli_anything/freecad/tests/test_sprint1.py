"""Tests for new Part and Sketcher commands (Sprint 1)."""

import json
import os
import tempfile
import pytest
from click.testing import CliRunner

from cli_anything.freecad.freecad_cli import cli
from cli_anything.freecad.core.session import Session
from cli_anything.freecad.core.project import _object_to_script


class TestPartOffset:
    """Tests for part_offset command."""

    def test_offset_basic(self):
        """Test basic offset creation."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(
                cli,
                ["--json", "project", "new", "-n", "TestProj", "-o", "proj.json"],
            )
            assert result.exit_code == 0
            result = runner.invoke(
                cli, ["--json", "--project", "proj.json", "part", "box", "-l", "10", "-w", "10", "-H", "10"]
            )
            assert result.exit_code == 0
            result = runner.invoke(
                cli,
                [
                    "--json",
                    "--project",
                    "proj.json",
                    "part",
                    "offset",
                    "Box",
                    "-d",
                    "2.0",
                ],
            )
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert data["name"] == "Offset"
            assert data["type"] == "Part::Offset"
            assert data["params"]["source"] == "Box"
            assert data["params"]["distance"] == 2.0

    def test_offset_script_generation(self):
        """Test FreeCAD script generation for offset."""
        obj = {
            "name": "Offset1",
            "type": "Part::Offset",
            "params": {"source": "Box1", "distance": 2.5, "mode": "skin"},
        }
        script = _object_to_script(obj)
        assert "Part::Offset" in script
        assert "Box1" in script
        assert "2.5" in script
        assert "skin" in script


class TestPartThicken:
    """Tests for part_thicken command."""

    def test_thicken_basic(self):
        """Test basic thicken creation."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(
                cli,
                ["--json", "project", "new", "-n", "TestProj", "-o", "proj.json"],
            )
            assert result.exit_code == 0
            result = runner.invoke(
                cli, ["--json", "--project", "proj.json", "part", "box", "-l", "10", "-w", "10", "-H", "10"]
            )
            assert result.exit_code == 0
            result = runner.invoke(
                cli,
                [
                    "--json",
                    "--project",
                    "proj.json",
                    "part",
                    "thicken",
                    "Box",
                    "-t",
                    "3.0",
                ],
            )
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert data["name"] == "Thicken"
            assert data["type"] == "Part::Thickness"
            assert data["params"]["source"] == "Box"
            assert data["params"]["thickness"] == 3.0

    def test_thicken_with_faces(self):
        """Test thicken with specific faces."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(
                cli,
                ["--json", "project", "new", "-n", "TestProj", "-o", "proj.json"],
            )
            assert result.exit_code == 0
            result = runner.invoke(
                cli, ["--json", "--project", "proj.json", "part", "box"]
            )
            assert result.exit_code == 0
            result = runner.invoke(
                cli,
                [
                    "--json",
                    "--project",
                    "proj.json",
                    "part",
                    "thicken",
                    "Box",
                    "-t",
                    "2.0",
                    "--faces",
                    "1,2,3",
                ],
            )
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert data["params"]["faces"] == [1, 2, 3]


class TestPartDraft:
    """Tests for part_draft command."""

    def test_draft_basic(self):
        """Test basic draft creation."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(
                cli,
                ["--json", "project", "new", "-n", "TestProj", "-o", "proj.json"],
            )
            assert result.exit_code == 0
            result = runner.invoke(
                cli, ["--json", "--project", "proj.json", "part", "box"]
            )
            assert result.exit_code == 0
            result = runner.invoke(
                cli,
                [
                    "--json",
                    "--project",
                    "proj.json",
                    "part",
                    "draft",
                    "Box",
                    "-a",
                    "5.0",
                ],
            )
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert data["name"] == "Draft"
            assert data["type"] == "Part::Draft"
            assert data["params"]["source"] == "Box"
            assert data["params"]["angle"] == 5.0

    def test_draft_script_generation(self):
        """Test FreeCAD script generation for draft."""
        obj = {
            "name": "Draft1",
            "type": "Part::Draft",
            "params": {
                "source": "Box1",
                "angle": 3.0,
                "direction_x": 0,
                "direction_y": 0,
                "direction_z": 1,
                "neutral_x": 0,
                "neutral_y": 0,
                "neutral_z": 0,
            },
        }
        script = _object_to_script(obj)
        assert "Part::Draft" in script
        assert "Box1" in script
        assert "3.0" in script


class TestPartScale:
    """Tests for part_scale command."""

    def test_scale_uniform(self):
        """Test uniform scale."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(
                cli,
                ["--json", "project", "new", "-n", "TestProj", "-o", "proj.json"],
            )
            assert result.exit_code == 0
            result = runner.invoke(
                cli, ["--json", "--project", "proj.json", "part", "box"]
            )
            assert result.exit_code == 0
            result = runner.invoke(
                cli,
                [
                    "--json",
                    "--project",
                    "proj.json",
                    "part",
                    "scale",
                    "Box",
                    "-s",
                    "2.0",
                ],
            )
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert data["name"] == "Scale"
            assert data["type"] == "Part::Scale"
            assert data["params"]["sx"] == 2.0
            assert data["params"]["sy"] == 2.0
            assert data["params"]["sz"] == 2.0

    def test_scale_non_uniform(self):
        """Test non-uniform scale."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(
                cli,
                ["--json", "project", "new", "-n", "TestProj", "-o", "proj.json"],
            )
            assert result.exit_code == 0
            result = runner.invoke(
                cli, ["--json", "--project", "proj.json", "part", "box"]
            )
            assert result.exit_code == 0
            result = runner.invoke(
                cli,
                [
                    "--json",
                    "--project",
                    "proj.json",
                    "part",
                    "scale",
                    "Box",
                    "--sx",
                    "2.0",
                    "--sy",
                    "1.5",
                    "--sz",
                    "0.5",
                ],
            )
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert data["params"]["sx"] == 2.0
            assert data["params"]["sy"] == 1.5
            assert data["params"]["sz"] == 0.5


class TestPartSection:
    """Tests for part_section command."""

    def test_section_xy(self):
        """Test section on XY plane."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(
                cli,
                ["--json", "project", "new", "-n", "TestProj", "-o", "proj.json"],
            )
            assert result.exit_code == 0
            result = runner.invoke(
                cli, ["--json", "--project", "proj.json", "part", "box"]
            )
            assert result.exit_code == 0
            result = runner.invoke(
                cli,
                [
                    "--json",
                    "--project",
                    "proj.json",
                    "part",
                    "section",
                    "Box",
                    "--plane",
                    "XY",
                    "--offset",
                    "5.0",
                ],
            )
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert data["name"] == "Section"
            assert data["type"] == "Part::Section"
            assert data["params"]["source"] == "Box"
            assert data["params"]["plane"] == "XY"
            assert data["params"]["offset"] == 5.0


class TestSketchSpline:
    """Tests for sketch_spline command."""

    def test_spline_basic(self):
        """Test basic spline creation."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(
                cli,
                ["--json", "project", "new", "-n", "TestProj", "-o", "proj.json"],
            )
            assert result.exit_code == 0
            result = runner.invoke(
                cli, ["--json", "--project", "proj.json", "sketch", "new", "-p", "XY"]
            )
            assert result.exit_code == 0
            result = runner.invoke(
                cli,
                [
                    "--json",
                    "--project",
                    "proj.json",
                    "sketch",
                    "spline",
                    "Sketch",
                    "--points",
                    "0,0;5,5;10,0",
                    "--degree",
                    "3",
                ],
            )
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert data["type"] == "spline"
            assert len(data["control_points"]) == 3
            assert data["degree"] == 3

    def test_spline_invalid_degree(self):
        """Test spline with invalid degree."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(
                cli,
                ["--json", "project", "new", "-n", "TestProj", "-o", "proj.json"],
            )
            assert result.exit_code == 0
            result = runner.invoke(
                cli, ["--json", "--project", "proj.json", "sketch", "new"]
            )
            assert result.exit_code == 0
            result = runner.invoke(
                cli,
                [
                    "--json",
                    "--project",
                    "proj.json",
                    "sketch",
                    "spline",
                    "Sketch",
                    "--points",
                    "0,0;5,5",
                    "--degree",
                    "1",
                ],
            )
            assert result.exit_code != 0


class TestSketchTrim:
    """Tests for sketch_trim command."""

    def test_trim_basic(self):
        """Test basic trim creation."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(
                cli,
                ["--json", "project", "new", "-n", "TestProj", "-o", "proj.json"],
            )
            assert result.exit_code == 0
            result = runner.invoke(
                cli, ["--json", "--project", "proj.json", "sketch", "new"]
            )
            assert result.exit_code == 0
            result = runner.invoke(
                cli,
                [
                    "--json",
                    "--project",
                    "proj.json",
                    "sketch",
                    "line",
                    "Sketch",
                    "--x1",
                    "0",
                    "--y1",
                    "0",
                    "--x2",
                    "10",
                    "--y2",
                    "10",
                ],
            )
            assert result.exit_code == 0
            result = runner.invoke(
                cli,
                [
                    "--json",
                    "--project",
                    "proj.json",
                    "sketch",
                    "trim",
                    "Sketch",
                    "-g",
                    "0",
                    "--pos-x",
                    "5",
                    "--pos-y",
                    "5",
                ],
            )
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert data["type"] == "trim"
            assert data["geometry_index"] == 0


class TestSketchFillet:
    """Tests for sketch_fillet command."""

    def test_fillet_basic(self):
        """Test basic fillet creation."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(
                cli,
                ["--json", "project", "new", "-n", "TestProj", "-o", "proj.json"],
            )
            assert result.exit_code == 0
            result = runner.invoke(
                cli, ["--json", "--project", "proj.json", "sketch", "new"]
            )
            assert result.exit_code == 0
            # Add two lines
            result = runner.invoke(
                cli,
                [
                    "--json",
                    "--project",
                    "proj.json",
                    "sketch",
                    "line",
                    "Sketch",
                    "--x1",
                    "0",
                    "--y1",
                    "0",
                    "--x2",
                    "10",
                    "--y2",
                    "0",
                ],
            )
            assert result.exit_code == 0
            result = runner.invoke(
                cli,
                [
                    "--json",
                    "--project",
                    "proj.json",
                    "sketch",
                    "line",
                    "Sketch",
                    "--x1",
                    "10",
                    "--y1",
                    "0",
                    "--x2",
                    "10",
                    "--y2",
                    "10",
                ],
            )
            assert result.exit_code == 0
            result = runner.invoke(
                cli,
                [
                    "--json",
                    "--project",
                    "proj.json",
                    "sketch",
                    "sketch-fillet",
                    "Sketch",
                    "-g1",
                    "0",
                    "-g2",
                    "1",
                    "-r",
                    "2.0",
                ],
            )
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert data["type"] == "fillet"
            assert data["geometry1"] == 0
            assert data["geometry2"] == 1
            assert data["radius"] == 2.0


class TestSketchOffset:
    """Tests for sketch_offset command."""

    def test_offset_basic(self):
        """Test basic offset creation."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(
                cli,
                ["--json", "project", "new", "-n", "TestProj", "-o", "proj.json"],
            )
            assert result.exit_code == 0
            result = runner.invoke(
                cli, ["--json", "--project", "proj.json", "sketch", "new"]
            )
            assert result.exit_code == 0
            result = runner.invoke(
                cli,
                [
                    "--json",
                    "--project",
                    "proj.json",
                    "sketch",
                    "circle",
                    "Sketch",
                    "--cx",
                    "0",
                    "--cy",
                    "0",
                    "-r",
                    "5",
                ],
            )
            assert result.exit_code == 0
            result = runner.invoke(
                cli,
                [
                    "--json",
                    "--project",
                    "proj.json",
                    "sketch",
                    "sketch-offset",
                    "Sketch",
                    "-g",
                    "0",
                    "-d",
                    "2.0",
                ],
            )
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert data["type"] == "offset"
            assert data["geometry_index"] == 0
            assert data["distance"] == 2.0
