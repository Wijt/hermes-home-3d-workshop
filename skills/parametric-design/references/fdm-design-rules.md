# FDM design rules for household parts

Learned on a Bambu Lab A1 (0.4 mm nozzle, textured PEI plate, PLA, 256 x 256 x 256 mm) with real
family requests. The numbers are starting points; the slicer settings themselves are the
household-printing skill's `references/printing-rules.md`.

## Basics
- **Build volume:** 256 x 256 x 256 mm. `assert` it in the code; the tool also reports
  `fits_build_volume`.
- **Walls:** at least 1.2 mm (3 lines), 2-3 mm for anything that is handled or carries load.
- **Smallest feature:** about 0.4 mm wide (one nozzle line). The workshop slices with Arachne walls,
  so thin letter strokes still print, but 0.8 mm or more stays crisp.
- **Layer height:** 0.2 mm by default. Make heights of steps, gaps and floors whole multiples of it.
- **Overhangs:** at most 45 degrees from vertical without supports.
- **Bridges:** keep them under 50 mm. A long floating underside (60 mm or more between two walls)
  is not acceptable even as a "bridge": turn the part instead.
- **Edges:** chamfer the edge that touches the bed (0.5-1 mm); a rounded bed edge curls up and shows
  elephant's foot. Round the other edges (`offset`, `hull`) as you like.
- **$fn:** 48-64 for printed circles.

## Fits and holes
| Fit | Clearance per side | Use |
|---|---|---|
| Press fit | 0.1 mm | pins, magnets pressed in |
| Moving | 0.2 mm | sliding lids, hinges |
| Loose | 0.3-0.5 mm | lids that drop on, parts glued in |
| Device in a cradle | about 0.8 mm | a phone with its case on |
- Holes for real parts: 20.3 mm for a 20 mm tube; screw clearance M3 3.4, M4 4.5, M5 5.5 mm; heat-set
  insert M3 4.0-4.2 mm; countersink head about 2x the shank.
- Small printed holes come out small: a hole that must fit a pin gets +0.2-0.3 mm, or a test piece.
- A device: measure it WITH its case, several times, and use the thickest reading.
- Print-in-place joints: at least 0.3 mm clearance, and vertical gaps on the layer grid: a 0.15 mm
  gap is less than one layer and prints fused. Leave one full empty layer above and below a pin.

## Shapes that print without supports
- **Horizontal holes and pockets:** a teardrop (45-degree pointed top) or a cone-shaped ceiling.

```scad
// horizontal hole along Y, pointed top up: prints without supports
module teardrop_hole(d, len) {
    rotate([90, 0, 0]) linear_extrude(len, center = true)
        hull() { circle(d = d); rotate(45) square(d / 2); }
}
```

- **Slot ceilings, lock lugs, ledges:** slope them at 45 degrees. A flat ceiling is a cantilever
  that sags (it did on a twist-lock lid).
- **Steps and offset features** (tabs above or below a plate) leave something floating whichever
  side is down. Decide the print orientation BEFORE you show the model and say it with the first
  picture. Standing a plate on its long edge is often better than supports.
- **A decorative part that a new feature would lift off the bed:** make the feature a separate,
  glued part with a rib-and-groove joint. Supports under a visible face leave scars.
- **Layers and strength:** layer lines are the weak plane. Hooks, clips and flexing arms need their
  layers running along the arm, not across it.

## The footprint (warping)
- **Never hollow out the underside of a tall part.** An open bottom leaves a thin ring on the bed,
  and the long front edge lifts while it prints. Keep the bottom closed and cut only narrow grooves
  (for a cable: about 8 x 6 mm).
- Tall and narrow: widen the base, or lay the part down. A brim does not save a tiny contact patch.
- Large flat corners can get 15 mm x 0.4 mm "mouse ears" (discs) against lifting.

## Round or domed bottoms
For a small pebble, gem, dome or anything round underneath, offer two print-ready versions:
1. **Cut flat at the WIDEST section** (sturdiest), or
2. **keep the full shape, tilt it about 20 degrees** and let the slicer put tree supports under it.
Never offer such a part a shallow 0.5-2 mm flat: every layer above it overhangs the first one, the
edges curl, the nozzle catches them and a small part gets knocked off. It failed twice that way.
A long round band or tube that prints lying on its side (a soap-dish wave, a rail) is different: give
it a 1.5-2 mm flat along its length to stand on, on a face nobody sees.

## Bought parts: magnets, nuts, bearings
- **Default: an open press-fit pocket** from the bottom or the side, part size + 0.15 mm, pressed in
  after printing (a drop of glue if loose). A 10 x 2 mm magnet: pocket 10.15 x 2.5 mm (sits 0.5 mm
  deep), with at least 1 mm of material above it.
- **Pause-and-insert does not work here.** A magnet sealed in during a print pause failed twice: the
  nozzle oozes while it waits, the first layers after the pause are thin, they do not bridge over
  the smooth metal, and everything above prints into the air (the printer still reports FINISH).
- If a hidden pocket is really needed: floor and ceiling on whole layers (`floor()`/`ceil()` with a
  `layer_height` parameter), pocket 0.3 mm deeper than the part, ceiling at least 1 mm, `echo` the
  pause height and layer, and say it is untested.
- Two halves with half-depth pockets and filament-pin alignment holes is the no-pause alternative.

## Several parts on one plate
- Parts must not touch: add a `layout_gap` (5-10 mm). Faces that share a plane give a
  non-manifold warning and print fused. Check `bodies` = number of parts. A plate with more than one
  body is never pushed off by auto-eject (the slice keeps it for the owner); a single thin or fragile
  part also needs `eject=off` at the slice.
- Several copies: space them along their SHORT side.
- Mirrored pairs (left/right brackets): `mirror()` one copy and keep the gap between their backs.
- **Bigger than the bed:** split into parts that each fit, joined by a jigsaw or dovetail with
  0.2-0.3 mm clearance, or by alignment pins. Keep every joint in a straight, solid section.
- **Fit-critical parts:** offer a small test piece of just the mating feature first (a 10-20 minute
  print: a ring of the phone slot, one tooth of a rail connector). It costs much less than a full
  print that does not fit.

## Lids, boxes and round things
- A lid is a mechanism: change its fit through a parameter, never by scaling the whole part.
- The axis of a round lid is the centre of its round base, not the centre of its bounding box: a
  decorative top (a rose, a handle) moves the box centre off the axis.
- The lid must sit where the original lid sat. Find the ledge it rests on and keep the assembled
  height the same.
- Check that box and lid really fit before the first print: place the lid where it sits and
  intersect the two (`openscad-syntax.md`, "Do the parts fit together?"). Contact is fine, overlap is
  not.

## Size words
- **"Width" is along the FRONT face** (the side with the opening, the slot or the thumb notch), not
  the longest side. Stretching the long side gave "long and thin", which was wrong.
- "A bit bigger" means one step (5-10 %), said back in cm before you render.
- When they leave the size to you, use the size of the thing it fits, plus the clearance above.

## Household specifics that came from real prints
- **Phone docks and charging stands:** ask in one message for the cased width and thickness, what
  is on the back of the case (a ring holder or grip needs a window in the backrest) and the plug
  type. A straight USB-C plug and its cable bend need about 25 mm under the port; a magnetic L-plug
  about 10 mm. Give the cable exits on ALL FOUR sides: the wall socket is not always on the same
  side. Keep the bottom closed (a cross of grooves; the plug pocket stops at them). The worked example
  `templates/phone-dock.scad` does all of this (`plug_len`, `floor_z = 28` for a straight plug).
- **A plate or card standing in a slotted stand:** the slot's lip hides `slot_depth / cos(tilt)` of
  the plate's bottom. Centre text and pictures in the part that stays visible, not on the whole plate.
- **"Make it nicer" for a boxy part:** draw the side profile in 2D (`hull()` of the pieces), round it
  with `offset(r = R) offset(delta = -R)`, extrude it across the width, then `intersection()` with a
  rounded plan. Add a finger notch where a hand reaches in.
- **Joining offset regions** (a raised tab on a plate): a full-height solid block running several mm
  into the body. A thin 2 mm neck or a sloped ramp was rejected as weak.
- **Snap forks and clips:** a small V lead-in at the mouth (about 1 mm per side) and chamfered tips.
  Thin the arms only when the arms themselves must flex.
- **Decorative prongs, vines, thin ornaments** that people handle: PLA prongs at least 2 mm thick
  (1 mm snapped at once, 1.6 mm still broke at the rim), stems tapering from about 1.2 to 0.6 mm
  radius, and anchor every prong down the outside of the wall, not on the rim edge. Keep every curl
  within 45 degrees of vertical.
- **A stone or object set into a cup:** object outline + 0.6 mm clearance, and the rim about 0.6 mm
  above the object's widest section so the wall holds it.
- **Dark filament:** the slicer preview is hard to read in black. The design previews are always a
  light colour; send one of those with the slice link.
