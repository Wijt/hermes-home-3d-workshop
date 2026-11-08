# Auto-eject: push the finished part off the plate

Why it matters: without it every finished part waits for a person, and so does the next job. Hand
removal also greases the plate (fingerprints), and the next thin part lifts. With a tilted printer and a
push baked into the end G-code, sturdy parts slide off into a box and the printer is ready again.

## How it works
1. **Tilt base.** The printer stands on a printed base that tilts it forward about 15-20 degrees (for the
   A1, e.g. MakerWorld 2335000: two side supports and two connectors; commercial print-farm kits use about
   20 degrees). The push frees the part; the tilt carries it off the machine.
2. **Auto-eject printer preset.** A copy of the standard A1 printer preset. Its end G-code, after the normal
   end sequence and while the axes are still homed:
   - turns the heaters off, parks the bed with the part fan on and waits for the bed to cool (about 15 min;
     PLA lets go of textured PEI when cold),
   - lowers the motor current on the push axis, so a welded part makes the motor skip instead of forcing it,
   - sweeps the nozzle at Z 2.5 mm across the plate from back to front, at the first-layer centre and near
     both sides of the part (the slicer's first-layer bounds placeholders give the X positions),
   - restores the motor currents and carries the marker comment `; HOME3D AUTO-EJECT`
     (older presets: `HERMES AUTO-EJECT`). The plugin detects eject plans by this marker.
   - Its start G-code also drops the purge line on the plate's front edge: thin lines can't be pushed off.
   This is a concept, not a drop-in file. Write it for the actual printer and run the first tests with a
   person present and a box in front of the printer.
3. **Settings.** `autoeject_printer_preset` = that preset's Bambuddy id. `standard_printer_preset` = a
   no-eject preset (ideally also without the purge line) for parts that must not be pushed.
4. **Slicing.** `home3d_slice eject=auto` slices with the eject preset, checks the G-code and keeps the
   eject plan only when the part qualifies. Otherwise it re-slices with the standard preset and returns
   `eject.reasons`.

## Eligibility (what the tool checks)
- Yes: sturdy PLA-like parts at least 3 mm tall, at least 15 mm on the short side of the first layer, and
  height no more than 2.5x that short side. Large flat parts (60 mm+ footprint) pass from about 2.8 mm.
- No: PETG (stays welded when cold), TPU and other flexible filament (bends), other non-PLA materials.
- No: under 3 mm tall (the push at Z 2.5 passes over it), a footprint under 15 mm (rolls or falls the wrong
  way), tall and narrow (tips over instead of sliding).
- The code cannot see shape. Use `eject=off` yourself for round parts that roll, fragile or detailed parts
  (figures, petals, thin cards), and plates of several loose small parts (sweeps miss the gaps).
- Default stays `eject=auto`. Don't switch it off just because a part is tall-ish: the numbers decide. If
  you think a part is risky for a reason the code can't see, say so in one line and ask.
- When eject is off, the requester hears once that someone will need to take the part off.

## Making a part ejectable
- A push tab: a 5-6 mm wall behind the part on a thin snap-off neck, so the nozzle has something to hit.
- A sled: a thin sheet with a raised back wall carrying several small parts.
- For flat parts a lower push height (about 0.8 mm) works, but that is a separate preset or a manual push.
- Keep brims on eject-bound parts at 3 mm or less.

## Verification (the watcher does this)
1. At the last layer, before the push, it takes the "done" photo. After the push there is nothing to show.
2. After FINISH it waits for the bed to cool and the eject window (about 20 min) to pass.
3. Then it checks the plate: lit camera photo plus the plate check, up to 3 times.
   - Empty: "dropped off" to the owner and the requester; ready for the next job.
   - Not empty: a person is needed (a `remove_part` moment); the family hears "it stayed on the plate".
   - Unsure: "could not verify"; look at the photo yourself.
4. Nothing new starts until the plate is verified empty.

## Plate check quirks
- The camera needs the chamber light on long enough for auto-exposure. With a 2-3 s wait an empty plate
  read 18-25 % different; after 20 s with the light on the same plate read under 1 %. The tools treat a
  "not empty" under 26 % as unsure.
- Calibrate the plate references where the bed really stops: after the end park, after an eject, idle.
  A bed parked at the far end reads "not empty" against a reference taken elsewhere.
- Recalibrate plate detection after tilting the printer or moving the camera. A sagging camera mount made
  empty plates read 7-36 % and every print paused at the start.
- Faint marks and residue also raise the difference. When in doubt, look at the photo.

## Known failure modes
- **Part slid but stopped on the machine base in front of the bed.** It now sits in the bed's travel path
  and the next bed move can crash into it. Move nothing, take a photo, ask a person. (This is exactly what
  the first manual push test showed, and why the tilt base exists.)
- **Part did not move** (welded, wide brim, PETG). The motor skips by design. Don't push again and again;
  ask a person to lift the flexible plate out and bend it gently.
- **Thin part missed:** under the push height. Next time: push tab, sled or no eject.
- **One of several small parts left behind** between the sweeps.
- **Someone took the part by hand before the check:** the plate is empty. Don't push again; say truthfully
  that it was removed by hand.
- **Greasy plate after many pushes:** thin parts start lifting. Wash with dish soap and warm water.
- **X-axis resonance warning after mounting on a printed base** (A1 HMS 0300-1000-0002-0001): a warning,
  the print continues. A softer mount lowers the measured frame resonance. Check every foot sits solidly,
  use harder pads, check belt tension using the official Bambu wiki page for that code, then run the
  calibration with vibration compensation.

## Manual push of a part sliced without eject
Only when the owner explicitly asks (a test, or the eject preset was forgotten). Say the risk to the part
in one line. Wait for FINISH and a bed at 30 C or cooler, pick a push height where the first layers are
still full width (the frame, not the detail), push, then keep the bed parked until the camera confirms
nothing lies in its path. This is owner-supervised work outside the tools; never do it from a cron job.

## The self-upgrade it came from
The `remove_part` upgrade proposal points here. A household agent noticed it kept needing a person to clear
the plate, researched how others solved it on the A1, printed the tilt base parts on its own printer, then
recalibrated the plate check on the tilted base and made auto-eject its default for sturdy PLA parts.
