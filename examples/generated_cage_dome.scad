// SCADGEN_META_BEGIN
// schema_version: 1
// template_id: cage_dome
// module_name: cage_dome
// description: Domed wire-frame top of the birdcage, curving upward from the top ring to a rounded apex
// category: decorative/birdcage
// tags: [cage, dome, birdcage, wireframe, canopy, roof]
// aliases: [cage top, dome top, birdcage roof, wire dome, canopy]
// keywords: [birdcage, dome, wire, rib, cage, roof, canopy, apex, curved, frame]
// length_param: height
// params:
//   - name: base_diam
//     type: float
//     default: 190.0
//     min: 20.0
//     max: 2000.0
//     unit: mm
//     description: Diameter of the base ring where the dome meets the top ring
//   - name: height
//     type: float
//     default: 90.0
//     min: 10.0
//     max: 1000.0
//     unit: mm
//     description: Height of the dome from base ring to apex
//   - name: rib_diam
//     type: float
//     default: 3.0
//     min: 0.5
//     max: 30.0
//     unit: mm
//     description: Diameter of the wire ribs and base ring
//   - name: rib_count
//     type: int
//     default: 16
//     min: 4
//     max: 64
//     unit: count
//     description: Number of vertical wire ribs around the dome
//   - name: ring_count
//     type: int
//     default: 2
//     min: 0
//     max: 10
//     unit: count
//     description: Number of horizontal bracing rings crossing the ribs
//   - name: apex_diam
//     type: float
//     default: 10.0
//     min: 2.0
//     max: 100.0
//     unit: mm
//     description: Diameter of the rounded apex cap where ribs converge
//   - name: dome_segments
//     type: int
//     default: 12
//     min: 3
//     max: 48
//     unit: count
//     description: Number of segments used to approximate the curved rib profile
//   - name: fn
//     type: int
//     default: 64
//     min: 16
//     max: 256
//     unit: count
//     description: Circle resolution
// connectors:
//   - name: bottom_face
//     type: planar
//     origin: [0, 0, 0]
//     direction: [0, 0, -1]
//   - name: top_face
//     type: planar
//     origin: [0, 0, "height"]
//     direction: [0, 0, 1]
// derived:
//   - base_radius: "base_diam / 2"
// constraints:
//   - check: "rib_diam < base_diam / 10"
//     message: "Rib diameter ({rib_diam}mm) is very thick relative to base diameter ({base_diam}mm)"
//     severity: warning
//   - check: "apex_diam < base_diam / 2"
//     message: "Apex diameter ({apex_diam}mm) should be smaller than half the base diameter ({base_diam}mm)"
//     severity: warning
//   - check: "height > 0 and base_diam > 0"
//     message: "Height and base diameter must both be positive"
//     severity: error
//   - check: "ring_count <= 10"
//     message: "Ring count ({ring_count}) is unusually high and may slow rendering"
//     severity: warning
// SCADGEN_META_END

module cage_dome(base_diam=190, height=90, rib_diam=3, rib_count=16,
                  ring_count=2, apex_diam=10, dome_segments=12, fn=64)
{
    $fn = fn;

    base_r = base_diam / 2;

    // Dome profile (quarter-circle-like curve) parameterized by t in [0,1]
    // t=0 -> base ring (r=base_r, z=0)
    // t=1 -> apex (r=0, z=height)
    function dome_radius(t) = base_r * cos(t * 90);
    function dome_z(t)      = height  * sin(t * 90);

    union() {

        // Vertical wire ribs curving from base ring up to apex
        for (i = [0 : rib_count - 1]) {
            rotate([0, 0, i * 360 / rib_count])
                cage_dome_rib(base_r, height, rib_diam, dome_segments);
        }

        // Horizontal bracing rings at intermediate heights
        if (ring_count > 0) {
            for (j = [1 : ring_count]) {
                t = j / (ring_count + 1);
                r = dome_radius(t);
                z = dome_z(t);
                translate([0, 0, z])
                    rotate_extrude()
                        translate([r, 0, 0])
                            circle(d = rib_diam * 0.85);
            }
        }

        // Rounded apex cap where all ribs converge
        translate([0, 0, height])
            sphere(d = apex_diam);

        // Base ring connecting to the top ring below
        rotate_extrude()
            translate([base_r, 0, 0])
                circle(d = rib_diam);
    }
}

// Single curved rib built from hulled sphere joints along the dome profile
module cage_dome_rib(base_r, height, rib_diam, segments)
{
    for (s = [0 : segments - 1]) {
        t0 = s / segments;
        t1 = (s + 1) / segments;

        p0 = [ base_r * cos(t0 * 90), 0, height * sin(t0 * 90) ];
        p1 = [ base_r * cos(t1 * 90), 0, height * sin(t1 * 90) ];

        hull() {
            translate(p0) sphere(d = rib_diam);
            translate(p1) sphere(d = rib_diam);
        }
    }
}

cage_dome();