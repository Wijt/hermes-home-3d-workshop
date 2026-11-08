# Showing a design: what to send to whom

Two audiences, two formats. Family members decide from a picture and a size. The owner, or anyone who
asks in technical words, gets the numbers and, on request, the code. Write in the household
language (the per-turn context says which one).

## Family chat
One message:
1. **One picture:** a `MEDIA:` line from the render's `media`. Use the `iso` picture, or the view that
   shows what changed. Look at it yourself first.
2. **The size in cm,** one decimal (`8.8 x 8.5 cm, 8.6 cm tall`; Turkish writes `8,8 x 8,5 cm`).
   `size_cm` is the size as modelled, which is how it prints. A part that prints on its side or
   upside down: give the size as it is used (from your own `echo`), not the print size.
3. **What it does or what changed,** one or two short lines, in their words ("your phone drops in
   with its case", "the cable can leave on any side").
4. **At most three short questions,** one is best: is the shape right, which colour, how many.

Never in a family message: code, file paths, version numbers, "STL", "render", "parametric",
"OpenSCAD", grams from the design (the slice gives the real grams and time), or a promise that it
will print or start.

English example:

```
Mum, here is the phone stand.
MEDIA:/abs/path/phone-dock_v2_iso.png
About 8.8 x 8.5 cm, 8.6 cm tall. Your phone drops in with its case, and the cable can leave on any side.
Is the shape right? Shall I make it white?
```

Turkish example:

```
Anneciğim, telefon yuvasını çizdim.
MEDIA:/abs/path/phone-dock_v2_iso.png
Yaklaşık 8,8 x 8,5 cm, 8,6 cm boyunda. Telefon kılıfıyla rahat girer, kablo dört taraftan da çıkabilir.
Şekli tamam mı? Beyaz mı olsun?
```

- A follow-up picture says only what changed: "Opened a window in the back for the ring holder, 4.2
  cm wide." Then one question.
- The person said "don't ask, just do it": make reasonable choices, show the result, and list the
  choices at the end in one line ("I made it 2 cm deep and white").
- A fit-critical part: offer the short test piece in the same message ("I can print a 15-minute test
  ring first to check the phone fits"). Upload the test piece with its own `request_text` ("phone
  dock test", "telefon yuvası deneme"), and the real part later with a new one.

## Owner or technical chat
Short, numbers first:

```
phone-dock v3: 88 x 85 x 85.7 mm, 1 body, simple, fits the bed. Solid weight at most 316 g (the slice gives the real grams).
Print base down, no supports. Changed from v2: ring window 42 mm wide, from 45 mm up.
Source: /abs/path/phone-dock_v3.scad
MEDIA:/abs/path/phone-dock_v3_iso.png
On your OK: upload, slice, show the preview link.
```

- Mention every warning the render returned, and what you did about it.
- **Code only when asked.** Then send the complete file in ONE ```scad block (never a fragment), and
  after the block, outside it, a short "Next tweaks" list of exactly 4 bullets. Each bullet:
  - uses the real variable or module names from the code (`Raise ring_from to 55 mm ...`);
  - is one sentence and a functional change, not a vague "make it nicer";
  - covers a different aspect: fit, function, printability, looks;
  - uses standard sizes (M3, M4, 20 mm tube, 0.8 mm per side).
  A bracketed tag at the start is fine: `- [Add screw holes] Add two 4.5 mm countersunk holes ...`

## After the OK
1. `home3d_design action=upload name=<name> version=<N> requester=<who> request_text=<2-3 words in
   their language>` (or `request_id=<id>` when the request was already recorded). Upload the version
   they approved, not simply the latest one: the tool refuses to guess when more than one rendered.
   Never upload a `display` part, and upload a fit test as its own request.
2. Slice and queue through the household-printing skill (steps 7-10): say the print time, grams and
   colour in plain words, give the owner the slice preview link, and remember that every start needs
   the owner. A design with more than one body (a box and its lid) is never pushed off: the slice
   says so. A thin, small or fragile single part: slice with `eject=off`.
3. When the print comes back ("it fits", "too tight", "it broke"), note it with
   `home3d_household action=note` and keep the lesson for the next design.
