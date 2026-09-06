// SCADGEN_META_BEGIN
// schema_version: 1
// template_id: lamp_base
// module_name: lamp_base
// description: Weighted circular lamp base with chamfered top edge
// category: lamp
// tags: [lamp, base, desk lamp, lighting]
// aliases: [lamp base, desk lamp base]
// keywords: [lamp, base, desk, light, stand, puck, weighted]
// length_param: height
// params:
//   - name: diameter
//     type: float
//     default: 130.0
//     min: 50.0
//     max: 300.0
//     unit: mm
//     description: Base outer diameter
//   - name: height
//     type: float
//     default: 18.0
//     min: 8.0
//     max: 50.0
//     unit: mm
//     description: Base height
//   - name: stem_hole_diam
//     type: float
//     default: 12.0
//     min: 5.0
//     max: 30.0
//     unit: mm
//     description: Center hole diameter for stem pass-through
//   - name: chamfer
//     type: float
//     default: 2.0
//     min: 0.5
//     max: 8.0
//     unit: mm
//     description: Top edge chamfer height
//   - name: fn
//     type: int
//     default: 128
//     min: 32
//     max: 512
//     unit: count
//     description: Circle resolution
// connectors:
//   - name: stem_mount
//     type: axial
//     origin: [0, 0, "height"]
//     direction: [0, 0, 1]
//     diameter_ref: stem_hole_diam
//   - name: bottom_face
//     type: planar
//     origin: [0, 0, 0]
//     direction: [0, 0, -1]
// constraints:
//   - check: "stem_hole_diam < diameter * 0.3"
//     message: "Stem hole ({stem_hole_diam}mm) too large for base diameter ({diameter}mm)"
//     severity: error
//   - check: "chamfer < height / 2"
//     message: "Chamfer ({chamfer}mm) exceeds half the base height ({height}mm)"
//     severity: error
// SCADGEN_META_END

module lamp_base(diameter=130, height=18, stem_hole_diam=12, chamfer=2, fn=128)
{
    $fn = fn;

    difference() {
        union() {
            cylinder(h = height - chamfer, d = diameter);
            translate([0, 0, height - chamfer])
                cylinder(h = chamfer, d1 = diameter, d2 = diameter - chamfer * 2);
            cylinder(h = chamfer, d1 = diameter - chamfer * 2, d2 = diameter);
        }

        // Anti-slip rubber ring recess on bottom
        translate([0, 0, -0.1])
            difference() {
                cylinder(h = 1.1, d = diameter - 10);
                cylinder(h = 1.1, d = diameter - 20);
            }
    }

    // Switch detail on side
    translate([diameter / 2 - 1.5, -4, height * 0.3])
        cube([3, 8, 6]);
}
