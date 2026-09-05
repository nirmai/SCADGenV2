// SCADGEN_META_BEGIN
// schema_version: 1
// template_id: gear_spur
// module_name: gear_spur
// description: Spur gear with arc-based tooth approximation
// category: mechanical/power_transmission
// tags: [gear, spur, cog, power_transmission, rotary]
// aliases: [gear, cog, spur gear, pinion, spur]
// keywords: [gear, teeth, tooth, module, pitch, meshing, involute, cog, sprocket]
// params:
//   - name: teeth
//     type: int
//     default: 24
//     min: 6
//     max: 200
//     unit: count
//     description: Number of teeth
//   - name: modul
//     type: float
//     default: 2.0
//     min: 0.3
//     max: 20.0
//     unit: mm
//     description: ISO gear module (mm/tooth). Controls tooth size.
//   - name: thickness
//     type: float
//     default: 8.0
//     min: 0.5
//     max: 500.0
//     unit: mm
//     description: Face width (extrusion height)
//   - name: bore_diam
//     type: float
//     default: 5.0
//     min: 0.0
//     max: 500.0
//     unit: mm
//     description: Center bore diameter. 0 = solid.
//   - name: fn
//     type: int
//     default: 128
//     min: 16
//     max: 512
//     unit: count
//     description: Circle resolution
// connectors:
//   - name: shaft_axis
//     type: axial
//     origin: [0, 0, 0]
//     direction: [0, 0, 1]
//     diameter_ref: bore_diam
//   - name: mesh_point
//     type: planar
//     origin: [0, 0, 0]
//     direction: [1, 0, 0]
// derived:
//   - pitch_diameter: "modul * teeth"
//   - outer_diameter: "modul * (teeth + 2)"
// SCADGEN_META_END

module gear_spur(teeth=24, modul=2, thickness=8, bore_diam=5, fn=128)
{
    valid_teeth     = (teeth >= 6);
    valid_modul     = (modul > 0);
    valid_thickness = (thickness > 0);
    valid_bore      = (bore_diam >= 0);

    if (!valid_teeth)     echo("[WARN] teeth should be >= 6 for a clean outline.");
    if (!valid_modul)     echo("[WARN] modul must be > 0.");
    if (!valid_thickness) echo("[WARN] thickness must be > 0.");
    if (!valid_bore)      echo("[WARN] bore_diam must be >= 0.");

    m = modul;
    z = teeth;

    pitch_radius     = 0.5 * m * z;
    addendum_radius  = pitch_radius + m;
    dedendum_factor  = 1.25;
    root_radius_raw  = pitch_radius - dedendum_factor * m;
    root_radius      = (root_radius_raw < 0.1) ? 0.1 : root_radius_raw;

    half_tooth_deg   = 180 / z;

    gear_fn = fn;

    $fn = gear_fn;
    linear_extrude(height = thickness)
        difference() {
            gear_spur_2d(z, pitch_radius, addendum_radius, root_radius, half_tooth_deg);
            if (bore_diam > 0)
                circle(d = bore_diam);
        }
}

module gear_spur_2d(teeth_count, pitch_radius, addendum_radius, root_radius, half_tooth_deg)
{
    tooth_step_deg = 360 / teeth_count;
    union() {
        for (i = [0 : teeth_count - 1])
            rotate(i * tooth_step_deg)
                gear_spur_single_tooth(addendum_radius, root_radius, half_tooth_deg);
    }
}

module gear_spur_single_tooth(addendum_radius, root_radius, half_angle_deg)
{
    pts = [
        [ root_radius * cos(-half_angle_deg),     root_radius * sin(-half_angle_deg)     ],
        [ addendum_radius * cos(-half_angle_deg/2), addendum_radius * sin(-half_angle_deg/2) ],
        [ addendum_radius * cos( half_angle_deg/2), addendum_radius * sin( half_angle_deg/2) ],
        [ root_radius * cos( half_angle_deg),     root_radius * sin( half_angle_deg)     ]
    ];
    polygon(points = pts);
}
