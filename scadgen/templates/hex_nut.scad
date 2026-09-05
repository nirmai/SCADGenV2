// SCADGEN_META_BEGIN
// schema_version: 1
// template_id: hex_nut
// module_name: hex_nut
// description: Hex nut with optional internal thread geometry
// category: fastener/nut
// tags: [nut, hex, fastener, thread, metric]
// aliases: [nut, hex nut]
// keywords: [nut, hex, thread, pitch, fastener, M3, M4, M5, M6, M8, M10, M12, M16, M20]
// params:
//   - name: thread_diam
//     type: float
//     default: 8.0
//     min: 1.6
//     max: 64.0
//     unit: mm
//     description: Nominal thread diameter
//   - name: pitch
//     type: float
//     default: 1.25
//     min: 0.2
//     max: 6.0
//     unit: mm
//     description: Thread pitch
//   - name: flat
//     type: float
//     default: 13.0
//     min: 3.2
//     max: 90.0
//     unit: mm
//     description: Across-flats dimension (S)
//   - name: thickness
//     type: float
//     default: 6.5
//     min: 1.0
//     max: 40.0
//     unit: mm
//     description: Nut height (m)
//   - name: clearance
//     type: float
//     default: 0.25
//     min: 0.0
//     max: 2.0
//     unit: mm
//     description: Bore clearance added to thread diameter
//   - name: add_threads
//     type: bool
//     default: true
//     description: Include internal thread geometry
//   - name: fn_nut
//     type: int
//     default: 96
//     min: 16
//     max: 512
//     unit: count
//     description: Body resolution
//   - name: fn_thread
//     type: int
//     default: 96
//     min: 16
//     max: 512
//     unit: count
//     description: Thread resolution
// connectors:
//   - name: thread_axis
//     type: threaded
//     origin: [0, 0, 0]
//     direction: [0, 0, 1]
//     diameter_ref: thread_diam
//   - name: top_face
//     type: planar
//     origin: [0, 0, 0]
//     direction: [0, 0, 1]
//   - name: bottom_face
//     type: planar
//     origin: [0, 0, 0]
//     direction: [0, 0, -1]
// SCADGEN_META_END

module hex_nut(thread_diam=8, pitch=1.25, flat=13, thickness=6.5,
               clearance=0.25, add_threads=true, fn_nut=96, fn_thread=96)
{
    hex_d_circ = flat / cos(30);
    $fn = fn_nut;

    difference() {
        cylinder(h = thickness, d = hex_d_circ, $fn = 6);

        if (add_threads) {
            hex_nut_thread_void(major_diam = thread_diam + clearance,
                                pitch = pitch,
                                length = thickness,
                                fn_thread = fn_thread);
        } else {
            translate([0,0,-0.2]) cylinder(h = thickness + 0.4, d = thread_diam + clearance);
        }
    }
}

module hex_nut_thread_void(major_diam=8.25, pitch=1.25, length=6.5, fn_thread=96)
{
    eps = 0.3;
    turns = length / pitch;

    minor_diam_raw = major_diam - 1.2 * pitch;
    minor_diam = (minor_diam_raw < 0.1) ? 0.1 : minor_diam_raw;
    thread_depth = (major_diam - minor_diam) / 2;
    minor_r = minor_diam / 2;

    $fn = fn_thread;

    translate([0,0,-eps])
    union() {
        cylinder(h = length + 2*eps, d = minor_diam);
        linear_extrude(height = length + 2*eps, twist = 360 * turns, convexity = 10)
            translate([minor_r, 0])
                polygon(points = [
                    [0, -pitch/2],
                    [thread_depth, 0],
                    [0,  pitch/2]
                ]);
    }
}
