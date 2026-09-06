// SCADGEN_META_BEGIN
// schema_version: 1
// template_id: socket_head_cap_screw
// module_name: socket_head_cap_screw
// description: Socket head cap screw (ISO 4762 / DIN 912) with hex socket drive
// category: fastener/bolt
// tags: [bolt, socket, shcs, allen, fastener, screw, thread, metric, cap screw]
// aliases: [socket head, shcs, allen bolt, allen screw, cap screw, socket cap screw, socket bolt]
// keywords: [bolt, screw, socket, allen, hex, cap, head, shaft, thread, pitch, fastener, SHCS, DIN912, ISO4762, M3, M4, M5, M6, M8, M10, M12, M16, M20]
// length_param: shaft_len
// params:
//   - name: shaft_diam
//     type: float
//     default: 8.0
//     min: 1.6
//     max: 36.0
//     unit: mm
//     description: Shaft (nominal) diameter
//   - name: shaft_len
//     type: float
//     default: 30.0
//     min: 3.0
//     max: 500.0
//     unit: mm
//     description: Total shaft length (below head)
//   - name: head_diam
//     type: float
//     default: 13.0
//     min: 3.0
//     max: 60.0
//     unit: mm
//     description: Head diameter
//   - name: head_height
//     type: float
//     default: 8.0
//     min: 1.5
//     max: 30.0
//     unit: mm
//     description: Head height
//   - name: socket_size
//     type: float
//     default: 6.0
//     min: 1.0
//     max: 22.0
//     unit: mm
//     description: Hex socket (Allen key) across-flats size
//   - name: socket_depth
//     type: float
//     default: 4.0
//     min: 0.5
//     max: 15.0
//     unit: mm
//     description: Hex socket depth
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
//   - check: "socket_size < head_diam"
//     message: "Socket size ({socket_size}mm) must be smaller than head diameter ({head_diam}mm)"
//     severity: error
//   - check: "socket_depth <= head_height"
//     message: "Socket depth ({socket_depth}mm) exceeds head height ({head_height}mm)"
//     severity: error
// SCADGEN_META_END

module socket_head_cap_screw(shaft_diam=8, shaft_len=30, head_diam=13,
                              head_height=8, socket_size=6, socket_depth=4,
                              thread_pitch=1.25, thread_len=20,
                              add_threads=true, fn=96)
{
    $fn = fn;
    socket_circ = socket_size / cos(30);

    difference() {
        union() {
            // Cylindrical head
            cylinder(h = head_height, d = head_diam);

            // Shaft
            translate([0, 0, -shaft_len])
                cylinder(h = shaft_len, d = shaft_diam);
        }

        // Hex socket cutout
        translate([0, 0, head_height - socket_depth])
            cylinder(h = socket_depth + 0.1, d = socket_circ, $fn = 6);
    }

    // Optional threads
    if (add_threads && thread_len > 0) {
        translate([0, 0, -thread_len])
            shcs_outer_thread(major_diam = shaft_diam,
                              pitch = thread_pitch,
                              length = thread_len,
                              fn = fn);
    }
}

module shcs_outer_thread(major_diam=8, pitch=1.25, length=10, fn=64) {
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
