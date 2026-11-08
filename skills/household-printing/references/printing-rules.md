# Printing rules: orientation, slicing, materials

Rules learned on a Bambu Lab A1 (0.4 mm nozzle, textured PEI plate, 256 x 256 x 256 mm build volume)
driven through Bambuddy. Numbers are starting points for that setup; other printers need their own.

## Already done by the plugin (don't repeat as advice)
- Every slice uses: Arachne walls (thin text and small features don't drop out), travel that follows walls
  plus retraction over infill (no strings across holes, no nozzle scraping), 0.4 mm slope-lift z-hop,
  no prime tower, no automatic brim, and the bed type from the `bed_type` setting.
- Queue items skip bed levelling, flow and vibration calibration (minutes and noise each time). Turning
  them back on is the owner's call: after moving or tilting the printer, belt or hotend work, a plate swap,
  or first-layer and ghosting problems.
- The G-code inspection warns about a file sliced for another printer (e.g. an A1 mini profile), a prime
  tower, and bed or nozzle temperatures outside the material's range. Read the warnings out to the owner.

## Per-job choices (tool arguments)
| Part | `quality` | Why |
|---|---|---|
| Functional: brackets, hooks, stands, organisers | `draft` (0.28 mm) | time and energy over looks |
| Everyday, mixed | `standard` (0.20 mm) | default |
| Display, round, detailed, faces, text | `fine` (0.16 mm) | smooth curves, about 2x the time of draft |
- Flat parts gain little from thin layers. Say the time difference when you choose `fine`.
- `material`: PLA unless asked. PETG for heat, sun or water; TPU for flexible parts. `colour`: the
  requester's words; the tool matches a loaded AMS tray.
- `eject`: `auto`. Use `off` only for parts someone removes by hand anyway (coupons, fragile pieces).
- Report the choice in one line: quality, material and colour, eject or not, and why if it is unusual.
- Settings the tools don't expose (orientation, supports, seam, ironing, brim) come from the model's own
  3MF profile or the owner's presets (`process_presets`, `filament_presets`). When a job needs one, pick a
  MakerWorld profile that already has it, or tell the owner exactly which setting to change and why.

## Orientation (decide before slicing a downloaded or functional model)
Never accept the designer's orientation blindly. Compare upright and lying down, then state the pick and why:
1. **Strength.** Layer lines are the weak plane. Find the load path (hook arm, clip, cantilever) and let
   layers run along it, not across it. A load that pulls layers apart snaps the part.
2. **Stability.** Low height, large first-layer contact. A tall part on a tiny footprint, or a high arm
   the nozzle pushes down on, acts as a lever and peels off. A brim on a tiny contact patch does not fix
   that: lay the part down or use a raft. Measure the contact area before the first print.
3. **Visible surface.** Curved display bands look best with the curve in the bed plane (smooth
   perimeters, layer lines hidden in grooves). Contact flats, seams and support scars go on hidden faces.
   Ask the requester when looks trade against time.
4. Then supports and time.
A profile titled for another orientation or scale often exists: check the other `a1_profiles` first.

## Seam
The vertical seam goes where it is least seen and least functional. Put it at the back (+Y) with the
decorated side facing front (-Y), or on a sharp hidden corner. On round visible walls consider a scarf
seam. A seam running straight down under a name on a gift box is the classic complaint.

## Top and bottom surfaces
- Ironing only for flat top faces people look at (nameplates, signs, lid tops). It adds time. If an ironed
  face comes out rough or grooved, print an ironing calibration grid and use the best cell.
- Fix the basics before ironing: at least 6 top layers at 0.20 mm, top line width about 0.32 mm on a
  0.4 nozzle (never under 0.25: the top layer delaminates), monotonic top and internal solid infill,
  slower top speed (30-45 mm/s) against shiny/matte patchwork, calibrated flow and pressure advance.
- Bottom face: a lower first-layer flow (about 0.95) often looks better, even when the defect looks like
  under-extrusion. Test it on a one-layer calibration print.
- First layer too low on an A1: check the hotend is fully clipped in before touching settings.
- Elephant foot: chamfer the bed edge in the design rather than filleting it.

## Brim
- Off by default. Add one only with a reason, and say it: a tiny or tall-narrow footprint, a material or
  filament that warps, a large flat base.
- Outer brim only, 3-6 mm wide, object gap 0.15-0.2 mm. A 0.1 mm gap fuses the brim and it tears off
  leaving a ragged edge people notice.
- Parts that will be pushed off: brim at most 3 mm. A 5 mm brim welded a 2 mm letter so firmly the
  low-current push could not move it.
- No brim on parts printed face down for display (glue-in letters): it leaves a burr on the visible face.

## Supports
- Fix orientation first. Then tree supports, only where needed. Supports everywhere is a common complaint.
- Clean-release settings that peel off well: threshold 45 deg, supports on the build plate only (but check
  that overhangs above the model itself still get support), top Z gap 0.25 mm, solid interface (spacing
  0) with 2 layers, XY gap 0.35 mm, supports on the same layer height as the part.
- PETG bonds harder: top gap 0.25-0.30 mm, never smaller. TPU: avoid supports.
- Tiny parts (under ~25 mm, round or tilted bottom): a raft plus snug normal supports, slow speeds. Thin
  tree branches get knocked over and the part levers off.
- A decorative part that an added feature lifts off the bed: split it into a separate glued part rather
  than supporting a visible face.

## Small and thin parts
- Slow first layer (about 20 mm/s outline, 30 mm/s infill). Thin tags and letters lift at default speeds.
- If one piece of a tray fails, reprint only that piece.
- Several small parts that touch become one merged piece: it lifts more easily. Space them or give that
  piece a small brim.

## Materials and temperatures (textured PEI)
| Material | Nozzle C | Bed C | Notes |
|---|---|---|---|
| PLA, PLA+, PLA/PHA | 190-230 | 45-65 | some budget black or white PLAs need 65-70 C first layer and warp on big flat bases |
| PETG | 220-260 | 70-80 | fan 30-60 % (100 % kills layer bonding), about 10 mm3/s, never auto-ejected |
| ASA / ABS | 240-280 | 100 (A1 max) | fan 10-30 %; the open A1 warps large flat parts |
| TPU | 220-240 | 30-45 | about 3.6 mm3/s, feed from the external spool holder, not the AMS lite, never ejected |
- Filament temperatures belong to the filament preset. Process overrides silently ignore them. A new
  filament gets a filament preset that inherits the matching generic A1 preset with the label's
  temperatures; the owner maps it in `filament_presets`.
- Bed type must match the real plate. PLA on a textured plate will not stick at a cool-plate 35 C.
- Dry PETG and TPU before use. PETG and PLA do not bond to each other in one part.
- Spools without an RFID tag: the remaining amount the printer shows means nothing. Ask.
- Printing a multi-colour model in one colour: map every used filament slot to the same tray.

## Plates with several colours or objects
- Prime tower stays off. Turn it on only with a reason (swaps every layer plus colour bleed on a visible
  face) and say the grams; once a tower was bigger than the model itself.
- Mixed colours with few swaps: print "by object" (each object finished before the next). A1 limits:
  objects about 73 mm apart including brim, and only one object taller than 25 mm, printed last. That
  needs a 3MF prepared in a slicer; ask the owner.

## Figures and miniatures
- Split the figure into two short, wide halves, cut faces down: it removes most overhangs.
- About 0.08 mm layers on a 0.4 nozzle, classic walls, support top gap equal to one layer, fan always on.
- Print several parts of similar height together so each layer cools. Never auto-eject them.
- Join halves with a PLA-melting solvent cement (plain PLA only, not PLA+) or thin super glue.

## Speed and size
- Sport speed mode only on purely functional parts, after the first layers; it causes cooling bands.
- Build volume 256 mm per side. Bigger objects need a profile designed to fit, or a split into
  interlocking parts (design work; ask the owner).
- Size words ("the big one", "original size") point at a profile or an earlier print. Match it; never put
  your own scale factor on top of a profile that is already large.

## Diagnosing defects
- A photo of a defect on a part you designed: measure the model and the slice before explaining. Guessing
  ("probably the brim") was wrong twice in a row; the real causes were geometric.
- Read the requester's mechanical explanation ("the arm sits high and the nozzle levers it off") and act
  on it. Stop a ruined print that is still running.
- After re-slicing an iteration, remove the superseded queue item (`home3d_queue action=remove`) so the
  old file is never printed.
