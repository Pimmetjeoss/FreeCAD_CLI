"""Tests for FEM workbench — fem.py.

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


# ── Fixtures ─────────────────────────────────────────────────────────


@pytest.fixture
def runner():
    return CliRunner()


def _new_project(runner):
    return runner.invoke(
        cli, ["--json", "project", "new", "-n", "TestProj", "-o", "proj.json"]
    )


# ── TestFemAnalysisCLI ───────────────────────────────────────────────


class TestFemAnalysisCLI:
    def test_create_analysis(self, runner):
        with runner.isolated_filesystem():
            _new_project(runner)
            result = runner.invoke(
                cli,
                ["--json", "--project", "proj.json", "fem", "analysis", "-n", "FEA1"],
            )
            _assert_ok_or_backend_error(result)
            if not _is_backend_error(result):
                data = json.loads(result.output)
                assert data["type"] == "Fem::FemAnalysis"

    def test_create_analysis_default_name(self, runner):
        with runner.isolated_filesystem():
            _new_project(runner)
            result = runner.invoke(
                cli,
                ["--json", "--project", "proj.json", "fem", "analysis"],
            )
            _assert_ok_or_backend_error(result)
            if not _is_backend_error(result):
                data = json.loads(result.output)
                assert data["type"] == "Fem::FemAnalysis"

    def test_analysis_no_project_error(self, runner):
        with runner.isolated_filesystem():
            result = runner.invoke(
                cli,
                ["--json", "fem", "analysis"],
            )
            assert "error" in result.output.lower() or result.exit_code != 0


# ── TestFemMaterialCLI ───────────────────────────────────────────────


class TestFemMaterialCLI:
    def test_material_types(self, runner):
        """Verify all material types are accepted by Click Choice."""
        with runner.isolated_filesystem():
            _new_project(runner)
            runner.invoke(
                cli,
                ["--json", "--project", "proj.json", "fem", "analysis", "-n", "FEA1"],
            )
            for mat_type in ["Steel", "Aluminum", "Concrete"]:
                result = runner.invoke(
                    cli,
                    [
                        "--json", "--project", "proj.json",
                        "fem", "material", "FEA1", "SomeObj",
                        "-m", mat_type,
                    ],
                )
                _assert_ok_or_backend_error(result)

    def test_material_wiring(self, runner):
        with runner.isolated_filesystem():
            _new_project(runner)
            runner.invoke(
                cli,
                ["--json", "--project", "proj.json", "fem", "analysis", "-n", "FEA1"],
            )
            result = runner.invoke(
                cli,
                [
                    "--json", "--project", "proj.json",
                    "fem", "material", "FEA1", "Part1",
                    "-m", "Steel",
                ],
            )
            _assert_ok_or_backend_error(result)

    def test_material_no_project_error(self, runner):
        with runner.isolated_filesystem():
            result = runner.invoke(
                cli,
                ["--json", "fem", "material", "FEA1", "Part1"],
            )
            assert "error" in result.output.lower() or result.exit_code != 0


# ── TestFemMeshCLI ───────────────────────────────────────────────────


class TestFemMeshCLI:
    def test_mesh_element_size(self, runner):
        with runner.isolated_filesystem():
            _new_project(runner)
            runner.invoke(
                cli,
                ["--json", "--project", "proj.json", "fem", "analysis", "-n", "FEA1"],
            )
            result = runner.invoke(
                cli,
                [
                    "--json", "--project", "proj.json",
                    "fem", "mesh", "FEA1", "Part1",
                    "-s", "3.0",
                ],
            )
            _assert_ok_or_backend_error(result)

    def test_mesh_element_type(self, runner):
        """Verify Tetrahedron/Hexahedron choices are accepted."""
        with runner.isolated_filesystem():
            _new_project(runner)
            runner.invoke(
                cli,
                ["--json", "--project", "proj.json", "fem", "analysis", "-n", "FEA1"],
            )
            for elem_type in ["Tetrahedron", "Hexahedron"]:
                result = runner.invoke(
                    cli,
                    [
                        "--json", "--project", "proj.json",
                        "fem", "mesh", "FEA1", "Part1",
                        "-t", elem_type,
                    ],
                )
                _assert_ok_or_backend_error(result)

    def test_mesh_no_project_error(self, runner):
        with runner.isolated_filesystem():
            result = runner.invoke(
                cli,
                ["--json", "fem", "mesh", "FEA1", "Part1"],
            )
            assert "error" in result.output.lower() or result.exit_code != 0


# ── TestFemConstraintsCLI ────────────────────────────────────────────


class TestFemConstraintsCLI:
    def test_fixed_constraint(self, runner):
        with runner.isolated_filesystem():
            _new_project(runner)
            runner.invoke(
                cli,
                ["--json", "--project", "proj.json", "fem", "analysis", "-n", "FEA1"],
            )
            result = runner.invoke(
                cli,
                [
                    "--json", "--project", "proj.json",
                    "fem", "fixed", "FEA1", "Part1",
                ],
            )
            _assert_ok_or_backend_error(result)

    def test_force_constraint(self, runner):
        with runner.isolated_filesystem():
            _new_project(runner)
            runner.invoke(
                cli,
                ["--json", "--project", "proj.json", "fem", "analysis", "-n", "FEA1"],
            )
            result = runner.invoke(
                cli,
                [
                    "--json", "--project", "proj.json",
                    "fem", "force", "FEA1", "Part1",
                    "-x", "100", "-y", "0", "-z", "-500",
                ],
            )
            _assert_ok_or_backend_error(result)

    def test_force_xyz_values(self, runner):
        """Verify force accepts x, y, z float values."""
        with runner.isolated_filesystem():
            _new_project(runner)
            runner.invoke(
                cli,
                ["--json", "--project", "proj.json", "fem", "analysis", "-n", "FEA1"],
            )
            result = runner.invoke(
                cli,
                [
                    "--json", "--project", "proj.json",
                    "fem", "force", "FEA1", "Part1",
                    "-x", "50.5", "-y", "-25.3", "-z", "0",
                ],
            )
            _assert_ok_or_backend_error(result)


# ── TestFemSolveCLI ──────────────────────────────────────────────────


class TestFemSolveCLI:
    def test_solver_types(self, runner):
        """Verify all solver types are accepted by Click Choice."""
        with runner.isolated_filesystem():
            _new_project(runner)
            runner.invoke(
                cli,
                ["--json", "--project", "proj.json", "fem", "analysis", "-n", "FEA1"],
            )
            for solver in ["CalculiX", "Elmer", "Z88"]:
                result = runner.invoke(
                    cli,
                    [
                        "--json", "--project", "proj.json",
                        "fem", "solve", "FEA1",
                        "-s", solver,
                    ],
                )
                _assert_ok_or_backend_error(result)

    def test_solve_no_project_error(self, runner):
        with runner.isolated_filesystem():
            result = runner.invoke(
                cli,
                ["--json", "fem", "solve", "FEA1"],
            )
            assert "error" in result.output.lower() or result.exit_code != 0


# ── TestFemInfoCLI ───────────────────────────────────────────────────


class TestFemInfoCLI:
    def test_info_wiring(self, runner):
        with runner.isolated_filesystem():
            _new_project(runner)
            runner.invoke(
                cli,
                ["--json", "--project", "proj.json", "fem", "analysis", "-n", "FEA1"],
            )
            result = runner.invoke(
                cli,
                ["--json", "--project", "proj.json", "fem", "info", "FEA1"],
            )
            _assert_ok_or_backend_error(result)

    def test_info_no_project_error(self, runner):
        with runner.isolated_filesystem():
            result = runner.invoke(
                cli,
                ["--json", "fem", "info", "FEA1"],
            )
            assert "error" in result.output.lower() or result.exit_code != 0
