// SCADGEN_META_BEGIN
// schema_version: 1
// template_id: sphere
// module_name: sphere_shape
// description: Parametric sphere
// category: primitive
// tags: [sphere, ball, round]
// aliases: [sphere, ball]
// keywords: [sphere, ball, round, diameter, radius]
// params:
//   - name: diam
//     type: float
//     default: 30.0
//     min: 0.1
//     max: 2000.0
//     unit: mm
//     description: Sphere diameter
//   - name: fn
//     type: int
//     default: 96
//     min: 16
//     max: 512
//     unit: count
//     description: Circle resolution
// SCADGEN_META_END

module sphere_shape(diam=30, fn=96) {
    $fn = fn;
    sphere(d = diam);
}
