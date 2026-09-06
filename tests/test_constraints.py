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


# ── New fastener templates ──────────────────────────────────────────


class TestSHCSConstraints:
    def test_thread_exceeds_shaft_errors(self, registry):
        tmpl = registry.get("socket_head_cap_screw")
        params = tmpl.apply_defaults({"shaft_len": 20, "thread_len": 30})
        errors, _ = check_template_constraints(tmpl, params)
        assert errors
        assert "thread" in errors[0].lower()

    def test_head_smaller_than_shaft_errors(self, registry):
        tmpl = registry.get("socket_head_cap_screw")
        params = tmpl.apply_defaults({"shaft_diam": 15, "head_diam": 10})
        errors, _ = check_template_constraints(tmpl, params)
        assert any("head" in e.lower() for e in errors)

    def test_socket_exceeds_head_errors(self, registry):
        tmpl = registry.get("socket_head_cap_screw")
        params = tmpl.apply_defaults({"head_diam": 10, "socket_size": 12})
        errors, _ = check_template_constraints(tmpl, params)
        assert any("socket" in e.lower() for e in errors)

    def test_valid_shcs_passes(self, registry):
        tmpl = registry.get("socket_head_cap_screw")
        params = tmpl.apply_defaults({})
        errors, _ = check_template_constraints(tmpl, params)
        assert not errors


class TestCountersunkConstraints:
    def test_thread_exceeds_shaft_errors(self, registry):
        tmpl = registry.get("countersunk_screw")
        params = tmpl.apply_defaults({"shaft_len": 15, "thread_len": 25})
        errors, _ = check_template_constraints(tmpl, params)
        assert errors

    def test_head_smaller_than_shaft_errors(self, registry):
        tmpl = registry.get("countersunk_screw")
        params = tmpl.apply_defaults({"shaft_diam": 15, "head_diam": 10})
        errors, _ = check_template_constraints(tmpl, params)
        assert any("head" in e.lower() for e in errors)

    def test_valid_countersunk_passes(self, registry):
        tmpl = registry.get("countersunk_screw")
        params = tmpl.apply_defaults({})
        errors, _ = check_template_constraints(tmpl, params)
        assert not errors


class TestWasherConstraints:
    def test_outer_smaller_than_inner_errors(self, registry):
        tmpl = registry.get("washer")
        params = tmpl.apply_defaults({"inner_diam": 20, "outer_diam": 10})
        errors, _ = check_template_constraints(tmpl, params)
        assert errors
        assert "outer" in errors[0].lower()

    def test_valid_washer_passes(self, registry):
        tmpl = registry.get("washer")
        params = tmpl.apply_defaults({})
        errors, _ = check_template_constraints(tmpl, params)
        assert not errors


class TestSetScrewConstraints:
    def test_socket_exceeds_diameter_errors(self, registry):
        tmpl = registry.get("set_screw")
        params = tmpl.apply_defaults({"shaft_diam": 4, "socket_size": 6})
        errors, _ = check_template_constraints(tmpl, params)
        assert any("socket" in e.lower() for e in errors)

    def test_valid_set_screw_passes(self, registry):
        tmpl = registry.get("set_screw")
        params = tmpl.apply_defaults({})
        errors, _ = check_template_constraints(tmpl, params)
        assert not errors


class TestSHCSLinkedDimensions:
    def test_shcs_shaft_diam_rederives(self, registry):
        tmpl = registry.get("socket_head_cap_screw")
        params = tmpl.apply_defaults({"shaft_diam": 10})
        params, messages = harmonize_linked_params(tmpl, params, user_explicit={"shaft_diam"})
        assert params["head_diam"] == 16.0   # M10 SHCS
        assert params["head_height"] == 10.0  # M10 SHCS
        assert params["socket_size"] == 8.0   # M10 SHCS
        assert any("Re-derived" in m for m in messages)

    def test_shcs_explicit_head_preserved(self, registry):
        tmpl = registry.get("socket_head_cap_screw")
        params = tmpl.apply_defaults({"shaft_diam": 10, "head_diam": 20})
        params, _ = harmonize_linked_params(
            tmpl, params, user_explicit={"shaft_diam", "head_diam"},
        )
        assert params["head_diam"] == 20  # user override kept

    def test_countersunk_shaft_rederives(self, registry):
        tmpl = registry.get("countersunk_screw")
        params = tmpl.apply_defaults({"shaft_diam": 8})
        params, messages = harmonize_linked_params(tmpl, params, user_explicit={"shaft_diam"})
        assert params["head_diam"] == 17.92  # M8 countersunk
        assert params["socket_size"] == 5.0
        assert any("Re-derived" in m for m in messages)


# ── Engine template constraints ────────────────────────────────────


class TestValveConstraints:
    def test_head_smaller_than_stem_errors(self, registry):
        tmpl = registry.get("valve")
        params = tmpl.apply_defaults({"head_diam": 5, "stem_diam": 8})
        errors, _ = check_template_constraints(tmpl, params)
        assert errors
        assert "head" in errors[0].lower()

    def test_seat_too_wide_errors(self, registry):
        tmpl = registry.get("valve")
        params = tmpl.apply_defaults({"head_diam": 30, "stem_diam": 6, "seat_width": 15})
        errors, _ = check_template_constraints(tmpl, params)
        assert any("seat" in e.lower() for e in errors)

    def test_valid_valve_passes(self, registry):
        tmpl = registry.get("valve")
        params = tmpl.apply_defaults({})
        errors, _ = check_template_constraints(tmpl, params)
        assert not errors


class TestShaftConstraints:
    def test_keyway_wider_than_shaft_errors(self, registry):
        tmpl = registry.get("shaft")
        params = tmpl.apply_defaults({
            "diameter": 10, "has_keyway": True, "keyway_width": 12,
        })
        errors, _ = check_template_constraints(tmpl, params)
        assert errors
        assert "keyway" in errors[0].lower()

    def test_keyway_deeper_than_radius_errors(self, registry):
        tmpl = registry.get("shaft")
        params = tmpl.apply_defaults({
            "diameter": 10, "has_keyway": True, "keyway_depth": 6,
        })
        errors, _ = check_template_constraints(tmpl, params)
        assert any("keyway" in e.lower() and "depth" in e.lower() for e in errors)

    def test_no_keyway_skips_checks(self, registry):
        tmpl = registry.get("shaft")
        params = tmpl.apply_defaults({
            "diameter": 10, "has_keyway": False, "keyway_width": 20,
        })
        errors, _ = check_template_constraints(tmpl, params)
        assert not errors

    def test_valid_shaft_passes(self, registry):
        tmpl = registry.get("shaft")
        params = tmpl.apply_defaults({})
        errors, _ = check_template_constraints(tmpl, params)
        assert not errors


class TestPistonConstraints:
    def test_pin_bore_too_large_errors(self, registry):
        tmpl = registry.get("piston")
        params = tmpl.apply_defaults({"bore_diam": 80, "pin_bore_diam": 60})
        errors, _ = check_template_constraints(tmpl, params)
        assert errors
        assert "pin" in errors[0].lower()

    def test_valid_piston_passes(self, registry):
        tmpl = registry.get("piston")
        params = tmpl.apply_defaults({})
        errors, _ = check_template_constraints(tmpl, params)
        assert not errors


class TestConnectingRodConstraints:
    def test_bore_too_large_for_end_errors(self, registry):
        tmpl = registry.get("connecting_rod")
        params = tmpl.apply_defaults({"big_end_bore": 50, "big_end_width": 55})
        errors, _ = check_template_constraints(tmpl, params)
        assert any("big end" in e.lower() for e in errors)

    def test_length_too_short_errors(self, registry):
        tmpl = registry.get("connecting_rod")
        params = tmpl.apply_defaults({
            "length": 20, "big_end_width": 55, "small_end_width": 30,
        })
        errors, _ = check_template_constraints(tmpl, params)
        assert any("center" in e.lower() or "short" in e.lower() for e in errors)

    def test_valid_conrod_passes(self, registry):
        tmpl = registry.get("connecting_rod")
        params = tmpl.apply_defaults({})
        errors, _ = check_template_constraints(tmpl, params)
        assert not errors


class TestCylinderBlockConstraints:
    def test_bore_spacing_too_tight_errors(self, registry):
        tmpl = registry.get("cylinder_block")
        params = tmpl.apply_defaults({
            "bore_diam": 80, "bore_spacing": 82, "wall_thickness": 8,
        })
        errors, _ = check_template_constraints(tmpl, params)
        assert any("spacing" in e.lower() for e in errors)

    def test_block_too_short_errors(self, registry):
        tmpl = registry.get("cylinder_block")
        params = tmpl.apply_defaults({
            "bore_diam": 80, "bore_count": 4, "bore_spacing": 90,
            "block_length": 200, "wall_thickness": 8,
        })
        errors, _ = check_template_constraints(tmpl, params)
        assert any("length" in e.lower() for e in errors)

    def test_valid_block_passes(self, registry):
        tmpl = registry.get("cylinder_block")
        params = tmpl.apply_defaults({})
        errors, _ = check_template_constraints(tmpl, params)
        assert not errors


class TestCylinderHeadConstraints:
    def test_valve_bore_too_large_errors(self, registry):
        tmpl = registry.get("cylinder_head")
        params = tmpl.apply_defaults({"bore_diam": 80, "valve_bore_diam": 50})
        errors, _ = check_template_constraints(tmpl, params)
        assert any("valve" in e.lower() for e in errors)

    def test_bore_wider_than_head_errors(self, registry):
        tmpl = registry.get("cylinder_head")
        params = tmpl.apply_defaults({"bore_diam": 150, "width": 120})
        errors, _ = check_template_constraints(tmpl, params)
        assert any("bore" in e.lower() and "width" in e.lower() for e in errors)

    def test_valid_head_passes(self, registry):
        tmpl = registry.get("cylinder_head")
        params = tmpl.apply_defaults({})
        errors, _ = check_template_constraints(tmpl, params)
        assert not errors


# ── Engine template linked dimensions ──────────────────────────────


class TestEngineLinkedDimensions:
    def test_valve_head_diam_rederives_stem(self, registry):
        tmpl = registry.get("valve")
        params = tmpl.apply_defaults({"head_diam": 40})
        params, messages = harmonize_linked_params(tmpl, params, user_explicit={"head_diam"})
        assert params["stem_diam"] == 8.0  # 40 * 0.2
        assert params["seat_width"] == 2.0  # 40 * 0.05
        assert any("Re-derived" in m for m in messages)

    def test_valve_explicit_stem_preserved(self, registry):
        tmpl = registry.get("valve")
        params = tmpl.apply_defaults({"head_diam": 40, "stem_diam": 10})
        params, _ = harmonize_linked_params(
            tmpl, params, user_explicit={"head_diam", "stem_diam"},
        )
        assert params["stem_diam"] == 10

    def test_shaft_keyway_rederives_from_din(self, registry):
        tmpl = registry.get("shaft")
        params = tmpl.apply_defaults({"diameter": 25, "has_keyway": True})
        params, messages = harmonize_linked_params(tmpl, params, user_explicit={"diameter", "has_keyway"})
        assert params["keyway_width"] == 8.0  # DIN 6885 for 25mm
        assert any("DIN 6885" in m for m in messages)

    def test_shaft_no_keyway_skips_harmonize(self, registry):
        tmpl = registry.get("shaft")
        params = tmpl.apply_defaults({"diameter": 25, "has_keyway": False})
        params, messages = harmonize_linked_params(tmpl, params, user_explicit={"diameter"})
        assert not any("keyway" in m.lower() for m in messages)

    def test_piston_bore_rederives_pin(self, registry):
        tmpl = registry.get("piston")
        params = tmpl.apply_defaults({"bore_diam": 100})
        params, messages = harmonize_linked_params(tmpl, params, user_explicit={"bore_diam"})
        assert params["pin_bore_diam"] == 25.0  # 100 * 0.25
        assert params["wall_thickness"] == 6.0  # 100 * 0.06
        assert any("Re-derived" in m for m in messages)

    def test_conrod_bore_rederives_widths(self, registry):
        tmpl = registry.get("connecting_rod")
        params = tmpl.apply_defaults({"big_end_bore": 50})
        params, messages = harmonize_linked_params(tmpl, params, user_explicit={"big_end_bore"})
        assert params["big_end_width"] == 70.0  # 50 * 1.4
        assert params["thickness"] == 22.5  # 50 * 0.45
        assert any("Re-derived" in m for m in messages)

    def test_block_bore_rederives_spacing(self, registry):
        tmpl = registry.get("cylinder_block")
        params = tmpl.apply_defaults({"bore_diam": 86})
        params, messages = harmonize_linked_params(tmpl, params, user_explicit={"bore_diam"})
        assert params["bore_spacing"] == 96.3  # 86 * 1.12, rounded
        assert any("Re-derived" in m for m in messages)

    def test_head_bore_rederives_valve_bore(self, registry):
        tmpl = registry.get("cylinder_head")
        params = tmpl.apply_defaults({"bore_diam": 86})
        params, messages = harmonize_linked_params(tmpl, params, user_explicit={"bore_diam"})
        assert params["valve_bore_diam"] == 8.6  # 86 * 0.1
        assert any("Re-derived" in m for m in messages)


# ── Tier 3 constraints ──────────────────────────────────────────────


class TestSpringConstraints:
    def test_defaults_pass(self, registry):
        tmpl = registry.get("spring_compression")
        params = tmpl.apply_defaults({})
        errors, warnings = check_template_constraints(tmpl, params)
        assert not errors

    def test_wire_too_thick_for_coil(self, registry):
        tmpl = registry.get("spring_compression")
        params = tmpl.apply_defaults({"wire_diam": 12.0, "coil_diam": 20.0})
        errors, _ = check_template_constraints(tmpl, params)
        assert errors

    def test_free_length_too_short(self, registry):
        tmpl = registry.get("spring_compression")
        params = tmpl.apply_defaults({"free_length": 5.0, "active_coils": 8, "wire_diam": 2.0})
        errors, _ = check_template_constraints(tmpl, params)
        assert errors


class TestGasketConstraints:
    def test_defaults_pass(self, registry):
        tmpl = registry.get("gasket")
        params = tmpl.apply_defaults({})
        errors, warnings = check_template_constraints(tmpl, params)
        assert not errors

    def test_outer_smaller_than_inner(self, registry):
        tmpl = registry.get("gasket")
        params = tmpl.apply_defaults({"inner_diam": 100.0, "outer_diam": 80.0})
        errors, _ = check_template_constraints(tmpl, params)
        assert errors

    def test_bolt_circle_too_close_to_bore(self, registry):
        tmpl = registry.get("gasket")
        params = tmpl.apply_defaults({"inner_diam": 80.0, "bolt_circle_diam": 85.0, "bolt_hole_diam": 10.0})
        errors, _ = check_template_constraints(tmpl, params)
        assert errors


class TestBearingShellConstraints:
    def test_defaults_pass(self, registry):
        tmpl = registry.get("bearing_shell")
        params = tmpl.apply_defaults({})
        errors, warnings = check_template_constraints(tmpl, params)
        assert not errors

    def test_outer_smaller_than_bore(self, registry):
        tmpl = registry.get("bearing_shell")
        params = tmpl.apply_defaults({"bore": 60.0, "outer_diam": 55.0})
        errors, _ = check_template_constraints(tmpl, params)
        assert errors


class TestPulleyConstraints:
    def test_defaults_pass(self, registry):
        tmpl = registry.get("pulley")
        params = tmpl.apply_defaults({})
        errors, warnings = check_template_constraints(tmpl, params)
        assert not errors

    def test_bore_exceeds_hub(self, registry):
        tmpl = registry.get("pulley")
        params = tmpl.apply_defaults({"bore_diam": 50.0, "hub_diam": 40.0})
        errors, _ = check_template_constraints(tmpl, params)
        assert errors

    def test_hub_exceeds_pitch(self, registry):
        tmpl = registry.get("pulley")
        params = tmpl.apply_defaults({"hub_diam": 90.0, "pitch_diam": 80.0})
        errors, _ = check_template_constraints(tmpl, params)
        assert errors


class TestFlywheelConstraints:
    def test_defaults_pass(self, registry):
        tmpl = registry.get("flywheel")
        params = tmpl.apply_defaults({})
        errors, warnings = check_template_constraints(tmpl, params)
        assert not errors

    def test_bore_too_large(self, registry):
        tmpl = registry.get("flywheel")
        params = tmpl.apply_defaults({"bore_diam": 120.0, "outer_diam": 200.0})
        errors, _ = check_template_constraints(tmpl, params)
        assert errors

    def test_bolt_circle_past_edge(self, registry):
        tmpl = registry.get("flywheel")
        params = tmpl.apply_defaults({"bolt_circle_diam": 198.0, "bolt_hole_diam": 10.0, "outer_diam": 200.0})
        errors, _ = check_template_constraints(tmpl, params)
        assert errors


class TestOilPanConstraints:
    def test_defaults_pass(self, registry):
        tmpl = registry.get("oil_pan")
        params = tmpl.apply_defaults({})
        errors, warnings = check_template_constraints(tmpl, params)
        assert not errors

    def test_wall_too_thick(self, registry):
        tmpl = registry.get("oil_pan")
        params = tmpl.apply_defaults({"wall_thickness": 50.0, "depth": 80.0})
        errors, _ = check_template_constraints(tmpl, params)
        assert errors


class TestTier3Harmonization:
    def test_spring_coil_rederives_wire(self, registry):
        tmpl = registry.get("spring_compression")
        params = tmpl.apply_defaults({"coil_diam": 30.0})
        params, messages = harmonize_linked_params(tmpl, params, user_explicit={"coil_diam"})
        assert params["wire_diam"] == 3.0  # 30 * 0.1
        assert any("Re-derived" in m for m in messages)

    def test_gasket_inner_rederives_outer(self, registry):
        tmpl = registry.get("gasket")
        params = tmpl.apply_defaults({"inner_diam": 100.0})
        params, messages = harmonize_linked_params(tmpl, params, user_explicit={"inner_diam"})
        assert params["outer_diam"] == 150.0  # 100 * 1.5
        assert params["bolt_circle_diam"] == 125.0  # 100 * 1.25

    def test_bearing_bore_rederives_outer(self, registry):
        tmpl = registry.get("bearing_shell")
        params = tmpl.apply_defaults({"bore": 40.0})
        params, messages = harmonize_linked_params(tmpl, params, user_explicit={"bore"})
        assert params["wall_thickness"] == 2.4  # 40 * 0.06
        assert params["outer_diam"] == 44.8  # 40 + 2*2.4

    def test_pulley_pitch_rederives_hub(self, registry):
        tmpl = registry.get("pulley")
        params = tmpl.apply_defaults({"pitch_diam": 100.0})
        params, messages = harmonize_linked_params(tmpl, params, user_explicit={"pitch_diam"})
        assert params["hub_diam"] == 50.0  # 100 * 0.5
        assert params["groove_depth"] == 10.0  # 100 * 0.1

    def test_flywheel_outer_rederives_bore(self, registry):
        tmpl = registry.get("flywheel")
        params = tmpl.apply_defaults({"outer_diam": 300.0})
        params, messages = harmonize_linked_params(tmpl, params, user_explicit={"outer_diam"})
        assert params["bore_diam"] == 37.5  # 300 * 0.125
        assert params["bolt_circle_diam"] == 225.0  # 300 * 0.75

    def test_oil_pan_rederives_flange(self, registry):
        tmpl = registry.get("oil_pan")
        params = tmpl.apply_defaults({"length": 500.0, "width": 200.0})
        params, messages = harmonize_linked_params(tmpl, params, user_explicit={"length", "width"})
        expected = round(2 * (500 + 200) * 0.014, 1)
        assert params["flange_width"] == max(expected, 10.0)


class TestTier3Warnings:
    def test_spring_index_too_low(self, registry):
        tmpl = registry.get("spring_compression")
        params = tmpl.apply_defaults({"coil_diam": 10.0, "wire_diam": 5.0})
        warnings = check_engineering_warnings(tmpl, params)
        assert any("index" in w.lower() for w in warnings)

    def test_spring_index_too_high(self, registry):
        tmpl = registry.get("spring_compression")
        params = tmpl.apply_defaults({"coil_diam": 100.0, "wire_diam": 2.0})
        warnings = check_engineering_warnings(tmpl, params)
        assert any("index" in w.lower() for w in warnings)

    def test_bearing_narrow_width(self, registry):
        tmpl = registry.get("bearing_shell")
        params = tmpl.apply_defaults({"bore": 100.0, "width": 10.0})
        warnings = check_engineering_warnings(tmpl, params)
        assert any("narrow" in w.lower() for w in warnings)
