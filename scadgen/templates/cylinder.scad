// SCADGEN_META_BEGIN
// schema_version: 1
// template_id: cylinder
// module_name: cylinder_shape
// description: Cylinder or tube (hollow when inner_diam > 0), with optional cutter mode
// category: primitive
// tags: [cylinder, tube, pipe, rod, shaft, hollow]
// aliases: [cylinder, tube, pipe]
// keywords: [cylinder, tube, pipe, hollow, bore, diameter, height, wall]
// length_param: height
// params:
//   - name: diam
//     type: float
//     default: 20.0
//     min: 0.1
//     max: 2000.0
//     unit: mm
//     description: Outer diameter
//   - name: height
//     type: float
//     default: 40.0
//     min: 0.1
//     max: 2000.0
//     unit: mm
//     description: Height
//   - name: center
//     type: bool
//     default: false
//     description: Center vertically on origin
//   - name: inner_diam
//     type: float
//     default: 0.0
//     min: 0.0
//     max: 2000.0
//     unit: mm
//     description: Inner diameter (0 = solid, >0 = tube)
//   - name: as_cutter
//     type: bool
//     default: false
//     description: Overshoot ends for boolean subtraction
//   - name: overshoot
//     type: float
//     default: 0.3
//     min: 0.0
//     max: 5.0
//     unit: mm
//     description: Overshoot amount in cutter mode
//   - name: fn
//     type: int
//     default: 96
//     min: 16
//     max: 512
//     unit: count
//     description: Circle resolution
// connectors:
//   - name: center_axis
//     type: axial
//     origin: [0, 0, "height / 2"]
//     direction: [0, 0, 1]
//     diameter_ref: diam
//   - name: top_face
//     type: planar
//     origin: [0, 0, "height"]
//     direction: [0, 0, 1]
//     diameter_ref: diam
//   - name: bottom_face
//     type: planar
//     origin: [0, 0, 0]
//     direction: [0, 0, -1]
//     diameter_ref: diam
// constraints:
//   - check: "inner_diam <= 0 or diam > inner_diam"
//     message: "Outer diameter ({diam}mm) must exceed inner diameter ({inner_diam}mm) for tube mode"
//     severity: error
// SCADGEN_META_END

module cylinder_shape(diam=20, height=40, center=false,
                      inner_diam=0, as_cutter=false,
                      overshoot=0.3, fn=96)
{
    $fn = fn;

    extra_h = as_cutter ? (height + 2*overshoot) : height;
    z_shift = as_cutter ? (center ? 0 : -overshoot) : 0;

    if (inner_diam <= 0) {
        translate([0,0,z_shift])
            cylinder(h = extra_h, d = diam, center = center);
    }
    else {
        difference() {
            translate([0,0,z_shift])
                cylinder(h = extra_h, d = diam, center = center);

            inner_extra_h = height + 2*overshoot;
            inner_shift   = center ? 0 : -overshoot;
            translate([0,0,inner_shift])
                cylinder(h = inner_extra_h, d = inner_diam, center = center);
        }
    }
}
