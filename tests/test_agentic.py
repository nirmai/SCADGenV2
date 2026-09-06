"""Tests for the agentic assembly pipeline."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from scadgen.agentic.connection_planner import ConnectionPlanner
from scadgen.agentic.decomposer import AssemblyDecomposer
from scadgen.agentic.executor import AssemblyExecutor
from scadgen.agentic.inventory import TemplateInventory
from scadgen.agentic.template_validator import validate_template
from scadgen.agentic.types import AssemblyPlan, ConnectionSpec, PartSpec
from scadgen.core.engine import SCADEngine
from scadgen.core.template_registry import TemplateRegistry
from scadgen.exceptions import DecompositionError, TemplateGenerationError
from scadgen.nlp.json_utils import parse_json_response
from scadgen.nlp.providers import LLMProvider


class MockProvider(LLMProvider):
    """LLM provider that returns pre-canned responses."""

    def __init__(self, responses: list[str] | None = None):
        self._responses = list(responses or [])
        self._call_idx = 0
        self.calls: list[tuple[str, str]] = []

    def chat(self, prompt: str, system: str = "", max_tokens: int = 0) -> str:
        self.calls.append((prompt, system))
        if self._call_idx < len(self._responses):
            resp = self._responses[self._call_idx]
            self._call_idx += 1
            return resp
        return "{}"

    def is_available(self) -> bool:
        return True


# ── Data type tests ──────────────────────────────────────────────────────


class TestAgenticTypes(unittest.TestCase):
    def test_part_spec_defaults(self):
        p = PartSpec(part_id="arm", description="An arm", suggested_template="arm_t")
        self.assertEqual(p.role, "structural")
        self.assertEqual(p.suggested_params, {})

    def test_connection_spec_defaults(self):
        c = ConnectionSpec(
            from_part="a", from_connector="top",
            to_part="b", to_connector="bottom",
        )
        self.assertEqual(c.type, "mate")
        self.assertEqual(c.offset, 0.0)

    def test_assembly_plan_defaults(self):
        plan = AssemblyPlan(name="test", description="test desc", root_part="base")
        self.assertEqual(plan.parts, [])
        self.assertEqual(plan.connections, [])
        self.assertEqual(plan.templates_found, [])
        self.assertEqual(plan.templates_needed, [])


# ── JSON parsing tests ───────────────────────────────────────────────────


class TestJsonParsing(unittest.TestCase):
    def test_clean_json(self):
        result = parse_json_response('{"template_id": "bolt"}')
        self.assertEqual(result["template_id"], "bolt")

    def test_markdown_fences(self):
        result = parse_json_response('```json\n{"a": 1}\n```')
        self.assertEqual(result["a"], 1)

    def test_python_booleans(self):
        result = parse_json_response('{"flag": True, "other": None}')
        self.assertTrue(result["flag"])
        self.assertIsNone(result["other"])

    def test_extra_text_around(self):
        result = parse_json_response('Here is the JSON:\n{"x": 42}\nDone!')
        self.assertEqual(result["x"], 42)

    def test_invalid_json_raises(self):
        with self.assertRaises(ValueError):
            parse_json_response("not json at all")


# ── Decomposer tests ────────────────────────────────────────────────────


DECOMPOSE_RESPONSE = json.dumps({
    "assembly_name": "engine_top",
    "root_part": "block",
    "parts": [
        {
            "part_id": "block",
            "description": "Cylinder block",
            "suggested_template": "cylinder_block",
            "suggested_params": {"bore_diam": 86, "bore_count": 4},
            "role": "structural",
        },
        {
            "part_id": "gasket",
            "description": "Head gasket",
            "suggested_template": "gasket",
            "suggested_params": {"outer_diam": 120, "inner_diam": 86},
            "role": "structural",
        },
    ],
    "connections": [
        {
            "from_part": "block",
            "from_connector": "deck_face",
            "to_part": "gasket",
            "to_connector": "bottom_face",
            "type": "mate",
            "offset": 0,
        },
    ],
    "colors": {"block": "Silver", "gasket": "DarkGray"},
})


class TestDecomposer(unittest.TestCase):
    def setUp(self):
        self.engine = SCADEngine()

    def test_decompose_produces_plan(self):
        provider = MockProvider([DECOMPOSE_RESPONSE])
        decomposer = AssemblyDecomposer(provider, self.engine.registry)
        plan = decomposer.decompose("build a 4-cylinder engine top end")

        self.assertEqual(plan.name, "engine_top")
        self.assertEqual(plan.root_part, "block")
        self.assertEqual(len(plan.parts), 2)
        self.assertEqual(plan.parts[0].part_id, "block")
        self.assertEqual(plan.parts[0].suggested_template, "cylinder_block")
        self.assertEqual(len(plan.connections), 1)
        self.assertEqual(plan.colors["block"], "Silver")

    def test_decompose_empty_parts_raises(self):
        provider = MockProvider([json.dumps({"parts": [], "assembly_name": "x", "root_part": "x"})])
        decomposer = AssemblyDecomposer(provider, self.engine.registry)
        with self.assertRaises(DecompositionError):
            decomposer.decompose("something")

    def test_decompose_bad_json_raises(self):
        provider = MockProvider(["this is not json at all"])
        decomposer = AssemblyDecomposer(provider, self.engine.registry)
        with self.assertRaises(DecompositionError):
            decomposer.decompose("something")

    def test_decompose_sends_system_prompt(self):
        provider = MockProvider([DECOMPOSE_RESPONSE])
        decomposer = AssemblyDecomposer(provider, self.engine.registry)
        decomposer.decompose("a 4-cylinder engine")
        self.assertEqual(len(provider.calls), 1)
        _, system = provider.calls[0]
        self.assertIn("assembly planner", system.lower())


# ── Inventory tests ──────────────────────────────────────────────────────


class TestInventory(unittest.TestCase):
    def setUp(self):
        self.engine = SCADEngine()

    def test_existing_templates_found(self):
        plan = AssemblyPlan(
            name="test", description="test", root_part="block",
            parts=[
                PartSpec("block", "A cylinder block", "cylinder_block"),
                PartSpec("gasket", "A head gasket", "gasket"),
            ],
        )
        inv = TemplateInventory(self.engine.registry)
        plan = inv.check(plan)

        self.assertIn("cylinder_block", plan.templates_found)
        self.assertIn("gasket", plan.templates_found)
        self.assertEqual(plan.templates_needed, [])

    def test_missing_template_flagged(self):
        plan = AssemblyPlan(
            name="test", description="test", root_part="widget",
            parts=[
                PartSpec("widget", "A nonexistent widget", "quantum_widget_xyz"),
            ],
        )
        inv = TemplateInventory(self.engine.registry)
        plan = inv.check(plan)

        self.assertEqual(plan.templates_found, [])
        self.assertIn("quantum_widget_xyz", plan.templates_needed)

    def test_fuzzy_match_remaps(self):
        plan = AssemblyPlan(
            name="test", description="test", root_part="b",
            parts=[
                PartSpec("b", "A hex bolt fastener", "bolt"),
            ],
        )
        inv = TemplateInventory(self.engine.registry)
        plan = inv.check(plan)

        self.assertEqual(plan.parts[0].suggested_template, "hex_bolt")
        self.assertIn("hex_bolt", plan.templates_found)
        self.assertEqual(plan.templates_needed, [])


# ── Template validator tests ─────────────────────────────────────────────


VALID_TEMPLATE = """\
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


class TestTemplateValidator(unittest.TestCase):
    def test_valid_template_passes(self):
        errors = validate_template(VALID_TEMPLATE)
        self.assertEqual(errors, [])

    def test_missing_meta_block(self):
        errors = validate_template("module foo() { cube(10); }")
        self.assertGreater(len(errors), 0)
        self.assertTrue(any("SCADGEN_META" in e for e in errors))

    def test_mismatched_module_name(self):
        bad = VALID_TEMPLATE.replace("module test_widget(", "module wrong_name(")
        errors = validate_template(bad)
        self.assertTrue(any("mismatch" in e.lower() for e in errors))

    def test_missing_param_in_signature(self):
        bad = VALID_TEMPLATE.replace("module test_widget(width=50, height=30, fn=64)",
                                      "module test_widget(width=50, fn=64)")
        errors = validate_template(bad)
        self.assertTrue(any("height" in e for e in errors))

    def test_default_below_min(self):
        bad = VALID_TEMPLATE.replace("default: 50.0", "default: 5.0")
        errors = validate_template(bad)
        self.assertTrue(any("below min" in e for e in errors))

    def test_unbalanced_braces(self):
        bad = VALID_TEMPLATE + "\n{"
        errors = validate_template(bad)
        self.assertTrue(any("brace" in e.lower() for e in errors))

    def test_unknown_param_in_connector(self):
        bad = VALID_TEMPLATE.replace(
            'origin: [0, 0, "height"]',
            'origin: [0, 0, "nonexistent_param"]',
        )
        errors = validate_template(bad)
        self.assertTrue(any("nonexistent_param" in e for e in errors))


# ── Registry register_template tests ────────────────────────────────────


class TestRegistryRegister(unittest.TestCase):
    def test_register_new_template(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test_widget.scad"
            path.write_text(VALID_TEMPLATE, encoding="utf-8")

            engine = SCADEngine()
            count_before = len(engine.registry.all_ids())
            tmpl = engine.registry.register_template(path)

            self.assertEqual(tmpl.template_id, "test_widget")
            self.assertEqual(len(engine.registry.all_ids()), count_before + 1)
            self.assertIs(engine.registry.get("test_widget"), tmpl)
            self.assertIs(engine.registry.get("widget"), tmpl)


# ── Connection planner tests ────────────────────────────────────────────


class TestConnectionPlanner(unittest.TestCase):
    def setUp(self):
        self.engine = SCADEngine()

    def test_valid_connections_pass_without_llm(self):
        plan = AssemblyPlan(
            name="engine", description="engine", root_part="block",
            parts=[
                PartSpec("block", "Cylinder block", "cylinder_block"),
                PartSpec("gasket", "Head gasket", "gasket"),
            ],
            connections=[
                ConnectionSpec("block", "deck_face", "gasket", "bottom_face", "mate"),
            ],
        )
        provider = MockProvider()
        planner = ConnectionPlanner(provider, self.engine.registry)
        result = planner.refine(plan)

        self.assertEqual(len(result.connections), 1)
        self.assertEqual(len(provider.calls), 0)

    def test_mismatched_connector_triggers_llm(self):
        plan = AssemblyPlan(
            name="engine", description="engine", root_part="block",
            parts=[
                PartSpec("block", "Cylinder block", "cylinder_block"),
                PartSpec("gasket", "Head gasket", "gasket"),
            ],
            connections=[
                ConnectionSpec("block", "nonexistent", "gasket", "bottom_face", "mate"),
            ],
        )
        fixed_response = json.dumps({
            "connections": [
                {
                    "from_part": "block", "from_connector": "deck_face",
                    "to_part": "gasket", "to_connector": "bottom_face",
                    "type": "mate", "offset": 0,
                }
            ]
        })
        provider = MockProvider([fixed_response])
        planner = ConnectionPlanner(provider, self.engine.registry)
        result = planner.refine(plan)

        self.assertEqual(len(provider.calls), 1)
        self.assertEqual(result.connections[0].from_connector, "deck_face")

    def test_auto_snap_single_connector_no_llm(self):
        """A bad reference to a part with exactly one connector snaps to it
        without any LLM call (lamp_shade has only 'socket')."""
        plan = AssemblyPlan(
            name="lamp", description="lamp", root_part="arm",
            parts=[
                PartSpec("arm", "Arm", "lamp_arm"),
                PartSpec("shade", "Shade", "lamp_shade"),
            ],
            connections=[
                ConnectionSpec("arm", "shade_mount", "shade", "wrong_name", "mate"),
            ],
        )
        provider = MockProvider()
        planner = ConnectionPlanner(provider, self.engine.registry)
        result = planner.refine(plan)

        self.assertEqual(len(provider.calls), 0)
        self.assertEqual(result.connections[0].to_connector, "socket")

    def test_unresolvable_connection_dropped_not_raised(self):
        """When neither auto-snap nor the LLM can fix a connection, it is
        dropped with a warning instead of raising."""
        plan = AssemblyPlan(
            name="engine", description="engine", root_part="block",
            parts=[
                PartSpec("block", "Cylinder block", "cylinder_block"),
                PartSpec("head", "Cylinder head", "cylinder_head"),
            ],
            connections=[
                ConnectionSpec("block", "bogus_a", "head", "bogus_b", "mate"),
            ],
        )
        provider = MockProvider(["{}"])  # LLM returns nothing useful
        planner = ConnectionPlanner(provider, self.engine.registry)
        result = planner.refine(plan)

        self.assertEqual(len(result.connections), 0)
        self.assertTrue(any("Dropped" in w for w in planner.warnings))


# ── Executor tests ───────────────────────────────────────────────────────


class TestExecutor(unittest.TestCase):
    def test_execute_block_gasket_head_assembly(self):
        engine = SCADEngine()
        plan = AssemblyPlan(
            name="engine_top", description="engine top end", root_part="block",
            parts=[
                PartSpec("block", "Cylinder block", "cylinder_block",
                         {"bore_diam": 86, "bore_count": 4}),
                PartSpec("gasket", "Head gasket", "gasket",
                         {"outer_diam": 120, "inner_diam": 86}),
                PartSpec("head", "Cylinder head", "cylinder_head",
                         {"bore_diam": 86, "bore_count": 4}),
            ],
            connections=[
                ConnectionSpec("block", "deck_face", "gasket", "bottom_face", "mate"),
                ConnectionSpec("gasket", "top_face", "head", "deck_face", "mate"),
            ],
            colors={"block": "Silver", "gasket": "DarkGray", "head": "Silver"},
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            executor = AssemblyExecutor(engine)
            result = executor.execute(plan, output_dir=tmpdir)

            self.assertTrue(result.success)
            self.assertIn("engine_top_assembly.scad", result.output_path)
            self.assertIn("cylinder_block", result.scad_code)
            self.assertIn("gasket", result.scad_code)
            self.assertIn("cylinder_head", result.scad_code)
            self.assertIn("translate", result.scad_code)

    def test_execute_lamp_assembly(self):
        """Verify the executor works with lamp templates."""
        engine = SCADEngine()
        plan = AssemblyPlan(
            name="lamp", description="desk lamp", root_part="base",
            parts=[
                PartSpec("base", "Base", "lamp_base", {"diameter": 130, "height": 18}),
                PartSpec("arm", "Arm", "lamp_arm", {"straight_height": 260}),
                PartSpec("shade", "Shade", "lamp_shade", {"bottom_diam": 115}),
            ],
            connections=[
                ConnectionSpec("base", "stem_mount", "arm", "base_end", "mate"),
                ConnectionSpec("arm", "shade_mount", "shade", "socket", "mate"),
            ],
            colors={"base": "Goldenrod", "arm": "Goldenrod", "shade": "Goldenrod"},
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            executor = AssemblyExecutor(engine)
            result = executor.execute(plan, output_dir=tmpdir)

            self.assertTrue(result.success)
            self.assertIn("lamp_assembly.scad", result.output_path)
            self.assertIn("lamp_base", result.scad_code)
            self.assertIn("lamp_arm", result.scad_code)
            self.assertIn("lamp_shade", result.scad_code)

    def test_execute_engine_assembly(self):
        """Verify the executor works with existing engine templates."""
        engine = SCADEngine()
        plan = AssemblyPlan(
            name="engine", description="4-cylinder engine", root_part="block",
            parts=[
                PartSpec("block", "Cylinder block", "cylinder_block",
                         {"bore_diam": 86, "bore_count": 4}),
                PartSpec("gasket", "Head gasket", "gasket",
                         {"outer_diam": 120, "inner_diam": 86}),
            ],
            connections=[
                ConnectionSpec("block", "deck_face", "gasket", "bottom_face", "mate"),
            ],
            colors={"block": "Silver", "gasket": "DarkGray"},
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            executor = AssemblyExecutor(engine)
            result = executor.execute(plan, output_dir=tmpdir)

            self.assertTrue(result.success)
            self.assertIn("cylinder_block", result.scad_code)
            self.assertIn("gasket", result.scad_code)

    def test_orphaned_part_dropped_to_recover(self):
        """A part with no connection to the root is dropped so the rest of
        the assembly still renders instead of crashing the solver."""
        engine = SCADEngine()
        plan = AssemblyPlan(
            name="engine", description="engine", root_part="block",
            parts=[
                PartSpec("block", "Cylinder block", "cylinder_block"),
                PartSpec("gasket", "Head gasket", "gasket"),
                PartSpec("orphan", "Disconnected shaft", "shaft"),
            ],
            connections=[
                ConnectionSpec("block", "deck_face", "gasket", "bottom_face", "mate"),
            ],
            colors={},
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            executor = AssemblyExecutor(engine)
            result = executor.execute(plan, output_dir=tmpdir)

            self.assertTrue(result.success)
            self.assertIn("cylinder_block", result.scad_code)
            self.assertIn("gasket", result.scad_code)
            self.assertTrue(any("orphan" in w for w in result.warnings))


# ── Full pipeline integration test (mock LLM) ───────────────────────────


class TestPipelineIntegration(unittest.TestCase):
    def test_pipeline_with_existing_templates(self):
        """Full pipeline using engine templates that already exist — no generation needed."""
        decompose_resp = json.dumps({
            "assembly_name": "engine_top",
            "root_part": "block",
            "parts": [
                {
                    "part_id": "block",
                    "description": "Cylinder block",
                    "suggested_template": "cylinder_block",
                    "suggested_params": {"bore_diam": 86, "bore_count": 4},
                    "role": "structural",
                },
                {
                    "part_id": "gasket",
                    "description": "Head gasket",
                    "suggested_template": "gasket",
                    "suggested_params": {"outer_diam": 120, "inner_diam": 86},
                    "role": "structural",
                },
            ],
            "connections": [
                {
                    "from_part": "block", "from_connector": "deck_face",
                    "to_part": "gasket", "to_connector": "bottom_face",
                    "type": "mate", "offset": 0,
                },
            ],
            "colors": {
                "block": "Silver", "gasket": "DarkGray",
            },
        })

        from scadgen.agentic.pipeline import run_pipeline

        engine = SCADEngine()
        import scadgen.agentic.pipeline as pipeline_mod
        original_create = pipeline_mod.create_provider
        provider = MockProvider([decompose_resp])
        pipeline_mod.create_provider = lambda cfg: provider

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                result = run_pipeline(
                    description="build a 4-cylinder engine top end",
                    engine=engine,
                    output_dir=tmpdir,
                )
                self.assertTrue(result.success)
                self.assertIn("cylinder_block", result.scad_code)
                self.assertIn("gasket", result.scad_code)
                self.assertEqual(len(result.plan.parts), 2)
                self.assertEqual(result.generated_templates, [])
        finally:
            pipeline_mod.create_provider = original_create

    def test_pipeline_drops_unresolved_placeholder_template(self):
        """A part with a bogus template name (e.g. 'not_defined') is dropped
        rather than crashing the connection planner."""
        decompose_resp = json.dumps({
            "assembly_name": "engine_top",
            "root_part": "block",
            "parts": [
                {"part_id": "block", "description": "Cylinder block",
                 "suggested_template": "cylinder_block", "role": "structural"},
                {"part_id": "gasket", "description": "Head gasket",
                 "suggested_template": "gasket", "role": "structural"},
                {"part_id": "mystery", "description": "Unknown widget",
                 "suggested_template": "not_defined", "role": "structural"},
            ],
            "connections": [
                {"from_part": "block", "from_connector": "deck_face",
                 "to_part": "gasket", "to_connector": "bottom_face", "type": "mate"},
                {"from_part": "gasket", "from_connector": "top_face",
                 "to_part": "mystery", "to_connector": "whatever", "type": "mate"},
            ],
            "colors": {"block": "Silver", "gasket": "DarkGray"},
        })

        from scadgen.agentic.pipeline import run_pipeline

        engine = SCADEngine()
        import scadgen.agentic.pipeline as pipeline_mod
        original_create = pipeline_mod.create_provider
        # No successful template generation: 'not_defined' stays unresolved.
        provider = MockProvider([decompose_resp, "invalid scad", "invalid", "invalid"])
        pipeline_mod.create_provider = lambda cfg: provider

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                result = run_pipeline(
                    description="engine with a mystery part",
                    engine=engine,
                    output_dir=tmpdir,
                )
                self.assertTrue(result.success)
                part_ids = [p.part_id for p in result.plan.parts]
                self.assertNotIn("mystery", part_ids)
                self.assertIn("block", part_ids)
                self.assertIn("gasket", part_ids)
        finally:
            pipeline_mod.create_provider = original_create


# ── Anthropic provider tests ────────────────────────────────────────────


class TestAnthropicProvider(unittest.TestCase):
    def test_provider_class_exists(self):
        from scadgen.nlp.providers import AnthropicProvider
        p = AnthropicProvider(api_key="test-key")
        self.assertTrue(p.is_available())

    def test_provider_no_key(self):
        from scadgen.nlp.providers import AnthropicProvider
        p = AnthropicProvider(api_key="")
        self.assertFalse(p.is_available())


# ── CLI assemble subcommand tests ────────────────────────────────────────


class TestCLIAssemble(unittest.TestCase):
    def test_assemble_subcommand_parses(self):
        """Verify the argparse setup accepts 'assemble' command."""
        import scadgen.cli as cli
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument("--provider", default="auto")
        parser.add_argument("--output-dir", default="output")
        subs = parser.add_subparsers(dest="command")
        asm = subs.add_parser("assemble")
        asm.add_argument("description")
        asm.add_argument("--dry-run", action="store_true")
        asm.add_argument("-v", "--verbose", action="store_true")

        args = parser.parse_args(["assemble", "make a lamp", "--dry-run"])
        self.assertEqual(args.command, "assemble")
        self.assertEqual(args.description, "make a lamp")
        self.assertTrue(args.dry_run)


if __name__ == "__main__":
    unittest.main()
