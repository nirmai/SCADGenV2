// SCADGEN_META_BEGIN
// schema_version: 1
// template_id: shaft
// module_name: shaft
// description: Shaft with optional DIN 6885 keyway slot
// category: mechanical/power_transmission
// tags: [shaft, axle, spindle, keyway, drive, power transmission]
// aliases: [shaft, axle, spindle]
// keywords: [shaft, axle, spindle, keyway, drive, power, transmission, DIN6885, rotate, torque]
// length_param: length
// params:
//   - name: diameter
//     type: float
//     default: 20.0
//     min: 3.0
//     max: 500.0
//     unit: mm
//     description: Shaft diameter
//   - name: length
//     type: float
//     default: 100.0
//     min: 5.0
//     max: 3000.0
//     unit: mm
//     description: Shaft length
//   - name: has_keyway
//     type: bool
//     default: false
//     description: Cut a DIN 6885 keyway slot
//   - name: keyway_width
//     type: float
//     default: 6.0
//     min: 2.0
//     max: 100.0
//     unit: mm
//     description: Keyway width (DIN 6885)
//   - name: keyway_depth
//     type: float
//     default: 3.5
//     min: 1.0
//     max: 50.0
//     unit: mm
//     description: Keyway depth into shaft (DIN 6885)
//   - name: keyway_length
//     type: float
//     default: 30.0
//     min: 4.0
//     max: 3000.0
//     unit: mm
//     description: Keyway slot length
//   - name: fn
//     type: int
//     default: 96
//     min: 16
//     max: 512
//     unit: count
//     description: Circle resolution
// connectors:
//   - name: end_a
//     type: axial
//     origin: [0, 0, 0]
//     direction: [0, 0, -1]
//   - name: end_b
//     type: axial
//     origin: [0, 0, "length"]
//     direction: [0, 0, 1]
//   - name: keyway_slot
//     type: planar
//     origin: ["diameter / 2", 0, "length / 2"]
//     direction: [1, 0, 0]
// constraints:
//   - check: "has_keyway == False or keyway_width < diameter"
//     message: "Keyway width ({keyway_width}mm) must be less than shaft diameter ({diameter}mm)"
//     severity: error
//   - check: "has_keyway == False or keyway_depth < diameter / 2"
//     message: "Keyway depth ({keyway_depth}mm) must be less than shaft radius ({diameter}mm / 2)"
//     severity: error
//   - check: "has_keyway == False or keyway_length <= length"
//     message: "Keyway length ({keyway_length}mm) must not exceed shaft length ({length}mm)"
//     severity: error
//   - check: "has_keyway == False or keyway_depth >= 1.0"
//     message: "Keyway depth ({keyway_depth}mm) is very shallow; may not transmit torque reliably"
//     severity: warning
// SCADGEN_META_END

module shaft(diameter=20, length=100, has_keyway=false,
             keyway_width=6, keyway_depth=3.5, keyway_length=30,
             fn=96)
{
    $fn = fn;
    r = diameter / 2;

    difference() {
        cylinder(h = length, d = diameter);

        if (has_keyway) {
            // Keyway slot: rectangular cut at the top of the shaft cross-section
            // Centered along the shaft length, cut from the outer surface inward
            translate([-keyway_width / 2,
                       r - keyway_depth,
                       (length - keyway_length) / 2])
                cube([keyway_width, keyway_depth + 0.1, keyway_length]);
        }
    }
}
