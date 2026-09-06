// SCADGEN_META_BEGIN
// schema_version: 1
// template_id: washer
// module_name: washer
// description: Flat washer (ISO 7089 normal series)
// category: fastener/washer
// tags: [washer, flat, fastener, metric, spacer]
// aliases: [flat washer, plain washer, washer]
// keywords: [washer, flat, spacer, shim, ring, fastener, ISO7089, ISO7090, M3, M4, M5, M6, M8, M10, M12, M16, M20]
// length_param: thickness
// params:
//   - name: inner_diam
//     type: float
//     default: 8.4
//     min: 1.0
//     max: 60.0
//     unit: mm
//     description: Inner diameter (bolt clearance hole)
//   - name: outer_diam
//     type: float
//     default: 16.0
//     min: 2.0
//     max: 100.0
//     unit: mm
//     description: Outer diameter
//   - name: thickness
//     type: float
//     default: 1.6
//     min: 0.1
//     max: 10.0
//     unit: mm
//     description: Washer thickness
//   - name: fn
//     type: int
//     default: 96
//     min: 16
//     max: 512
//     unit: count
//     description: Cylinder resolution
// connectors:
//   - name: top_face
//     type: planar
//     origin: [0, 0, "thickness"]
//     direction: [0, 0, 1]
//   - name: bottom_face
//     type: planar
//     origin: [0, 0, 0]
//     direction: [0, 0, -1]
//   - name: bore_axis
//     type: axial
//     origin: [0, 0, "thickness / 2"]
//     direction: [0, 0, -1]
//     diameter_ref: inner_diam
// constraints:
//   - check: "outer_diam > inner_diam"
//     message: "Outer diameter ({outer_diam}mm) must exceed inner diameter ({inner_diam}mm)"
//     severity: error
//   - check: "(outer_diam - inner_diam) / 2 >= 0.5"
//     message: "Wall thickness is under 0.5mm — washer may be structurally inadequate"
//     severity: warning
// derived:
//   - wall_thickness: "(outer_diam - inner_diam) / 2"
// SCADGEN_META_END

module washer(inner_diam=8.4, outer_diam=16.0, thickness=1.6, fn=96) {
    $fn = fn;
    difference() {
        cylinder(h = thickness, d = outer_diam);
        translate([0, 0, -0.05])
            cylinder(h = thickness + 0.1, d = inner_diam);
    }
}
