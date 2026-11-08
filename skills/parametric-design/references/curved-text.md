# Names and text: flat faces, round bodies, glue-on strips, inlays

Names are the most common personal touch, and the most common source of a reprint: a misheard
name, a missing Turkish letter, a word that reads backwards on a curve, a seam right through it.

## Before you draw
- Get the name **in writing, in capitals,** and spell it back. Voice transcripts mangle names.
- Watch the special letters (Turkish I/İ, Ş, Ğ, Ç, Ö, Ü) and use a font that has them:
  `"DejaVu Sans:style=Bold"` has them and is on almost every Linux machine. Look at the preview: a
  missing letter shows as a gap or a box.
- Confirm three things before slicing: text, colours, size. Re-render every time one changes, and
  wait for an OK on the new picture.
- A simple key-ring tag or a box with a label: the ready templates (`home3d_customize
  template=name_tag` or `label_box`) are faster than a design.

## Text on a flat face
- `text()` lies flat in XY. On a front face it needs `rotate([90, 0, 0])` (snippet in
  `openscad-syntax.md`). Face the name to the front (-Y) and keep the back plain for the seam.
- Raised letters (emboss) 0.6-1.2 mm; cut letters (engrave) 0.6-1 mm deep, never deeper than the wall
  allows. On a thin wall (dividers can be 0.8 mm) emboss instead of engraving.
- Letters at least 6-8 mm tall for a name people read from a distance; strokes 0.8 mm or more.
- Text on a vertical face prints without supports. Text on the top face is crisp too; text on the
  bottom face (printed face down) takes the plate's texture.
- **Check the relief at an angle.** A straight-on picture hides 0.6 mm of relief and the name looks
  missing. The `iso` preview shows it; the `front` view does not.

## Text on a round body (box, jar, cup)
1. Use the real radius at the text height: a parameter you know from your own design, or a measurement.
2. Put the text at the widest or middle height, not on the foot. A name on the foot looks too low
   and hides in the base's shadow.
3. **Wrap, don't plate.** Place each letter by angle and cut it to a thin shell. A flat text plate
   pushed onto a curve distorts or cuts off the END letters (the family noticed at once).
4. Spacing: about 9-9.5 degrees per letter for 8 mm letters at a 47 mm radius; scale it with letter
   size and radius.
5. **Sign check:** `(i - (n-1)/2) * step` reads left to right from the front (-Y). The opposite sign
   prints the name backwards. Look at every preview and read the word.

## A glue-on strip for an object that already exists
Adding a name to a box that is already printed (or bought) costs a full reprint of the box. **Offer
a glue-on strip by default:** a curved band, inner radius = the box's radius, 1 mm thick, letters
1.2 mm proud, 2.5 mm of band above and below. It weighs about 1 g and prints in minutes, standing as
modelled, without supports. Make one strip per box size, and ask which box.

```scad
// Glue-on name strip for a round box that is already printed.
name    = "SAM";     // capitals, confirmed in writing
r_body  = 47;        // the box's outer radius where the strip goes (mm), measured
h       = 8;         // letter size (mm): DejaVu Sans Bold capitals are about h tall
relief  = 1.2;       // letters stand out of the strip (mm)
band_t  = 1;         // strip thickness (mm)
margin  = 2.5;       // strip above and below the capitals (mm): at least 0.3 * h for dots and cedillas
step    = 9.5;       // degrees between letter centres (about 9.5 for 8 mm letters at r 47)
font    = "DejaVu Sans:style=Bold";
$fn = 180;

n   = len(name);
arc = (n + 1) * step;  // strip length in degrees: the letters plus a letter of margin in all
band_h = h + 2 * margin;
assert(margin >= 0.3 * h - 1e-6, "margin under 0.3 * h: the dots of Ü, İ, Ö and the tail of Ş, Ç leave the strip");

module strip() rotate([0, 0, -90 - arc / 2]) rotate_extrude(angle = arc)
    translate([r_body, 0]) square([band_t, band_h]);

// Each letter placed by angle and cut to a thin shell, so it follows the curve.
// (i - (n-1)/2) * step reads left to right from the front (-Y); the other sign mirrors the name.
// All letters share ONE baseline (valign = "baseline", moved down by half the capital height):
// valign = "center" centres each letter on its own box, so Ş rises and Ü sinks by about 1 mm.
module letters() intersection() {
    difference() {
        cylinder(r = r_body + band_t + relief, h = band_h);
        translate([0, 0, -1]) cylinder(r = r_body + band_t - 0.01, h = band_h + 2);
    }
    for (i = [0:n-1])
        rotate([0, 0, -90 + (i - (n-1)/2) * step]) translate([0, 0, band_h / 2])
            rotate([90, 0, 90]) linear_extrude(r_body + 10)
                translate([0, -h / 2]) text(name[i], size = h, font = font, halign = "center", valign = "baseline");
}

strip();
letters();
```

Read the `front` or `iso` preview and check that every letter sits on one line. A strip like this
renders in about 15-60 s (the letter shells are booleans); that is normal.

For a name on a body you design yourself, use the same `letters()` on the body's own radius and
`union()` it with the body.

## Two colours
- The workshop slices one file in one colour. For two colours (strip + letters, plate + inlay),
  render each colour as its own `part`, upload both, and tell the owner: putting two parts together
  as one two-colour object is a job for the slicer on the owner's side today.
- **Flush inlay** (letters level with the face, the "plaque" look): print the face down so it takes
  the plate's texture. Light over dark needs at least 1.0 mm (5-6 layers at 0.2 mm) of the light
  colour, or it looks grey; dark over light is opaque at 0.6 mm.
- **Glue-in letters** for pockets: pocket outline minus 0.3 mm per side (0.15 was too tight for glue),
  letters 1 mm proud, printed face down. Letters that touch in a bold font come out as one piece; the
  dot of an İ comes out as its own piece: lay them out with a gap and say so.
- One colour on a busy surface (a lattice, a ribbed wall) is unreadable: use contrasting inlay letters
  or closed pockets that can be painted.
- Print all copies of one order from the same files, so every set is identical.

## Seams and presentation
- Name to the front (-Y). The seam belongs at the back; the owner's process preset decides where
  it goes, so tell the owner when a seam through the name would matter (household-printing
  `references/printing-rules.md`, "Seam").
- Send the `iso` preview for a name (it shows relief). For a black part, say the real colour in
  words: the preview is always light blue.
