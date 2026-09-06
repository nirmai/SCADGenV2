// SCADGEN_META_BEGIN
// schema_version: 1
// template_id: set_screw
// module_name: set_screw
// description: Set screw / grub screw with hex socket drive (ISO 4029)
// category: fastener/bolt
// tags: [set screw, grub screw, fastener, screw, thread, metric, headless]
// aliases: [set screw, grub screw, headless screw, socket set screw]
// keywords: [set, grub, screw, headless, socket, Allen, thread, pitch, fastener, ISO4029, collar, shaft, M3, M4, M5, M6, M8, M10, M12]
// length_param: length
// params:
//   - name: shaft_diam
//     type: float
//     default: 6.0
//     min: 1.6
//     max: 24.0
//     unit: mm
//     description: Screw (nominal) diameter
//   - name: length
//     type: float
//     default: 10.0
//     min: 2.0
//     max: 100.0
//     unit: mm
//     description: Total screw length
//   - name: socket_size
//     type: float
//     default: 3.0
//     min: 0.7
//     max: 14.0
//     unit: mm
//     description: Hex socket (Allen key) across-flats size
//   - name: socket_depth
//     type: float
//     default: 3.0
//     min: 0.5
//     max: 15.0
//     unit: mm
//     description: Hex socket depth
//   - name: point_type
//     type: int
//     default: 0
//     min: 0
//     max: 3
//     description: Point style (0=flat, 1=cup, 2=cone, 3=dog)
//   - name: point_len
//     type: float
//     default: 2.0
//     min: 0.5
//     max: 20.0
//     unit: mm
//     description: Point feature length/depth
//   - name: thread_pitch
//     type: float
//     default: 1.0
//     min: 0.2
//     max: 4.0
//     unit: mm
//     description: Thread pitch
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
//   - name: drive_end
//     type: planar
//     origin: [0, 0, "length"]
//     direction: [0, 0, 1]
//   - name: point_end
//     type: axial
//     origin: [0, 0, 0]
//     direction: [0, 0, -1]
//     diameter_ref: shaft_diam
// constraints:
//   - check: "socket_size < shaft_diam"
//     message: "Socket size ({socket_size}mm) must be smaller than screw diameter ({shaft_diam}mm)"
//     severity: error
//   - check: "socket_depth < length"
//     message: "Socket depth ({socket_depth}mm) must be less than total length ({length}mm)"
//     severity: error
//   - check: "point_len < length - socket_depth"
//     message: "Point length ({point_len}mm) leaves no room for the body"
//     severity: error
// SCADGEN_META_END

module set_screw(shaft_diam=6, length=10, socket_size=3, socket_depth=3,
                  point_type=0, point_len=2, thread_pitch=1.0,
                  add_threads=true, fn=96)
{
    $fn = fn;
    socket_circ = socket_size / cos(30);
    r = shaft_diam / 2;

    difference() {
        union() {
            // Main body
            cylinder(h = length, d = shaft_diam);

            // Point geometry at bottom (z=0 end)
            // (points are handled as modifications below)
        }

        // Hex socket at the top
        translate([0, 0, length - socket_depth])
            cylinder(h = socket_depth + 0.1, d = socket_circ, $fn = 6);

        // Point cutouts
        if (point_type == 1) {
            // Cup point: concave dimple
            translate([0, 0, -0.01])
                cylinder(h = point_len, d1 = shaft_diam * 0.5, d2 = shaft_diam * 0.8);
        }
        if (point_type == 2) {
            // Cone point: trim to cone (remove cylinder below cone)
            translate([0, 0, -0.01])
                difference() {
                    cylinder(h = point_len + 0.02, d = shaft_diam + 0.1);
                    cylinder(h = point_len + 0.02, d1 = 0, d2 = shaft_diam);
                }
        }
    }

    // Dog point: protruding reduced-diameter cylinder
    if (point_type == 3) {
        translate([0, 0, -point_len])
            cylinder(h = point_len, d = shaft_diam * 0.6);
    }

    // Optional threads on the main body
    if (add_threads) {
        set_screw_thread(major_diam = shaft_diam,
                         pitch = thread_pitch,
                         length = length,
                         fn = fn);
    }
}

module set_screw_thread(major_diam=6, pitch=1.0, length=10, fn=64) {
    turns = length / pitch;
    minor_diam_raw = major_diam - 1.2 * pitch;
    minor_diam = (minor_diam_raw < 0.1) ? 0.1 : minor_diam_raw;
    thread_depth = (major_diam - minor_diam) / 2;
    minor_r = minor_diam / 2;

    $fn = fn;

    linear_extrude(height = length, twist = 360 * turns, center = false)
        translate([minor_r, 0])
            polygon(points = [
                [0, -pitch/2],
                [thread_depth, 0],
                [0,  pitch/2]
            ]);
}
