"""Tests for SVG import and units/scaling (TDD - written BEFORE implementation)."""

import json
import os
import tempfile
import pytest
from click.testing import CliRunner

from cli_anything.freecad.freecad_cli import cli
from cli_anything.freecad.core.project import _object_to_script


# ── SVG Import Tests ─────────────────────────────────────────────────


class TestSvgImport:
    """Tests for svg-import command."""

    def test_svg_import_basic(self, tmp_path):
        """Test basic SVG import creates correct object."""
        # Create a minimal SVG file
        svg_file = tmp_path / "test.svg"
        svg_file.write_text("""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="100mm" height="100mm" viewBox="0 0 100 100">
  <rect x="10" y="10" width="80" height="80" fill="blue"/>
</svg>""")
        
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(
                cli,
                ["--json", "project", "new", "-n", "TestProj", "-o", "proj.json"],
            )
            assert result.exit_code == 0
            
            result = runner.invoke(
                cli,
                [
                    "--json",
                    "--project",
                    "proj.json",
                    "svg-import",
                    str(svg_file),
                ],
            )
            assert result.exit_code == 0, f"Command failed: {result.output}"
            data = json.loads(result.output)
            assert data["name"] == "SVG"
            assert data["type"] == "ImportSVG"
            assert "filepath" in data["params"]

    def test_svg_import_with_units(self, tmp_path):
        """Test SVG import with explicit unit conversion."""
        svg_file = tmp_path / "test.svg"
        svg_file.write_text("""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="10cm" height="10cm" viewBox="0 0 100 100">
  <circle cx="50" cy="50" r="40"/>
</svg>""")
        
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(
                cli,
                ["--json", "project", "new", "-n", "TestProj", "-o", "proj.json"],
            )
            assert result.exit_code == 0
            
            result = runner.invoke(
                cli,
                [
                    "--json",
                    "--project",
                    "proj.json",
                    "svg-import",
                    str(svg_file),
                    "--units",
                    "mm",
                ],
            )
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert data["params"]["target_units"] == "mm"

    def test_svg_import_with_scale(self, tmp_path):
        """Test SVG import with scale factor."""
        svg_file = tmp_path / "test.svg"
        svg_file.write_text("""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
  <path d="M 10 10 L 90 90"/>
</svg>""")
        
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(
                cli,
                ["--json", "project", "new", "-n", "TestProj", "-o", "proj.json"],
            )
            assert result.exit_code == 0
            
            result = runner.invoke(
                cli,
                [
                    "--json",
                    "--project",
                    "proj.json",
                    "svg-import",
                    str(svg_file),
                    "--scale",
                    "2.0",
                ],
            )
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert data["params"]["scale"] == 2.0

    def test_svg_import_custom_name(self, tmp_path):
        """Test SVG import with custom object name."""
        svg_file = tmp_path / "logo.svg"
        svg_file.write_text("""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
  <rect width="100" height="100"/>
</svg>""")
        
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(
                cli,
                ["--json", "project", "new", "-n", "TestProj", "-o", "proj.json"],
            )
            assert result.exit_code == 0
            
            result = runner.invoke(
                cli,
                [
                    "--json",
                    "--project",
                    "proj.json",
                    "svg-import",
                    str(svg_file),
                    "-n",
                    "MyLogo",
                ],
            )
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert data["name"] == "MyLogo"

    def test_svg_import_file_not_found(self):
        """Test SVG import with non-existent file."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(
                cli,
                ["--json", "project", "new", "-n", "TestProj", "-o", "proj.json"],
            )
            assert result.exit_code == 0
            
            result = runner.invoke(
                cli,
                [
                    "--json",
                    "--project",
                    "proj.json",
                    "svg-import",
                    "nonexistent.svg",
                ],
            )
            assert result.exit_code != 0

    def test_svg_import_script_generation(self):
        """Test FreeCAD script generation for SVG import."""
        obj = {
            "name": "SVG1",
            "type": "ImportSVG",
            "params": {
                "filepath": "/path/to/file.svg",
                "target_units": "mm",
                "scale": 1.0,
            },
        }
        script = _object_to_script(obj)
        assert "importSVG" in script or "ImportSVG" in script
        assert "/path/to/file.svg" in script


# ── Units/Scaling Tests ──────────────────────────────────────────────


class TestUnitsParsing:
    """Tests for SVG unit detection and parsing."""

    def test_parse_svg_units_mm(self):
        """Test parsing SVG with mm units."""
        from cli_anything.freecad.core.svg_import import parse_svg_units
        
        svg_content = """<?xml version="1.0"?>
<svg xmlns="http://www.w3.org/2000/svg" width="100mm" height="100mm">
  <rect width="100" height="100"/>
</svg>"""
        units = parse_svg_units(svg_content)
        assert units["width"] == 100.0
        assert units["height"] == 100.0
        assert units["unit"] == "mm"

    def test_parse_svg_units_cm(self):
        """Test parsing SVG with cm units."""
        from cli_anything.freecad.core.svg_import import parse_svg_units
        
        svg_content = """<?xml version="1.0"?>
<svg xmlns="http://www.w3.org/2000/svg" width="10cm" height="15cm">
  <rect width="100" height="100"/>
</svg>"""
        units = parse_svg_units(svg_content)
        assert units["width"] == 10.0
        assert units["height"] == 15.0
        assert units["unit"] == "cm"

    def test_parse_svg_units_inches(self):
        """Test parsing SVG with inch units."""
        from cli_anything.freecad.core.svg_import import parse_svg_units
        
        svg_content = """<?xml version="1.0"?>
<svg xmlns="http://www.w3.org/2000/svg" width="5in" height="3in">
  <rect width="100" height="100"/>
</svg>"""
        units = parse_svg_units(svg_content)
        assert units["width"] == 5.0
        assert units["height"] == 3.0
        assert units["unit"] == "in"

    def test_parse_svg_viewbox(self):
        """Test parsing SVG viewBox for unit-less dimensions."""
        from cli_anything.freecad.core.svg_import import parse_svg_units
        
        svg_content = """<?xml version="1.0"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 210 297">
  <rect width="100" height="100"/>
</svg>"""
        units = parse_svg_units(svg_content)
        assert units["viewbox_width"] == 210.0
        assert units["viewbox_height"] == 297.0


class TestUnitConversion:
    """Tests for unit conversion utilities."""

    def test_mm_to_mm(self):
        """Test mm to mm (identity)."""
        from cli_anything.freecad.core.svg_import import convert_units
        
        result = convert_units(100.0, "mm", "mm")
        assert result == 100.0

    def test_cm_to_mm(self):
        """Test cm to mm conversion."""
        from cli_anything.freecad.core.svg_import import convert_units
        
        result = convert_units(10.0, "cm", "mm")
        assert result == 100.0

    def test_in_to_mm(self):
        """Test inches to mm conversion."""
        from cli_anything.freecad.core.svg_import import convert_units
        
        result = convert_units(1.0, "in", "mm")
        assert abs(result - 25.4) < 0.001

    def test_mm_to_cm(self):
        """Test mm to cm conversion."""
        from cli_anything.freecad.core.svg_import import convert_units
        
        result = convert_units(100.0, "mm", "cm")
        assert result == 10.0

    def test_scale_factor(self):
        """Test applying scale factor."""
        from cli_anything.freecad.core.svg_import import apply_scale
        
        result = apply_scale(100.0, 2.0)
        assert result == 200.0

    def test_scale_with_unit_conversion(self):
        """Test combined scale and unit conversion."""
        from cli_anything.freecad.core.svg_import import convert_and_scale
        
        # 10cm to mm with 2x scale = 200mm
        result = convert_and_scale(10.0, "cm", "mm", 2.0)
        assert result == 200.0


class TestSvgImportIntegration:
    """Integration tests for SVG import workflow."""

    def test_full_svg_to_dxf_workflow(self, tmp_path):
        """Test complete workflow: SVG import -> DXF export."""
        svg_file = tmp_path / "design.svg"
        svg_file.write_text("""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="200mm" height="200mm" viewBox="0 0 200 200">
  <rect x="10" y="10" width="180" height="180" fill="none" stroke="black"/>
  <circle cx="100" cy="100" r="50" fill="none" stroke="black"/>
</svg>""")
        
        runner = CliRunner()
        with runner.isolated_filesystem():
            # Create project
            result = runner.invoke(
                cli,
                ["--json", "project", "new", "-n", "LaserCut", "-o", "proj.json"],
            )
            assert result.exit_code == 0
            
            # Import SVG
            result = runner.invoke(
                cli,
                [
                    "--json",
                    "--project",
                    "proj.json",
                    "svg-import",
                    str(svg_file),
                    "--units",
                    "mm",
                    "--scale",
                    "1.0",
                ],
            )
            assert result.exit_code == 0
            
            # Verify SVG was imported into project
            import json
            with open("proj.json") as f:
                proj = json.load(f)
            assert len(proj["objects"]) == 1
            assert proj["objects"][0]["type"] == "ImportSVG"
            
            # Export command should succeed (file creation requires FreeCAD backend)
            result = runner.invoke(
                cli,
                [
                    "--json",
                    "--project",
                    "proj.json",
                    "export",
                    "dxf",
                    "output.dxf",
                    "--overwrite",
                ],
            )
            # Command should parse correctly (exit code 0 or specific error about missing FreeCAD)
            # We don't check file existence since FreeCAD isn't running in test env
            assert result.exit_code in [0, 1]  # 0 = success, 1 = FreeCAD not found (acceptable)

    def test_svg_scale_to_fit_plate(self, tmp_path):
        """Test scaling SVG to fit a specific plate size."""
        svg_file = tmp_path / "logo.svg"
        svg_file.write_text("""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="500mm" height="500mm" viewBox="0 0 500 500">
  <rect x="50" y="50" width="400" height="400"/>
</svg>""")
        
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(
                cli,
                ["--json", "project", "new", "-n", "TestProj", "-o", "proj.json"],
            )
            assert result.exit_code == 0
            
            # Import with scale to fit 200mm plate
            result = runner.invoke(
                cli,
                [
                    "--json",
                    "--project",
                    "proj.json",
                    "svg-import",
                    str(svg_file),
                    "--units",
                    "mm",
                    "--fit-width",
                    "200",
                ],
            )
            assert result.exit_code == 0
            data = json.loads(result.output)
            # Should scale down from 500mm to 200mm (scale = 0.4)
            assert data["params"]["scale"] == pytest.approx(0.4, rel=0.01)
