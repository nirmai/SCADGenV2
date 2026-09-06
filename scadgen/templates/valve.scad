// SCADGEN_META_BEGIN
// schema_version: 1
// template_id: valve
// module_name: valve
// description: Poppet valve with stem and mushroom head (intake/exhaust)
// category: engine/valve_train
// tags: [valve, poppet, intake, exhaust, engine, stem, head]
// aliases: [valve, poppet valve, intake valve, exhaust valve, engine valve]
// keywords: [valve, poppet, intake, exhaust, engine, stem, head, seat, margin, guide]
// length_param: stem_len
// params:
//   - name: stem_diam
//     type: float
//     default: 6.0
//     min: 3.0
//     max: 20.0
//     unit: mm
//     description: Valve stem diameter
//   - name: stem_len
//     type: float
//     default: 100.0
//     min: 20.0
//     max: 300.0
//     unit: mm
//     description: Valve stem length
//   - name: head_diam
//     type: float
//     default: 30.0
//     min: 10.0
//     max: 80.0
//     unit: mm
//     description: Valve head (tulip) diameter
//   - name: head_angle
//     type: float
//     default: 45.0
//     min: 20.0
//     max: 60.0
//     unit: deg
//     description: Seat face angle
//   - name: seat_width
//     type: float
//     default: 1.5
//     min: 0.5
//     max: 5.0
//     unit: mm
//     description: Seat contact band width
//   - name: margin_width
//     type: float
//     default: 1.0
//     min: 0.3
//     max: 4.0
//     unit: mm
//     description: Margin (flat rim) width below seat
//   - name: fn
//     type: int
//     default: 96
//     min: 16
//     max: 512
//     unit: count
//     description: Circle resolution
// connectors:
//   - name: stem_axis
//     type: axial
//     origin: [0, 0, 0]
//     direction: [0, 0, 1]
//   - name: head_face
//     type: planar
//     origin: [0, 0, 0]
//     direction: [0, 0, -1]
//   - name: stem_tip
//     type: axial
//     origin: [0, 0, "margin_width + stem_len"]
//     direction: [0, 0, 1]
// constraints:
//   - check: "head_diam > stem_diam"
//     message: "Valve head diameter ({head_diam}mm) must exceed stem diameter ({stem_diam}mm)"
//     severity: error
//   - check: "seat_width < (head_diam - stem_diam) / 2"
//     message: "Seat width ({seat_width}mm) exceeds available head annulus ({head_diam}mm head, {stem_diam}mm stem)"
//     severity: error
//   - check: "head_diam >= stem_diam * 2"
//     message: "Head diameter ({head_diam}mm) is less than 2x stem ({stem_diam}mm); atypical proportions"
//     severity: warning
// SCADGEN_META_END

module valve(stem_diam=6, stem_len=100, head_diam=30,
             head_angle=45, seat_width=1.5, margin_width=1.0,
             fn=96)
{
    $fn = fn;
    stem_r = stem_diam / 2;
    head_r = head_diam / 2;

    // Conical transition height from stem to head
    cone_h = (head_r - stem_r) / tan(head_angle);
    margin_h = margin_width;

    // Stem: cylinder from top of head upward
    translate([0, 0, margin_h + cone_h])
        cylinder(h = stem_len, d = stem_diam);

    // Conical seat face: from stem diameter up to head diameter
    translate([0, 0, margin_h])
        cylinder(h = cone_h, d1 = head_diam, d2 = stem_diam);

    // Margin: flat cylindrical rim at the bottom of the head
    cylinder(h = margin_h, d = head_diam);
}
