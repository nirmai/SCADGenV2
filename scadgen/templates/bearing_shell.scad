// SCADGEN_META_BEGIN
// schema_version: 1
// template_id: bearing_shell
// module_name: bearing_shell
// description: Plain bearing half-shell for journal bearings
// category: mechanical/bearing
// tags: [bearing, shell, plain, journal, sleeve, bush]
// aliases: [bearing shell, plain bearing, journal bearing, bush bearing, sleeve bearing]
// keywords: [bearing, shell, plain, journal, bush, sleeve, half, bore, crank, cam, oil, clearance]
// length_param: width
// params:
//   - name: bore
//     type: float
//     default: 50.0
//     min: 5.0
//     max: 500.0
//     unit: mm
//     description: Inner bore diameter
//   - name: outer_diam
//     type: float
//     default: 56.0
//     min: 6.0
//     max: 600.0
//     unit: mm
//     description: Outer diameter
//   - name: width
//     type: float
//     default: 20.0
//     min: 2.0
//     max: 300.0
//     unit: mm
//     description: Axial width of the bearing shell
//   - name: wall_thickness
//     type: float
//     default: 3.0
//     min: 0.5
//     max: 30.0
//     unit: mm
//     description: Shell wall thickness
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
//     origin: [0, 0, "width / 2"]
//     direction: [0, 0, 1]
//   - name: outer_face
//     type: axial
//     origin: [0, 0, "width / 2"]
//     direction: [0, 0, 1]
// constraints:
//   - check: "outer_diam > bore"
//     message: "Outer diameter ({outer_diam}mm) must exceed bore ({bore}mm)"
//     severity: error
//   - check: "wall_thickness <= (outer_diam - bore) / 2 + 0.1"
//     message: "Wall thickness ({wall_thickness}mm) exceeds available radial space"
//     severity: error
//   - check: "wall_thickness >= 1.5"
//     message: "Wall thickness ({wall_thickness}mm) is very thin; may not withstand bearing loads"
//     severity: warning
// SCADGEN_META_END

module bearing_shell(bore=50, outer_diam=56, width=20,
                     wall_thickness=3, fn=96)
{
    $fn = fn;
    r_inner = bore / 2;
    r_outer = outer_diam / 2;

    // Half-shell: intersect full cylindrical shell with a half-space
    intersection() {
        difference() {
            cylinder(h = width, d = outer_diam);
            translate([0, 0, -0.1])
                cylinder(h = width + 0.2, d = bore);
        }
        // Keep only the top half (y >= 0)
        translate([-r_outer, 0, 0])
            cube([outer_diam, r_outer, width]);
    }
}
