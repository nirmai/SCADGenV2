// SCADGEN_META_BEGIN
// schema_version: 1
// template_id: cone
// module_name: cone_shape
// description: Truncated cone (frustum) or full cone
// category: primitive
// tags: [cone, frustum, truncated, tapered]
// aliases: [cone, frustum, truncated cone]
// keywords: [cone, frustum, truncated, taper, base, top, conical]
// params:
//   - name: base_diam
//     type: float
//     default: 30.0
//     min: 0.1
//     max: 2000.0
//     unit: mm
//     description: Base diameter
//   - name: top_diam
//     type: float
//     default: 10.0
//     min: 0.0
//     max: 2000.0
//     unit: mm
//     description: Top diameter (0 for a full cone)
//   - name: height
//     type: float
//     default: 40.0
//     min: 0.1
//     max: 2000.0
//     unit: mm
//     description: Height
//   - name: center
//     type: bool
//     default: false
//     description: Center vertically on origin
//   - name: fn
//     type: int
//     default: 96
//     min: 16
//     max: 512
//     unit: count
//     description: Circle resolution
// connectors:
//   - name: center_axis
//     type: axial
//     origin: [0, 0, "height / 2"]
//     direction: [0, 0, 1]
//   - name: bottom_face
//     type: planar
//     origin: [0, 0, 0]
//     direction: [0, 0, -1]
//     diameter_ref: base_diam
//   - name: top_face
//     type: planar
//     origin: [0, 0, "height"]
//     direction: [0, 0, 1]
//     diameter_ref: top_diam
// SCADGEN_META_END

module cone_shape(base_diam=30, top_diam=10, height=40, center=false, fn=96) {
    $fn = fn;
    cylinder(h = height, d1 = base_diam, d2 = top_diam, center = center);
}
