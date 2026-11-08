# Measuring from photos, and the replacement-part feedback loop

Family members send a photo, often with a coin next to the object, and expect you to work out the
sizes. Do that yourself before you ask. Ask only for what a photo cannot give: thickness, the depth of a
recess, a hidden offset, and the one dimension that must fit exactly. Treat every estimate as a check,
not as the truth: pixel estimates and "which way is it rotated" answers from vision were wrong several
times.

## Scale references
| Reference | Size (mm) |
|---|---|
| bank card (ISO ID-1) | 85.60 x 53.98 |
| 1 TL coin | 26.15 |
| 50 kuruş | 23.85 |
| 25 kuruş | 20.5 |
| 1 euro | 23.25 |
| 2 euro | 25.75 |
| US quarter | 24.26 |
| A4 sheet | 210 x 297 |

## Measuring a flat part from a top photo
1. Correct the phone's rotation first (Pillow: `ImageOps.exif_transpose`).
2. Find the coin and the part. Rough boxes from vision are only for choosing crops.
3. **Scale from the coin's area, not its box:** mask the coin, count its pixels, take the
   area-equivalent diameter `2 * sqrt(area / pi)`; `px_per_mm = that / coin_mm`. A bounding box
   includes the shadow. Try two or three mask thresholds and use the middle result.
4. **Part outline:** mask the part, turn it to its main axis, and read its width every few
   millimetres along that axis. That width profile gives head, body, shoulder and foot sizes directly.
5. **Model the outline as a parametric 2D module** (`hull()` of circles for arches, squares for
   stems), then extrude it.
6. **Check:** render a `top` view and put it next to a crop of the photo at the same rotation.
   Previews zoom to fit, so the scale never matches the photo: compare proportions (width to length,
   head to body), and `echo` the key widths to compare with your photo measurements in mm. Ask vision
   where the outline is too wide or too narrow. Repeat until it matches.
7. Expect an error on the side where the camera sees the part's thickness or shadow. Keep the model
   symmetric where the part is, and ask for calipers for anything that must fit.

- On a busy background (a patterned mat, glass, a translucent part) masks leak and give nonsense (a
  26 mm "stone"). Check that the coin mask is about coin-sized; if not, crop around coin and part, ask
  vision for the edge pixels of both and compute the scale from the coin span. Say it is an estimate.
- **Small rounded objects** (glass gems, pebbles): ask for TWO photos with the coin. (1) Straight
  from above with the object on or next to the coin: the outline. (2) From the side with the camera
  at table height: the thickness and profile. Angled shots only give the general look.
- **Videos:** take 1-2 frames per second, put 8 of them on one contact sheet, look at it once. Side
  frames give thickness and profile.

## Copying a product from a shop photo (no scale)
They want it "exactly like this" and will spot every proportion error. Measure everything up front;
one parameter per round cost four rounds once.
1. **Count every repeated feature first** (waves, legs, ribs, slots) and say the counts in your reply.
   People check counts before anything else.
2. **Measure in units of the main member's thickness T, not in mm.** Gaps, heights and lengths as
   ratios (gap about 0.2 T, height about 3 T). Product photos usually have thick members and tight
   gaps: lean towards chunkier and tighter.
3. **Set the absolute size from something in the photo** (a soap bar is about 92 x 58 x 28 mm, a phone,
   a hand), or from the listing. Ask only when there is nothing.
4. **Compare side by side every round:** the preview from a similar angle next to the photo; ask
   vision for concrete differences (thickness, gaps, ribs, ratios). Send that comparison, not a lone
   render.
5. **No flats on visible or functional faces** they did not ask for. A small print flat on top of an
   arch, where the soap sits, was rejected. Flats go on hidden faces only.
6. **Curved bands print on their side,** with the curve flat on the bed: smooth curves, layer lines
   hidden in the grooves, no supports.

## Replacement or adapter part for something they own
- **Coin in the photo = measure it yourself first.** A caliper reading from a person beats any photo
  estimate: use it as given. Log it: `home3d_human_needed action=log kind=measure`.
- **Start from the measured mating feature** (a 7.2 mm peg hole), and keep each fit as its own
  parameter (peg diameter, arm width, gap), so a later "1.35, not 1.5" is a one-line change.
- **Words map to geometry. Get them right the first time.** Turkish households use these:
  | Word | Means |
  |---|---|
  | girinti | a recess cut INTO your part |
  | çıkıntı, pim | something sticking OUT |
  | kısa kenar / uzun kenar | the short / long edges of a plate |
  | alt taraf | the face opposite the one with the other features |
  | pay ("2.8 mm pay ver") | an offset or step between two regions, NOT extra length |
  | esneme payı | room to flex: a small V lead-in at the mouth of a snap |
  | aynala | mirror: flip the step direction only (see below) |
  | "bir önceki basılmış modele dönelim" | go back to the version that was printed, then apply only the new change |
- A position given relative to another feature is edge to edge: `centre = other_edge - gap - d / 2`.
- Their axis words ("minus y", "the other side") do not map reliably to CAD axes.

## The feedback loop
- **Vague feedback** ("it's wrong", "the other way", "wrong side"): do not guess a fix. Offer two
  concrete readings, one line each, or a short numbered list of likely misreads (position, sticking
  out vs cut in, size, shape), and ask them to draw on your last picture.
- **Direction unclear** (up or down, which edge): render your best reading, show a view where the
  step is visible plus the `top` view, say the direction in words, and ask for a yes or no. One
  question costs a message; a wrong guess costs a print.
- **Mirror** ("aynala") flips only the offset direction (tabs 2.8 mm above instead of below) and keeps
  every hole, mouth, recess and gap identical.
- **Marked positions** (red dots on your picture): place the feature exactly there, compute it from the
  neighbouring features, and `echo` the coordinate.
- **Show the side where the feature is.** Recesses and walls on the underside are invisible from the
  top, and people reject a top view of them. Render `views=["bottom"]` (the bed face from below), or
  `iso`/`plan` for features on top. The flat `top`, `front` and `side` views show outlines only: a
  recess or a raised name in the middle of a face does not show there.
- **Small steps:** move a size by 2-3 mm per round on a 90 mm part. A big jump overshoots and they ask
  to go back.
- **Compare feature by feature before the first render,** not after they correct you: same length or
  alternating long and short? Round or square tips? How big is the centre compared with the whole?
  Make such things parameters from the start (`i % 2` for alternating lengths).
- **Every change is a new version.** When they say an earlier one was right, go back to that version
  and apply only the new change.
- **After the shape is approved,** slice it and give the owner the slice preview link before it is
  queued: hole spacing and wall thickness get checked there too.
