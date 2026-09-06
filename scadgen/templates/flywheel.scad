// SCADGEN_META_BEGIN
// schema_version: 1
// template_id: flywheel
// module_name: flywheel
// description: Solid disc flywheel with center bore and bolt pattern
// category: engine/rotating
// tags: [flywheel, inertia, rotating, engine, disc]
// aliases: [flywheel, inertia wheel]
// keywords: [flywheel, inertia, wheel, disc, mass, crankshaft, bolt, bore, engine, rotating, energy, storage]
// length_param: thickness
// params:
//   - name: outer_diam
//     type: float
//     default: 200.0
//     min: 30.0
//     max: 2000.0
//     unit: mm
//     description: Overall flywheel diameter
//   - name: thickness
//     type: float
//     default: 30.0
//     min: 5.0
//     max: 200.0
//     unit: mm
//     description: Flywheel thickness
//   - name: bore_diam
//     type: float
//     default: 25.0
//     min: 5.0
//     max: 500.0
//     unit: mm
//     description: Center bore diameter
//   - name: bolt_circle_diam
//     type: float
//     default: 150.0
//     min: 15.0
//     max: 1500.0
//     unit: mm
//     description: Bolt circle diameter
//   - name: bolt_hole_diam
//     type: float
//     default: 10.0
//     min: 3.0
//     max: 50.0
//     unit: mm
//     description: Bolt hole diameter
//   - name: bolt_count
//     type: int
//     default: 6
//     min: 0
//     max: 24
//     unit: count
//     description: Number of mounting bolts
//   - name: fn
//     type: int
//     default: 96
//     min: 16
//     max: 512
//     unit: count
//     description: Circle resolution
// connectors:
//   - name: front_face
//     type: planar
//     origin: [0, 0, "thickness"]
//     direction: [0, 0, 1]
//   - name: rear_face
//     type: planar
//     origin: [0, 0, 0]
//     direction: [0, 0, -1]
//   - name: bore_axis
//     type: axial
//     origin: [0, 0, "thickness / 2"]
//     direction: [0, 0, 1]
// constraints:
//   - check: "bore_diam < outer_diam * 0.5"
//     message: "Bore ({bore_diam}mm) must be less than 50% of outer diameter ({outer_diam}mm)"
//     severity: error
//   - check: "bolt_count == 0 or bolt_circle_diam > bore_diam + bolt_hole_diam"
//     message: "Bolt circle ({bolt_circle_diam}mm) too close to center bore"
//     severity: error
//   - check: "bolt_count == 0 or bolt_circle_diam < outer_diam - bolt_hole_diam"
//     message: "Bolt circle ({bolt_circle_diam}mm) too close to outer edge"
//     severity: error
//   - check: "thickness >= 5"
//     message: "Flywheel thickness ({thickness}mm) is very thin for energy storage"
//     severity: warning
// SCADGEN_META_END

module flywheel(outer_diam=200, thickness=30, bore_diam=25,
                bolt_circle_diam=150, bolt_hole_diam=10,
                bolt_count=6, fn=96)
{
    $fn = fn;
    bcd_r = bolt_circle_diam / 2;

    difference() {
        // Main disc
        cylinder(h = thickness, d = outer_diam);

        // Center bore
        translate([0, 0, -0.1])
            cylinder(h = thickness + 0.2, d = bore_diam);

        // Bolt holes
        if (bolt_count > 0) {
            for (i = [0 : bolt_count - 1]) {
                angle = i * 360 / bolt_count;
                translate([bcd_r * cos(angle), bcd_r * sin(angle), -0.1])
                    cylinder(h = thickness + 0.2, d = bolt_hole_diam);
            }
        }
    }
}
