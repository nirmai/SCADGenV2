// SCADGEN_META_BEGIN
// schema_version: 1
// template_id: oil_pan
// module_name: oil_pan
// description: Rectangular oil pan with flange and drain boss
// category: engine/block
// tags: [oil pan, sump, engine, lubrication, drain]
// aliases: [oil pan, sump, oil sump, crankcase pan]
// keywords: [oil, pan, sump, crankcase, drain, flange, tray, lubrication, engine, reservoir]
// length_param: depth
// params:
//   - name: length
//     type: float
//     default: 400.0
//     min: 50.0
//     max: 2000.0
//     unit: mm
//     description: Pan length (along engine axis)
//   - name: width
//     type: float
//     default: 150.0
//     min: 30.0
//     max: 1000.0
//     unit: mm
//     description: Pan width
//   - name: depth
//     type: float
//     default: 80.0
//     min: 15.0
//     max: 500.0
//     unit: mm
//     description: Pan depth
//   - name: wall_thickness
//     type: float
//     default: 3.0
//     min: 1.0
//     max: 15.0
//     unit: mm
//     description: Wall and floor thickness
//   - name: flange_width
//     type: float
//     default: 15.0
//     min: 5.0
//     max: 50.0
//     unit: mm
//     description: Mounting flange width
//   - name: flange_thickness
//     type: float
//     default: 8.0
//     min: 3.0
//     max: 25.0
//     unit: mm
//     description: Mounting flange thickness
//   - name: drain_diam
//     type: float
//     default: 20.0
//     min: 8.0
//     max: 50.0
//     unit: mm
//     description: Drain plug boss diameter
//   - name: fn
//     type: int
//     default: 96
//     min: 16
//     max: 512
//     unit: count
//     description: Circle resolution
// connectors:
//   - name: flange_face
//     type: planar
//     origin: [0, 0, "flange_thickness"]
//     direction: [0, 0, 1]
//   - name: drain_port
//     type: axial
//     origin: [0, 0, "-depth"]
//     direction: [0, 0, -1]
// constraints:
//   - check: "wall_thickness < depth / 2"
//     message: "Wall thickness ({wall_thickness}mm) exceeds half the pan depth"
//     severity: error
//   - check: "drain_diam < width / 2"
//     message: "Drain boss ({drain_diam}mm) too large for pan width ({width}mm)"
//     severity: error
//   - check: "flange_width >= 10"
//     message: "Flange width ({flange_width}mm) is narrow; may not seal well"
//     severity: warning
// SCADGEN_META_END

module oil_pan(length=400, width=150, depth=80, wall_thickness=3,
               flange_width=15, flange_thickness=8, drain_diam=20,
               fn=96)
{
    $fn = fn;
    wt = wall_thickness;
    total_length = length + 2 * flange_width;
    total_width = width + 2 * flange_width;

    union() {
        // Mounting flange (at the top)
        translate([-total_length / 2, -total_width / 2, 0])
            cube([total_length, total_width, flange_thickness]);

        // Pan body (extends downward from flange)
        translate([0, 0, -depth])
        difference() {
            // Outer shell
            translate([-length / 2, -width / 2, 0])
                cube([length, width, depth]);

            // Inner cavity
            translate([-(length - 2 * wt) / 2, -(width - 2 * wt) / 2, wt])
                cube([length - 2 * wt, width - 2 * wt, depth]);
        }

        // Drain boss (on the bottom)
        translate([length / 4, 0, -depth - 5])
            cylinder(h = 10, d = drain_diam);
    }
}
