// SCADGEN_META_BEGIN
// schema_version: 1
// template_id: bushing
// module_name: bushing
// description: Cylindrical bushing (sleeve bearing)
// category: mechanical/bearing
// tags: [bushing, sleeve, bearing, spacer, washer]
// aliases: [bushing, sleeve, spacer, sleeve bearing]
// keywords: [bushing, sleeve, bearing, spacer, inner, outer, wall, press, fit]
// params:
//   - name: inner_d
//     type: float
//     default: 10.0
//     min: 0.5
//     max: 500.0
//     unit: mm
//     description: Inner (bore) diameter
//   - name: outer_d
//     type: float
//     default: 20.0
//     min: 1.0
//     max: 600.0
//     unit: mm
//     description: Outer diameter
//   - name: thickness
//     type: float
//     default: 8.0
//     min: 0.5
//     max: 500.0
//     unit: mm
//     description: Axial length (height)
// connectors:
//   - name: bore_axis
//     type: axial
//     origin: [0, 0, 0]
//     direction: [0, 0, 1]
//     diameter_ref: inner_d
//   - name: outer_axis
//     type: axial
//     origin: [0, 0, 0]
//     direction: [0, 0, 1]
//     diameter_ref: outer_d
// SCADGEN_META_END

module bushing(inner_d=10, outer_d=20, thickness=8) {
    difference() {
        cylinder(h = thickness, r=outer_d/2, $fn=64);
        cylinder(h = thickness+2, r=inner_d/2, $fn=64);
    }
}
