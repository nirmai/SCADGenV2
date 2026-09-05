// SCADGEN_META_BEGIN
// schema_version: 1
// template_id: hex_bolt
// module_name: hex_bolt
// description: Hex head bolt with optional thread geometry
// category: fastener/bolt
// tags: [bolt, hex, fastener, screw, thread, metric]
// aliases: [bolt, hex bolt, cap screw, hex head bolt]
// keywords: [bolt, screw, hex, head, shaft, thread, pitch, fastener, M3, M4, M5, M6, M8, M10, M12, M16, M20]
// params:
//   - name: shaft_diam
//     type: float
//     default: 8.0
//     min: 1.6
//     max: 64.0
//     unit: mm
//     description: Shaft (nominal) diameter
//   - name: shaft_len
//     type: float
//     default: 30.0
//     min: 4.0
//     max: 500.0
//     unit: mm
//     description: Total shaft length (below head)
//   - name: head_flat
//     type: float
//     default: 13.0
//     min: 3.2
//     max: 90.0
//     unit: mm
//     description: Head across-flats dimension (S)
//   - name: head_height
//     type: float
//     default: 5.3
//     min: 1.1
//     max: 40.0
//     unit: mm
//     description: Head height (k)
//   - name: thread_pitch
//     type: float
//     default: 1.25
//     min: 0.2
//     max: 6.0
//     unit: mm
//     description: Thread pitch
//   - name: thread_len
//     type: float
//     default: 20.0
//     min: 0.0
//     max: 500.0
//     unit: mm
//     description: Threaded portion length
//   - name: add_threads
//     type: bool
//     default: true
//     description: Include thread geometry
//   - name: fn_bolt
//     type: int
//     default: 96
//     min: 16
//     max: 512
//     unit: count
//     description: Body resolution
//   - name: fn_thread
//     type: int
//     default: 64
//     min: 16
//     max: 512
//     unit: count
//     description: Thread resolution
// connectors:
//   - name: shaft_axis
//     type: axial
//     origin: [0, 0, 0]
//     direction: [0, 0, -1]
//     diameter_ref: shaft_diam
//   - name: head_top
//     type: planar
//     origin: [0, 0, 0]
//     direction: [0, 0, 1]
//   - name: thread_end
//     type: threaded
//     origin: [0, 0, 0]
//     direction: [0, 0, -1]
//     diameter_ref: shaft_diam
// SCADGEN_META_END

module hex_bolt(shaft_diam=8, shaft_len=30, head_flat=13, head_height=6,
                thread_pitch=1.25, thread_len=20, add_threads=true,
                fn_bolt=96, fn_thread=64)
{
    $fn = fn_bolt;
    head_d_circ = head_flat / cos(30);

    // Head
    translate([0,0,0])
        cylinder(h = head_height, d = head_d_circ, $fn = 6);

    // Shaft
    translate([0,0,-shaft_len])
        cylinder(h = shaft_len, d = shaft_diam);

    // Optional threads
    if (add_threads && thread_len > 0) {
        translate([0,0,-thread_len])
            hex_bolt_outer_thread(major_diam = shaft_diam,
                                  pitch = thread_pitch,
                                  length = thread_len,
                                  fn_thread = fn_thread);
    }
}

module hex_bolt_outer_thread(major_diam=8, pitch=1.25, length=10, fn_thread=64) {
    turns = length / pitch;
    minor_diam_raw = major_diam - 1.2 * pitch;
    minor_diam = (minor_diam_raw < 0.1) ? 0.1 : minor_diam_raw;
    thread_depth = (major_diam - minor_diam) / 2;
    minor_r = minor_diam / 2;

    $fn = fn_thread;
    cylinder(h = length, d = minor_diam);

    linear_extrude(height = length, twist = 360 * turns, center = false)
        translate([minor_r, 0])
            polygon(points = [
                [0, -pitch/2],
                [thread_depth, 0],
                [0,  pitch/2]
            ]);
}
