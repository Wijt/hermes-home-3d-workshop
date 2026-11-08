# OpenSCAD syntax and orientation

OpenSCAD 2021.01 is the version this skill was tested with. Every snippet below renders cleanly with it.

## Core ideas
- A file is a description, not a program that runs step by step. Statements end with `;`.
- Variables are fixed. In one scope the LAST assignment wins everywhere, also above it. You cannot
  count up inside a `for`; build lists with list comprehensions instead.
- Modules make geometry (`module name(args) { ... }`, `children()` for what is passed in). Functions
  return values (`function f(x) = x * 2;`).
- Parametric first: every size is a named variable at the top. The tool sets top-level variables
  with `params` (`-D name=value`), so only top-level variables can be tuned without new code.

## Language
- Values: numbers, `true`/`false`, `"strings"`, lists `[1, 2, 3]`, `undef`. `p.x`, `p.y`, `p.z` read
  list items 0-2.
- Operators: `+ - * / % ^`, `< <= == != >= >`, `a && b`, `a || b`, `!a`, `cond ? a : b`.
- Special variables: `$fn` (segments of a circle), `$fa`, `$fs`, `$preview` (true only in the
  editor preview; the tool renders with `$preview = false`).
- Math: `abs sign sin cos tan asin acos atan atan2 floor round ceil ln log pow sqrt exp min max norm
  cross len`. Trigonometry uses degrees.
- Strings: `str(...)`, `len(s)`, `s[i]`, `chr`, `ord`, `search`.
- Checks: `is_num is_string is_list is_bool is_undef`.
- `let (a = 1, b = a * 2) ...`, `if (...) { } else { }`, `for (...)`, `intersection_for(...)`.
- Lists: `[for (i = [0:9]) i * 2]`, `[for (i = [0:9]) if (i % 2 == 0) i]`, `[each other_list]`,
  `concat(a, b)`.
- Ranges include the end: `[0:5]` is 0..5 (6 items). For `count` items use `[0:count-1]` and multiply
  by the spacing. `[0:spacing:count*spacing]` gives count + 1 items.
- Debug: `echo("label", value)` (the tool returns the first 20 `ECHO:` lines; an echo of one string
  comes back without its quotes), `assert(cond, "plain message")` (a failed assert stops the render;
  the tool returns it as the error). Put the report `echo` lines BEFORE the asserts: a failed assert
  stops everything after it, so its explaining numbers come back only when they are printed first.
- Floating point: `3 - 2.6 >= 0.4` is false (3 - 2.6 is 0.39999...). An assert exactly at its limit
  needs a small slack: `assert(wall >= 1.2 - 1e-6, ...)`.

## Geometry
- 3D: `cube([x, y, z], center = false)`, `sphere(d = ...)`, `cylinder(h, d = ...)`,
  `cylinder(h, d1 = ..., d2 = ...)` (cone), `polyhedron(points, faces)`.
- 2D: `square([x, y])`, `circle(d = ...)`, `polygon(points)`, `text("s", size, font, halign, valign)`.
- 2D to 3D: `linear_extrude(height, center, twist, scale)`, `rotate_extrude(angle)` (the 2D shape must
  sit at x >= 0).
- Transforms: `translate`, `rotate([x, y, z])` (degrees, applied x then y then z), `scale`, `mirror`,
  `color` (lost in the STL: previews are one colour), `offset(r = ...)` / `offset(delta = ...)` (2D).
- Booleans: `union`, `difference` (first child minus the rest), `intersection`, `hull`, `minkowski`.
- `render(convexity = N)` forces a full render of its children; `convexity` (2-10) only affects
  pictures.
- Files: `import("part.stl")`, `include <lib.scad>` (runs everything in it), `use <lib.scad>` (only
  its modules and functions). The tool accepts only relative paths inside the design's own folder.

## Orientation
- FRONT = towards the person = **-Y**. BACK = +Y. RIGHT = +X. LEFT = -X. TOP = +Z.
- Put the face that matters (opening, label, phone screen, drawer front) towards the front.
- Model the part the way it prints: the flat face on z = 0, nothing below z = 0. Say the print
  orientation in a comment ("print base down, no supports").
- `text()` is flat in the XY plane (lying on the table, read from above). It is NOT upright. A label
  on the front face needs a rotate:

```scad
// raised letters on a front face at y = front_y, centred at x = cx, z = cz
translate([cx, front_y + 0.01, cz]) rotate([90, 0, 0])
    linear_extrude(relief + 0.01)
        text("TOYS", size = 8, font = "DejaVu Sans:style=Bold", halign = "center", valign = "center");
```

  `rotate([90, 0, 0])` turns the letters upright and extrudes them towards -Y, out of the front face.
  For engraved letters, extrude into the face inside a `difference()`.
- `text()` is 2D: wrap it in `linear_extrude()` before combining it with 3D shapes.
- A face that leans back (a dock's sloped front, a wedge sign): turn the text by `90 - lean`, where
  `lean` is the face's angle back from vertical, computed from your derived values:

```scad
// engraved name on a front face that leans back `lean` degrees (a wedge: base d deep, h tall, top t deep)
d = 40; h = 30; t = 12; depth = 0.8; size = 7; cut = 1;
lean = atan2(d - t, h);                      // the front face's angle back from vertical
function face_y(z) = z * tan(lean);          // the front face's Y at height z
cz = h / 2;                                  // centre height of the letters
difference() {
    rotate([90, 0, 90]) linear_extrude(60) polygon([[0, 0], [d, 0], [d, h], [d - t, h]]);
    translate([30, face_y(cz), cz]) rotate([90 - lean, 0, 0]) translate([0, 0, -depth])
        linear_extrude(depth + cut) translate([0, -size / 2])
            text("SAM", size = size, font = "DejaVu Sans:style=Bold", halign = "center", valign = "baseline");
}
```
- Centre a name on its capital letters: a name with a descender ("g", "y") moves up with
  `valign = "center"`. Use `valign = "baseline"` and place the baseline yourself when it matters.

## Customizer comments
- `/* [Group name] */` starts a group of parameters. `/* [Hidden] */` hides what follows.
- `part = "all"; // [all, base, lid]` makes a drop-down; `wall = 2; // [1.2:0.4:4]` a slider.
- They are comments: OpenSCAD itself ignores them, but they document the allowed values.

## Presets that really work
A `preset` variable is only a comment unless the code branches on it:

```scad
preset = "medium"; // [small, medium, large]
function pick(s, m, l) = preset == "small" ? s : preset == "large" ? l : m;
length = pick(60, 100, 160);   // mm
```

## Several parts in one file

```scad
part = "all";        // [all, box, lid]
box = [60, 40, 25];  // outer size (mm)
wall = 2;            // (mm)
gap = 0.3;           // lid clearance per side (mm): loose fit
layout_gap = 8;      // space between the parts on the bed (mm): touching parts print fused
$fn = 48;

module the_box() difference() {
    cube(box);
    translate([wall, wall, wall]) cube(box - [2 * wall, 2 * wall, 0]);
}
module the_lid() {   // prints top face down
    cube([box.x, box.y, wall]);
    translate([wall + gap, wall + gap, 0]) cube([box.x - 2 * (wall + gap), box.y - 2 * (wall + gap), wall + 3]);
}

if (part == "box" || part == "all") the_box();
// the low lid goes in FRONT of the tall box (-Y): behind it, the box hides it in the iso picture
if (part == "lid" || part == "all") translate([0, part == "all" ? -(box.y + layout_gap) : 0, 0]) the_lid();
```

`home3d_design ... part=lid` renders only the lid. With `part = "all"` the tool's `bodies` must equal
the number of parts (here 2). One body less means two parts touch and would print as one.
- `from_version` keeps the earlier version's `part` too: pass `part=""` to get the whole design again.
- **Do the parts fit together?** Before the first print, check the assembled pair: in a second file
  in the same design (`use <box_v3.scad>` gives its modules), place the lid where it sits on the box
  and render `intersection() { the_box(); placed_lid(); }`. Empty (the tool says nothing to render)
  means no overlap; a body means they collide. Touching faces only are fine for a lid that rests.
- **A picture-only part** (the part next to a soap bar, a phone, the box it goes on, turned as it is
  used): make it a `part = "display"` and never upload it. Render only what prints when the person
  asked for one piece: a composite looks as if all of it would print.

## Curvy shapes without slow booleans
A union of many `rotate_extrude` / `hull` pieces can run for minutes (one ribbed wave band ran past 7
minutes and never finished). The tool stops a render after its time limit. For a swept or organic
shape, build ONE `polyhedron()` from rings of points: no booleans, renders in a second.

```scad
// rings: cross-sections along a path, each a list of n points [x, y, z]; every ring runs
// counter-clockwise around the direction of travel (right-hand rule).
// The side faces are TRIANGLES: on a curved path the four corners of a quad are not in one plane,
// and a boolean with such a sweep stops with "CGAL error ... assertion violation".
module sweep(rings) {
    m = len(rings); n = len(rings[0]);
    pts = [for (r = rings) each r];
    sides = [for (i = [0:m-2]) for (j = [0:n-1])
             let (a = i*n + j, b = (i+1)*n + j, c = (i+1)*n + (j+1)%n, d = i*n + (j+1)%n)
             each [[a, b, c], [a, c, d]]];
    caps = [[for (j = [0:n-1]) j], [for (j = [n-1:-1:0]) (m-1)*n + j]];
    polyhedron(points = pts, faces = concat(sides, caps), convexity = 4);
}

// A wavy band: an oval cross-section swept along a sine path (soap dish, bracelet, rail).
L = 90; amp = 8; waves = 2; w = 10; h = 6; seg = 60; k = 16;
function section(x, y) = [for (a = [0:360/k:359.9]) [x, y + w/2*cos(a), h/2 + h/2*sin(a)]];
sweep([for (i = [0:seg]) let(x = i*L/seg) section(x, amp*sin(360*waves*x/L))]);
```

- A lone `polyhedron()` skips CGAL: it renders in about a second, and `simple` comes back null
  (nothing was combined). The tool still measures it: `inverted: true` (a warning "inside out") means
  the rings run the wrong way, so reverse the order of the points in each ring; `bodies` comes from
  the mesh.
- Combine a sweep with other shapes (a flat cut, a hole, a second part) only when the part needs it:
  with triangle faces it works and `simple` is checked, but the render takes about 10 times longer
  (1 s became 13 s for a soap dish).
- Count the features in the person's photo (waves, ribs, legs) and make the count a parameter.

## Speed
- `minkowski()` is very slow. Round corners with `hull()` of corner cylinders, or with
  `offset(r = R) offset(delta = -R)` on a 2D outline before `linear_extrude`.
- Build profiles in 2D (`hull`, `offset`, `polygon`) and extrude once; 2D work is cheap.
- `$fn` 48-64 is enough for printing; 96+ only for large visible circles.
- Hundreds of small `hull()` or `sphere()` pieces in one union are slow: make one polyhedron instead.
