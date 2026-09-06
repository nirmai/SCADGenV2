// SCADGEN_META_BEGIN
// schema_version: 1
// template_id: lamp_shade
// module_name: lamp_shade
// description: Truncated cone lamp shade with rolled rim and socket collar
// category: lamp
// tags: [lamp, shade, lampshade, desk lamp, cone]
// aliases: [lamp shade, lampshade, shade]
// keywords: [lamp, shade, cone, bell, light, desk, reflector, hood]
// length_param: height
// params:
//   - name: top_diam
//     type: float
//     default: 52.0
//     min: 15.0
//     max: 120.0
//     unit: mm
//     description: Narrow top opening diameter
//   - name: bottom_diam
//     type: float
//     default: 115.0
//     min: 40.0
//     max: 250.0
//     unit: mm
//     description: Wide bottom opening diameter
//   - name: height
//     type: float
//     default: 85.0
//     min: 20.0
//     max: 200.0
//     unit: mm
//     description: Shade height (cone section)
//   - name: thickness
//     type: float
//     default: 1.5
//     min: 0.5
//     max: 5.0
//     unit: mm
//     description: Shade wall thickness
//   - name: collar_height
//     type: float
//     default: 10.0
//     min: 3.0
//     max: 30.0
//     unit: mm
//     description: Top collar/socket height
//   - name: collar_diam
//     type: float
//     default: 22.0
//     min: 8.0
//     max: 50.0
//     unit: mm
//     description: Top collar outer diameter
//   - name: rim_height
//     type: float
//     default: 3.0
//     min: 1.0
//     max: 10.0
//     unit: mm
//     description: Bottom rim roll thickness
//   - name: fn
//     type: int
//     default: 128
//     min: 32
//     max: 512
//     unit: count
//     description: Circle resolution
// connectors:
//   - name: socket
//     type: axial
//     origin: [0, 0, "height + collar_height"]
//     direction: [0, 0, 1]
//     diameter_ref: collar_diam
// constraints:
//   - check: "bottom_diam > top_diam"
//     message: "Bottom diameter ({bottom_diam}mm) must exceed top diameter ({top_diam}mm)"
//     severity: error
//   - check: "collar_diam <= top_diam"
//     message: "Collar diameter ({collar_diam}mm) exceeds top opening ({top_diam}mm)"
//     severity: error
// SCADGEN_META_END

module lamp_shade(top_diam=52, bottom_diam=115, height=85,
                  thickness=1.5, collar_height=10, collar_diam=22,
                  rim_height=3, fn=128)
{
    $fn = fn;
    t = thickness;

    difference() {
        union() {
            cylinder(h = height, d1 = bottom_diam, d2 = top_diam);

            // Bottom rim roll (thickened edge ring)
            rotate_extrude()
                translate([bottom_diam / 2 - rim_height / 2, rim_height / 2, 0])
                    circle(d = rim_height);
        }

        // Inner hollow
        translate([0, 0, t])
            cylinder(h = height, d1 = bottom_diam - 2 * t, d2 = top_diam - 2 * t);
    }

    // Top collar / socket mount
    translate([0, 0, height]) {
        difference() {
            cylinder(h = collar_height, d = collar_diam);
            translate([0, 0, -0.1])
                cylinder(h = collar_height + 0.2, d = collar_diam - 2 * t);
        }

        // Knurled grip ring (decorative)
        translate([0, 0, collar_height * 0.3])
            difference() {
                cylinder(h = collar_height * 0.4, d = collar_diam + 2);
                cylinder(h = collar_height * 0.4, d = collar_diam - 0.1);
                for (i = [0 : 35]) {
                    rotate([0, 0, i * 10])
                        translate([collar_diam / 2 + 0.5, 0, 0])
                            cylinder(h = collar_height, d = 1.5);
                }
            }
    }
}
