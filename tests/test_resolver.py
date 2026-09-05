"""Tests for the engineering resolver and standards lookup tables."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scadgen.knowledge.resolver import EngineeringResolver
from scadgen.knowledge.standards import (
    ISO_METRIC_THREADS,
    UNC_THREADS,
    ISO_GEAR_MODULES,
    BEARING_SERIES,
    lookup_keyway,
    nearest_gear_module,
    lookup_bearing,
)


def get_resolver():
    return EngineeringResolver()


# --- Standards table tests ---

def test_iso_metric_coverage():
    assert "M3" in ISO_METRIC_THREADS
    assert "M8" in ISO_METRIC_THREADS
    assert "M20" in ISO_METRIC_THREADS
    assert "M64" in ISO_METRIC_THREADS
    m8 = ISO_METRIC_THREADS["M8"]
    assert m8["shaft_diam"] == 8.0
    assert m8["pitch_coarse"] == 1.25
    assert m8["head_flat"] == 13.0


def test_unc_coverage():
    assert "1/4-20" in UNC_THREADS
    assert "#10-24" in UNC_THREADS
    assert "1-8" in UNC_THREADS
    quarter = UNC_THREADS["1/4-20"]
    assert quarter["shaft_diam"] == 6.350


def test_gear_modules():
    assert 1.0 in ISO_GEAR_MODULES
    assert 2.5 in ISO_GEAR_MODULES
    assert 0.3 in ISO_GEAR_MODULES


def test_nearest_gear_module():
    assert nearest_gear_module(2.3) == 2.5
    assert nearest_gear_module(1.0) == 1.0
    assert nearest_gear_module(0.35) == 0.3


def test_bearing_lookup():
    assert lookup_bearing("6000", 10) == (26, 8)
    assert lookup_bearing("6200", 25) == (52, 15)
    assert lookup_bearing("6300", 30) == (72, 19)
    assert lookup_bearing("9999", 10) is None


def test_keyway_lookup():
    dims = lookup_keyway(20.0)
    assert dims is not None
    key_w, key_h, shaft_depth, hub_depth = dims
    assert key_w == 6
    assert key_h == 6
    assert lookup_keyway(3.0) is None


# --- Resolver pattern matching tests ---

def test_resolve_m8_bolt():
    r = get_resolver()
    result = r.resolve("M8 bolt 40mm long")
    assert result.resolved_params["shaft_diam"] == 8.0
    assert result.resolved_params["head_flat"] == 13.0
    assert result.resolved_params["shaft_len"] == 40.0
    assert result.suggested_template == "hex_bolt"
    assert result.confidence > 0.5
    assert any("M8" in s for s in result.standards_matched)


def test_resolve_m8_fine_pitch():
    r = get_resolver()
    result = r.resolve("M8x1.0 bolt 25mm")
    assert result.resolved_params["shaft_diam"] == 8.0
    assert result.resolved_params["pitch"] == 1.0
    assert any("x1.0" in s for s in result.standards_matched)


def test_resolve_m8_nut():
    r = get_resolver()
    result = r.resolve("M8 nut")
    assert result.resolved_params["shaft_diam"] == 8.0
    assert result.suggested_template == "hex_nut"


def test_resolve_unc_thread():
    r = get_resolver()
    result = r.resolve("1/4-20 UNC bolt 30mm")
    assert result.resolved_params["shaft_diam"] == 6.350
    assert any("UNC" in s for s in result.standards_matched)


def test_resolve_bearing():
    r = get_resolver()
    result = r.resolve("bearing 6205")
    assert result.resolved_params["bore_diam"] == 25.0
    assert result.resolved_params["outer_diam"] == 52.0
    assert result.resolved_params["width"] == 15.0


def test_resolve_gear_teeth():
    r = get_resolver()
    result = r.resolve("32 tooth gear module 2")
    assert result.resolved_params["teeth"] == 32
    assert result.resolved_params["modul"] == 2.0
    assert result.suggested_template == "gear_spur"


def test_resolve_fit_keyword():
    r = get_resolver()
    result = r.resolve("press fit bushing for 25mm shaft")
    assert result.resolved_params["fit_class"] == "H7/p6"
    assert any("ISO 286" in s for s in result.standards_matched)


def test_resolve_keyway():
    r = get_resolver()
    result = r.resolve("keyway for 25mm shaft")
    assert result.resolved_params["key_width"] == 8
    assert result.resolved_params["key_height"] == 7


def test_resolve_no_match():
    r = get_resolver()
    result = r.resolve("a simple cube")
    assert result.confidence == 0.0
    assert result.suggested_template is None
    assert not result.standards_matched


def test_resolve_multiple_standards():
    r = get_resolver()
    result = r.resolve("M10 bolt 50mm with H7/p6 press fit")
    assert result.resolved_params["shaft_diam"] == 10.0
    assert "fit_class" in result.resolved_params
    assert len(result.standards_matched) >= 2


if __name__ == "__main__":
    test_iso_metric_coverage()
    test_unc_coverage()
    test_gear_modules()
    test_nearest_gear_module()
    test_bearing_lookup()
    test_keyway_lookup()
    test_resolve_m8_bolt()
    test_resolve_m8_fine_pitch()
    test_resolve_m8_nut()
    test_resolve_unc_thread()
    test_resolve_bearing()
    test_resolve_gear_teeth()
    test_resolve_fit_keyword()
    test_resolve_keyway()
    test_resolve_no_match()
    test_resolve_multiple_standards()
    print("All resolver tests passed!")
