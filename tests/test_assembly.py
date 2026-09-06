"""Assembly engine tests — connectors, solver, renderer, builder, and engine proving ground."""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scadgen.assembly.assembly import Assembly, Connection
from scadgen.assembly.builder import AssemblyBuilder
from scadgen.assembly.connectors import (
    compute_connector_direction,
    compute_connector_position,
)
from scadgen.assembly.part import ConnectorInstance, Part, Transform
from scadgen.assembly.renderer import render_assembly
from scadgen.assembly.solver import (
    compute_world_connectors,
    solve_assembly,
    _euler_to_matrix,
    _mat_apply,
    _rotation_between,
    _euler_from_matrix,
)
from scadgen.core.engine import SCADEngine
from scadgen.types import ConnectorDef, Template


TEMPLATES_DIR = str(Path(__file__).resolve().parent.parent / "scadgen" / "templates")


def _engine():
    return SCADEngine(template_dirs=[TEMPLATES_DIR])


def _simple_template(tid="t1", module="mod1", connectors=None):
    return Template(
        template_id=tid,
        file_path="test.scad",
        module_name=module,
        description="test",
        category="test",
        connectors=connectors or [],
        source_code=f"module {module}() {{ cube(10); }}",
    )


# ── Connector expression tests ─────────────────────────────────────────


class TestConnectorExpressions:
    def test_numeric_origin(self):
        c = ConnectorDef(name="a", type="planar", origin=[1.0, 2.0, 3.0])
        assert compute_connector_position(c, {}) == (1.0, 2.0, 3.0)

    def test_string_expression_origin(self):
        c = ConnectorDef(name="a", type="planar", origin=[0, 0, "height"])
        assert compute_connector_position(c, {"height": 200}) == (0, 0, 200)

    def test_mixed_origin(self):
        c = ConnectorDef(
            name="a", type="planar",
            origin=["length / 2", "width / 2", "height"],
        )
        pos = compute_connector_position(c, {"length": 400, "width": 120, "height": 200})
        assert pos == (200.0, 60.0, 200.0)

    def test_arithmetic_expression(self):
        c = ConnectorDef(name="a", type="axial", origin=[0, 0, "thickness / 2"])
        assert compute_connector_position(c, {"thickness": 18}) == (0, 0, 9.0)

    def test_complex_expression(self):
        c = ConnectorDef(
            name="a", type="axial",
            origin=["(block_length - bore_spacing * (bore_count - 1)) / 2", 0, 0],
        )
        pos = compute_connector_position(
            c, {"block_length": 400, "bore_spacing": 90, "bore_count": 4},
        )
        assert abs(pos[0] - 65.0) < 0.01

    def test_negative_expression(self):
        c = ConnectorDef(name="a", type="axial", origin=[0, 0, "-shaft_len"])
        assert compute_connector_position(c, {"shaft_len": 40}) == (0, 0, -40.0)

    def test_direction_expressions(self):
        c = ConnectorDef(name="a", type="axial", direction=[0, 0, 1])
        assert compute_connector_direction(c, {}) == (0, 0, 1)


# ── Solver math tests ──────────────────────────────────────────────────


class TestSolverMath:
    def test_rotation_identity(self):
        m = _rotation_between((0, 0, 1), (0, 0, 1))
        assert m[0][0] == 1 and m[1][1] == 1 and m[2][2] == 1

    def test_rotation_180(self):
        m = _rotation_between((0, 0, 1), (0, 0, -1))
        v = _mat_apply(m, (0, 0, 1))
        assert abs(v[2] - (-1)) < 1e-6

    def test_rotation_90(self):
        m = _rotation_between((0, 0, 1), (1, 0, 0))
        v = _mat_apply(m, (0, 0, 1))
        assert abs(v[0] - 1) < 1e-6 and abs(v[2]) < 1e-6

    def test_euler_roundtrip(self):
        euler = (30.0, 45.0, 60.0)
        m = _euler_to_matrix(euler)
        recovered = _euler_from_matrix(m)
        for a, b in zip(euler, recovered):
            assert abs(a - b) < 1e-6


# ── Solver integration tests ───────────────────────────────────────────


class TestSolver:
    def _make_conn(self, name, origin, direction):
        return ConnectorDef(name=name, type="planar", origin=origin, direction=direction)

    def test_two_part_mate(self):
        c_top = self._make_conn("top", [0, 0, "h"], [0, 0, 1])
        c_bot = self._make_conn("bottom", [0, 0, 0], [0, 0, -1])

        t1 = _simple_template("t1", "m1", [c_top])
        t2 = _simple_template("t2", "m2", [c_bot])

        asm = Assembly(assembly_id="test")
        asm.add_part(Part("a", t1, {"h": 100}))
        asm.add_part(Part("b", t2, {"h": 50}))
        asm.connect("a", "top", "b", "bottom", type="mate")

        transforms = solve_assembly(asm, "a")
        assert transforms["a"].translation == (0, 0, 0)
        assert transforms["b"].translation == (0, 0, 100)

    def test_two_part_coaxial(self):
        c_end = self._make_conn("end_b", [0, 0, "length"], [0, 0, 1])
        c_start = self._make_conn("end_a", [0, 0, 0], [0, 0, 1])

        t1 = _simple_template("t1", "m1", [c_end])
        t2 = _simple_template("t2", "m2", [c_start])

        asm = Assembly(assembly_id="test")
        asm.add_part(Part("shaft1", t1, {"length": 200}))
        asm.add_part(Part("shaft2", t2, {"length": 150}))
        asm.connect("shaft1", "end_b", "shaft2", "end_a", type="coaxial")

        transforms = solve_assembly(asm)
        tf2 = transforms["shaft2"]
        assert abs(tf2.translation[2] - 200) < 1e-6

    def test_three_part_chain(self):
        c_top = self._make_conn("top", [0, 0, "h"], [0, 0, 1])
        c_bot = self._make_conn("bot", [0, 0, 0], [0, 0, -1])

        t = _simple_template("t", "m", [c_top, c_bot])

        asm = Assembly(assembly_id="test")
        asm.add_part(Part("a", t, {"h": 10}))
        asm.add_part(Part("b", t, {"h": 20}))
        asm.add_part(Part("c", t, {"h": 30}))
        asm.connect("a", "top", "b", "bot", type="mate")
        asm.connect("b", "top", "c", "bot", type="mate")

        transforms = solve_assembly(asm, "a")
        assert abs(transforms["b"].translation[2] - 10) < 1e-6
        assert abs(transforms["c"].translation[2] - 30) < 1e-6

    def test_offset(self):
        c_top = self._make_conn("top", [0, 0, "h"], [0, 0, 1])
        c_bot = self._make_conn("bot", [0, 0, 0], [0, 0, -1])

        t = _simple_template("t", "m", [c_top, c_bot])

        asm = Assembly(assembly_id="test")
        asm.add_part(Part("a", t, {"h": 10}))
        asm.add_part(Part("b", t, {"h": 20}))
        asm.connect("a", "top", "b", "bot", type="mate", offset=5.0)

        transforms = solve_assembly(asm, "a")
        assert abs(transforms["b"].translation[2] - 15) < 1e-6

    def test_disconnected_raises(self):
        t = _simple_template("t", "m", [])
        asm = Assembly(assembly_id="test")
        asm.add_part(Part("a", t, {}))
        asm.add_part(Part("b", t, {}))

        try:
            solve_assembly(asm)
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "Disconnected" in str(e)

    def test_missing_connector_raises(self):
        c = self._make_conn("top", [0, 0, 0], [0, 0, 1])
        t = _simple_template("t", "m", [c])

        asm = Assembly(assembly_id="test")
        asm.add_part(Part("a", t, {}))
        asm.add_part(Part("b", t, {}))
        asm.connect("a", "top", "b", "nonexistent", type="mate")

        try:
            solve_assembly(asm)
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "nonexistent" in str(e)

    def test_world_connectors(self):
        c = self._make_conn("top", [0, 0, "h"], [0, 0, 1])
        t = _simple_template("t", "m", [c])
        p = Part("a", t, {"h": 50})
        tf = Transform(translation=(10, 20, 30))
        instances = compute_world_connectors(p, tf)
        assert "top" in instances
        wo = instances["top"].world_origin
        assert abs(wo[0] - 10) < 1e-6
        assert abs(wo[1] - 20) < 1e-6
        assert abs(wo[2] - 80) < 1e-6


# ── Renderer tests ──────────────────────────────────────────────────────


class TestRenderer:
    def test_single_part(self):
        t = _simple_template("cube_t", "cube_mod", [])
        asm = Assembly(assembly_id="single")
        asm.add_part(Part("p1", t, {}))
        transforms = {"p1": Transform.identity()}
        scad = render_assembly(asm, transforms)
        assert "Assembly: single" in scad
        assert "cube_mod" in scad
        assert "translate" in scad

    def test_unique_modules(self):
        t = _simple_template("shared", "shared_mod", [])
        asm = Assembly(assembly_id="multi")
        asm.add_part(Part("a", t, {}))
        asm.add_part(Part("b", t, {}))
        transforms = {
            "a": Transform.identity(),
            "b": Transform(translation=(10, 0, 0)),
        }
        scad = render_assembly(asm, transforms)
        assert scad.count("module shared_mod") == 1

    def test_color_assignment(self):
        t = _simple_template("t", "m", [])
        asm = Assembly(assembly_id="colored")
        asm.add_part(Part("p1", t, {}))
        transforms = {"p1": Transform.identity()}
        scad = render_assembly(asm, transforms, colors={"p1": "Red"})
        assert '"Red"' in scad

    def test_bom_present(self):
        t = _simple_template("t", "m", [])
        asm = Assembly(assembly_id="bom")
        asm.add_part(Part("widget", t, {}))
        transforms = {"widget": Transform.identity()}
        scad = render_assembly(asm, transforms)
        assert "Bill of Materials" in scad
        assert "widget" in scad

    def test_rotation_omitted_when_zero(self):
        t = _simple_template("t", "m", [])
        asm = Assembly(assembly_id="norot")
        asm.add_part(Part("p", t, {}))
        transforms = {"p": Transform.identity()}
        scad = render_assembly(asm, transforms)
        assert "rotate" not in scad


# ── Builder tests ───────────────────────────────────────────────────────


class TestBuilder:
    def test_add_and_build(self):
        engine = _engine()
        b = AssemblyBuilder(engine)
        b.add_part("block", "cylinder_block")
        b.add_part("gasket", "gasket", {
            "inner_diam": 86, "outer_diam": 120, "bolt_hole_count": 0,
        })
        b.connect("block", "deck_face", "gasket", "bottom_face")
        asm = b.build()
        assert "block" in asm.parts
        assert "gasket" in asm.parts
        assert asm.parts["block"].transform.translation == (0, 0, 0)
        gasket_z = asm.parts["gasket"].transform.translation[2]
        block_height = asm.parts["block"].parameters["block_height"]
        assert abs(gasket_z - block_height) < 1e-3

    def test_duplicate_part_raises(self):
        engine = _engine()
        b = AssemblyBuilder(engine)
        b.add_part("a", "cylinder_block")
        try:
            b.add_part("a", "cylinder_block")
            assert False, "Should raise"
        except ValueError:
            pass

    def test_unknown_part_connect_raises(self):
        engine = _engine()
        b = AssemblyBuilder(engine)
        b.add_part("a", "cylinder_block")
        try:
            b.connect("a", "deck_face", "b", "bottom_face")
            assert False, "Should raise"
        except ValueError:
            pass

    def test_render_output(self):
        engine = _engine()
        b = AssemblyBuilder(engine)
        b.add_part("block", "cylinder_block")
        b.add_part("gasket", "gasket", {
            "inner_diam": 86, "outer_diam": 120, "bolt_hole_count": 0,
        })
        b.connect("block", "deck_face", "gasket", "bottom_face")
        scad = b.render()
        assert "cylinder_block" in scad
        assert "gasket" in scad
        assert "translate" in scad

    def test_set_root(self):
        engine = _engine()
        b = AssemblyBuilder(engine)
        b.add_part("gasket", "gasket", {
            "inner_diam": 86, "outer_diam": 120, "bolt_hole_count": 0,
        })
        b.add_part("block", "cylinder_block")
        b.connect("block", "deck_face", "gasket", "bottom_face")
        b.set_root("block")
        asm = b.build()
        assert asm.parts["block"].transform.translation == (0, 0, 0)


# ── Engine Assembly Proving Ground ──────────────────────────────────────


class TestEngineAssembly:
    def test_block_gasket_head_stack(self):
        """Planar mate stack: block → gasket → head."""
        engine = _engine()
        b = AssemblyBuilder(engine)

        b.add_part("block", "cylinder_block", {
            "bore_diam": 86, "bore_count": 4, "bore_spacing": 96,
            "block_length": 400, "block_width": 120, "block_height": 200,
            "wall_thickness": 4,
        })
        b.add_part("gasket", "gasket", {
            "inner_diam": 86, "outer_diam": 120, "thickness": 1.5,
            "bolt_hole_count": 0,
        })
        b.add_part("head", "cylinder_head", {
            "bore_diam": 86, "bore_count": 4, "bore_spacing": 96,
            "length": 400, "width": 120, "height": 50,
        })

        b.connect("block", "deck_face", "gasket", "bottom_face")
        b.connect("gasket", "top_face", "head", "deck_face")

        asm = b.build()

        block_z = asm.parts["block"].transform.translation[2]
        gasket_z = asm.parts["gasket"].transform.translation[2]
        head_z = asm.parts["head"].transform.translation[2]

        assert abs(block_z - 0) < 1e-3
        assert abs(gasket_z - 200) < 1e-3
        assert abs(head_z - 201.5) < 1e-3

    def test_shaft_with_flywheel(self):
        """Coaxial connection: shaft end_b → flywheel bore_axis."""
        engine = _engine()
        b = AssemblyBuilder(engine)

        b.add_part("crankshaft", "shaft", {"diameter": 50, "length": 500})
        b.add_part("flywheel", "flywheel", {
            "outer_diam": 300, "bore_diam": 50, "thickness": 25,
        })

        b.connect("crankshaft", "end_b", "flywheel", "bore_axis", type="coaxial")

        asm = b.build()
        fw_z = asm.parts["flywheel"].transform.translation[2]
        assert abs(fw_z - (500 - 12.5)) < 1e-3

    def test_block_with_oil_pan(self):
        """Oil pan mates to block sump face."""
        engine = _engine()
        b = AssemblyBuilder(engine)

        b.add_part("block", "cylinder_block", {
            "bore_diam": 86, "bore_count": 4, "bore_spacing": 96,
            "block_length": 400, "block_width": 120, "block_height": 200,
            "wall_thickness": 4,
        })
        b.add_part("pan", "oil_pan", {
            "length": 380, "width": 100, "depth": 80,
            "flange_thickness": 8,
        })

        b.connect("block", "sump_face", "pan", "flange_face")

        asm = b.build()
        pan_z = asm.parts["pan"].transform.translation[2]
        assert abs(pan_z - (-8)) < 1e-3

    def test_full_engine_assembly(self):
        """Proving ground: 10-part engine assembly renders without error."""
        engine = _engine()
        b = AssemblyBuilder(engine)

        b.add_part("block", "cylinder_block", {
            "bore_diam": 86, "bore_count": 4, "bore_spacing": 96,
            "block_length": 400, "block_width": 120, "block_height": 200,
            "wall_thickness": 4,
        })
        b.add_part("gasket", "gasket", {
            "inner_diam": 86, "outer_diam": 120, "thickness": 1.5,
            "bolt_hole_count": 0,
        })
        b.add_part("head", "cylinder_head", {
            "bore_diam": 86, "bore_count": 4, "bore_spacing": 96,
            "length": 400, "width": 120, "height": 50,
        })
        b.add_part("crankshaft", "shaft", {"diameter": 50, "length": 500})
        b.add_part("flywheel", "flywheel", {
            "outer_diam": 300, "bore_diam": 50, "thickness": 25,
        })
        b.add_part("pan", "oil_pan", {
            "length": 380, "width": 100, "depth": 80,
            "flange_thickness": 8,
        })
        for i in range(1, 5):
            b.add_part(f"piston_{i}", "piston", {
                "bore_diam": 86, "height": 60, "pin_bore_height": 20,
            })

        b.connect("block", "deck_face", "gasket", "bottom_face")
        b.connect("gasket", "top_face", "head", "deck_face")
        b.connect("block", "sump_face", "pan", "flange_face")
        b.connect("crankshaft", "end_b", "flywheel", "bore_axis", type="coaxial")
        b.connect("block", "crank_axis", "crankshaft", "end_a", type="coaxial")
        for i in range(1, 5):
            b.connect(
                "block", f"bore_{i}_axis",
                f"piston_{i}", "crown_face",
                type="coaxial", offset=-50,
            )

        b.set_root("block")

        scad = b.render()

        assert len(scad) > 500
        assert "cylinder_block" in scad
        assert "gasket" in scad
        assert "cylinder_head" in scad
        assert "shaft" in scad
        assert "flywheel" in scad
        assert "oil_pan" in scad
        assert "piston" in scad

        assert scad.count("translate") >= 10
        assert "Assembly" in scad
        assert "Bill of Materials" in scad

    def test_bolt_washer_stack(self):
        """Fastener assembly: washer on bolt head."""
        engine = _engine()
        b = AssemblyBuilder(engine)

        b.add_part("bolt", "hex_bolt", {"shaft_diam": 8, "shaft_len": 40})
        b.add_part("washer", "washer", {
            "inner_diam": 9, "outer_diam": 16, "thickness": 1.5,
        })

        b.connect("bolt", "head_top", "washer", "bottom_face")

        asm = b.build()
        bolt_head_h = asm.parts["bolt"].parameters["head_height"]
        washer_z = asm.parts["washer"].transform.translation[2]
        assert abs(washer_z - bolt_head_h) < 1e-3


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
