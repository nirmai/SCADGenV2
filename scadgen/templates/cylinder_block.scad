// SCADGEN_META_BEGIN
// schema_version: 1
// template_id: cylinder_block
// module_name: cylinder_block
// description: Cylinder block with inline bore pattern
// category: engine/block
// tags: [cylinder block, engine block, crankcase, bore, inline]
// aliases: [cylinder block, engine block, crankcase]
// keywords: [cylinder, block, engine, crankcase, bore, inline, deck, sump, wall, coolant]
// length_param: bore_diam
// params:
//   - name: bore_diam
//     type: float
//     default: 80.0
//     min: 20.0
//     max: 300.0
//     unit: mm
//     description: Cylinder bore diameter
//   - name: bore_count
//     type: int
//     default: 4
//     min: 1
//     max: 16
//     description: Number of cylinders
//   - name: bore_spacing
//     type: float
//     default: 90.0
//     min: 25.0
//     max: 400.0
//     unit: mm
//     description: Center-to-center bore spacing
//   - name: block_height
//     type: float
//     default: 200.0
//     min: 30.0
//     max: 800.0
//     unit: mm
//     description: Total block height (deck to sump face)
//   - name: block_width
//     type: float
//     default: 120.0
//     min: 30.0
//     max: 500.0
//     unit: mm
//     description: Block width (perpendicular to bore line)
//   - name: block_length
//     type: float
//     default: 400.0
//     min: 30.0
//     max: 2000.0
//     unit: mm
//     description: Block length (along bore line)
//   - name: wall_thickness
//     type: float
//     default: 8.0
//     min: 3.0
//     max: 30.0
//     unit: mm
//     description: Minimum wall thickness between bores and outside
//   - name: deck_height
//     type: float
//     default: 10.0
//     min: 3.0
//     max: 40.0
//     unit: mm
//     description: Deck surface thickness above bore tops
//   - name: fn
//     type: int
//     default: 96
//     min: 16
//     max: 512
//     unit: count
//     description: Circle resolution
// connectors:
//   - name: deck_face
//     type: planar
//     origin: ["block_length / 2", "block_width / 2", "block_height"]
//     direction: [0, 0, 1]
//   - name: sump_face
//     type: planar
//     origin: ["block_length / 2", "block_width / 2", 0]
//     direction: [0, 0, -1]
//   - name: bore_1_axis
//     type: axial
//     origin: ["(block_length - bore_spacing * (bore_count - 1)) / 2", "block_width / 2", "block_height"]
//     direction: [0, 0, 1]
//   - name: bore_2_axis
//     type: axial
//     origin: ["(block_length - bore_spacing * (bore_count - 1)) / 2 + bore_spacing", "block_width / 2", "block_height"]
//     direction: [0, 0, 1]
//   - name: bore_3_axis
//     type: axial
//     origin: ["(block_length - bore_spacing * (bore_count - 1)) / 2 + bore_spacing * 2", "block_width / 2", "block_height"]
//     direction: [0, 0, 1]
//   - name: bore_4_axis
//     type: axial
//     origin: ["(block_length - bore_spacing * (bore_count - 1)) / 2 + bore_spacing * 3", "block_width / 2", "block_height"]
//     direction: [0, 0, 1]
//   - name: crank_axis
//     type: axial
//     origin: [0, "block_width / 2", 0]
//     direction: [-1, 0, 0]
// constraints:
//   - check: "bore_spacing >= bore_diam + wall_thickness"
//     message: "Bore spacing ({bore_spacing}mm) too tight for bore diameter ({bore_diam}mm) plus wall ({wall_thickness}mm)"
//     severity: error
//   - check: "block_length >= bore_spacing * (bore_count - 1) + bore_diam + 2 * wall_thickness"
//     message: "Block length ({block_length}mm) too short to contain {bore_count} bores at {bore_spacing}mm spacing"
//     severity: error
//   - check: "block_width >= bore_diam + 2 * wall_thickness"
//     message: "Block width ({block_width}mm) too narrow for bore diameter ({bore_diam}mm) plus walls"
//     severity: error
//   - check: "block_height > bore_diam"
//     message: "Block height ({block_height}mm) shorter than bore diameter ({bore_diam}mm); stroke would be very limited"
//     severity: warning
//   - check: "deck_height >= 3"
//     message: "Deck height ({deck_height}mm) is very thin; may not seal reliably"
//     severity: warning
// SCADGEN_META_END

module cylinder_block(bore_diam=80, bore_count=4, bore_spacing=90,
                      block_height=200, block_width=120, block_length=400,
                      wall_thickness=8, deck_height=10, fn=96)
{
    $fn = fn;

    // First bore center X offset: center the bore pattern in the block
    first_bore_x = (block_length - bore_spacing * (bore_count - 1)) / 2;
    bore_depth = block_height - deck_height;

    difference() {
        // Outer block
        cube([block_length, block_width, block_height]);

        // Cylinder bores
        for (i = [0 : bore_count - 1]) {
            bore_x = first_bore_x + i * bore_spacing;
            translate([bore_x, block_width / 2, -0.1])
                cylinder(h = bore_depth + 0.1, d = bore_diam);
        }
    }
}
