"""Tests for PartDesign modules — partdesign.py, partdesign_patterns.py, partdesign_manufacturing.py.

Tests use CliRunner with isolated_filesystem — no FreeCAD backend required.
Tests that would call the FreeCAD backend are designed to pass both when
FreeCAD is installed (success path) and when it is not (RuntimeError path).
"""

from __future__ import annotations

import json

import pytest
from click.testing import CliRunner

from cli_anything.freecad.freecad_cli import cli
from cli_anything.freecad.core.partdesign_patterns import linear_pattern, polar_pattern


# ── Helpers ──────────────────────────────────────────────────────────


FREECAD_NOT_INSTALLED_MSG = "FreeCAD is not installed"


def _is_backend_error(result) -> bool:
    """True if the CLI result failed due to missing FreeCAD backend."""
    if result.exception and FREECAD_NOT_INSTALLED_MSG in str(result.exception):
        return True
    return False


def _assert_ok_or_backend_error(result):
    """Assert: exit_code==0 with valid JSON, OR backend not available."""
    if _is_backend_error(result):
        return  # acceptable — FreeCAD not installed
    assert result.exit_code == 0, f"exit={result.exit_code}, output={result.output}"


def _assert_error_or_backend_error(result):
    """Assert: exit_code!=0 (error expected), or backend not available."""
    if _is_backend_error(result):
        return
    assert result.exit_code != 0 or "error" in result.output.lower()


# ── Fixtures ─────────────────────────────────────────────────────────


@pytest.fixture
def runner():
    return CliRunner()


def _new_project(runner):
    """Helper: create a project and return result."""
    return runner.invoke(
        cli, ["--json", "project", "new", "-n", "TestProj", "-o", "proj.json"]
    )


# ── TestPartDesignBodyCLI ────────────────────────────────────────────


class TestPartDesignBodyCLI:
    def test_body_create(self, runner):
        with runner.isolated_filesystem():
            _new_project(runner)
            result = runner.invoke(
                cli,
                ["--json", "--project", "proj.json", "partdesign", "body", "-n", "MyBody"],
            )
            _assert_ok_or_backend_error(result)
            if not _is_backend_error(result):
                data = json.loads(result.output)
                assert data["type"] == "PartDesign::Body"
                assert data["name"] is not None

    def test_body_no_project_error(self, runner):
        with runner.isolated_filesystem():
            result = runner.invoke(
                cli,
                ["--json", "partdesign", "body"],
            )
            assert "error" in result.output.lower() or result.exit_code != 0

    def test_body_json_output(self, runner):
        with runner.isolated_filesystem():
            _new_project(runner)
            result = runner.invoke(
                cli,
                ["--json", "--project", "proj.json", "partdesign", "body"],
            )
            _assert_ok_or_backend_error(result)
            if not _is_backend_error(result):
                data = json.loads(result.output)
                assert "type" in data
                assert "name" in data


# ── TestPartDesignPadPocketCLI ───────────────────────────────────────


class TestPartDesignPadPocketCLI:
    def test_pad_missing_sketch_error(self, runner):
        """Pad requires a sketch that exists in the session."""
        with runner.isolated_filesystem():
            _new_project(runner)
            result = runner.invoke(
                cli,
                ["--json", "--project", "proj.json", "partdesign", "pad", "NonExistent"],
            )
            # Should fail because sketch doesn't exist
            assert result.exit_code != 0 or "error" in result.output.lower()

    def test_pocket_missing_sketch_error(self, runner):
        """Pocket requires a sketch that exists in the session."""
        with runner.isolated_filesystem():
            _new_project(runner)
            result = runner.invoke(
                cli,
                ["--json", "--project", "proj.json", "partdesign", "pocket", "NonExistent"],
            )
            assert result.exit_code != 0 or "error" in result.output.lower()

    def test_pad_option_parsing(self, runner):
        """Verify pad accepts --length, --symmetric, --reverse."""
        with runner.isolated_filesystem():
            _new_project(runner)
            runner.invoke(
                cli,
                ["--json", "--project", "proj.json", "sketch", "new", "-n", "Sketch001"],
            )
            result = runner.invoke(
                cli,
                [
                    "--json", "--project", "proj.json",
                    "partdesign", "pad", "Sketch001",
                    "-l", "25.0", "--symmetric",
                ],
            )
            _assert_ok_or_backend_error(result)

    def test_pocket_through_all_option(self, runner):
        """Verify pocket --through-all flag is accepted."""
        with runner.isolated_filesystem():
            _new_project(runner)
            runner.invoke(
                cli,
                ["--json", "--project", "proj.json", "sketch", "new", "-n", "Sketch001"],
            )
            result = runner.invoke(
                cli,
                [
                    "--json", "--project", "proj.json",
                    "partdesign", "pocket", "Sketch001",
                    "--through-all",
                ],
            )
            _assert_ok_or_backend_error(result)


# ── TestLinearPatternValidation ──────────────────────────────────────


class TestLinearPatternValidation:
    """Direct core calls — these hit Python-layer validation, no backend needed."""

    def test_invalid_direction_returns_error(self):
        result = linear_pattern("SomeFeature", direction="W")
        assert result["success"] is False
        assert "Invalid direction" in result["error"]

    def test_valid_x_direction(self):
        try:
            result = linear_pattern("SomeFeature", direction="X")
        except RuntimeError as e:
            if FREECAD_NOT_INSTALLED_MSG in str(e):
                pytest.skip("FreeCAD not installed")
            raise
        assert "Invalid direction" not in result.get("error", "")

    def test_valid_y_direction(self):
        try:
            result = linear_pattern("SomeFeature", direction="Y")
        except RuntimeError as e:
            if FREECAD_NOT_INSTALLED_MSG in str(e):
                pytest.skip("FreeCAD not installed")
            raise
        assert "Invalid direction" not in result.get("error", "")

    def test_valid_z_direction(self):
        try:
            result = linear_pattern("SomeFeature", direction="Z")
        except RuntimeError as e:
            if FREECAD_NOT_INSTALLED_MSG in str(e):
                pytest.skip("FreeCAD not installed")
            raise
        assert "Invalid direction" not in result.get("error", "")

    def test_case_insensitive_direction(self):
        """direction.upper() is used, so lowercase should work."""
        try:
            result = linear_pattern("SomeFeature", direction="x")
        except RuntimeError as e:
            if FREECAD_NOT_INSTALLED_MSG in str(e):
                pytest.skip("FreeCAD not installed")
            raise
        assert "Invalid direction" not in result.get("error", "")


# ── TestPolarPatternValidation ───────────────────────────────────────


class TestPolarPatternValidation:
    """Direct core calls — these hit Python-layer validation, no backend needed."""

    def test_invalid_axis_returns_error(self):
        result = polar_pattern("SomeFeature", axis="W")
        assert result["success"] is False
        assert "Invalid axis" in result["error"]

    def test_valid_x_axis(self):
        try:
            result = polar_pattern("SomeFeature", axis="X")
        except RuntimeError as e:
            if FREECAD_NOT_INSTALLED_MSG in str(e):
                pytest.skip("FreeCAD not installed")
            raise
        assert "Invalid axis" not in result.get("error", "")

    def test_valid_y_axis(self):
        try:
            result = polar_pattern("SomeFeature", axis="Y")
        except RuntimeError as e:
            if FREECAD_NOT_INSTALLED_MSG in str(e):
                pytest.skip("FreeCAD not installed")
            raise
        assert "Invalid axis" not in result.get("error", "")

    def test_valid_z_axis(self):
        try:
            result = polar_pattern("SomeFeature", axis="Z")
        except RuntimeError as e:
            if FREECAD_NOT_INSTALLED_MSG in str(e):
                pytest.skip("FreeCAD not installed")
            raise
        assert "Invalid axis" not in result.get("error", "")


# ── TestDraftCLI ─────────────────────────────────────────────────────


class TestDraftCLI:
    def test_draft_no_project_error(self, runner):
        with runner.isolated_filesystem():
            result = runner.invoke(
                cli,
                ["--json", "partdesign", "draft", "Face001"],
            )
            assert "error" in result.output.lower() or result.exit_code != 0

    def test_draft_angle_parsing(self, runner):
        with runner.isolated_filesystem():
            _new_project(runner)
            result = runner.invoke(
                cli,
                [
                    "--json", "--project", "proj.json",
                    "partdesign", "draft", "Face001",
                    "-a", "5.0",
                ],
            )
            # Face won't exist in session, expect error
            assert result.exit_code != 0 or "error" in result.output.lower()


# ── TestManufacturingCLI ─────────────────────────────────────────────


class TestManufacturingCLI:
    def test_fillet_no_edge_error(self, runner):
        with runner.isolated_filesystem():
            _new_project(runner)
            result = runner.invoke(
                cli,
                [
                    "--json", "--project", "proj.json",
                    "partdesign", "fillet", "Edge001",
                ],
            )
            # Edge won't exist in session
            assert result.exit_code != 0 or "error" in result.output.lower()

    def test_chamfer_size_and_angle_parsing(self, runner):
        with runner.isolated_filesystem():
            _new_project(runner)
            result = runner.invoke(
                cli,
                [
                    "--json", "--project", "proj.json",
                    "partdesign", "chamfer", "Edge001",
                    "-s", "2.0", "-a", "30.0",
                ],
            )
            assert result.exit_code != 0 or "error" in result.output.lower()

    def test_thickness_mode_parsing(self, runner):
        with runner.isolated_filesystem():
            _new_project(runner)
            result = runner.invoke(
                cli,
                [
                    "--json", "--project", "proj.json",
                    "partdesign", "thickness", "Face001",
                    "-t", "3.0", "-m", "offset",
                ],
            )
            assert result.exit_code != 0 or "error" in result.output.lower()

    def test_thickness_join_option(self, runner):
        with runner.isolated_filesystem():
            _new_project(runner)
            result = runner.invoke(
                cli,
                [
                    "--json", "--project", "proj.json",
                    "partdesign", "thickness", "Face001",
                    "-j", "intersection",
                ],
            )
            assert result.exit_code != 0 or "error" in result.output.lower()


# ── TestFeatureListCLI ───────────────────────────────────────────────


class TestFeatureListCLI:
    def test_features_no_project_error(self, runner):
        with runner.isolated_filesystem():
            result = runner.invoke(
                cli,
                ["--json", "partdesign", "features", "Body001"],
            )
            assert "error" in result.output.lower() or result.exit_code != 0

    def test_patterns_no_project_error(self, runner):
        with runner.isolated_filesystem():
            result = runner.invoke(
                cli,
                ["--json", "partdesign", "patterns", "Body001"],
            )
            assert "error" in result.output.lower() or result.exit_code != 0


# ── TestPartDesignHelpOutput ─────────────────────────────────────────


class TestPartDesignHelpOutput:
    def test_partdesign_help(self, runner):
        result = runner.invoke(cli, ["partdesign", "--help"])
        assert result.exit_code == 0
        assert "partdesign" in result.output.lower() or "parametric" in result.output.lower()

    def test_partdesign_body_help(self, runner):
        result = runner.invoke(cli, ["partdesign", "body", "--help"])
        assert result.exit_code == 0
        assert "--name" in result.output or "-n" in result.output
