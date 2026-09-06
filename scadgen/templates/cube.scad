// SCADGEN_META_BEGIN
// schema_version: 1
// template_id: cube
// module_name: cube_shape
// description: Parametric cube or rectangular block
// category: primitive
// tags: [cube, block, box, rectangular]
// aliases: [cube, block, box]
// keywords: [cube, square, block, box, rectangular, size]
// params:
//   - name: size
//     type: float
//     default: 10.0
//     min: 0.1
//     max: 1000.0
//     unit: mm
//     description: Side length of the cube
// connectors:
//   - name: top_face
//     type: planar
//     origin: [0, 0, "size / 2"]
//     direction: [0, 0, 1]
//   - name: bottom_face
//     type: planar
//     origin: [0, 0, "-size / 2"]
//     direction: [0, 0, -1]
//   - name: side_face
//     type: planar
//     origin: ["size / 2", 0, 0]
//     direction: [1, 0, 0]
// SCADGEN_META_END

module cube_shape(size=10) {
    cube([size, size, size], center=true);
}
