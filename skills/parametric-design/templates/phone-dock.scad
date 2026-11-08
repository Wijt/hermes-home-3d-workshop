/*
   Phone dock with a charging cable (worked example for the parametric-design skill).

   A household asked for a stand that holds one phone, with its case on, while it charges.
   What the first prints taught (each one is a parameter or a check below):
   - Measure the phone WITH its case. Take the thickest of several caliper readings and add
     `fit` per side, so the phone drops in.
   - The plug needs room under the port: about 10 mm for a magnetic L-plug, about 25 mm for a
     straight USB-C plug and its cable bend. `plug_len` says which, and an assert stops a dock
     that is too low for it (a straight plug needs floor_z = 28).
   - The wall socket moves from day to day, so the cable can leave on ALL FOUR sides.
   - Keep the underside CLOSED. Only narrow grooves for the cable. An open underside left a
     thin ring on the bed, and the front edge of the tall part lifted while it printed.
   - A ring holder or grip on the back of the case needs a window in the backrest.
   - A finger notch in the front lip makes the phone easy to take out.

   Units: mm. Front = -Y (the screen faces the person). The model sits as it prints.
   Print: standing on its base, no supports. The slot walls lean `tilt` degrees, and the
   cable grooves are short bridges.
   part = "dock" is the stand. part = "fit_test" is a thin ring of the slot (about 15 min):
   print it first and check that the phone slides through it.
*/

// === MAIN PARAMETERS (USER CUSTOMIZABLE) ===
/* [Phone, measured with its case] */
phone_w = 78.4;     // width across the screen, case on (mm)
phone_t = 15.3;     // thickness, thickest caliper reading, case on (mm)
phone_h = 160;      // length; only used for the tip-over check (mm)
fit     = 0.8;      // clearance per side (mm): 0.8 lets a cased phone drop in

/* [Cradle] */
tilt    = 15;       // lean back from vertical (degrees)
lip_h   = 10;       // front lip height above the phone's bottom edge (mm)
back_h  = 80;       // backrest length above the slot floor (mm)
wall    = 4;        // lip, backrest and side wall thickness (mm)
floor_z = 14;       // height of the slot floor's front edge above the table (mm)

/* [Base] */
base_d       = 85;  // depth, front to back (mm)
base_h       = 8;   // base slab height (mm)
front_margin = 6;   // base in front of the lip (mm)
back_foot    = 12;  // depth of the base strip that carries the backrest (mm)

/* [Cable] */
plug_w   = 40;      // plug pocket across (mm)
plug_t   = 11;      // plug pocket front to back (mm)
plug_len = 10;      // room the plug needs under the port (mm): 10 magnetic L-plug, 25 straight USB-C
groove_w = 8;       // cable groove width (mm)
groove_h = 6;       // cable groove height (mm)

/* [Back of the case] */
ring_window = true; // window in the backrest for a ring holder or grip
ring_w      = 42;   // window width (mm)
ring_from   = 45;   // window starts this far above the phone's bottom edge (mm)

/* [Looks] */
edge_r   = 3;       // rounding of the side profile (mm)
corner_r = 6;       // rounding of the plan corners (mm)
notch_r  = 8;       // finger notch radius in the front lip (mm)

/* [Print] */
part  = "dock";     // [dock, fit_test]
fit_h = 6;          // height of the fit-test ring (mm)

/* [Hidden] */
cut = 1;           // cutters reach this far past the faces they cut (no zero-thickness skins)
big = 400;          // longer than any part of the dock
$fn = $preview ? 32 : 64;

// === DERIVED VALUES ===
slot_w  = phone_w + 2 * fit;            // inside width of the slot
slot_t  = phone_t + 2 * fit;            // inside thickness of the slot
width   = slot_w + 2 * wall;            // overall width (X)
pivot_y = front_margin + wall;          // front bottom edge of the slot (Y)
pivot_z = floor_z;                      // front bottom edge of the slot (Z)
// A point in the tilted cradle frame: t = toward the back, s = up along the phone.
function cradle(t, s) = [pivot_y + t * cos(tilt) + s * sin(tilt),
                         pivot_z - t * sin(tilt) + s * cos(tilt)];
back_top   = cradle(slot_t, back_h);           // highest point of the backrest
back_rear  = cradle(slot_t + wall, back_h);    // its top rear corner
phone_cog  = cradle(slot_t / 2, phone_h / 2);  // the phone's centre of mass
port_y     = cradle(slot_t / 2, 0)[0];         // the phone's port (Y)
floor_low  = cradle(slot_t, 0)[1];             // lowest point of the slot floor (Z)
port_z     = cradle(slot_t / 2, 0)[1];         // the phone's port, above the table (Z)
groove_y   = port_y - (port_z - groove_h / 2) * tan(tilt);  // where the plug's line meets the grooves (Y)
fit_s0     = 2;                                // fit test: cut from 2 mm above the floor

// Report first: when an assert below stops the render, these numbers still come back.
echo(str("FOOTPRINT: ", width, " x ", base_d, " mm (W x D); the tool's size_mm has the height"));
echo(str("SLOT: ", slot_w, " x ", slot_t, " mm inside, for a ", phone_w, " x ", phone_t, " mm phone"));
echo(str("PORT: ", round(port_z), " mm above the table, the plug needs ", plug_len, " mm"));
echo(str("PHONE WEIGHT AT Y = ", round(phone_cog[0]), " mm of ", base_d, " mm base depth"));
echo(str("PRINT: base down, no supports. part = ", part));

// === VALIDATION ===  (eps: a check exactly at its limit must not fail on rounding)
eps = 1e-6;
assert(width <= 256 && base_d <= 256 && back_top[1] <= 256, "Bigger than the 256 mm build volume");
assert(wall >= 1.2, "Walls under 1.2 mm break");
assert(tilt >= 0 && tilt <= 30, "Lean back between 0 and 30 degrees");
assert(back_rear[0] <= base_d - edge_r, "The backrest leans past the back of the base");
assert(phone_cog[0] < base_d - 10, "The phone's weight sits behind the base: it tips over backward");
assert(plug_t <= slot_t - 4, "The plug pocket must stay inside the slot floor");
assert(plug_w <= slot_w - 2 * wall, "The plug pocket is wider than the slot allows");
assert(floor_low - groove_h >= 3 - eps, "Too little material between the slot floor and the cable grooves");
assert(port_z >= plug_len - eps, "Too low for this plug: raise floor_z (28 for a straight USB-C plug) or use an L-plug");
assert(notch_r < lip_h, "The finger notch cuts through the whole lip");
assert(!ring_window || ring_from > lip_h + 5, "The ring window starts too low");
assert(fit_s0 + fit_h <= lip_h, "The fit-test ring must stay below the top of the lip");


// === MODULES ===
// Children are placed in the tilted cradle frame (x across, y = t, z = s).
module tilted() translate([0, pivot_y, pivot_z]) rotate([-tilt, 0, 0]) children();

// Side profile in the Y-Z plane: u = Y (front to back), v = Z.
// The shapes reach below the bed and are clipped at v = 0: a flat bottom with sharp bed
// edges (a rounded bed edge curls up), rounded edges everywhere else.
module side_profile() {
    module tilted2d() translate([pivot_y, pivot_z]) rotate(-tilt) children();
    below = edge_r + 1;
    intersection() {
        square([base_d, big]);
        offset(r = edge_r) offset(delta = -edge_r) union() {
            // base + slot floor + front lip
            hull() {
                translate([0, -below]) square([base_d, base_h + below]);
                tilted2d() translate([-wall, -floor_z]) square([slot_t + 2 * wall, floor_z + lip_h]);
            }
            // backrest, carried by the back strip of the base (a sloped back)
            hull() {
                translate([base_d - back_foot, -below]) square([back_foot, base_h + below]);
                tilted2d() translate([slot_t, -floor_z]) square([wall, floor_z + back_h]);
            }
        }
    }
}

module rounded_plan(w, d, r) {
    translate([-w / 2, 0]) offset(r = r) offset(delta = -r) square([w, d]);
}

module body() {
    intersection() {
        rotate([90, 0, 90]) linear_extrude(height = width, center = true) side_profile();
        linear_extrude(height = big) rounded_plan(width, base_d, corner_r);
    }
}

module phone_slot() {
    tilted() translate([-slot_w / 2, 0, 0]) cube([slot_w, slot_t, big]);
}

// Under the phone's port, along the phone: the plug goes straight down and its cable meets the
// grooves. The pocket stops at the grooves, so the bed face stays closed except their cross.
module plug_pocket() {
    intersection() {
        tilted() translate([-plug_w / 2, slot_t / 2 - plug_t / 2, -big]) cube([plug_w, plug_t, big + cut]);
        translate([-big / 2, -big / 2, groove_h - cut]) cube(big);
    }
}

// A cross of narrow grooves in the closed underside: the cable leaves on any side.
module cable_grooves() {
    translate([-width / 2 - cut, groove_y - groove_w / 2, -cut]) cube([width + 2 * cut, groove_w, groove_h + cut]);
    translate([-groove_w / 2, -cut, -cut]) cube([groove_w, base_d + 2 * cut, groove_h + cut]);
}

module ring_window_cut() {
    if (ring_window)
        tilted() translate([-ring_w / 2, slot_t - cut, ring_from]) cube([ring_w, big, big]);
}

module finger_notch() {
    tilted() translate([0, cut, lip_h]) rotate([90, 0, 0]) cylinder(r = notch_r, h = 40);
}

module phone_dock(notch = true) {
    difference() {
        body();
        phone_slot();
        plug_pocket();
        cable_grooves();
        ring_window_cut();
        if (notch) finger_notch();
    }
}

// A thin slice of the cradle, cut square to the phone and laid flat on the bed. The cased
// phone must slide through it: a 15-minute check before the 3-hour print.
module fit_test() {
    translate([0, 0, -fit_s0]) rotate([tilt, 0, 0]) translate([0, -pivot_y, -pivot_z])
        intersection() {
            phone_dock(notch = false);
            tilted() translate([-big / 2, -wall - 3, fit_s0]) cube([big, slot_t + 2 * wall + 6, fit_h]);
        }
}

// === RENDER ===
if (part == "fit_test") fit_test();
else phone_dock();

/* Next tweaks people asked for (they are one-line parameter changes):
- A thicker case: raise `phone_t` to the new thickest reading; `fit` stays 0.8.
- A straight USB-C cable: `plug_len = 25`, `floor_z = 28` (the plug and its bend fit under the port).
- No ring holder: `ring_window = false` closes the backrest.
- A tablet: `phone_w = 180`, `phone_h = 250`, `back_h = 120`, `base_d = 120` (the asserts check it still stands).
- Cable only to the back: keep the cross anyway; it costs nothing and the socket moves.
*/
