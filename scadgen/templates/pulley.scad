// SCADGEN_META_BEGIN
// schema_version: 1
// template_id: pulley
// module_name: pulley
// description: V-belt or flat belt pulley with hub bore
// category: mechanical/power_transmission
// tags: [pulley, belt, sheave, drive, power transmission]
// aliases: [pulley, belt pulley, sheave, v-belt pulley]
// keywords: [pulley, belt, sheave, groove, hub, bore, v-belt, flat, drive, power, transmission, pitch]
// length_param: hub_length
// params:
//   - name: pitch_diam
//     type: float
//     default: 80.0
//     min: 20.0
//     max: 1000.0
//     unit: mm
//     description: Pitch diameter of the pulley
//   - name: groove_count
//     type: int
//     default: 1
//     min: 1
//     max: 10
//     unit: count
//     description: Number of belt grooves
//   - name: groove_depth
//     type: float
//     default: 8.0
//     min: 2.0
//     max: 40.0
//     unit: mm
//     description: Depth of each V-groove
//   - name: groove_angle
//     type: float
//     default: 38.0
//     min: 20.0
//     max: 60.0
//     unit: degrees
//     description: V-groove included angle
//   - name: belt_width
//     type: float
//     default: 13.0
//     min: 4.0
//     max: 50.0
//     unit: mm
//     description: Belt top width (determines groove spacing)
//   - name: hub_diam
//     type: float
//     default: 40.0
//     min: 10.0
//     max: 500.0
//     unit: mm
//     description: Hub outer diameter
//   - name: hub_length
//     type: float
//     default: 25.0
//     min: 5.0
//     max: 200.0
//     unit: mm
//     description: Hub axial length
//   - name: bore_diam
//     type: float
//     default: 20.0
//     min: 3.0
//     max: 200.0
//     unit: mm
//     description: Shaft bore diameter
//   - name: fn
//     type: int
//     default: 96
//     min: 16
//     max: 512
//     unit: count
//     description: Circle resolution
// connectors:
//   - name: bore_axis
//     type: axial
//     origin: [0, 0, "hub_length / 2"]
//     direction: [0, 0, 1]
//   - name: face_a
//     type: planar
//     origin: [0, 0, 0]
//     direction: [0, 0, -1]
//   - name: face_b
//     type: planar
//     origin: [0, 0, "hub_length"]
//     direction: [0, 0, 1]
// constraints:
//   - check: "bore_diam < hub_diam"
//     message: "Bore ({bore_diam}mm) must be smaller than hub ({hub_diam}mm)"
//     severity: error
//   - check: "hub_diam < pitch_diam"
//     message: "Hub ({hub_diam}mm) must be smaller than pitch diameter ({pitch_diam}mm)"
//     severity: error
//   - check: "groove_depth < (pitch_diam - hub_diam) / 2"
//     message: "Groove depth ({groove_depth}mm) exceeds available rim thickness"
//     severity: error
//   - check: "groove_count >= 1"
//     message: "At least 1 groove is required"
//     severity: warning
// SCADGEN_META_END

module pulley(pitch_diam=80, groove_count=1, groove_depth=8,
              groove_angle=38, belt_width=13, hub_diam=40,
              hub_length=25, bore_diam=20, fn=96)
{
    $fn = fn;
    rim_width = groove_count * (belt_width + 2) + 2;
    rim_r = pitch_diam / 2;
    half_angle = groove_angle / 2;
    hub_r = hub_diam / 2;

    difference() {
        union() {
            // Rim disc
            translate([0, 0, (hub_length - rim_width) / 2])
                cylinder(h = rim_width, r = rim_r);

            // Hub
            cylinder(h = hub_length, r = hub_r);

            // Web connecting hub to rim
            translate([0, 0, (hub_length - rim_width) / 2])
                cylinder(h = rim_width, r = hub_r + (rim_r - hub_r) * 0.4);
        }

        // Bore
        translate([0, 0, -0.1])
            cylinder(h = hub_length + 0.2, d = bore_diam);

        // V-grooves
        for (i = [0 : groove_count - 1]) {
            z_off = (hub_length - rim_width) / 2 + 1 + (belt_width + 2) * i + belt_width / 2 + 1;
            translate([0, 0, z_off])
                rotate_extrude($fn = fn)
                    translate([rim_r, 0, 0])
                        polygon([
                            [0, -belt_width / 2],
                            [-groove_depth, 0],
                            [0, belt_width / 2]
                        ]);
        }
    }
}
