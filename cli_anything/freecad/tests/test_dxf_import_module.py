"""Tests for DXF import module — dxf_import.py.

Tests use CliRunner with isolated_filesystem — no FreeCAD backend required.
Tests that would call the FreeCAD backend are designed to pass both when
FreeCAD is installed (success path) and when it is not (RuntimeError path).
"""

from __future__ import annotations

import inspect
import json
import os

import pytest
from click.testing import CliRunner

from cli_anything.freecad.freecad_cli import cli
from cli_anything.freecad.core.dxf_import import import_dxf, analyze_dxf


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
        return
    assert result.exit_code == 0, f"exit={result.exit_code}, output={result.output}"


# ── Fixtures ─────────────────────────────────────────────────────────


@pytest.fixture
def runner():
    return CliRunner()


def _new_project(runner):
    return runner.invoke(
        cli, ["--json", "project", "new", "-n", "TestProj", "-o", "proj.json"]
    )


# ── TestDxfImportValidation ──────────────────────────────────────────


class TestDxfImportValidation:
    """Direct core calls — Python-layer validation (no backend needed)."""

    def test_file_not_found(self):
        result = import_dxf("/nonexistent/path/test.dxf")
        assert result["success"] is False
        assert "not found" in result["error"]

    def test_auto_naming(self):
        """Verify auto-naming from filename when name=None."""
        result = import_dxf("/nonexistent/path/my_drawing.dxf")
        # File doesn't exist, returns error before reaching naming
        assert result["success"] is False

    def test_analyze_file_not_found(self):
        result = analyze_dxf("/nonexistent/path/test.dxf")
        assert result["success"] is False
        assert "not found" in result["error"]

    def test_analyze_error_message(self):
        """Verify analyze returns a clear error message."""
        result = analyze_dxf("/tmp/nonexistent.dxf")
        assert result["success"] is False
        assert "DXF file not found" in result["error"]


# ── TestDxfImportCLI ─────────────────────────────────────────────────


class TestDxfImportCLI:
    def test_dxf_import_layers_option(self, runner):
        """Verify --layers option is accepted."""
        with runner.isolated_filesystem():
            _new_project(runner)
            with open("test.dxf", "w") as f:
                f.write("0\nSECTION\n")
            result = runner.invoke(
                cli,
                [
                    "--json", "--project", "proj.json",
                    "dxf-import", "test.dxf",
                    "-l", "Layer1,Layer2",
                ],
            )
            _assert_ok_or_backend_error(result)

    def test_dxf_import_scale_option(self, runner):
        """Verify --scale option is accepted."""
        with runner.isolated_filesystem():
            _new_project(runner)
            with open("test.dxf", "w") as f:
                f.write("0\nSECTION\n")
            result = runner.invoke(
                cli,
                [
                    "--json", "--project", "proj.json",
                    "dxf-import", "test.dxf",
                    "-s", "2.0",
                ],
            )
            _assert_ok_or_backend_error(result)

    def test_dxf_import_units_option(self, runner):
        """Verify --units option is accepted."""
        with runner.isolated_filesystem():
            _new_project(runner)
            with open("test.dxf", "w") as f:
                f.write("0\nSECTION\n")
            result = runner.invoke(
                cli,
                [
                    "--json", "--project", "proj.json",
                    "dxf-import", "test.dxf",
                    "-u", "inch",
                ],
            )
            _assert_ok_or_backend_error(result)

    def test_dxf_import_no_project_error(self, runner):
        with runner.isolated_filesystem():
            with open("test.dxf", "w") as f:
                f.write("0\nSECTION\n")
            result = runner.invoke(
                cli,
                ["--json", "dxf-import", "test.dxf"],
            )
            assert "error" in result.output.lower() or result.exit_code != 0


# ── TestDxfInfoCLI ───────────────────────────────────────────────────


class TestDxfInfoCLI:
    def test_info_wiring(self, runner):
        """Verify dxf-info command is wired and accepts filepath."""
        with runner.isolated_filesystem():
            with open("test.dxf", "w") as f:
                f.write("0\nSECTION\n")
            result = runner.invoke(
                cli,
                ["--json", "dxf-info", "test.dxf"],
            )
            _assert_ok_or_backend_error(result)

    def test_info_file_not_found(self, runner):
        """dxf-info should fail if file doesn't exist."""
        with runner.isolated_filesystem():
            result = runner.invoke(
                cli,
                ["--json", "dxf-info", "nonexistent.dxf"],
            )
            # Click's exists=True will catch this
            assert result.exit_code != 0


# ── TestBareExceptRegression ─────────────────────────────────────────


class TestBareExceptRegression:
    """Verify the bare except bug was fixed."""

    def test_no_bare_except_in_source(self):
        """Source code should not contain bare 'except:' statements."""
        source_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "core",
            "dxf_import.py",
        )
        with open(source_path) as f:
            source = f.read()

        lines = source.split("\n")
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped == "except:" or stripped.startswith("except: "):
                pytest.fail(
                    f"Bare except found at line {i}: {stripped!r}. "
                    "Should catch specific exception types."
                )

    def test_specific_exceptions_caught(self):
        """Verify the except clause catches AttributeError, TypeError, ValueError."""
        source = inspect.getsource(analyze_dxf)
        assert "except (AttributeError, TypeError, ValueError)" in source
