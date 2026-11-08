// Name tag: raised text on a rounded plate, with a key-ring hole on the left.
// Rendered by home3d.customize.render_template; every parameter can be overridden with -D.
// Units: mm. Print flat, text up; the plate is sturdy enough for auto-eject at >= 3 mm total height.

text = "Sam";
width = 80;
height = 25;
thickness = 3;
font_size = 10;

text_height = 1.2;   // how far the letters stand above the plate
corner_radius = 4;
hole = true;         // key-ring hole
hole_d = 4;
font = "Liberation Sans:style=Bold";
$fn = 48;

hole_margin = hole ? hole_d + 3 : 0;

module rounded_plate(w, h, t, r) {
    rr = max(0.01, min(r, h / 2 - 0.01, w / 2 - 0.01));
    linear_extrude(height = t)
        offset(r = rr) offset(delta = -rr) square([w, h]);
}

union() {
    difference() {
        rounded_plate(width, height, thickness, corner_radius);
        if (hole)
            translate([hole_d / 2 + 2.5, height / 2, -1])
                cylinder(d = hole_d, h = thickness + 2);
    }
    translate([hole_margin + (width - hole_margin) / 2, height / 2, thickness - 0.01])
        linear_extrude(height = text_height + 0.01)
            text(text, size = font_size, font = font, halign = "center", valign = "center");
}
