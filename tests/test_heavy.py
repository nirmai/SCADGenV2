"""Heavy diagnostic tests — boundary conditions, edge cases, stress tests."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from scadgen.core.engine import SCADEngine
from scadgen.core.template_registry import TemplateRegistry
from scadgen.exceptions import ConstraintViolationError, ParameterValidationError
from scadgen.knowledge.constraints import (
    check_engineering_warnings,
    check_template_constraints,
    harmonize_linked_params,
    validate_constraints,
)
from scadgen.knowledge.resolver import EngineeringResolver
from scadgen.knowledge.standards import ISO_COUNTERSUNK, ISO_METRIC_THREADS, ISO_SHCS, ISO_WASHERS

PYTHON = str(Path(sys.executable))
PROJECT = str(Path(__file__).parent.parent)


def _make_resolver():
    reg = TemplateRegistry(["scadgen/templates"])
    return EngineeringResolver(registry=reg)


@pytest.fixture
def registry():
    return TemplateRegistry(["scadgen/templates"])


@pytest.fixture
def engine():
    return SCADEngine(template_dirs=["scadgen/templates"])


@pytest.fixture
def resolver(registry):
    return EngineeringResolver(registry=registry)


# ── 1. Boundary value testing for every constraint ─────────────────


class TestBoundaryValues:
    """Test exact boundary values — the constraint should pass AT the boundary
    and fail just past it."""

    def test_bushing_equal_diameters_fails(self, registry):
        tmpl = registry.get("bushing")
        params = tmpl.apply_defaults({"inner_d": 20, "outer_d": 20})
        errors, _ = check_template_constraints(tmpl, params)
        assert errors

    def test_bushing_outer_exceeds_by_epsilon(self, registry):
        tmpl = registry.get("bushing")
        params = tmpl.apply_defaults({"inner_d": 19.999, "outer_d": 20})
        errors, _ = check_template_constraints(tmpl, params)
        assert not errors

    def test_bolt_thread_equals_shaft_passes(self, registry):
        tmpl = registry.get("hex_bolt")
        params = tmpl.apply_defaults({"thread_len": 30, "shaft_len": 30})
        errors, _ = check_template_constraints(tmpl, params)
        assert not errors  # <= means equal is OK

    def test_bolt_thread_exceeds_by_epsilon(self, registry):
        tmpl = registry.get("hex_bolt")
        params = tmpl.apply_defaults({"thread_len": 30.001, "shaft_len": 30})
        errors, _ = check_template_constraints(tmpl, params)
        assert errors

    def test_shcs_socket_equals_head_fails(self, registry):
        tmpl = registry.get("socket_head_cap_screw")
        params = tmpl.apply_defaults({"socket_size": 13, "head_diam": 13})
        errors, _ = check_template_constraints(tmpl, params)
        assert errors  # strict < required

    def test_shcs_socket_just_under_head_passes(self, registry):
        tmpl = registry.get("socket_head_cap_screw")
        params = tmpl.apply_defaults({"socket_size": 12.9, "head_diam": 13})
        errors, _ = check_template_constraints(tmpl, params)
        assert not errors

    def test_shcs_socket_depth_equals_head_height_passes(self, registry):
        tmpl = registry.get("socket_head_cap_screw")
        params = tmpl.apply_defaults({"socket_depth": 8, "head_height": 8})
        errors, _ = check_template_constraints(tmpl, params)
        assert not errors  # <= means equal is OK

    def test_shcs_socket_depth_exceeds_head_height_fails(self, registry):
        tmpl = registry.get("socket_head_cap_screw")
        params = tmpl.apply_defaults({"socket_depth": 8.1, "head_height": 8})
        errors, _ = check_template_constraints(tmpl, params)
        assert errors

    def test_washer_equal_diameters_fails(self, registry):
        tmpl = registry.get("washer")
        params = tmpl.apply_defaults({"inner_diam": 16, "outer_diam": 16})
        errors, _ = check_template_constraints(tmpl, params)
        assert errors

    def test_torus_equal_radii_fails(self, registry):
        tmpl = registry.get("torus")
        params = tmpl.apply_defaults({"major_r": 10, "minor_r": 10})
        errors, _ = check_template_constraints(tmpl, params)
        assert errors

    def test_cylinder_inner_equals_outer_fails(self, registry):
        tmpl = registry.get("cylinder")
        params = tmpl.apply_defaults({"diam": 20, "inner_diam": 20})
        errors, _ = check_template_constraints(tmpl, params)
        assert errors

    def test_set_screw_socket_equals_diam_fails(self, registry):
        tmpl = registry.get("set_screw")
        params = tmpl.apply_defaults({"shaft_diam": 6, "socket_size": 6})
        errors, _ = check_template_constraints(tmpl, params)
        assert errors

    def test_countersunk_socket_at_80_pct_head_fails(self, registry):
        tmpl = registry.get("countersunk_screw")
        # socket_size < head_diam * 0.8  =>  10.752 < 13.44 * 0.8 = 10.752 => NOT less
        params = tmpl.apply_defaults({"head_diam": 13.44, "socket_size": 10.752})
        errors, _ = check_template_constraints(tmpl, params)
        assert errors

    def test_countersunk_socket_just_under_80_pct_passes(self, registry):
        tmpl = registry.get("countersunk_screw")
        params = tmpl.apply_defaults({"head_diam": 13.44, "socket_size": 10.0})
        errors, _ = check_template_constraints(tmpl, params)
        assert not errors


# ── 2. Multi-violation cascades ────────────────────────────────────


class TestMultiViolation:
    """Every possible constraint on a template fires at once."""

    def test_shcs_all_constraints_fire(self, registry):
        tmpl = registry.get("socket_head_cap_screw")
        params = tmpl.apply_defaults({
            "shaft_diam": 15,
            "head_diam": 10,       # head < shaft
            "socket_size": 12,     # socket >= head
            "socket_depth": 20,    # socket_depth > head_height
            "thread_len": 50,      # thread > shaft
            "shaft_len": 20,
            "head_height": 5,
        })
        errors, _ = check_template_constraints(tmpl, params)
        assert len(errors) >= 3

    def test_bolt_all_constraints_fire(self, registry):
        tmpl = registry.get("hex_bolt")
        params = tmpl.apply_defaults({
            "shaft_diam": 20,
            "head_flat": 10,       # head < shaft
            "thread_len": 50,      # thread > shaft
            "shaft_len": 30,
        })
        errors, _ = check_template_constraints(tmpl, params)
        assert len(errors) == 2

    def test_set_screw_all_constraints_fire(self, registry):
        tmpl = registry.get("set_screw")
        params = tmpl.apply_defaults({
            "shaft_diam": 4,
            "socket_size": 6,      # socket >= diam
            "socket_depth": 12,    # socket >= length
            "length": 10,
            "point_len": 9,        # point >= length - socket_depth
        })
        errors, _ = check_template_constraints(tmpl, params)
        assert len(errors) >= 2


# ── 3. Type coercion edge cases ───────────────────────────────────


class TestTypeCoercion:
    """Params arrive as int, float, string, bool — all should work."""

    def test_int_for_float_param(self, engine):
        result = engine.generate(
            template_id="washer",
            params={"inner_diam": 8, "outer_diam": 16, "thickness": 2},
        )
        assert "cylinder" in result.scad_code

    def test_float_for_int_param(self, engine):
        result = engine.generate(
            template_id="gear_spur",
            params={"teeth": 24.0, "modul": 2.0},
        )
        assert "teeth" in result.scad_code

    def test_string_number_coercion(self, registry):
        tmpl = registry.get("hex_bolt")
        validated = tmpl.validate_params({"shaft_diam": "10"})
        assert validated["shaft_diam"] == 10.0
        assert isinstance(validated["shaft_diam"], float)

    def test_string_bool_coercion(self, registry):
        tmpl = registry.get("hex_bolt")
        validated = tmpl.validate_params({"add_threads": "false"})
        assert validated["add_threads"] is False

    def test_bool_true_as_string(self, registry):
        tmpl = registry.get("hex_bolt")
        validated = tmpl.validate_params({"add_threads": "true"})
        assert validated["add_threads"] is True


# ── 4. Parameter range validation ─────────────────────────────────


class TestRangeValidation:
    """Every template rejects out-of-range values cleanly."""

    @pytest.fixture
    def all_templates(self, registry):
        return registry.list_templates()

    def test_below_min_raises(self, registry):
        for tmpl in registry.list_templates():
            for p in tmpl.parameters:
                if p.min is not None and p.type in ("float", "int"):
                    below = p.min - 1
                    with pytest.raises((ParameterValidationError, ValueError)):
                        tmpl.validate_params({p.name: below})

    def test_above_max_raises(self, registry):
        for tmpl in registry.list_templates():
            for p in tmpl.parameters:
                if p.max is not None and p.type in ("float", "int"):
                    above = p.max + 1
                    with pytest.raises((ParameterValidationError, ValueError)):
                        tmpl.validate_params({p.name: above})

    def test_at_min_accepted(self, registry):
        for tmpl in registry.list_templates():
            for p in tmpl.parameters:
                if p.min is not None and p.type in ("float", "int"):
                    result = tmpl.validate_params({p.name: p.min})
                    assert p.name in result

    def test_at_max_accepted(self, registry):
        for tmpl in registry.list_templates():
            for p in tmpl.parameters:
                if p.max is not None and p.type in ("float", "int"):
                    result = tmpl.validate_params({p.name: p.max})
                    assert p.name in result


# ── 5. Harmonization exhaustive ───────────────────────────────────


class TestHarmonizationExhaustive:
    """Every ISO size in every standard table re-derives correctly."""

    def test_every_iso_bolt_size(self, registry):
        tmpl = registry.get("hex_bolt")
        for key, data in ISO_METRIC_THREADS.items():
            params = tmpl.apply_defaults({"shaft_diam": data["shaft_diam"]})
            params, msgs = harmonize_linked_params(tmpl, params, {"shaft_diam"})
            assert params["head_flat"] == data["head_flat"], f"{key} head_flat"
            assert params["head_height"] == data["head_height"], f"{key} head_height"
            assert params["thread_pitch"] == data["pitch_coarse"], f"{key} pitch"
            assert any("Re-derived" in m for m in msgs), f"{key} no message"

    def test_every_iso_shcs_size(self, registry):
        tmpl = registry.get("socket_head_cap_screw")
        for key, data in ISO_SHCS.items():
            params = tmpl.apply_defaults({"shaft_diam": data["shaft_diam"]})
            params, msgs = harmonize_linked_params(tmpl, params, {"shaft_diam"})
            assert params["head_diam"] == data["head_diam"], f"{key} head_diam"
            assert params["head_height"] == data["head_height"], f"{key} head_height"
            assert params["socket_size"] == data["socket_size"], f"{key} socket_size"
            assert any("Re-derived" in m for m in msgs), f"{key} no message"

    def test_every_iso_countersunk_size(self, registry):
        tmpl = registry.get("countersunk_screw")
        for key, data in ISO_COUNTERSUNK.items():
            params = tmpl.apply_defaults({"shaft_diam": data["shaft_diam"]})
            params, msgs = harmonize_linked_params(tmpl, params, {"shaft_diam"})
            assert params["head_diam"] == data["head_diam"], f"{key} head_diam"
            assert params["head_height"] == data["head_height"], f"{key} head_height"
            assert params["socket_size"] == data["socket_size"], f"{key} socket_size"
            assert any("Re-derived" in m for m in msgs), f"{key} no message"

    def test_harmonized_bolt_passes_constraints(self, registry):
        tmpl = registry.get("hex_bolt")
        for size_key, size_data in ISO_METRIC_THREADS.items():
            sd = size_data["shaft_diam"]
            params = tmpl.apply_defaults({"shaft_diam": sd, "shaft_len": max(30, sd * 4)})
            params, _ = harmonize_linked_params(tmpl, params, {"shaft_diam", "shaft_len"})
            errors, _ = validate_constraints(tmpl, params)
            assert not errors, f"hex_bolt {size_key} fails: {errors}"

    def test_harmonized_shcs_passes_constraints(self, registry):
        tmpl = registry.get("socket_head_cap_screw")
        for size_key, size_data in ISO_SHCS.items():
            sd = size_data["shaft_diam"]
            params = tmpl.apply_defaults({"shaft_diam": sd, "shaft_len": max(30, sd * 4)})
            params, _ = harmonize_linked_params(tmpl, params, {"shaft_diam", "shaft_len"})
            errors, _ = validate_constraints(tmpl, params)
            assert not errors, f"SHCS {size_key} fails: {errors}"

    def test_harmonized_countersunk_passes_constraints(self, registry):
        tmpl = registry.get("countersunk_screw")
        for size_key, size_data in ISO_COUNTERSUNK.items():
            sd = size_data["shaft_diam"]
            params = tmpl.apply_defaults({"shaft_diam": sd, "shaft_len": max(25, sd * 4)})
            params, _ = harmonize_linked_params(tmpl, params, {"shaft_diam", "shaft_len"})
            errors, _ = validate_constraints(tmpl, params)
            assert not errors, f"Countersunk {size_key} fails: {errors}"

    def test_explicit_override_never_overwritten(self, registry):
        """If user sets a param explicitly, harmonization must not change it."""
        tmpl = registry.get("socket_head_cap_screw")
        custom_head = 99.0
        params = tmpl.apply_defaults({"shaft_diam": 10, "head_diam": custom_head})
        params, _ = harmonize_linked_params(
            tmpl, params, {"shaft_diam", "head_diam"},
        )
        assert params["head_diam"] == custom_head

    def test_no_value_change_without_explicit_driver(self, registry):
        """If shaft_diam is just a default, values should stay the same
        (even though re-derivation runs and produces messages)."""
        tmpl = registry.get("socket_head_cap_screw")
        params = tmpl.apply_defaults({})
        orig = {k: v for k, v in params.items()}
        params, _ = harmonize_linked_params(tmpl, params, set())
        for key in ["head_diam", "head_height", "socket_size"]:
            assert params[key] == orig[key], f"{key} changed unexpectedly"


# ── 6. Render validity — every template, multiple param combos ────


class TestRenderValidity:
    """Every template renders valid OpenSCAD (no Python errors, output non-empty)."""

    def test_all_templates_default_render(self, engine):
        for tmpl in engine.registry.list_templates():
            result = engine.generate(template_id=tmpl.template_id)
            assert len(result.scad_code) > 100, f"{tmpl.template_id} too short"
            assert tmpl.module_name in result.scad_code

    def test_shcs_various_sizes(self, engine):
        for sd in [3, 5, 8, 12, 20]:
            result = engine.generate(
                template_id="socket_head_cap_screw",
                params={"shaft_diam": sd, "shaft_len": max(30, sd * 4)},
            )
            assert "socket_head_cap_screw" in result.scad_code

    def test_countersunk_various_sizes(self, engine):
        for sd in [3, 6, 10]:
            result = engine.generate(
                template_id="countersunk_screw",
                params={"shaft_diam": sd, "shaft_len": max(25, sd * 4)},
            )
            assert "countersunk_screw" in result.scad_code

    def test_washer_various_sizes(self, engine):
        for inner, outer in [(3.2, 7), (8.4, 16), (21, 37)]:
            result = engine.generate(
                template_id="washer",
                params={"inner_diam": inner, "outer_diam": outer, "thickness": 1.5},
            )
            assert "washer" in result.scad_code

    def test_set_screw_all_point_types(self, engine):
        for pt in [0, 1, 2, 3]:
            result = engine.generate(
                template_id="set_screw",
                params={"point_type": pt},
            )
            assert "set_screw" in result.scad_code

    def test_bolt_threads_off(self, engine):
        result = engine.generate(
            template_id="hex_bolt",
            params={"add_threads": False},
        )
        assert "hex_bolt" in result.scad_code

    def test_shcs_threads_off(self, engine):
        result = engine.generate(
            template_id="socket_head_cap_screw",
            params={"add_threads": False},
        )
        assert "socket_head_cap_screw" in result.scad_code


# ── 7. Resolver inference for new templates ───────────────────────


class TestResolverInference:
    """NLP resolver correctly routes descriptions to new templates."""

    def test_shcs_keywords(self, resolver):
        for desc in [
            "M8 socket head cap screw 30mm",
            "M6 SHCS 25mm long",
            "M10 allen bolt 40mm",
            "M5 allen screw",
            "M8 socket cap screw",
        ]:
            result = resolver.resolve(desc)
            assert result.suggested_template == "socket_head_cap_screw", \
                f"'{desc}' -> {result.suggested_template}"

    def test_countersunk_keywords(self, resolver):
        for desc in [
            "M6 countersunk screw 25mm",
            "M8 flat head screw",
            "M5 flush bolt 20mm",
            "M4 csk screw 15mm",
        ]:
            result = resolver.resolve(desc)
            assert result.suggested_template == "countersunk_screw", \
                f"'{desc}' -> {result.suggested_template}"

    def test_set_screw_keywords(self, resolver):
        for desc in [
            "M6 set screw 10mm",
            "M4 grub screw 8mm",
            "M8 headless screw",
        ]:
            result = resolver.resolve(desc)
            assert result.suggested_template == "set_screw", \
                f"'{desc}' -> {result.suggested_template}"

    def test_washer_keywords(self, resolver):
        for desc in [
            "M8 washer",
            "flat washer 10mm",
            "plain washer",
        ]:
            result = resolver.resolve(desc)
            assert result.suggested_template == "washer", \
                f"'{desc}' -> {result.suggested_template}"

    def test_hex_bolt_still_works(self, resolver):
        for desc in [
            "M8 hex bolt 30mm",
            "M10 bolt 40mm long",
            "M6 hex head bolt",
        ]:
            result = resolver.resolve(desc)
            assert result.suggested_template == "hex_bolt", \
                f"'{desc}' -> {result.suggested_template}"

    def test_shcs_gets_correct_params(self, resolver):
        result = resolver.resolve("M10 socket head cap screw 40mm")
        assert result.resolved_params.get("shaft_diam") == 10.0
        assert result.resolved_params.get("shaft_len") == 40.0

    def test_ambiguous_screw_defaults_to_hex(self, resolver):
        result = resolver.resolve("M8 screw 30mm")
        assert result.suggested_template == "hex_bolt"


# ── 8. Engineering warnings for new templates ─────────────────────


class TestEngineeringWarningsNew:
    def test_shcs_nonstandard_head_warns(self, registry):
        tmpl = registry.get("socket_head_cap_screw")
        params = tmpl.apply_defaults({"shaft_diam": 8, "head_diam": 20})
        warnings = check_engineering_warnings(tmpl, params)
        assert any("SHCS" in w and "head" in w.lower() for w in warnings)

    def test_shcs_standard_head_no_warning(self, registry):
        tmpl = registry.get("socket_head_cap_screw")
        params = tmpl.apply_defaults({"shaft_diam": 8})
        params, _ = harmonize_linked_params(tmpl, params, {"shaft_diam"})
        warnings = check_engineering_warnings(tmpl, params)
        assert not any("head" in w.lower() for w in warnings)

    def test_shcs_large_pitch_warns(self, registry):
        tmpl = registry.get("socket_head_cap_screw")
        params = tmpl.apply_defaults({"shaft_diam": 4, "thread_pitch": 3.0})
        warnings = check_engineering_warnings(tmpl, params)
        assert any("pitch" in w.lower() for w in warnings)

    def test_countersunk_nonstandard_head_warns(self, registry):
        tmpl = registry.get("countersunk_screw")
        params = tmpl.apply_defaults({"shaft_diam": 6, "head_diam": 20})
        warnings = check_engineering_warnings(tmpl, params)
        assert any("countersunk" in w.lower() and "head" in w.lower() for w in warnings)


# ── 9. Engine.generate integration ────────────────────────────────


class TestEngineIntegration:
    """Full pipeline through engine.generate()."""

    def test_constraint_violation_raises(self, engine):
        with pytest.raises(ConstraintViolationError) as exc_info:
            engine.generate(
                template_id="socket_head_cap_screw",
                params={"shaft_diam": 20, "head_diam": 10},
            )
        assert "head" in str(exc_info.value).lower()

    def test_range_violation_raises(self, engine):
        with pytest.raises(ParameterValidationError):
            engine.generate(
                template_id="hex_bolt",
                params={"shaft_diam": 0},
            )

    def test_warnings_propagated(self, engine):
        result = engine.generate(
            template_id="gear_spur",
            params={"modul": 1.1},
        )
        assert any("ISO 54" in w for w in result.warnings)

    def test_harmonization_propagated(self, engine):
        result = engine.generate(
            template_id="socket_head_cap_screw",
            params={"shaft_diam": 10, "shaft_len": 40},
        )
        assert result.parameters["head_diam"] == 16.0
        assert any("Re-derived" in w for w in result.warnings)

    def test_derived_values_computed_gear(self, engine):
        result = engine.generate(
            template_id="gear_spur",
            params={"teeth": 24, "modul": 2.0},
        )
        assert "pitch_diameter" in result.derived_values
        assert abs(result.derived_values["pitch_diameter"] - 48.0) < 0.01

    def test_derived_values_computed_washer(self, engine):
        result = engine.generate(
            template_id="washer",
            params={"inner_diam": 8.4, "outer_diam": 16, "thickness": 1.6},
        )
        assert "wall_thickness" in result.derived_values
        assert abs(result.derived_values["wall_thickness"] - 3.8) < 0.01

    def test_output_file_written(self, engine, tmp_path):
        out = str(tmp_path / "test_bolt.scad")
        result = engine.generate(
            template_id="hex_bolt",
            params={"shaft_diam": 8},
            output_path=out,
        )
        assert Path(out).exists()
        content = Path(out).read_text()
        assert "hex_bolt" in content


# ── 10. CLI integration ──────────────────────────────────────────


class TestCLIIntegration:
    """Run the actual CLI and check exit codes + output."""

    def _run(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [PYTHON, "-m", "scadgen", *args],
            capture_output=True, text=True, cwd=PROJECT,
            env={**__import__("os").environ, "PYTHONPATH": "."},
            timeout=30,
        )

    def test_list_shows_all_templates(self):
        r = self._run("list")
        assert r.returncode == 0
        for tid in ["hex_bolt", "socket_head_cap_screw", "countersunk_screw",
                     "washer", "set_screw", "hex_nut", "gear_spur"]:
            assert tid in r.stdout, f"{tid} missing from list"

    def test_info_shows_params(self):
        r = self._run("info", "socket_head_cap_screw")
        assert r.returncode == 0
        assert "socket_size" in r.stdout
        assert "head_diam" in r.stdout

    def test_generate_stdout(self):
        r = self._run("generate", "--template", "washer", "--stdout")
        assert r.returncode == 0
        assert "washer" in r.stdout
        assert "cylinder" in r.stdout

    def test_constraint_error_exit_code(self):
        r = self._run("generate", "--template", "hex_bolt",
                       "--set", "thread_len=50", "shaft_len=20", "--stdout")
        assert r.returncode == 1
        assert "Geometry error" in r.stderr

    def test_range_error_exit_code(self):
        r = self._run("generate", "--template", "hex_bolt",
                       "--set", "shaft_diam=0", "--stdout")
        assert r.returncode == 1
        assert "Error" in r.stderr
        assert "below minimum" in r.stderr

    def test_dry_run(self):
        r = self._run("generate", "--template", "socket_head_cap_screw",
                       "--set", "shaft_diam=10", "--dry-run")
        assert r.returncode == 0
        assert "shaft_diam" in r.stdout
        assert "head_diam" in r.stdout

    def test_verbose_output(self):
        r = self._run("generate", "--template", "socket_head_cap_screw",
                       "--set", "shaft_diam=10", "shaft_len=40", "-v")
        assert r.returncode == 0
        assert "head_diam = 16.0" in r.stdout

    def test_unknown_template(self):
        r = self._run("generate", "--template", "nonexistent_template", "--stdout")
        assert r.returncode == 1

    def test_bad_set_syntax(self):
        r = self._run("generate", "--template", "hex_bolt", "--set", "badparam", "--stdout")
        assert r.returncode == 1
        assert "key=value" in r.stderr


# ── 11. Floating point precision in constraints ───────────────────


class TestFloatingPointConstraints:
    def test_ieee_754_subtraction_doesnt_cause_false_positive(self, registry):
        tmpl = registry.get("bushing")
        # 0.1 + 0.2 != 0.3 in IEEE 754, but constraint is (outer_d - inner_d)/2 >= 1.0
        params = tmpl.apply_defaults({"inner_d": 8.0, "outer_d": 10.0})
        errors, warnings = check_template_constraints(tmpl, params)
        assert not errors

    def test_very_small_valid_wall(self, registry):
        tmpl = registry.get("bushing")
        params = tmpl.apply_defaults({"inner_d": 8.0, "outer_d": 10.0})
        _, warnings = check_template_constraints(tmpl, params)
        assert not any("1mm" in w for w in warnings)  # wall = 1.0, exactly at threshold

    def test_gear_root_circle_precision(self, registry):
        tmpl = registry.get("gear_spur")
        # root_diam = modul * (teeth - 2.5) = 1.0 * (12 - 2.5) = 9.5
        # bore < root_diam: bore_diam/2 < root_diam/2 => bore_diam < 9.5
        params = tmpl.apply_defaults({"teeth": 12, "modul": 1.0, "bore_diam": 9.49})
        errors, _ = check_template_constraints(tmpl, params)
        assert not errors

    def test_gear_bore_at_root_fails(self, registry):
        tmpl = registry.get("gear_spur")
        params = tmpl.apply_defaults({"teeth": 12, "modul": 1.0, "bore_diam": 9.5})
        errors, _ = check_template_constraints(tmpl, params)
        assert errors


# ── 12. Template discovery and metadata ───────────────────────────


class TestTemplateMetadata:
    def test_expected_template_count(self, registry):
        templates = registry.list_templates()
        ids = [t.template_id for t in templates]
        expected = [
            "bushing", "cone", "connecting_rod", "countersunk_screw",
            "cube", "cylinder", "cylinder_block", "cylinder_head",
            "gear_spur", "hex_bolt", "hex_nut", "lamp_arm",
            "lamp_base", "lamp_shade", "piston",
            "set_screw", "shaft", "socket_head_cap_screw", "sphere",
            "torus", "valve", "washer",
        ]
        for eid in expected:
            assert eid in ids, f"Missing template: {eid}"
        assert len(templates) == 28

    def test_all_fasteners_have_connectors(self, registry):
        fastener_ids = [
            "hex_bolt", "hex_nut", "socket_head_cap_screw",
            "countersunk_screw", "set_screw", "washer",
        ]
        for tid in fastener_ids:
            tmpl = registry.get(tid)
            assert len(tmpl.connectors) >= 2, f"{tid} has < 2 connectors"

    def test_all_fasteners_have_constraints(self, registry):
        fastener_ids = [
            "hex_bolt", "hex_nut", "socket_head_cap_screw",
            "countersunk_screw", "set_screw", "washer",
        ]
        for tid in fastener_ids:
            tmpl = registry.get(tid)
            assert len(tmpl.constraints) >= 1, f"{tid} has no constraints"

    def test_aliases_resolve(self, registry):
        alias_map = {
            "shcs": "socket_head_cap_screw",
            "allen bolt": "socket_head_cap_screw",
            "cap screw": "socket_head_cap_screw",
            "flat head screw": "countersunk_screw",
            "grub screw": "set_screw",
            "flat washer": "washer",
            "bolt": "hex_bolt",
        }
        for alias, expected_id in alias_map.items():
            tmpl = registry.get(alias)
            assert tmpl.template_id == expected_id, \
                f"Alias '{alias}' -> {tmpl.template_id}, expected {expected_id}"

    def test_all_templates_have_category(self, registry):
        for tmpl in registry.list_templates():
            assert tmpl.category, f"{tmpl.template_id} has no category"

    def test_all_templates_have_description(self, registry):
        for tmpl in registry.list_templates():
            assert len(tmpl.description) > 10, f"{tmpl.template_id} description too short"


# ── 13. Stress: generate all ISO sizes through full pipeline ──────


class TestStressAllSizes:
    """Generate every ISO metric size for bolt, SHCS, and nut through the full engine."""

    def test_every_iso_bolt(self, engine):
        for key, data in ISO_METRIC_THREADS.items():
            sd = data["shaft_diam"]
            result = engine.generate(
                template_id="hex_bolt",
                params={"shaft_diam": sd, "shaft_len": max(30, sd * 4)},
            )
            assert result.parameters["head_flat"] == data["head_flat"], f"{key}"
            assert not any("error" in w.lower() for w in result.warnings)

    def test_every_iso_shcs(self, engine):
        for key, data in ISO_SHCS.items():
            sd = data["shaft_diam"]
            result = engine.generate(
                template_id="socket_head_cap_screw",
                params={"shaft_diam": sd, "shaft_len": max(30, sd * 4)},
            )
            assert result.parameters["head_diam"] == data["head_diam"], f"{key}"

    def test_every_iso_countersunk(self, engine):
        for key, data in ISO_COUNTERSUNK.items():
            sd = data["shaft_diam"]
            result = engine.generate(
                template_id="countersunk_screw",
                params={"shaft_diam": sd, "shaft_len": max(25, sd * 4)},
            )
            assert result.parameters["head_diam"] == data["head_diam"], f"{key}"


# ── 14. Bug regression: cylinder cutter mode z_shift ───────────────


class TestCylinderCutterMode:
    """Verify cylinder template cutter mode produces correct OpenSCAD geometry."""

    def test_cutter_zshift_uses_ternary(self, registry):
        """The z_shift must use ternary, not if-block assignment (OpenSCAD scoping)."""
        tmpl = registry.get("cylinder")
        assert "z_shift = as_cutter ?" in tmpl.source_code

    def test_cutter_mode_no_if_block_reassignment(self, registry):
        """Ensure there's no if(as_cutter) { z_shift = ... } pattern."""
        tmpl = registry.get("cylinder")
        import re
        bad_pattern = re.compile(r"if\s*\(as_cutter\)\s*\{[^}]*z_shift\s*=", re.DOTALL)
        assert not bad_pattern.search(tmpl.source_code), \
            "z_shift must not be assigned inside if-block (OpenSCAD child scope issue)"


# ── 15. Bug regression: washer resolver maps M-size correctly ──────


class TestWasherResolverMapping:
    """Verify M-size descriptions resolve to correct washer dimensions."""

    def test_m6_washer_gets_m6_dimensions(self):
        resolver = _make_resolver()
        result = resolver.resolve("M6 washer")
        assert result.suggested_template == "washer"
        assert result.resolved_params.get("inner_diam") == ISO_WASHERS["M6"]["inner_diam"]
        assert result.resolved_params.get("outer_diam") == ISO_WASHERS["M6"]["outer_diam"]

    def test_m10_washer_gets_m10_dimensions(self):
        resolver = _make_resolver()
        result = resolver.resolve("M10 washer")
        assert result.suggested_template == "washer"
        assert result.resolved_params.get("inner_diam") == ISO_WASHERS["M10"]["inner_diam"]

    def test_m8_washer_gets_m8_dimensions(self):
        resolver = _make_resolver()
        result = resolver.resolve("M8 flat washer")
        assert result.suggested_template == "washer"
        assert result.resolved_params.get("inner_diam") == ISO_WASHERS["M8"]["inner_diam"]

    def test_washer_resolver_removes_bolt_params(self):
        resolver = _make_resolver()
        result = resolver.resolve("M8 washer")
        assert "shaft_diam" not in result.resolved_params
        assert "head_flat" not in result.resolved_params
        assert "head_height" not in result.resolved_params

    def test_washer_length_mapped_to_thickness(self):
        resolver = _make_resolver()
        result = resolver.resolve("M8 washer 3mm")
        assert result.resolved_params.get("thickness") == 3.0

    def test_every_iso_washer_resolves(self):
        resolver = _make_resolver()
        for key in ISO_WASHERS:
            result = resolver.resolve(f"{key} washer")
            assert result.suggested_template == "washer", f"{key} not inferred as washer"
            assert "inner_diam" in result.resolved_params, f"{key} missing inner_diam"
            assert result.resolved_params["inner_diam"] == ISO_WASHERS[key]["inner_diam"], \
                f"{key}: expected {ISO_WASHERS[key]['inner_diam']}, got {result.resolved_params['inner_diam']}"


# ── 16. Engine template rendering ────────────────────────────────


class TestEngineTemplateRendering:
    """All engine templates render valid OpenSCAD with default params."""

    ENGINE_IDS = [
        "valve", "shaft", "piston", "connecting_rod",
        "cylinder_block", "cylinder_head",
    ]

    def test_all_engine_templates_render(self, engine):
        for tid in self.ENGINE_IDS:
            result = engine.generate(template_id=tid, params={})
            assert result.scad_code, f"{tid} produced empty output"
            assert result.template.template_id == tid

    def test_engine_templates_have_connectors(self, registry):
        for tid in self.ENGINE_IDS:
            tmpl = registry.get(tid)
            assert len(tmpl.connectors) >= 2, f"{tid} has < 2 connectors"

    def test_engine_templates_have_constraints(self, registry):
        for tid in self.ENGINE_IDS:
            tmpl = registry.get(tid)
            assert len(tmpl.constraints) >= 2, f"{tid} has < 2 constraints"

    def test_engine_defaults_pass_constraints(self, engine):
        for tid in self.ENGINE_IDS:
            result = engine.generate(template_id=tid, params={})
            assert not any("error" in w.lower() for w in result.warnings), \
                f"{tid} defaults produce errors: {result.warnings}"

    def test_valve_render_contains_module_call(self, engine):
        result = engine.generate(template_id="valve", params={})
        assert "valve(" in result.scad_code

    def test_shaft_render_with_keyway(self, engine):
        result = engine.generate(
            template_id="shaft",
            params={"diameter": 25, "has_keyway": True},
        )
        assert "shaft(" in result.scad_code
        assert "has_keyway = true" in result.scad_code

    def test_piston_render_ring_count(self, engine):
        result = engine.generate(
            template_id="piston",
            params={"bore_diam": 86, "ring_count": 3},
        )
        assert "piston(" in result.scad_code
        assert "ring_count = 3" in result.scad_code

    def test_cylinder_block_four_bores(self, engine):
        result = engine.generate(
            template_id="cylinder_block",
            params={"bore_diam": 86, "bore_count": 4},
        )
        assert "cylinder_block(" in result.scad_code
        assert "bore_count = 4" in result.scad_code

    def test_cylinder_head_valve_count(self, engine):
        result = engine.generate(
            template_id="cylinder_head",
            params={"valves_per_cyl": 4},
        )
        assert "cylinder_head(" in result.scad_code
        assert "valves_per_cyl = 4" in result.scad_code

    def test_connecting_rod_render(self, engine):
        result = engine.generate(
            template_id="connecting_rod",
            params={"length": 160, "big_end_bore": 45},
        )
        assert "connecting_rod(" in result.scad_code


# ── 17. Engine template harmonization via full pipeline ──────────


class TestEngineHarmonization:
    def test_valve_harmonizes_stem_from_head(self, engine):
        result = engine.generate(
            template_id="valve",
            params={"head_diam": 40},
        )
        assert result.parameters["stem_diam"] == 8.0

    def test_shaft_harmonizes_keyway_from_din(self, engine):
        result = engine.generate(
            template_id="shaft",
            params={"diameter": 25, "has_keyway": True},
        )
        assert result.parameters["keyway_width"] == 8.0

    def test_piston_harmonizes_pin_from_bore(self, engine):
        result = engine.generate(
            template_id="piston",
            params={"bore_diam": 100},
        )
        assert result.parameters["pin_bore_diam"] == 25.0

    def test_block_harmonizes_spacing_from_bore(self, engine):
        result = engine.generate(
            template_id="cylinder_block",
            params={"bore_diam": 86},
        )
        assert result.parameters["bore_spacing"] == 96.3

    def test_head_harmonizes_valve_bore(self, engine):
        result = engine.generate(
            template_id="cylinder_head",
            params={"bore_diam": 86},
        )
        assert result.parameters["valve_bore_diam"] == 8.6

    def test_conrod_harmonizes_widths(self, engine):
        result = engine.generate(
            template_id="connecting_rod",
            params={"big_end_bore": 50},
        )
        assert result.parameters["big_end_width"] == 70.0


# ── 18. Engine template resolver routing ─────────────────────────


class TestEngineResolverRouting:
    def test_cylinder_block_not_matched_as_cylinder(self):
        resolver = _make_resolver()
        result = resolver.resolve("cylinder block")
        assert result.suggested_template == "cylinder_block"

    def test_cylinder_head_not_matched_as_cylinder(self):
        resolver = _make_resolver()
        result = resolver.resolve("cylinder head")
        assert result.suggested_template == "cylinder_head"

    def test_plain_cylinder_still_works(self):
        resolver = _make_resolver()
        result = resolver.resolve("cylinder 50mm")
        assert result.suggested_template is None or result.suggested_template == "cylinder"

    def test_shaft_with_m8_bolt_resolves_bolt(self):
        resolver = _make_resolver()
        result = resolver.resolve("M8 bolt for shaft")
        assert result.suggested_template == "hex_bolt"

    def test_standalone_shaft_resolves_shaft(self):
        resolver = _make_resolver()
        result = resolver.resolve("shaft 100mm")
        assert result.suggested_template == "shaft"

    def test_engine_block_resolves(self):
        resolver = _make_resolver()
        result = resolver.resolve("engine block 4 cylinder")
        assert result.suggested_template == "cylinder_block"


# ── 19. Tier 3 template rendering ──────────────────────────────────


class TestTier3Rendering:
    TIER3_IDS = [
        "spring_compression", "gasket", "bearing_shell",
        "pulley", "flywheel", "oil_pan",
    ]

    def test_all_tier3_render_defaults(self, engine):
        for tid in self.TIER3_IDS:
            result = engine.generate(template_id=tid, params={})
            assert result.scad_code, f"{tid} produced empty output"
            assert result.template.template_id == tid

    def test_tier3_have_connectors(self, registry):
        for tid in self.TIER3_IDS:
            tmpl = registry.get(tid)
            assert len(tmpl.connectors) >= 2, f"{tid} has < 2 connectors"

    def test_tier3_have_constraints(self, registry):
        for tid in self.TIER3_IDS:
            tmpl = registry.get(tid)
            assert len(tmpl.constraints) >= 2, f"{tid} has < 2 constraints"

    def test_tier3_defaults_pass_constraints(self, engine):
        for tid in self.TIER3_IDS:
            result = engine.generate(template_id=tid, params={})
            assert not any("error" in w.lower() for w in result.warnings), \
                f"{tid} defaults produce errors: {result.warnings}"

    def test_spring_with_custom_coils(self, engine):
        result = engine.generate(
            template_id="spring_compression",
            params={"active_coils": 12, "coil_diam": 25},
        )
        assert "spring_compression(" in result.scad_code
        assert "active_coils = 12" in result.scad_code

    def test_gasket_with_bolt_pattern(self, engine):
        result = engine.generate(
            template_id="gasket",
            params={"bolt_hole_count": 12, "inner_diam": 90},
        )
        assert "gasket(" in result.scad_code
        assert "bolt_hole_count = 12" in result.scad_code

    def test_flywheel_six_bolts(self, engine):
        result = engine.generate(
            template_id="flywheel",
            params={"outer_diam": 250, "bolt_count": 8},
        )
        assert "flywheel(" in result.scad_code
        assert "bolt_count = 8" in result.scad_code

    def test_oil_pan_custom_depth(self, engine):
        result = engine.generate(
            template_id="oil_pan",
            params={"depth": 120, "length": 450},
        )
        assert "oil_pan(" in result.scad_code


# ── 20. Tier 3 harmonization via full pipeline ─────────────────────


class TestTier3HarmonizationPipeline:
    def test_spring_harmonizes_wire(self, engine):
        result = engine.generate(
            template_id="spring_compression",
            params={"coil_diam": 30},
        )
        assert result.parameters["wire_diam"] == 3.0

    def test_gasket_harmonizes_outer(self, engine):
        result = engine.generate(
            template_id="gasket",
            params={"inner_diam": 100},
        )
        assert result.parameters["outer_diam"] == 150.0
        assert result.parameters["bolt_circle_diam"] == 125.0

    def test_bearing_harmonizes_outer(self, engine):
        result = engine.generate(
            template_id="bearing_shell",
            params={"bore": 40},
        )
        assert result.parameters["wall_thickness"] == 2.4
        assert result.parameters["outer_diam"] == 44.8

    def test_pulley_harmonizes_hub(self, engine):
        result = engine.generate(
            template_id="pulley",
            params={"pitch_diam": 100},
        )
        assert result.parameters["hub_diam"] == 50.0
        assert result.parameters["groove_depth"] == 10.0

    def test_flywheel_harmonizes_bore(self, engine):
        result = engine.generate(
            template_id="flywheel",
            params={"outer_diam": 300},
        )
        assert result.parameters["bore_diam"] == 37.5
        assert result.parameters["bolt_circle_diam"] == 225.0

    def test_oil_pan_harmonizes_flange(self, engine):
        result = engine.generate(
            template_id="oil_pan",
            params={"length": 500, "width": 200},
        )
        assert result.parameters["flange_width"] == 19.6


# ── 21. Tier 3 resolver routing ────────────────────────────────────


class TestTier3ResolverRouting:
    def test_compression_spring_resolves(self):
        resolver = _make_resolver()
        result = resolver.resolve("compression spring 50mm")
        assert result.suggested_template == "spring_compression"
        assert result.resolved_params.get("free_length") == 50.0

    def test_gasket_resolves(self):
        resolver = _make_resolver()
        result = resolver.resolve("flange gasket 2mm")
        assert result.suggested_template == "gasket"
        assert result.resolved_params.get("thickness") == 2.0

    def test_bearing_shell_resolves(self):
        resolver = _make_resolver()
        result = resolver.resolve("sleeve bearing 25mm")
        assert result.suggested_template == "bearing_shell"
        assert result.resolved_params.get("width") == 25.0

    def test_pulley_resolves(self):
        resolver = _make_resolver()
        result = resolver.resolve("v-belt pulley")
        assert result.suggested_template == "pulley"

    def test_flywheel_resolves(self):
        resolver = _make_resolver()
        result = resolver.resolve("inertia wheel 40mm")
        assert result.suggested_template == "flywheel"
        assert result.resolved_params.get("thickness") == 40.0

    def test_oil_pan_resolves(self):
        resolver = _make_resolver()
        result = resolver.resolve("oil sump 90mm deep")
        assert result.suggested_template == "oil_pan"
        assert result.resolved_params.get("depth") == 90.0

    def test_spring_not_confused_with_set_screw(self):
        resolver = _make_resolver()
        result = resolver.resolve("helical spring")
        assert result.suggested_template == "spring_compression"
