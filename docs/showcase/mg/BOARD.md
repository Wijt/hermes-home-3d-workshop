# The film, scene by scene (84 s, 1920 x 1080, 30 fps, no sound needed to follow it)

One belief: **ask the group chat for an object, and it is in the box.** The film follows one request (Mum's key
tag) from a chat message to a box, shows the plugin's real screen where a person presses Start, then the twist (the
printer printed its own upgrade), then what the plugin is.

Everything is drawn with `mg/kit.tsx` (read it first: palette `P`, type `F` and `T`, `Stage`, `Words`, `Line`,
`Bubble`, `Chip`, `Label`, `Wipe`, `Screen`, `Iso` with `plateSlabs` / `tagSlabs` / `boxSlabs` / `Nozzle`, `Photo`,
`Count`, and the time helpers `s`, `ramp`, `tween`, `pop`, `hold`, `keys`). `mg-look.tsx` shows the kit in use.

This page is the plan the scenes were built from. Where a scene file differs from it, the scene file is right;
the differences that matter are listed at the end.

## Rules for every scene

- A scene is `mg/scenes/<id>.tsx`: `export const DURATION = <frames>` and a default-exported component with no
  props. It draws the whole frame. Frames are local (0 = the scene's first frame).
- Use only the kit's colours, faces and sizes. Do not edit `mg/kit.tsx`; a helper you need goes in your scene file.
- Frame-pure: everything comes from `useCurrentFrame()`. No `useState`, `useEffect`, timers, `Math.random()`.
  Clamp every `interpolate`. Keep `transform` and `opacity` present on every frame.
- Type: big words in `F.display` weight 800, everything else `F.text`. Text that must be read is 60 px or more,
  small print 32 px or more. Always set `fontFamily` and `fontWeight`. Keep all text 120 px from the top and bottom
  edges and 80 px from the sides. Reading time: 0.3 s a word, at least 1 s a line.
- Motion: nothing stands still for 3 s. Things arrive with `Words`, `pop` or a rise; they leave before the next
  thing needs the space. Do not use the same entrance for every element. No bounce beyond the kit's `pop`.
- No glow, no gradient text, no glass, no drop shadows for decoration, no emoji, no arrows in text, no ALL CAPS
  labels, no middle dots, no "Not X. Y." lines. Sentence case. Short plain sentences.
- Nothing invented: only the words, numbers and names on this page. Names: Mum, Family, Mıstık (dotless i twice),
  Engineer, Lab, the owner.
- A picture that is not live footage carries its `Label` (kind "chat", "photo" or "screen").
- The first and last frames matter: the board says what each scene starts and ends on, because scenes are cut
  together with no crossfade.

## Scenes

| id | frames | starts on | ends on |
|---|---|---|---|
| ask | 195 | ink, empty | the whole frame red (`P.red`) |
| title | 135 | the whole frame red | the whole frame ink |
| make | 225 | ink | the whole frame `#F4F5F7` (the real screen's ground) |
| approve | 330 | the real screen, whole, scale 1 | the real screen zoomed on its top card |
| print | 300 | the real screen zoomed on its top card | ink, the finished tag on the plate |
| box | 285 | the same plate view as the end of print | ink, the tagline |
| twist | 330 | a real photo, full frame | a real photo, full frame |
| groups | 270 | ink | ink |
| close | 300 | ink | ink, the end card held |

### ask (195 frames): one message
Ink ground. Mum's message is the picture: a red `Bubble` (who "Mum", group "Family"), big (size about 76, width
about 1150), left of centre, typed at about 30 characters a second from frame 8:
"Mıstık, can you make me a key tag with MUM on it? Red please."
At about frame 96 Mıstık answers from the right in a bone bubble with ink text (who "Mıstık"):
"On it. I'll ask the owner to approve the print."
`Label kind="chat"`. From frame 178 Mum's red grows from her bubble (`Wipe`, `P.red`) until the whole frame is red
on the last frame.

### title (135 frames): the idea
The whole frame is `P.red` (use `Stage bg={P.red}`). Bone words, `F.display` 800, very large (180 to 200 px), two
lines, left aligned with a wide left margin: "A 3D printer" / "in the group chat." arriving from frame 4. At about
frame 50 a `Line` in bone: "home-3d-workshop, a plugin for Hermes Agent". Something keeps moving (the Stage drift,
or a large bubble shape sliding slowly behind the words in `P.redDeep`). From frame 120 an ink `Wipe` from the
bottom centre covers the frame by the last frame.

### make (225 frames): the agent does the work
Ink. Right two thirds: the plate (`Iso`), turning very slowly. Left third: one tool at a time, each a mono `Chip`
with one plain line under it, the earlier ones staying, dimmed.
- frames 6 to 75: `home3d_design`. On the plate the tag grows out of the sheet (`tagSlabs printed` 0 to 1 over
  about 24 frames, no nozzle). Line: "Designs the part. 58 × 24 × 4.2 mm".
- frames 78 to 150: `home3d_slice`. The tag's layers lift apart (`spread` 1 to about 2.6 and back to 1).
  Line: "21 layers, 13 minutes, 4 g of PLA".
- frames 153 to 210: `home3d_queue`. A blue `Chip` over the plate: "Waiting for the owner's OK". Line: "Queues it.
  It cannot start a print by itself."
From frame 211 a `Wipe` in `#F4F5F7` covers the frame by the last frame.

### approve (330 frames): a person presses Start (the real screen)
`Screen file="screen/backroom.mp4"` (360 source frames, 1920 x 1080; the scene's frame is the source frame). In the
capture the Start button is pressed at source frame 210 and the card then changes to "Printing". Capture pixels:
the top card spans x 482..1698, y 128..757; the 3D preview's centre is (801, 494); the request bubble is at about
(1400, 325); the Start button's centre is (1201, 709).
Camera: whole screen at frame 0, by frame 60 pushed in on the card (centre about (1090, 445), scale about 1.5), by
frame 190 nearer the Start button (scale about 1.8), after the press ease back to the card. Never stop the camera
for more than 2 s; a very slow creep is enough. The pointer (`ptr`) arrives from the right, pauses near the
preview, and clicks Start exactly at frame 210 (`clicks={[210]}`), then leaves.
Words over the screen sit in an ink bar (a rounded ink box with bone `F.text` 600 at 60 px, bottom left, inside the
safe area): "The agent prepares everything." (frames 24 to 150), then "A person presses Start." (frames 160 to
310). `Label kind="screen"` goes top right (`style={{ left: "auto", right: 64, bottom: "auto", top: 124 }}`).
The scene ends zoomed on the card.

### print (300 frames): the print, watched
- frames 0 to 112: `Screen file="screen/watch.mp4"` (270 source frames; the print's percent rises). Capture
  pixels: the card spans x 482..1698, y 128..640; the big percent is at about (1180, 360); the progress bar at
  (1400, 412); the camera picture's centre (801, 435). Start zoomed on the card (the same framing approve ended
  on), creep toward the percent. Ink bar: "Then the plugin watches the print." `Label kind="screen"` top right.
- frames 100 to 114: an ink `Wipe` from where the percent is.
- frames 112 to 300: ink. The plate with the tag printing: `printed` from 0.48 to 1 between frames 124 and 250,
  the `Nozzle` following `nozzleAt`. Left: a giant percent (`F.display` 800, `T.giant`, bone) counting 48 to 100
  with the same progress, and under it "Layer N of 21" (N = floor(printed × 21)). At about frame 150, to the right
  or under: `Words` "0 model calls while it prints." and a `Line`: "A scheduled job checks the printer. No tokens
  spent." At frame 250 the nozzle lifts away and a green "Finished" chip appears.
  End on the finished tag with the view `{ cx: 1180, cy: 640, scale: 2.2, yaw: -0.42, pitch: 0.56 }`.

### box (285 frames): it is in the box
Ink. Starts on exactly the view print ended on, tag finished at the plate's centre, nothing else on screen.
- frames 0 to 50: the view eases out and over so the plate's right edge and the done box beside it come into frame
  (`boxSlabs`, placed just past the plate's right edge, its floor below the plate's level).
- frames 40 to 110: the print head (the `Nozzle`) comes down behind the tag and pushes it to the right, off the
  plate's edge; the tag drops into the box and settles (one small settle, no bouncing ball).
- frame 118: Mıstık's bone bubble (ink text, who "Mıstık", group "Family"): "Mum, your key tag is in the box."
- frame 170: `Words`, `F.display` 800, very large: "Ask. It's in the box." The bubble leaves or shrinks to make
  room. Hold the tagline to the end with the plate still turning slowly.

### twist (330 frames): it printed its own upgrade
- frames 0 to 80: `Photo file="real/rose-box-on-bed.jpg"` (a red rose and a red box on the real bed), dimmed about
  0.35. `Words` (bone, about 110 px, bottom left): "Six weeks on a real printer at home." `Label kind="photo"`
  top left (`style={{ bottom: "auto", top: 124 }}`).
- frames 80 to 170: `Screen file="screen/twist.png"`. Capture pixels: "Where it needed you" heading at (570, 127);
  three rows "Take a finished part off the plate: no auto-eject planned" at y 338, 432, 525 (x 477..1020);
  "Proposed upgrades" at (545, 626); the proposal "Auto-eject: tilted base + push-off preset" at (700, 674) with
  its text down to y 800. Camera: start on the three rows (centre about (850, 400), scale 1.5), move down to the
  proposal (centre about (850, 720), scale 1.5). Ink bar: "It kept needing a person to clear the plate." then (as
  the camera reaches the proposal) "So it proposed an upgrade." `Label kind="screen"` top right.
- frames 170 to 250: `Photo file="real/tilted-base-parts-on-bed.jpg"` (two long dark parts on the real bed).
  `Words`: "A tilted base. The printer printed it." `Label kind="photo"`.
- frames 250 to 330: `Photo file="real/empty-bed-after-push.jpg"` (the real bed, tilted, empty). The owner's
  message as a blue `Bubble` (who "The owner", no group), size about 84: "it fell in by itself". `Label
  kind="photo"`.
Cut between the four parts on motion (each picture already pushing in on its first frame).

### groups (270 frames): one printer, every group
Ink.
- frames 0 to 125: two bubbles arrive one after the other, Family's in red from the left (who "Mum", group
  "Family": "A key tag, red please.") and Lab's in blue from the right (who "Engineer", group "Lab": "A phone stand
  for the bench."). Then `Words` under them, large: "One printer. Every group chat." They leave by frame 125.
- frames 125 to 270: what the plugin is, as four big numbers that count up, in a row or a 2 x 2 grid, each with
  one plain label in `F.text`: 14 "tools", 4 "hooks", 1 "screen in Hermes Desktop", 0 "model calls to watch a
  print". Numbers in `F.display` 800 at `T.huge`; stagger their arrival; the 0 does not count, it lands last.

### close (300 frames): the end card
Ink. `Words` "Ask. It's in the box." in `F.display` 800 at about 190 px, left aligned, from frame 6. At frame 50 a
mono `Chip` (size 40): `hermes plugins install Wijt/hermes-home-3d-workshop`. At frame 70 a `Line` in bone:
"home-3d-workshop, a plugin for Hermes Agent", and under it in mist: "github.com/Wijt/hermes-home-3d-workshop".
On the right a small plate with the finished tag turning slowly through the whole scene (it keeps the card alive).
Everything is on screen by frame 100 and holds to the end.

## Where the built scenes differ from this page

- **Labels.** The screen label reads "The plugin's real screen, on its simulated printer". In `approve` it sits top
  right and steps down when the card turns to "Printing", so it never covers Pause and Stop; `print` keeps it there.
- **approve.** The camera stays on the whole card (scale about 1.5) and leans toward the Start button, because a
  closer framing puts the label and the words over the card's own text.
- **print.** The capture starts at source frame 78, so the screen shows 24% rising to 48%, and the drawn percent
  takes over from the screen's own "48%" where the ink opens. "Layer N of 21" starts at layer 11, as on the screen.
- **box.** The box is 400 x 300 x 120 units at x 747. The tag stays flat as it drops (the kit's slabs cannot tilt)
  and turns a few degrees in plan.
- **twist.** Words on the first photo are top left (the rose is bottom left). The two lines over the screen stack
  in one ink bar. Red marks beside the three rows and the proposal were added. The owner's bubble is 116 px.
- **groups.** The line about each group's colour, tone and rules was cut: there was no time to read it. The four
  numbers step down across the frame instead of sitting in a row.
- **Ground.** The studio's light has a fine grain over it (`media/grain/grain.png`), so video does not draw the
  gradient as rings.
- **Second cut (the owner's notes).** The film now says what the plugin is for the people who ask: plain words in,
  and the agent finds models, shows the options, customises and prepares. `make` is 345 frames with four tools
  (`home3d_find_models`, `home3d_customize`, `home3d_slice`, `home3d_queue`), three drawn model cards and Mum's
  "The second one."; the reply in `ask` is "On it. I'll find a few and show you."; the second line of `title` is
  "Anyone in the chat can ask. Nobody opens a slicer."; the bars in `approve` are "The owner sees the part in 3D."
  and "One tap starts the print."; the small line in `print` ends "If something is off, it tells the owner."
- **Real footage.** The last beat of `twist` (now 120 frames; the scene is 370) is a phone clip of the printer at
  home pushing parts off its plate, then the box with the parts in it, beside the owner's line and "Now it clears
  its own plate." The scene table's frame counts above are the first cut's: `make` 345, `twist` 370, film 2530.
