// Label box: open storage box with a raised label on the front wall.
// Rendered by home3d.customize.render_template; every parameter can be overridden with -D.
// Units: mm. Print open side up.

text = "Box";
width = 60;     // outer X
depth = 40;     // outer Y
height = 30;    // outer Z
wall = 2;
font_size = 8;

text_depth = 0.8;    // how far the letters stand out of the front wall
corner_radius = 3;
font = "Liberation Sans:style=Bold";
$fn = 48;

module rounded_block(w, d, h, r) {
    rr = max(0.01, min(r, w / 2 - 0.01, d / 2 - 0.01));
    linear_extrude(height = h)
        offset(r = rr) offset(delta = -rr) square([w, d]);
}

union() {
    difference() {
        rounded_block(width, depth, height, corner_radius);
        translate([wall, wall, wall])
            rounded_block(width - 2 * wall, depth - 2 * wall, height, corner_radius - wall);
    }
    // front face is y = 0; letters read upright when looking at the front
    translate([width / 2, 0.01, height / 2])
        rotate([90, 0, 0])
            linear_extrude(height = text_depth + 0.01)
                text(text, size = font_size, font = font, halign = "center", valign = "center");
}
