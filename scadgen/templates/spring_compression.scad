// SCADGEN_META_BEGIN
// schema_version: 1
// template_id: spring_compression
// module_name: spring_compression
// description: Helical compression spring with configurable coil geometry
// category: mechanical/spring
// tags: [spring, coil, compression, helical, wire, mechanical]
// aliases: [compression spring, coil spring, helical spring, spring]
// keywords: [spring, coil, compression, helical, wire, stiffness, free, length, active, coils, end, closed, ground]
// length_param: free_length
// params:
//   - name: wire_diam
//     type: float
//     default: 2.0
//     min: 0.2
//     max: 25.0
//     unit: mm
//     description: Wire diameter
//   - name: coil_diam
//     type: float
//     default: 20.0
//     min: 2.0
//     max: 500.0
//     unit: mm
//     description: Mean coil diameter (center of wire to center of wire)
//   - name: free_length
//     type: float
//     default: 50.0
//     min: 5.0
//     max: 1000.0
//     unit: mm
//     description: Free length (uncompressed)
//   - name: active_coils
//     type: int
//     default: 8
//     min: 2
//     max: 100
//     unit: count
//     description: Number of active coils
//   - name: end_type
//     type: int
//     default: 0
//     min: 0
//     max: 2
//     description: End style (0=open, 1=closed, 2=closed and ground)
//   - name: fn
//     type: int
//     default: 64
//     min: 12
//     max: 256
//     unit: count
//     description: Points per coil turn
// connectors:
//   - name: top_end
//     type: planar
//     origin: [0, 0, "free_length"]
//     direction: [0, 0, 1]
//   - name: bottom_end
//     type: planar
//     origin: [0, 0, 0]
//     direction: [0, 0, -1]
// constraints:
//   - check: "wire_diam < coil_diam / 2"
//     message: "Wire diameter ({wire_diam}mm) must be less than half the coil diameter ({coil_diam}mm)"
//     severity: error
//   - check: "free_length > wire_diam * (active_coils + 2)"
//     message: "Free length ({free_length}mm) too short for {active_coils} active coils of {wire_diam}mm wire"
//     severity: error
//   - check: "active_coils >= 3"
//     message: "Fewer than 3 active coils ({active_coils}) may give inconsistent spring rate"
//     severity: warning
// derived:
//   - spring_index: "coil_diam / wire_diam"
//   - pitch: "free_length / active_coils"
// SCADGEN_META_END

module spring_compression(wire_diam=2, coil_diam=20, free_length=50,
                          active_coils=8, end_type=0, fn=64)
{
    total_coils = (end_type == 0) ? active_coils
                : (end_type == 1) ? active_coils + 2
                : active_coils + 2;
    pitch = free_length / total_coils;
    r_coil = coil_diam / 2;
    r_wire = wire_diam / 2;
    total_angle = total_coils * 360;
    steps = total_coils * fn;

    // Build coil as a sequence of spheres along the helix
    union() {
        for (i = [0 : steps]) {
            a = i / steps * total_angle;
            z = i / steps * free_length;
            translate([r_coil * cos(a), r_coil * sin(a), z])
                sphere(r = r_wire, $fn = max(12, fn / 4));
        }

        // Flat ends for closed/ground types
        if (end_type >= 1) {
            // Bottom dead coil
            for (i = [0 : fn]) {
                a = i / fn * 360;
                translate([r_coil * cos(a), r_coil * sin(a), 0])
                    sphere(r = r_wire, $fn = max(12, fn / 4));
            }
            // Top dead coil
            for (i = [0 : fn]) {
                a = i / fn * 360;
                translate([r_coil * cos(a), r_coil * sin(a), free_length])
                    sphere(r = r_wire, $fn = max(12, fn / 4));
            }
        }

        // Ground flat faces
        if (end_type == 2) {
            translate([0, 0, -r_wire / 2])
                cylinder(h = r_wire, d = coil_diam + wire_diam, $fn = fn);
            translate([0, 0, free_length - r_wire / 2])
                cylinder(h = r_wire, d = coil_diam + wire_diam, $fn = fn);
        }
    }
}
