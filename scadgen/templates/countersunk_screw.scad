// SCADGEN_META_BEGIN
// schema_version: 1
// template_id: countersunk_screw
// module_name: countersunk_screw
// description: Countersunk (flat head) screw with hex socket drive (ISO 10642)
// category: fastener/bolt
// tags: [bolt, countersunk, flat head, fastener, screw, thread, metric, flush]
// aliases: [countersunk, flat head screw, flush bolt, csk screw, countersunk bolt]
// keywords: [bolt, screw, countersunk, flat, head, flush, socket, shaft, thread, pitch, fastener, ISO10642, M3, M4, M5, M6, M8, M10, M12]
// length_param: shaft_len
// params:
//   - name: shaft_diam
//     type: float
//     default: 6.0
//     min: 1.6
//     max: 24.0
//     unit: mm
//     description: Shaft (nominal) diameter
//   - name: shaft_len
//     type: float
//     default: 25.0
//     min: 3.0
//     max: 300.0
//     unit: mm
//     description: Total shaft length (below head)
//   - name: head_diam
//     type: float
//     default: 13.44
//     min: 3.0
//     max: 50.0
//     unit: mm
//     description: Head outer diameter (top surface)
//   - name: head_height
//     type: float
//     default: 3.72
//     min: 0.5
//     max: 15.0
//     unit: mm
//     description: Head height (cone depth)
//   - name: socket_size
//     type: float
//     default: 4.0
//     min: 1.0
//     max: 14.0
//     unit: mm
//     description: Hex socket (Allen key) across-flats size
//   - name: thread_pitch
//     type: float
//     default: 1.0
//     min: 0.2
//     max: 4.0
//     unit: mm
//     description: Thread pitch
//   - name: thread_len
//     type: float
//     default: 20.0
//     min: 0.0
//     max: 300.0
//     unit: mm
//     description: Threaded portion length
//   - name: add_threads
//     type: bool
//     default: true
//     description: Include thread geometry
//   - name: fn
//     type: int
//     default: 96
//     min: 16
//     max: 512
//     unit: count
//     description: Cylinder resolution
// connectors:
//   - name: shaft_axis
//     type: axial
//     origin: [0, 0, 0]
//     direction: [0, 0, -1]
//     diameter_ref: shaft_diam
//   - name: head_top
//     type: planar
//     origin: [0, 0, "head_height"]
//     direction: [0, 0, 1]
//   - name: thread_end
//     type: threaded
//     origin: [0, 0, "-shaft_len"]
//     direction: [0, 0, -1]
//     diameter_ref: shaft_diam
// constraints:
//   - check: "thread_len <= shaft_len"
//     message: "Thread length ({thread_len}mm) exceeds shaft length ({shaft_len}mm)"
//     severity: error
//   - check: "head_diam > shaft_diam"
//     message: "Head diameter ({head_diam}mm) must exceed shaft diameter ({shaft_diam}mm)"
//     severity: error
//   - check: "socket_size < head_diam * 0.8"
//     message: "Socket size ({socket_size}mm) is too large for head diameter ({head_diam}mm)"
//     severity: error
// SCADGEN_META_END

module countersunk_screw(shaft_diam=6, shaft_len=25, head_diam=13.44,
                          head_height=3.72, socket_size=4,
                          thread_pitch=1.0, thread_len=20,
                          add_threads=true, fn=96)
{
    $fn = fn;
    socket_circ = socket_size / cos(30);

    difference() {
        union() {
            // Conical countersunk head (tapers from head_diam at top to shaft_diam at bottom)
            cylinder(h = head_height, d1 = shaft_diam, d2 = head_diam);

            // Shaft
            translate([0, 0, -shaft_len])
                cylinder(h = shaft_len, d = shaft_diam);
        }

        // Hex socket cutout in the top of the head
        translate([0, 0, head_height - head_height * 0.6])
            cylinder(h = head_height * 0.6 + 0.1, d = socket_circ, $fn = 6);
    }

    // Optional threads
    if (add_threads && thread_len > 0) {
        translate([0, 0, -thread_len])
            csk_outer_thread(major_diam = shaft_diam,
                             pitch = thread_pitch,
                             length = thread_len,
                             fn = fn);
    }
}

module csk_outer_thread(major_diam=6, pitch=1.0, length=10, fn=64) {
    turns = length / pitch;
    minor_diam_raw = major_diam - 1.2 * pitch;
    minor_diam = (minor_diam_raw < 0.1) ? 0.1 : minor_diam_raw;
    thread_depth = (major_diam - minor_diam) / 2;
    minor_r = minor_diam / 2;

    $fn = fn;
    cylinder(h = length, d = minor_diam);

    linear_extrude(height = length, twist = 360 * turns, center = false)
        translate([minor_r, 0])
            polygon(points = [
                [0, -pitch/2],
                [thread_depth, 0],
                [0,  pitch/2]
            ]);
}
