// SCADGEN_META_BEGIN
// schema_version: 1
// template_id: connecting_rod
// module_name: connecting_rod
// description: Connecting rod with big end and small end bores joined by an I-beam
// category: engine/reciprocating
// tags: [connecting rod, con rod, conrod, engine, reciprocating, big end, small end]
// aliases: [connecting rod, con rod, conrod]
// keywords: [connecting, rod, con, conrod, engine, reciprocating, big, small, end, beam, crank, piston, wrist]
// length_param: length
// params:
//   - name: length
//     type: float
//     default: 150.0
//     min: 30.0
//     max: 600.0
//     unit: mm
//     description: Center-to-center distance between big and small end bores
//   - name: big_end_bore
//     type: float
//     default: 40.0
//     min: 10.0
//     max: 150.0
//     unit: mm
//     description: Big end bore diameter (crank journal)
//   - name: small_end_bore
//     type: float
//     default: 20.0
//     min: 5.0
//     max: 80.0
//     unit: mm
//     description: Small end bore diameter (wrist pin)
//   - name: big_end_width
//     type: float
//     default: 55.0
//     min: 15.0
//     max: 200.0
//     unit: mm
//     description: Big end outer width
//   - name: small_end_width
//     type: float
//     default: 30.0
//     min: 10.0
//     max: 120.0
//     unit: mm
//     description: Small end outer width
//   - name: beam_width
//     type: float
//     default: 15.0
//     min: 3.0
//     max: 60.0
//     unit: mm
//     description: Beam (shank) width
//   - name: beam_height
//     type: float
//     default: 20.0
//     min: 5.0
//     max: 80.0
//     unit: mm
//     description: Beam (shank) height for I-section depth
//   - name: thickness
//     type: float
//     default: 18.0
//     min: 5.0
//     max: 80.0
//     unit: mm
//     description: Rod thickness (extrusion depth along Z)
//   - name: fn
//     type: int
//     default: 96
//     min: 16
//     max: 512
//     unit: count
//     description: Circle resolution
// connectors:
//   - name: big_end
//     type: axial
//     origin: [0, 0, "thickness / 2"]
//     direction: [0, 0, 1]
//   - name: small_end
//     type: axial
//     origin: [0, "length", "thickness / 2"]
//     direction: [0, 0, 1]
// constraints:
//   - check: "big_end_bore < big_end_width * 0.85"
//     message: "Big end bore ({big_end_bore}mm) leaves insufficient wall in big end ({big_end_width}mm wide)"
//     severity: error
//   - check: "small_end_bore < small_end_width * 0.85"
//     message: "Small end bore ({small_end_bore}mm) leaves insufficient wall in small end ({small_end_width}mm wide)"
//     severity: error
//   - check: "length > (big_end_width + small_end_width) / 2"
//     message: "Center distance ({length}mm) too short for the end sizes ({big_end_width}mm + {small_end_width}mm)"
//     severity: error
//   - check: "beam_width >= 3"
//     message: "Beam width ({beam_width}mm) is very narrow; structural weakness likely"
//     severity: warning
//   - check: "big_end_bore > small_end_bore"
//     message: "Big end bore ({big_end_bore}mm) is smaller than small end bore ({small_end_bore}mm); unusual geometry"
//     severity: warning
// SCADGEN_META_END

module connecting_rod(length=150, big_end_bore=40, small_end_bore=20,
                      big_end_width=55, small_end_width=30,
                      beam_width=15, beam_height=20, thickness=18,
                      fn=96)
{
    $fn = fn;
    big_r = big_end_width / 2;
    small_r = small_end_width / 2;

    linear_extrude(height = thickness) {
        difference() {
            union() {
                // Big end circle at origin
                circle(d = big_end_width);

                // Small end circle at (0, length)
                translate([0, length])
                    circle(d = small_end_width);

                // Connecting beam
                translate([-beam_width / 2, 0])
                    square([beam_width, length]);
            }

            // Big end bore
            circle(d = big_end_bore);

            // Small end bore
            translate([0, length])
                circle(d = small_end_bore);
        }
    }
}
