"""Tests for the OpenSCAD render integration (Blocker 3)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scadgen.config import Config
from scadgen.render import check_scad, find_openscad

_VALID_SCAD = "cube([10, 10, 10], center=true);\n"
_BROKEN_SCAD = "cubee([10, 10, 10]);\n"  # typo'd builtin -> renders nothing / warns
_UNDEFINED_SCAD = "cube([w, w, w]);\n"    # undefined variable

_OPENSCAD = find_openscad()


class TestFindOpenscad(unittest.TestCase):
    def test_config_path_honored(self):
        with tempfile.TemporaryDirectory() as d:
            fake = Path(d) / "openscad.exe"
            fake.write_text("", encoding="utf-8")
            cfg = Config()
            cfg.openscad_path = str(fake)
            self.assertEqual(find_openscad(cfg), str(fake))

    def test_missing_config_path_falls_through(self):
        cfg = Config()
        cfg.openscad_path = "/nonexistent/openscad"
        # Should not return the bogus path; returns a real one or None.
        self.assertNotEqual(find_openscad(cfg), "/nonexistent/openscad")


@unittest.skipUnless(_OPENSCAD, "OpenSCAD binary not installed")
class TestCheckScadReal(unittest.TestCase):
    def test_valid_renders_clean(self):
        self.assertEqual(check_scad(_VALID_SCAD, _OPENSCAD), [])

    def test_typoed_builtin_flagged(self):
        self.assertTrue(check_scad(_BROKEN_SCAD, _OPENSCAD))

    def test_undefined_variable_flagged(self):
        self.assertTrue(check_scad(_UNDEFINED_SCAD, _OPENSCAD))


class TestCheckScadMissingBinary(unittest.TestCase):
    def test_missing_binary_raises(self):
        with self.assertRaises(FileNotFoundError):
            check_scad(_VALID_SCAD, "/nonexistent/openscad")


class TestGeneratorRenderPlumbing(unittest.TestCase):
    """The generator feeds render-check errors into its repair loop."""

    def test_render_errors_empty_without_binary(self):
        from scadgen.agentic.template_generator import TemplateGenerator
        g = TemplateGenerator(None, None, Path("x"), openscad_bin=None)
        self.assertEqual(g._render_errors("anything"), [])

    def test_render_errors_uses_checker_when_binary_set(self):
        import scadgen.agentic.template_generator as tg
        from scadgen.agentic.template_generator import TemplateGenerator

        original = tg.check_scad
        tg.check_scad = lambda code, binp: ["ERROR: boom"]
        try:
            g = TemplateGenerator(None, None, Path("x"), openscad_bin="/fake/openscad")
            self.assertEqual(g._render_errors("code"), ["ERROR: boom"])
        finally:
            tg.check_scad = original


if __name__ == "__main__":
    unittest.main()
