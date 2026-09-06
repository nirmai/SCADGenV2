// SCADGEN_META_BEGIN
// schema_version: 1
// template_id: cylinder_head
// module_name: cylinder_head
// description: Cylinder head with combustion chamber recesses and valve guide bores
// category: engine/block
// tags: [cylinder head, head, engine, combustion, valve, gasket]
// aliases: [cylinder head]
// keywords: [cylinder, head, engine, combustion, chamber, valve, guide, bore, gasket, deck, port]
// length_param: height
// params:
//   - name: length
//     type: float
//     default: 400.0
//     min: 30.0
//     max: 2000.0
//     unit: mm
//     description: Head length (along bore line, matches block)
//   - name: width
//     type: float
//     default: 120.0
//     min: 30.0
//     max: 500.0
//     unit: mm
//     description: Head width (matches block width)
//   - name: height
//     type: float
//     default: 50.0
//     min: 15.0
//     max: 200.0
//     unit: mm
//     description: Head total height
//   - name: bore_diam
//     type: float
//     default: 80.0
//     min: 20.0
//     max: 300.0
//     unit: mm
//     description: Combustion chamber bore diameter (matches block bore)
//   - name: bore_count
//     type: int
//     default: 4
//     min: 1
//     max: 16
//     description: Number of cylinders (matches block)
//   - name: bore_spacing
//     type: float
//     default: 90.0
//     min: 25.0
//     max: 400.0
//     unit: mm
//     description: Center-to-center bore spacing (matches block)
//   - name: valves_per_cyl
//     type: int
//     default: 2
//     min: 1
//     max: 5
//     description: Number of valve guide bores per cylinder
//   - name: valve_bore_diam
//     type: float
//     default: 8.0
//     min: 3.0
//     max: 30.0
//     unit: mm
//     description: Valve guide bore diameter
//   - name: valve_angle
//     type: float
//     default: 0.0
//     min: 0.0
//     max: 30.0
//     unit: deg
//     description: Valve cant angle from vertical
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
//     origin: ["length / 2", "width / 2", 0]
//     direction: [0, 0, -1]
//   - name: top_face
//     type: planar
//     origin: ["length / 2", "width / 2", "height"]
//     direction: [0, 0, 1]
//   - name: valve_bore_1
//     type: axial
//     origin: ["(length - bore_spacing * (bore_count - 1)) / 2", "width / 2", 0]
//     direction: [0, 0, 1]
// constraints:
//   - check: "valve_bore_diam < bore_diam / 2"
//     message: "Valve bore ({valve_bore_diam}mm) must be less than half the bore diameter ({bore_diam}mm)"
//     severity: error
//   - check: "valves_per_cyl * valve_bore_diam < bore_diam * 0.8"
//     message: "Total valve bore width ({valves_per_cyl} x {valve_bore_diam}mm) exceeds 80% of bore ({bore_diam}mm)"
//     severity: error
//   - check: "bore_spacing * (bore_count - 1) + bore_diam < length"
//     message: "Bore pattern ({bore_count} at {bore_spacing}mm spacing) exceeds head length ({length}mm)"
//     severity: error
//   - check: "bore_diam < width"
//     message: "Bore diameter ({bore_diam}mm) exceeds head width ({width}mm)"
//     severity: error
//   - check: "height >= 20"
//     message: "Head height ({height}mm) is very thin; may not have room for valve guides and ports"
//     severity: warning
// SCADGEN_META_END

module cylinder_head(length=400, width=120, height=50,
                     bore_diam=80, bore_count=4, bore_spacing=90,
                     valves_per_cyl=2, valve_bore_diam=8,
                     valve_angle=0, fn=96)
{
    $fn = fn;

    // Center bore pattern in head length
    first_bore_x = (length - bore_spacing * (bore_count - 1)) / 2;
    chamber_depth = 5;  // combustion chamber recess depth

    difference() {
        // Main head slab
        cube([length, width, height]);

        // Combustion chamber recesses (bottom face)
        for (i = [0 : bore_count - 1]) {
            bore_x = first_bore_x + i * bore_spacing;
            translate([bore_x, width / 2, -0.1])
                cylinder(h = chamber_depth + 0.1, d = bore_diam * 0.9);
        }

        // Valve guide bores (through-holes from top)
        for (i = [0 : bore_count - 1]) {
            bore_x = first_bore_x + i * bore_spacing;
            for (v = [0 : valves_per_cyl - 1]) {
                // Space valves evenly across the bore diameter
                valve_offset = (v - (valves_per_cyl - 1) / 2) * bore_diam * 0.3;
                translate([bore_x + valve_offset, width / 2, -0.1])
                    rotate([valve_angle, 0, 0])
                        cylinder(h = height + 0.2, d = valve_bore_diam);
            }
        }
    }
}
