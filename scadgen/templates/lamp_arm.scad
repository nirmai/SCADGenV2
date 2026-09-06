// SCADGEN_META_BEGIN
// schema_version: 1
// template_id: lamp_arm
// module_name: lamp_arm
// description: Gooseneck lamp arm with smooth quarter-circle curve at top
// category: lamp
// tags: [lamp, arm, gooseneck, stem, desk lamp]
// aliases: [lamp arm, gooseneck, lamp stem]
// keywords: [lamp, arm, gooseneck, stem, tube, curve, bend, neck, desk]
// length_param: straight_height
// params:
//   - name: stem_diam
//     type: float
//     default: 10.0
//     min: 4.0
//     max: 25.0
//     unit: mm
//     description: Arm tube diameter
//   - name: straight_height
//     type: float
//     default: 260.0
//     min: 50.0
//     max: 600.0
//     unit: mm
//     description: Height of the straight vertical section
//   - name: curve_radius
//     type: float
//     default: 55.0
//     min: 15.0
//     max: 150.0
//     unit: mm
//     description: Radius of the gooseneck bend
//   - name: joint_diam
//     type: float
//     default: 18.0
//     min: 8.0
//     max: 40.0
//     unit: mm
//     description: Shade joint ball diameter
//   - name: collar_diam
//     type: float
//     default: 18.0
//     min: 8.0
//     max: 40.0
//     unit: mm
//     description: Base collar diameter
//   - name: collar_height
//     type: float
//     default: 6.0
//     min: 2.0
//     max: 20.0
//     unit: mm
//     description: Base collar height
//   - name: fn
//     type: int
//     default: 64
//     min: 16
//     max: 256
//     unit: count
//     description: Circle resolution
// connectors:
//   - name: base_end
//     type: axial
//     origin: [0, 0, 0]
//     direction: [0, 0, -1]
//     diameter_ref: stem_diam
//   - name: shade_mount
//     type: axial
//     origin: ["curve_radius", 0, "straight_height + curve_radius"]
//     direction: [0.34, 0, -0.94]
// constraints:
//   - check: "joint_diam >= stem_diam"
//     message: "Joint diameter ({joint_diam}mm) should be at least as large as stem ({stem_diam}mm)"
//     severity: warning
//   - check: "curve_radius > stem_diam * 2"
//     message: "Curve radius ({curve_radius}mm) too tight for stem diameter ({stem_diam}mm)"
//     severity: error
// SCADGEN_META_END

module lamp_arm(stem_diam=10, straight_height=260, curve_radius=55,
                joint_diam=18, collar_diam=18, collar_height=6, fn=64)
{
    $fn = fn;
    curve_steps = 24;

    // Base collar
    cylinder(h = collar_height, d1 = collar_diam, d2 = stem_diam);

    // Straight vertical section
    cylinder(h = straight_height, d = stem_diam);

    // Curved section — quarter circle in XZ plane
    for (i = [0 : curve_steps - 1]) {
        a1 = i * 90 / curve_steps;
        a2 = (i + 1) * 90 / curve_steps;
        hull() {
            translate([curve_radius * (1 - cos(a1)), 0,
                       straight_height + curve_radius * sin(a1)])
                sphere(d = stem_diam);
            translate([curve_radius * (1 - cos(a2)), 0,
                       straight_height + curve_radius * sin(a2)])
                sphere(d = stem_diam);
        }
    }

    // Joint ball at shade mount point
    translate([curve_radius, 0, straight_height + curve_radius])
        sphere(d = joint_diam);

    // Thumbscrew knobs on joint (decorative)
    translate([curve_radius, 0, straight_height + curve_radius])
        rotate([90, 0, 0])
            cylinder(h = joint_diam * 0.7, d = joint_diam * 0.35, center = true);
}
