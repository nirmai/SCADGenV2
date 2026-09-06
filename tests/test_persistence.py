"""Tests for persisting LLM-generated templates across runs."""

from __future__ import annotations

import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from scadgen.agentic.types import AssemblyPlan, PartSpec
from scadgen.config import Config
from scadgen.core.template_registry import TemplateRegistry

_MINIMAL_TEMPLATE = """\
// SCADGEN_META_BEGIN
// schema_version: 1
// template_id: {tid}
// module_name: {tid}
// description: {desc}
// params: []
// SCADGEN_META_END

module {tid}() {{ cube(1); }}
"""

_VALID_WIDGET = """\
// SCADGEN_META_BEGIN
// schema_version: 1
// template_id: test_widget
// module_name: test_widget
// description: A test widget
// category: test
// tags: [test]
// aliases: [widget]
// keywords: [test, widget]
// params:
//   - name: width
//     type: float
//     default: 50.0
//     min: 10.0
//     max: 200.0
//     unit: mm
//     description: Widget width
//   - name: height
//     type: float
//     default: 30.0
//     min: 5.0
//     max: 100.0
//     unit: mm
//     description: Widget height
//   - name: fn
//     type: int
//     default: 64
//     min: 16
//     max: 256
//     unit: count
//     description: Resolution
// connectors:
//   - name: top_face
//     type: axial
//     origin: [0, 0, "height"]
//     direction: [0, 0, 1]
//   - name: bottom_face
//     type: axial
//     origin: [0, 0, 0]
//     direction: [0, 0, -1]
// SCADGEN_META_END

module test_widget(width=50, height=30, fn=64)
{
    $fn = fn;
    cube([width, width, height], center=true);
}
"""


class TestConfigGeneratedDir(unittest.TestCase):
    def test_default_generated_dir_included_in_template_dirs(self):
        cfg = Config.load()
        self.assertTrue(cfg.generated_templates_dir)
        self.assertIn(cfg.generated_templates_dir, cfg.template_dirs)

    def test_env_var_overrides_location(self):
        with tempfile.TemporaryDirectory() as d:
            custom = str(Path(d) / "my_generated")
            with patch.dict(os.environ, {"SCADGEN_GENERATED_DIR": custom}):
                cfg = Config.load()
                self.assertEqual(cfg.generated_templates_dir, custom)
                self.assertIn(custom, cfg.template_dirs)


class TestRegistryPrecedence(unittest.TestCase):
    def test_curated_wins_over_generated_on_id_collision(self):
        with tempfile.TemporaryDirectory() as curated_d, \
                tempfile.TemporaryDirectory() as generated_d:
            (Path(curated_d) / "shared.scad").write_text(
                _MINIMAL_TEMPLATE.format(tid="shared_id", desc="curated version"),
                encoding="utf-8",
            )
            (Path(generated_d) / "shared.scad").write_text(
                _MINIMAL_TEMPLATE.format(tid="shared_id", desc="generated version"),
                encoding="utf-8",
            )
            # Curated dir scanned first -> must win regardless of scan order
            # within _scan_directory's per-file loop.
            registry = TemplateRegistry([curated_d, generated_d])
            self.assertEqual(registry.get("shared_id").description, "curated version")


class TestReuseAcrossRuns(unittest.TestCase):
    def test_previously_generated_template_found_without_generation(self):
        with tempfile.TemporaryDirectory() as gen_dir:
            (Path(gen_dir) / "test_widget.scad").write_text(_VALID_WIDGET, encoding="utf-8")

            registry = TemplateRegistry([gen_dir])
            from scadgen.agentic.inventory import TemplateInventory

            plan = AssemblyPlan(
                name="t", description="", root_part="w",
                parts=[PartSpec("w", "a widget", "test_widget")],
            )
            TemplateInventory(registry).check(plan)

            self.assertIn("test_widget", plan.templates_found)
            self.assertEqual(plan.templates_needed, [])


class TestPipelineWritesToPersistentDir(unittest.TestCase):
    def test_generated_template_lands_in_config_dir_not_output_dir(self):
        from scadgen.core.engine import SCADEngine
        import scadgen.agentic.pipeline as pipeline_mod
        from tests.test_agentic import MockProvider

        decompose_resp = json.dumps({
            "assembly_name": "widget_asm", "root_part": "w",
            "parts": [{
                "part_id": "w", "description": "a custom widget",
                "suggested_template": "widget_custom", "custom": True,
            }],
            "connections": [],
        })
        generation_resp = _VALID_WIDGET.replace("test_widget", "widget_custom")

        with tempfile.TemporaryDirectory() as gen_cache, \
                tempfile.TemporaryDirectory() as out_dir:
            engine = SCADEngine()
            engine.config.generated_templates_dir = gen_cache

            original_create = pipeline_mod.create_provider
            original_find = pipeline_mod.find_openscad
            provider = MockProvider([decompose_resp, generation_resp])
            pipeline_mod.create_provider = lambda cfg, prefer_vision=False: provider
            # A non-existent binary path: passes the "OpenSCAD is configured"
            # guard, but check_scad() raises FileNotFoundError internally,
            # which the generator treats as "skip render-check" -- keeping
            # this test offline while still exercising the write location.
            pipeline_mod.find_openscad = lambda cfg: "/fake/openscad"

            try:
                pipeline_mod.run_pipeline(
                    description="a custom widget", engine=engine, output_dir=out_dir,
                )
            finally:
                pipeline_mod.create_provider = original_create
                pipeline_mod.find_openscad = original_find

            self.assertTrue((Path(gen_cache) / "widget_custom.scad").exists())
            self.assertFalse((Path(out_dir) / "generated_templates").exists())


class TestCliGeneratedTag(unittest.TestCase):
    def test_list_tags_generated_template(self):
        import scadgen.cli as cli

        with tempfile.TemporaryDirectory() as gen_dir:
            curated = SimpleNamespace(
                template_id="builtin_part", description="A builtin part",
                category="mechanical", file_path=str(Path("scadgen/templates/builtin_part.scad")),
            )
            generated = SimpleNamespace(
                template_id="cage_dome", description="A generated dome",
                category="custom", file_path=str(Path(gen_dir) / "cage_dome.scad"),
            )
            fake_engine = SimpleNamespace(
                registry=SimpleNamespace(list_templates=lambda category="": [curated, generated]),
                config=SimpleNamespace(generated_templates_dir=gen_dir),
            )
            with patch("scadgen.core.engine.SCADEngine", return_value=fake_engine):
                buf = io.StringIO()
                with redirect_stdout(buf):
                    cli._cmd_list(SimpleNamespace(category=""))
                output = buf.getvalue()

            self.assertIn("builtin_part", output)
            self.assertIn("cage_dome", output)
            self.assertIn("[generated]", output)
            builtin_line = next(l for l in output.splitlines() if "builtin_part" in l)
            self.assertNotIn("[generated]", builtin_line)


class TestClearGenerated(unittest.TestCase):
    def test_dry_run_reports_without_deleting(self):
        import scadgen.cli as cli

        with tempfile.TemporaryDirectory() as gen_dir:
            f = Path(gen_dir) / "cage_dome.scad"
            f.write_text(_MINIMAL_TEMPLATE.format(tid="cage_dome", desc="x"), encoding="utf-8")

            with patch.dict(os.environ, {"SCADGEN_GENERATED_DIR": gen_dir}):
                buf = io.StringIO()
                with redirect_stdout(buf):
                    cli._cmd_clear_generated(SimpleNamespace(yes=False))

            self.assertTrue(f.exists())
            self.assertIn("Would remove", buf.getvalue())

    def test_yes_flag_deletes(self):
        import scadgen.cli as cli

        with tempfile.TemporaryDirectory() as gen_dir:
            f = Path(gen_dir) / "cage_dome.scad"
            f.write_text(_MINIMAL_TEMPLATE.format(tid="cage_dome", desc="x"), encoding="utf-8")

            with patch.dict(os.environ, {"SCADGEN_GENERATED_DIR": gen_dir}):
                buf = io.StringIO()
                with redirect_stdout(buf):
                    cli._cmd_clear_generated(SimpleNamespace(yes=True))

            self.assertFalse(f.exists())
            self.assertIn("Removed 1", buf.getvalue())

    def test_empty_dir_reports_nothing_to_remove(self):
        import scadgen.cli as cli

        with tempfile.TemporaryDirectory() as gen_dir:
            with patch.dict(os.environ, {"SCADGEN_GENERATED_DIR": gen_dir}):
                buf = io.StringIO()
                with redirect_stdout(buf):
                    cli._cmd_clear_generated(SimpleNamespace(yes=False))
            self.assertIn("No generated templates found", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
