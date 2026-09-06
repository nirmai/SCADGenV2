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


from scadgen.core.template_registry import TemplateRegistry

TEMPLATES_DIR = str(Path(__file__).resolve().parent.parent / "scadgen" / "templates")

def get_resolver():
    registry = TemplateRegistry([TEMPLATES_DIR])
    return EngineeringResolver(registry=registry)


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
    result = r.resolve("something with no matching template xyz123")
    assert result.confidence == 0.0
    assert result.suggested_template is None
    assert not result.standards_matched


def test_resolve_cube_inferred():
    r = get_resolver()
    result = r.resolve("a simple cube")
    assert result.suggested_template == "cube"


def test_resolve_multiple_standards():
    r = get_resolver()
    result = r.resolve("M10 bolt 50mm with H7/p6 press fit")
    assert result.resolved_params["shaft_diam"] == 10.0
    assert "fit_class" in result.resolved_params
    assert len(result.standards_matched) >= 2


# --- Engine template inference tests ---


def test_infer_cylinder_block():
    r = get_resolver()
    result = r.resolve("cylinder block 86mm bore")
    assert result.suggested_template == "cylinder_block"
    assert result.resolved_params.get("bore_diam") == 86.0


def test_infer_engine_block():
    r = get_resolver()
    result = r.resolve("engine block")
    assert result.suggested_template == "cylinder_block"


def test_infer_cylinder_head():
    r = get_resolver()
    result = r.resolve("cylinder head 50mm")
    assert result.suggested_template == "cylinder_head"
    assert result.resolved_params.get("height") == 50.0


def test_infer_connecting_rod():
    r = get_resolver()
    result = r.resolve("connecting rod 150mm")
    assert result.suggested_template == "connecting_rod"
    assert result.resolved_params.get("length") == 150.0


def test_infer_conrod():
    r = get_resolver()
    result = r.resolve("conrod 200mm long")
    assert result.suggested_template == "connecting_rod"


def test_infer_piston():
    r = get_resolver()
    result = r.resolve("piston 86mm bore")
    assert result.suggested_template == "piston"
    assert result.resolved_params.get("bore_diam") == 86.0


def test_infer_valve():
    r = get_resolver()
    result = r.resolve("intake valve 100mm stem")
    assert result.suggested_template == "valve"
    assert result.resolved_params.get("stem_len") == 100.0


def test_infer_shaft():
    r = get_resolver()
    result = r.resolve("shaft 200mm long")
    assert result.suggested_template == "shaft"
    assert result.resolved_params.get("length") == 200.0


def test_shaft_not_inferred_with_bolt():
    r = get_resolver()
    result = r.resolve("M8 bolt shaft")
    assert result.suggested_template != "shaft"


# --- Tier 3 data-driven inference tests ---


def test_infer_compression_spring():
    r = get_resolver()
    result = r.resolve("compression spring 50mm")
    assert result.suggested_template == "spring_compression"
    assert result.resolved_params.get("free_length") == 50.0


def test_infer_coil_spring():
    r = get_resolver()
    result = r.resolve("coil spring")
    assert result.suggested_template == "spring_compression"


def test_infer_gasket():
    r = get_resolver()
    result = r.resolve("head gasket 2mm")
    assert result.suggested_template == "gasket"
    assert result.resolved_params.get("thickness") == 2.0


def test_infer_journal_bearing():
    r = get_resolver()
    result = r.resolve("journal bearing 30mm wide")
    assert result.suggested_template == "bearing_shell"
    assert result.resolved_params.get("width") == 30.0


def test_infer_plain_bearing():
    r = get_resolver()
    result = r.resolve("plain bearing")
    assert result.suggested_template == "bearing_shell"


def test_infer_belt_pulley():
    r = get_resolver()
    result = r.resolve("belt pulley 40mm hub")
    assert result.suggested_template == "pulley"
    assert result.resolved_params.get("hub_length") == 40.0


def test_infer_sheave():
    r = get_resolver()
    result = r.resolve("sheave")
    assert result.suggested_template == "pulley"


def test_infer_flywheel():
    r = get_resolver()
    result = r.resolve("flywheel 25mm thick")
    assert result.suggested_template == "flywheel"
    assert result.resolved_params.get("thickness") == 25.0


def test_infer_oil_sump():
    r = get_resolver()
    result = r.resolve("oil sump 100mm")
    assert result.suggested_template == "oil_pan"
    assert result.resolved_params.get("depth") == 100.0


def test_infer_crankcase_pan():
    r = get_resolver()
    result = r.resolve("crankcase pan")
    assert result.suggested_template == "oil_pan"


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
    test_infer_cylinder_block()
    test_infer_engine_block()
    test_infer_cylinder_head()
    test_infer_connecting_rod()
    test_infer_conrod()
    test_infer_piston()
    test_infer_valve()
    test_infer_shaft()
    test_shaft_not_inferred_with_bolt()
    print("All resolver tests passed!")
