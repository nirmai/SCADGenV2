// SCADGEN_META_BEGIN
// schema_version: 1
// template_id: piston
// module_name: piston
// description: Piston with ring grooves and wrist pin bore
// category: engine/reciprocating
// tags: [piston, engine, reciprocating, bore, ring, wrist pin]
// aliases: [piston]
// keywords: [piston, engine, reciprocating, bore, ring, wrist, pin, compression, oil, groove, crown, skirt]
// length_param: bore_diam
// params:
//   - name: bore_diam
//     type: float
//     default: 80.0
//     min: 20.0
//     max: 300.0
//     unit: mm
//     description: Piston outer diameter (matches cylinder bore)
//   - name: height
//     type: float
//     default: 60.0
//     min: 10.0
//     max: 200.0
//     unit: mm
//     description: Total piston height
//   - name: pin_bore_diam
//     type: float
//     default: 20.0
//     min: 5.0
//     max: 80.0
//     unit: mm
//     description: Wrist pin bore diameter
//   - name: pin_bore_height
//     type: float
//     default: 20.0
//     min: 5.0
//     max: 150.0
//     unit: mm
//     description: Height of pin bore center from piston bottom
//   - name: ring_count
//     type: int
//     default: 3
//     min: 0
//     max: 6
//     description: Number of ring grooves
//   - name: ring_width
//     type: float
//     default: 2.0
//     min: 0.5
//     max: 6.0
//     unit: mm
//     description: Ring groove width (axial)
//   - name: ring_depth
//     type: float
//     default: 1.5
//     min: 0.5
//     max: 5.0
//     unit: mm
//     description: Ring groove depth (radial)
//   - name: skirt_length
//     type: float
//     default: 15.0
//     min: 3.0
//     max: 80.0
//     unit: mm
//     description: Skirt length below ring land
//   - name: wall_thickness
//     type: float
//     default: 5.0
//     min: 2.0
//     max: 30.0
//     unit: mm
//     description: Crown and wall thickness
//   - name: fn
//     type: int
//     default: 96
//     min: 16
//     max: 512
//     unit: count
//     description: Circle resolution
// connectors:
//   - name: crown_face
//     type: planar
//     origin: [0, 0, "height"]
//     direction: [0, 0, 1]
//   - name: pin_bore
//     type: axial
//     origin: [0, 0, "pin_bore_height"]
//     direction: [1, 0, 0]
//   - name: skirt_outer
//     type: axial
//     origin: [0, 0, 0]
//     direction: [0, 0, -1]
// constraints:
//   - check: "pin_bore_diam < bore_diam * 0.7"
//     message: "Pin bore ({pin_bore_diam}mm) must be less than 70% of bore diameter ({bore_diam}mm)"
//     severity: error
//   - check: "pin_bore_height < height"
//     message: "Pin bore center height ({pin_bore_height}mm) must be within piston height ({height}mm)"
//     severity: error
//   - check: "ring_depth < (bore_diam - pin_bore_diam) / 4"
//     message: "Ring depth ({ring_depth}mm) too deep for available wall between bore ({bore_diam}mm) and pin ({pin_bore_diam}mm)"
//     severity: error
//   - check: "ring_count == 0 or pin_bore_height > ring_count * (ring_width + 1)"
//     message: "Pin bore center ({pin_bore_height}mm) is within the ring groove zone; rings and pin would overlap"
//     severity: warning
//   - check: "wall_thickness < bore_diam / 3"
//     message: "Wall thickness ({wall_thickness}mm) is very thick relative to bore ({bore_diam}mm)"
//     severity: warning
// SCADGEN_META_END

module piston(bore_diam=80, height=60, pin_bore_diam=20,
              pin_bore_height=20, ring_count=3, ring_width=2,
              ring_depth=1.5, skirt_length=15, wall_thickness=5,
              fn=96)
{
    $fn = fn;
    r = bore_diam / 2;

    // Ring grooves start from the top, spaced evenly in the land zone
    ring_spacing = ring_width + 2;  // groove + land between
    ring_zone_start = height - wall_thickness - ring_count * ring_spacing;

    difference() {
        // Outer shell
        cylinder(h = height, d = bore_diam);

        // Hollow interior (leave crown thickness at top, wall around sides)
        translate([0, 0, -0.1])
            cylinder(h = height - wall_thickness + 0.1,
                     d = bore_diam - 2 * wall_thickness);

        // Ring grooves
        for (i = [0 : ring_count - 1]) {
            groove_z = height - wall_thickness - (i + 1) * ring_spacing + 1;
            translate([0, 0, groove_z])
                difference() {
                    cylinder(h = ring_width, d = bore_diam + 0.1);
                    cylinder(h = ring_width, d = bore_diam - 2 * ring_depth);
                }
        }

        // Wrist pin bore (through-hole along X axis)
        translate([-(r + 0.1), 0, pin_bore_height])
            rotate([0, 90, 0])
                cylinder(h = bore_diam + 0.2, d = pin_bore_diam);
    }
}
