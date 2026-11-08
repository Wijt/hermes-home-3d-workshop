---
name: parametric-design
description: "Use to design a part in OpenSCAD when no ready model fits."
version: 0.1.0
author: Wijt, Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [OpenSCAD, CAD, 3D-Printing, Parametric, Design, Household]
    related_skills: [home-3d-workshop:household-printing]
---

# Parametric design (OpenSCAD)

You write parametric OpenSCAD code. `home3d_design` renders it to an STL, measures it, draws preview
pictures and keeps every version. You look at the pictures yourself before anybody else sees them.
When the person says yes, the design joins the normal flow: upload, slice, queue, and a start that
only the owner approves (skill `home-3d-workshop:household-printing`).

Load references with `skill_view name="home-3d-workshop:parametric-design" file_path="references/<file>.md"`.
Worked example: `file_path="templates/phone-dock.scad"` (a phone dock for a charging cable; read it
before your first design, and start from it when the request is close).

## When to Use
- No MakerWorld model fits after a real search, or the model cannot be imported and the shape is
  simple (box, holder, stand, hook, tray, spacer, organiser): draw it rather than offering something
  else.
- A personal or measured part: it must fit this phone, this shelf edge, this tube; it replaces a
  broken piece; it joins two things the household owns.
- A change a scale cannot make: a longer slot, a thicker wall, a hole for a cable, a lid that must
  still fit, a part bigger than the bed split into pieces, a name on a round box.
- The owner asks for OpenSCAD code or a .scad file.
- Ask before you design for a family member ("nothing ready fits; shall I draw one?"). Ready models
  are tested; your first draft is not.
- Not for: figurines, faces and organic sculptures (search MakerWorld). Not for parts whose failure
  can hurt someone (a shelf bracket above a bed, a heavy hook over people, anything for a small
  child's mouth): say so and suggest a bought part.

## The loop
1. **Understand and measure.** Restate the goal in one line: object, rough size, what it fits. Ask
   only what blocks, in one message. A part that fits something needs that one dimension from a ruler
   or calipers. A photo with a coin: measure it yourself first (`references/photo-measurement.md`).
2. **Decide the print orientation before you draw:** which face lies on the bed, which way the layers
   run under load, nothing floating, no support under a visible face. Say it with the first picture.
3. **Write the code** (rules below).
4. **Render:** `home3d_design action=render name=<short name> scad=<the whole file>`. Default views
   are `iso` and `top`. Others: `front`, `side`, `plan` (the top tilted 25 degrees) and `bottom` (the
   bed face), e.g. `views=["iso","plan"]`.
5. **Read the numbers before the pictures.** `ok: false`: read the error and its line, fix, render
   again (a failed `assert` comes back as the error, with the `echo` lines printed before it). Then
   check `suspect` (not empty: OpenSCAD skipped part of your code, see "When something goes wrong"),
   `warnings`, `simple` (false: broken), `inverted` (true: inside out), `bodies` (= the number of
   separate parts you meant), `size_mm` against what you intended, `fits_build_volume`, and your `echo`.
6. **Look.** `vision_analyze` each preview path with a concrete question ("Is the slot open at the
   top? Does the groove reach all four sides?"). Perspective lies: confirm outlines and the gaps
   between parts in the flat `top` view and in the numbers. `top`, `front` and `side` are flat-lit:
   they do NOT show raised or cut-in detail (letters, pockets, compartments, recesses). Check those in
   `iso` or `plan`, and features on the bed face in `bottom`. Previews zoom to fit, so a size change
   shows only in the numbers.
7. **Show it** (`references/response-format.md`). Family: one picture, the size in cm, at most three
   short questions, no code. Owner or technical: numbers, version, source path; code only when asked.
   `size_cm` is the size as modelled, which is how it prints. For a part that prints on its side or
   upside down, tell people the size as it is used, from your own `echo`.
8. **Iterate in versions.** Every render is a new version; nothing is overwritten. One correction is
   usually one parameter. A quick tweak: `from_version=<N> params={"wall": 3}`; it keeps that
   version's params AND its `part` (pass `part=""` for the whole design). A real change: a new
   `scad`. "The first one was right": render `from_version=1` with only the new change.
9. **On their OK:** `home3d_design action=upload name=<name> version=<N> requester=<who>
   request_text=<2-3 words naming the thing, in their language>` (or `request_id=<id>` when the
   request was already recorded), so the watcher later tells the right person in their words. Always
   give the version they approved (the render's `next` names it); without it, the upload refuses when
   more than one version rendered. Then household-printing step 7: slice, explain, queue, and the
   owner starts it. For a fit-critical part, offer a short test piece first (`part=fit_test` in the
   example). The test piece is its own request (`request_text` "phone dock test", "telefon yuvası
   deneme"); the real part later gets a new `request_text`, never the test's `request_id`, or the
   watcher names the real part a test.

`action=list` shows the recent designs; `action=get` returns a version's source, params and facts.
Read it before you write a new version of an existing design, and write any params it carries into
the new source: a full `scad` starts without them.

## Writing the code
- **Parameters first,** every dimension a named variable with its unit in a comment, grouped with
  `/* [Group] */` headers. No bare numbers inside modules; name small overlaps (`cut = 1;`).
- **Section order:** MAIN PARAMETERS, then (presets that the code really branches on), DERIVED
  VALUES, the report `echo` lines, VALIDATION (`assert`), MODULES, and the render call at the end.
  Echo before assert: a failed assert stops the file, and the numbers that explain it must already
  be printed.
- **`assert()` the impossible:** a wall under 1.2 mm, bigger than the 256 mm bed, a stand that tips
  over, a feature that leaves the part. Write the message in plain words; it comes back as the error.
  Compare with a small slack (`wall >= 1.2 - 1e-6`): `3 - 2.6` is 0.39999..., so a value exactly at
  the limit fails without it.
- **`echo()` the numbers that matter:** overall size, inside size, the fit you chose, and the size
  as used when it prints in another orientation. They come back in `echo` and save you a measurement.
- **Front is -Y.** The face that matters (opening, slot, label, screen) faces front. Model the part
  as it prints, flat on z = 0, nothing below z = 0, and say the print orientation in a comment.
- **Several parts:** `part = "all"; // [all, base, lid]` plus a `layout_gap`; the tool's `part=`
  renders one. Parts in `all` must not touch; put the low part (a lid) in front (-Y) so the tall one
  does not hide it. A `display` part (the piece turned as it is used, next to a soap bar or the box it
  goes on) is for pictures only: never upload it. Render only what prints when one piece was asked.
- **Quality:** `$fn = $preview ? 32 : 64;` (the tool renders the full quality).
- **Files:** `include`, `use` and `import` only with relative paths inside the design's folder; the
  tool refuses anything else. Fonts by name: `"DejaVu Sans:style=Bold"` (has Turkish letters).
- **Keep it fast** (the tool stops a render after 180 s; `timeout_s` allows up to 600): `hull()` and
  `offset()` instead of `minkowski()`, 2D profiles extruded once, and one `polyhedron()` sweep for
  curvy shapes (`references/openscad-syntax.md`).

## Rules that cost real prints
The full list with numbers is `references/fdm-design-rules.md`. These come up every time:
- `text()` lies flat in XY. A label on a front face needs `rotate([90, 0, 0])` and
  `linear_extrude()`. Names on round bodies: `references/curved-text.md`.
- Cutters must pass through the faces they cut (`cut` past them). Touching faces and zero-thickness
  skins make non-manifold parts.
- Fits per side: 0.1 mm press, 0.2 mm moving, 0.3-0.5 mm loose, about 0.8 mm for a cased phone.
- Overhangs at most 45 degrees: teardrop or 45-degree tops on horizontal holes, sloped ceilings,
  never a flat cantilever.
- A magnet or nut goes into an open press-fit pocket (size + 0.15 mm) after printing. Never plan a
  pause to insert it: that failed twice.
- Never hollow out the underside of a tall part: it warps. Keep the bottom closed and cut narrow
  grooves. Phone docks: cable exits on all four sides.
- A small rounded or domed part (a pebble, a gem, a dome): cut it flat at the widest section, or keep
  it whole and tilt it about 20 degrees on tree supports. Never a shallow 0.5-2 mm flat on such a
  part. (A long round band lying on its side is different: it needs a 1.5-2 mm flat to stand on.)
- "Width" is the size along the front face, not the longest side.
- A design you made is never scaled: change its parameters. Lids and snaps stop fitting when scaled.

## Feedback from people
- Vague ("it's wrong", "the other side"): don't guess. Offer two concrete readings, one line each,
  and ask them to mark your last picture.
- Mirror means: flip only the offset direction; every hole, recess and gap stays the same.
- Change sizes in small steps (2-3 mm on a 90 mm part); a big jump overshoots.
- A direction you are not sure of: render your reading, show the view where it is visible, say the
  direction in words and ask yes or no.
- A position they marked on your picture: put the feature exactly there and `echo` its coordinate.
- Turkish geometry words (girinti, çıkıntı, pay, aynala): `references/photo-measurement.md`.

## When something goes wrong
- `code: no_openscad`: tell the owner that designing needs `openscad` (and `xvfb` for pictures) on the
  Hermes machine; meanwhile look for ready models. Never say a design rendered when it did not.
- A timeout: simplify (lower `$fn`, fewer pieces, `hull` instead of long unions, a polyhedron sweep).
- A preview failed (a warning): the STL still counts. Check the numbers, and say you have no picture.
- `simple: false` or a non-manifold warning: find the touching faces or zero-thickness cuts.
- `suspect` is not empty (`Ignoring unknown variable/module/function`, `Unable to convert`, `Mixing 2D
  and 3D`): a typo or a wrong name, and that piece is MISSING from the model although `ok` is true.
  Fix it and render again before you show or upload anything.
- `inverted: true`: a polyhedron is inside out. Reverse the point order of each ring or face.
- `code: refused`: the code names a file outside the design folder, or reads one through a param.
  Use only files in the design folder (`include <lib/x.scad>`, `import("part.stl")`).
- `code: too_big`: the model is too detailed. Lower `$fn` (48-64 is plenty) or use fewer pieces.
- A printed design failed or did not fit: find the cause (footprint, orientation, fit), make a new
  version, and keep the lesson (`home3d_household action=note`).

**Where this comes from.** A real household's phone dock: the first print had an open underside for the
cable, and its front edge lifted off the bed. The family then asked for a cable exit at the front,
then on all four sides, because the wall socket moves. A window for the ring holder on the back of
the case came from another family member. Each lesson became a parameter or a rule, and all of them
are in `templates/phone-dock.scad`.

## References
- `references/openscad-syntax.md`: language, orientation, text, customizer, multi-part files,
  presets, polyhedron sweeps, speed.
- `references/fdm-design-rules.md`: walls, fits, holes, overhangs, footprint, magnets, layouts, big
  parts, household specifics.
- `references/photo-measurement.md`: coin scale, copying from a shop photo, replacement parts, the
  feedback loop, Turkish geometry words.
- `references/curved-text.md`: names on flat and round faces, glue-on strips, two colours, inlays.
- `references/response-format.md`: what to send to the family and to the owner, and what happens
  after the OK.
- `templates/phone-dock.scad`: the worked example.
