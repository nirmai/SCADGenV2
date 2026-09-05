// SCADGEN_META_BEGIN
// schema_version: 1
// template_id: torus
// module_name: torus_shape
// description: Parametric torus (ring shape)
// category: primitive
// tags: [torus, ring, donut, o-ring]
// aliases: [torus, ring, donut]
// keywords: [torus, ring, donut, major, minor, tube, o-ring]
// params:
//   - name: major_r
//     type: float
//     default: 25.0
//     min: 0.5
//     max: 1000.0
//     unit: mm
//     description: Major radius (center of tube path)
//   - name: minor_r
//     type: float
//     default: 6.0
//     min: 0.1
//     max: 500.0
//     unit: mm
//     description: Minor radius (tube cross-section)
//   - name: fn
//     type: int
//     default: 120
//     min: 16
//     max: 512
//     unit: count
//     description: Circle resolution
// connectors:
//   - name: center_axis
//     type: axial
//     origin: [0, 0, 0]
//     direction: [0, 0, 1]
// SCADGEN_META_END

module torus_shape(major_r=25, minor_r=6, fn=120) {
    $fn = fn;
    rotate_extrude(angle = 360)
        translate([major_r, 0, 0])
            circle(r = minor_r);
}
