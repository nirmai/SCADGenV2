// SCADGEN_META_BEGIN
// schema_version: 1
// template_id: gasket
// module_name: gasket
// description: Annular flat gasket with bolt holes
// category: sealing/gasket
// tags: [gasket, seal, flange, ring, sealing]
// aliases: [gasket, head gasket, flange gasket, seal ring]
// keywords: [gasket, seal, ring, flange, head, bolt, hole, annular, flat, compressed, fiber, metal]
// length_param: thickness
// params:
//   - name: inner_diam
//     type: float
//     default: 80.0
//     min: 5.0
//     max: 2000.0
//     unit: mm
//     description: Inner bore diameter
//   - name: outer_diam
//     type: float
//     default: 120.0
//     min: 10.0
//     max: 3000.0
//     unit: mm
//     description: Outer diameter
//   - name: thickness
//     type: float
//     default: 1.5
//     min: 0.1
//     max: 10.0
//     unit: mm
//     description: Gasket thickness
//   - name: bolt_hole_diam
//     type: float
//     default: 10.0
//     min: 2.0
//     max: 100.0
//     unit: mm
//     description: Bolt hole diameter
//   - name: bolt_hole_count
//     type: int
//     default: 8
//     min: 0
//     max: 48
//     unit: count
//     description: Number of bolt holes
//   - name: bolt_circle_diam
//     type: float
//     default: 100.0
//     min: 10.0
//     max: 3000.0
//     unit: mm
//     description: Bolt circle (PCD) diameter
//   - name: fn
//     type: int
//     default: 96
//     min: 16
//     max: 512
//     unit: count
//     description: Circle resolution
// connectors:
//   - name: top_face
//     type: planar
//     origin: [0, 0, "thickness"]
//     direction: [0, 0, 1]
//   - name: bottom_face
//     type: planar
//     origin: [0, 0, 0]
//     direction: [0, 0, -1]
// constraints:
//   - check: "outer_diam > inner_diam"
//     message: "Outer diameter ({outer_diam}mm) must exceed inner diameter ({inner_diam}mm)"
//     severity: error
//   - check: "bolt_hole_count == 0 or bolt_circle_diam > inner_diam + bolt_hole_diam"
//     message: "Bolt circle ({bolt_circle_diam}mm) too close to inner bore"
//     severity: error
//   - check: "bolt_hole_count == 0 or bolt_circle_diam < outer_diam - bolt_hole_diam"
//     message: "Bolt circle ({bolt_circle_diam}mm) too close to outer edge"
//     severity: error
//   - check: "thickness <= 5"
//     message: "Gasket thickness ({thickness}mm) is unusually large; typical range 0.5-3mm"
//     severity: warning
// SCADGEN_META_END

module gasket(inner_diam=80, outer_diam=120, thickness=1.5,
              bolt_hole_diam=10, bolt_hole_count=8, bolt_circle_diam=100,
              fn=96)
{
    $fn = fn;
    bcd_r = bolt_circle_diam / 2;

    difference() {
        // Main ring
        cylinder(h = thickness, d = outer_diam);

        // Central bore
        translate([0, 0, -0.1])
            cylinder(h = thickness + 0.2, d = inner_diam);

        // Bolt holes
        if (bolt_hole_count > 0) {
            for (i = [0 : bolt_hole_count - 1]) {
                angle = i * 360 / bolt_hole_count;
                translate([bcd_r * cos(angle), bcd_r * sin(angle), -0.1])
                    cylinder(h = thickness + 0.2, d = bolt_hole_diam);
            }
        }
    }
}
