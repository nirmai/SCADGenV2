"""Tests for cross-parameter constraints, linked re-derivation, and engineering warnings."""

from __future__ import annotations

import pytest

from scadgen.core.template_registry import TemplateRegistry
from scadgen.exceptions import ConstraintViolationError
from scadgen.knowledge.constraints import (
    check_engineering_warnings,
    check_template_constraints,
    find_iso_by_shaft_diam,
    harmonize_linked_params,
    validate_constraints,
)


@pytest.fixture
def registry():
    return TemplateRegistry(["scadgen/templates"])


# ── Tier 1: Geometric feasibility (hard errors) ─────────────────────


class TestBushingConstraints:
    def test_inner_exceeds_outer_errors(self, registry):
        tmpl = registry.get("bushing")
        params = tmpl.apply_defaults({"inner_d": 30, "outer_d": 20, "thickness": 10})
        errors, _ = check_template_constraints(tmpl, params)
        assert errors
        assert "must exceed" in errors[0].lower() or "outer" in errors[0].lower()

    def test_valid_bushing_passes(self, registry):
        tmpl = registry.get("bushing")
        params = tmpl.apply_defaults({"inner_d": 10, "outer_d": 20, "thickness": 8})
        errors, _ = check_template_constraints(tmpl, params)
        assert not errors

    def test_thin_wall_warns(self, registry):
        tmpl = registry.get("bushing")
        params = tmpl.apply_defaults({"inner_d": 19.5, "outer_d": 20, "thickness": 8})
        _, warnings = check_template_constraints(tmpl, params)
        assert any("1mm" in w for w in warnings)


class TestCylinderConstraints:
    def test_inner_exceeds_outer_in_tube_mode(self, registry):
        tmpl = registry.get("cylinder")
        params = tmpl.apply_defaults({"diam": 10, "inner_diam": 15})
        errors, _ = check_template_constraints(tmpl, params)
        assert errors

    def test_solid_cylinder_passes(self, registry):
        tmpl = registry.get("cylinder")
        params = tmpl.apply_defaults({"diam": 20, "inner_diam": 0})
        errors, _ = check_template_constraints(tmpl, params)
        assert not errors

    def test_valid_tube_passes(self, registry):
        tmpl = registry.get("cylinder")
        params = tmpl.apply_defaults({"diam": 20, "inner_diam": 10})
        errors, _ = check_template_constraints(tmpl, params)
        assert not errors


class TestTorusConstraints:
    def test_minor_exceeds_major_errors(self, registry):
        tmpl = registry.get("torus")
        params = tmpl.apply_defaults({"major_r": 5, "minor_r": 10})
        errors, _ = check_template_constraints(tmpl, params)
        assert errors
        assert "self-intersection" in errors[0].lower()

    def test_valid_torus_passes(self, registry):
        tmpl = registry.get("torus")
        params = tmpl.apply_defaults({"major_r": 25, "minor_r": 6})
        errors, _ = check_template_constraints(tmpl, params)
        assert not errors


class TestGearConstraints:
    def test_bore_obliterates_gear_errors(self, registry):
        tmpl = registry.get("gear_spur")
        params = tmpl.apply_defaults({"teeth": 12, "modul": 1.0, "bore_diam": 50})
        errors, _ = check_template_constraints(tmpl, params)
        assert errors
        assert "bore" in errors[0].lower()

    def test_zero_bore_passes(self, registry):
        tmpl = registry.get("gear_spur")
        params = tmpl.apply_defaults({"teeth": 24, "modul": 2.0, "bore_diam": 0})
        errors, _ = check_template_constraints(tmpl, params)
        assert not errors

    def test_reasonable_bore_passes(self, registry):
        tmpl = registry.get("gear_spur")
        params = tmpl.apply_defaults({"teeth": 24, "modul": 2.0, "bore_diam": 5})
        errors, _ = check_template_constraints(tmpl, params)
        assert not errors

    def test_thin_hub_warns(self, registry):
        tmpl = registry.get("gear_spur")
        # root_diam = 2.0 * (24 - 2.5) = 43.0, root_r = 21.5
        # bore_r = 20.5, hub = 1.0 — exactly 1 module boundary
        # Make hub thinner: bore_diam = 41.5, bore_r = 20.75, hub = 0.75
        params = tmpl.apply_defaults({"teeth": 24, "modul": 2.0, "bore_diam": 41.5})
        _, warnings = check_template_constraints(tmpl, params)
        assert any("hub" in w.lower() or "structurally" in w.lower() for w in warnings)


class TestBoltConstraints:
    def test_thread_exceeds_shaft_errors(self, registry):
        tmpl = registry.get("hex_bolt")
        params = tmpl.apply_defaults({"shaft_len": 30, "thread_len": 50})
        errors, _ = check_template_constraints(tmpl, params)
        assert errors
        assert "thread" in errors[0].lower()

    def test_head_smaller_than_shaft_errors(self, registry):
        tmpl = registry.get("hex_bolt")
        params = tmpl.apply_defaults({"shaft_diam": 20, "head_flat": 10})
        errors, _ = check_template_constraints(tmpl, params)
        assert any("head" in e.lower() for e in errors)

    def test_valid_bolt_passes(self, registry):
        tmpl = registry.get("hex_bolt")
        params = tmpl.apply_defaults({})
        errors, _ = check_template_constraints(tmpl, params)
        assert not errors


class TestNutConstraints:
    def test_flat_smaller_than_thread_errors(self, registry):
        tmpl = registry.get("hex_nut")
        params = tmpl.apply_defaults({"thread_diam": 20, "flat": 10})
        errors, _ = check_template_constraints(tmpl, params)
        assert errors

    def test_valid_nut_passes(self, registry):
        tmpl = registry.get("hex_nut")
        params = tmpl.apply_defaults({})
        errors, _ = check_template_constraints(tmpl, params)
        assert not errors


class TestAllDefaultsPass:
    """Every template must pass constraints with its default parameters."""

    def test_defaults_pass(self, registry):
        for tmpl in registry.list_templates():
            params = tmpl.apply_defaults({})
            errors, _ = validate_constraints(tmpl, params)
            assert not errors, f"{tmpl.template_id} fails with defaults: {errors}"


# ── Tier 2: Linked dimension re-derivation ───────────────────────────


class TestLinkedDimensions:
    def test_bolt_shaft_diam_rederives_head(self, registry):
        tmpl = registry.get("hex_bolt")
        params = tmpl.apply_defaults({"shaft_diam": 10})
        params, messages = harmonize_linked_params(tmpl, params, user_explicit={"shaft_diam"})
        assert params["head_flat"] == 16.0  # M10
        assert params["head_height"] == 6.4  # M10
        assert params["thread_pitch"] == 1.5  # M10
        assert any("Re-derived" in m for m in messages)

    def test_bolt_explicit_head_preserved(self, registry):
        tmpl = registry.get("hex_bolt")
        params = tmpl.apply_defaults({"shaft_diam": 10, "head_flat": 20})
        params, _ = harmonize_linked_params(
            tmpl, params, user_explicit={"shaft_diam", "head_flat"},
        )
        assert params["head_flat"] == 20  # user override kept

    def test_bolt_nonstandard_shaft_warns(self, registry):
        tmpl = registry.get("hex_bolt")
        params = tmpl.apply_defaults({"shaft_diam": 7})
        params, messages = harmonize_linked_params(tmpl, params, user_explicit={"shaft_diam"})
        assert any("does not match" in m for m in messages)

    def test_bolt_default_no_rederivation(self, registry):
        tmpl = registry.get("hex_bolt")
        params = tmpl.apply_defaults({})
        original_head_flat = params["head_flat"]
        params, messages = harmonize_linked_params(tmpl, params, user_explicit=set())
        assert params["head_flat"] == original_head_flat

    def test_nut_thread_diam_rederives(self, registry):
        tmpl = registry.get("hex_nut")
        params = tmpl.apply_defaults({"thread_diam": 12})
        params, messages = harmonize_linked_params(tmpl, params, user_explicit={"thread_diam"})
        assert params["flat"] == 18.0  # M12
        assert params["thickness"] == 10.8  # M12
        assert params["pitch"] == 1.75  # M12


# ── Tier 3: Engineering warnings ─────────────────────────────────────


class TestEngineeringWarnings:
    def test_nonstandard_gear_module_warns(self, registry):
        tmpl = registry.get("gear_spur")
        params = tmpl.apply_defaults({"modul": 1.1})
        warnings = check_engineering_warnings(tmpl, params)
        assert any("ISO 54" in w for w in warnings)
        assert any("1.0" in w for w in warnings)

    def test_standard_gear_module_no_warning(self, registry):
        tmpl = registry.get("gear_spur")
        params = tmpl.apply_defaults({"modul": 2.0})
        warnings = check_engineering_warnings(tmpl, params)
        assert not any("ISO 54" in w for w in warnings)

    def test_bolt_pitch_too_large_warns(self, registry):
        tmpl = registry.get("hex_bolt")
        params = tmpl.apply_defaults({"shaft_diam": 4, "thread_pitch": 3.0})
        warnings = check_engineering_warnings(tmpl, params)
        assert any("pitch" in w.lower() for w in warnings)

    def test_bolt_iso_mismatch_warns(self, registry):
        tmpl = registry.get("hex_bolt")
        # M8 shaft but non-standard head
        params = tmpl.apply_defaults({"shaft_diam": 8, "head_flat": 20})
        warnings = check_engineering_warnings(tmpl, params)
        assert any("head" in w.lower() and "M8" in w for w in warnings)


# ── ISO reverse lookup ───────────────────────────────────────────────


class TestFindIso:
    def test_finds_m8(self):
        result = find_iso_by_shaft_diam(8.0)
        assert result is not None
        key, data = result
        assert key == "M8"
        assert data["head_flat"] == 13.0

    def test_finds_m12(self):
        result = find_iso_by_shaft_diam(12.0)
        assert result is not None
        assert result[0] == "M12"

    def test_no_match_for_nonstandard(self):
        result = find_iso_by_shaft_diam(7.0)
        assert result is None
