"""Tests for Assembly workbench — assembly.py.

Tests use CliRunner with isolated_filesystem — no FreeCAD backend required.
Tests that would call the FreeCAD backend are designed to pass both when
FreeCAD is installed (success path) and when it is not (RuntimeError path).
"""

from __future__ import annotations

import json

import pytest
from click.testing import CliRunner

from cli_anything.freecad.freecad_cli import cli


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
    return runner.invoke(
        cli, ["--json", "project", "new", "-n", "TestProj", "-o", "proj.json"]
    )


# ── TestAssemblyCreateCLI ────────────────────────────────────────────


class TestAssemblyCreateCLI:
    def test_create_assembly(self, runner):
        with runner.isolated_filesystem():
            _new_project(runner)
            result = runner.invoke(
                cli,
                ["--json", "--project", "proj.json", "assembly", "create", "-n", "Assy1"],
            )
            _assert_ok_or_backend_error(result)
            if not _is_backend_error(result):
                data = json.loads(result.output)
                assert data["type"] == "Assembly::AssemblyObject"

    def test_create_with_parts(self, runner):
        with runner.isolated_filesystem():
            _new_project(runner)
            runner.invoke(
                cli,
                ["--json", "--project", "proj.json", "part", "box", "-n", "Part1"],
            )
            runner.invoke(
                cli,
                ["--json", "--project", "proj.json", "part", "box", "-n", "Part2"],
            )
            result = runner.invoke(
                cli,
                [
                    "--json", "--project", "proj.json",
                    "assembly", "create", "-n", "Assy1",
                    "-p", "Part1,Part2",
                ],
            )
            _assert_ok_or_backend_error(result)
            if not _is_backend_error(result):
                data = json.loads(result.output)
                assert data["type"] == "Assembly::AssemblyObject"

    def test_create_no_project_error(self, runner):
        with runner.isolated_filesystem():
            result = runner.invoke(
                cli,
                ["--json", "assembly", "create"],
            )
            assert "error" in result.output.lower() or result.exit_code != 0


# ── TestAssemblyAddPartCLI ───────────────────────────────────────────


class TestAssemblyAddPartCLI:
    def test_add_part_with_placement(self, runner):
        with runner.isolated_filesystem():
            _new_project(runner)
            runner.invoke(
                cli,
                ["--json", "--project", "proj.json", "assembly", "create", "-n", "Assy1"],
            )
            result = runner.invoke(
                cli,
                [
                    "--json", "--project", "proj.json",
                    "assembly", "add-part", "Assy1", "SomePart",
                    "-x", "10", "-y", "20", "-z", "30",
                ],
            )
            _assert_ok_or_backend_error(result)

    def test_add_part_without_placement(self, runner):
        with runner.isolated_filesystem():
            _new_project(runner)
            runner.invoke(
                cli,
                ["--json", "--project", "proj.json", "assembly", "create", "-n", "Assy1"],
            )
            result = runner.invoke(
                cli,
                [
                    "--json", "--project", "proj.json",
                    "assembly", "add-part", "Assy1", "SomePart",
                ],
            )
            _assert_ok_or_backend_error(result)

    def test_add_part_no_project_error(self, runner):
        with runner.isolated_filesystem():
            result = runner.invoke(
                cli,
                ["--json", "assembly", "add-part", "Assy1", "Part1"],
            )
            assert "error" in result.output.lower() or result.exit_code != 0


# ── TestAssemblyConstraintCLI ────────────────────────────────────────


class TestAssemblyConstraintCLI:
    def test_constraint_types(self, runner):
        """Verify all constraint types are accepted by Click Choice."""
        with runner.isolated_filesystem():
            _new_project(runner)
            runner.invoke(
                cli,
                ["--json", "--project", "proj.json", "assembly", "create", "-n", "Assy1"],
            )
            for ctype in ["coincident", "parallel", "perpendicular", "distance"]:
                result = runner.invoke(
                    cli,
                    [
                        "--json", "--project", "proj.json",
                        "assembly", "constraint", "Assy1", "P1", "P2",
                        "-t", ctype,
                    ],
                )
                _assert_ok_or_backend_error(result)

    def test_constraint_wiring(self, runner):
        with runner.isolated_filesystem():
            _new_project(runner)
            runner.invoke(
                cli,
                ["--json", "--project", "proj.json", "assembly", "create", "-n", "Assy1"],
            )
            result = runner.invoke(
                cli,
                [
                    "--json", "--project", "proj.json",
                    "assembly", "constraint", "Assy1", "PartA", "PartB",
                ],
            )
            _assert_ok_or_backend_error(result)

    def test_constraint_no_project_error(self, runner):
        with runner.isolated_filesystem():
            result = runner.invoke(
                cli,
                ["--json", "assembly", "constraint", "Assy1", "P1", "P2"],
            )
            assert "error" in result.output.lower() or result.exit_code != 0


# ── TestAssemblyExplodeCLI ───────────────────────────────────────────


class TestAssemblyExplodeCLI:
    def test_explode_factor(self, runner):
        with runner.isolated_filesystem():
            _new_project(runner)
            runner.invoke(
                cli,
                ["--json", "--project", "proj.json", "assembly", "create", "-n", "Assy1"],
            )
            result = runner.invoke(
                cli,
                [
                    "--json", "--project", "proj.json",
                    "assembly", "explode", "Assy1",
                    "-f", "2.5",
                ],
            )
            _assert_ok_or_backend_error(result)

    def test_explode_no_project_error(self, runner):
        with runner.isolated_filesystem():
            result = runner.invoke(
                cli,
                ["--json", "assembly", "explode", "Assy1"],
            )
            assert "error" in result.output.lower() or result.exit_code != 0


# ── TestAssemblyInfoCLI ──────────────────────────────────────────────


class TestAssemblyInfoCLI:
    def test_info_wiring(self, runner):
        with runner.isolated_filesystem():
            _new_project(runner)
            runner.invoke(
                cli,
                ["--json", "--project", "proj.json", "assembly", "create", "-n", "Assy1"],
            )
            result = runner.invoke(
                cli,
                ["--json", "--project", "proj.json", "assembly", "info", "Assy1"],
            )
            _assert_ok_or_backend_error(result)

    def test_info_no_project_error(self, runner):
        with runner.isolated_filesystem():
            result = runner.invoke(
                cli,
                ["--json", "assembly", "info", "Assy1"],
            )
            assert "error" in result.output.lower() or result.exit_code != 0


# ── TestAssemblyHelpOutput ───────────────────────────────────────────


class TestAssemblyHelpOutput:
    def test_assembly_help(self, runner):
        result = runner.invoke(cli, ["assembly", "--help"])
        assert result.exit_code == 0
        assert "assembly" in result.output.lower() or "multi-part" in result.output.lower()
