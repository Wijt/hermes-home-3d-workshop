# Showcase timeline (79 seconds)

The film makes one argument: **ask the group chat for an object, and it is in the box.** It follows one
request, Mum's key tag, from a chat message to the done box, shows the plugin's own screen where a person
presses Start, then the twist (the printer printed its own upgrade), then what the plugin is.

It is a motion-graphics film. The drawn scenes take their look from the plugin: the dark studio and the
bronze build plate of the Workshop screen, the red of the filament, the blue of the Start button, and a chat
bubble in the group's colour. The plugin itself is never redrawn: it appears as real captures of the Workshop
screen, full frame.

Rules the film keeps:

- Under 90 seconds (hackathon rule). This cut is 79 s.
- It works with the sound off: every beat has its words on screen. The sound is a marimba bed and a few
  sounds on physical moments (a message landing, the press of Start, the part dropping into the box).
- Nothing is invented. See "What is real" at the end.

## Second by second

| # | Time | Scene | Picture | Words on screen |
|---|---|---|---|---|
| 1 | 0:00 to 0:06.5 | `ask` | Mum's message types itself into a red bubble; Mıstık answers from the right. Mum's red then grows until it fills the frame. | "Mıstık, can you make me a key tag with MUM on it? Red please." and "On it. I'll ask the owner to approve the print." |
| 2 | 0:06.5 to 0:11 | `title` | Red ground, big words. | "A 3D printer in the group chat." and "home-3d-workshop, a plugin for Hermes Agent" |
| 3 | 0:11 to 0:18.5 | `make` | Three of the plugin's tools, one at a time. On a tile of the build plate the key tag rises out of the sheet, its 21 layers lift apart, and it waits under a blue note. | `home3d_design` "Designs the part. 58 × 24 × 4.2 mm", `home3d_slice` "21 layers, 13 minutes, 4 g of PLA", `home3d_queue` "Queues it. It cannot start a print by itself.", note "Waiting for the owner's OK" |
| 4 | 0:18.5 to 0:29.5 | `approve` | The real Workshop screen, full frame: the approval card with the part turning in 3D and the six checks. The camera moves in; the pointer presses Start; the card changes to Printing. | "The agent prepares everything." then "A person presses Start." |
| 5 | 0:29.5 to 0:39.5 | `print` | The real screen while the percent rises, then the drawn plate: the tag printed layer by layer under the print head, a giant percent counting to 100. | "Then the plugin watches the print.", "0 model calls while it prints." and "A scheduled job checks the printer. No tokens spent." |
| 6 | 0:39.5 to 0:49 | `box` | The print head pushes the finished tag off the plate; it drops into the done box. Mıstık tells Mum. | "Mum, your key tag is in the box." then "Ask. It's in the box." |
| 7 | 0:49 to 1:00 | `twist` | A real photo of prints on the real bed; the real screen's list of moments that needed a person and the upgrade it proposed; a real photo of the tilted-base parts; a real photo of the empty tilted bed with the owner's message. | "Six weeks on a real printer at home.", "It kept needing a person to clear the plate.", "So it proposed an upgrade.", "A tilted base. The printer printed it." and the owner: "it fell in by itself" |
| 8 | 1:00 to 1:09 | `groups` | A red message from Family and a blue one from Lab; then four numbers. | "One printer. Every group chat.", then 14 tools, 4 hooks, 1 screen in Hermes Desktop, 0 model calls to watch a print |
| 9 | 1:09 to 1:19 | `close` | The end card, with the finished tag turning on its plate. | "Ask. It's in the box.", `hermes plugins install Wijt/hermes-home-3d-workshop`, "home-3d-workshop, a plugin for Hermes Agent", "github.com/Wijt/hermes-home-3d-workshop" |

The exact frames and the rules every scene keeps are in [mg/BOARD.md](mg/BOARD.md).

## Why this order

1. **One person, one request.** The film opens on Mum's message and follows it until the part is in the box.
2. **The owner's screen is the proof of the plugin.** Scenes 4 and 5 are where a judge sees what a prompt or a
   skill could not be: a rule that waits for a person, and a watcher that needs no model.
3. **The twist earns the second half.** The machine printed the part that lets it deliver.
4. **The second group makes it useful beyond one home.** One line, four numbers, then the end card.

## What is real

| Picture | What it is | Label on screen |
|---|---|---|
| The chat bubbles | Re-created from real chats, names changed | "Re-created from real chats. Names changed." |
| The Workshop screen (scenes 4, 5 and 7) | Real captures of the plugin in Hermes on its built-in simulated printer | "The plugin's real screen, on its simulated printer" |
| The photos (scene 7) | From the real printer's camera | "Real photo from the printer's camera" |
| The key tag, the plate, the print head, the box | Drawings | none |

The numbers are read off the capture (58 × 24 × 4.2 mm, 21 layers, 13 minutes, 4 g of PLA) or off the plugin
(14 tools, 4 hooks, the watcher's 0 model calls). "it fell in by itself" is the owner's own line, from the story
in the main README.

What the film must not say:

- That the plugin's own start, stop or auto-eject was verified on the real printer, until it has been. The
  real photos come from six weeks of the same agent running this printer with scripts and skills, which the
  plugin packages. The push into the box is a drawing.
- Any number that was not measured.
- Any real name, phone number or group name.

## The first cut

The earlier film (86 s, silent: photos and captions on paper) is still here as `fallback.tsx`, and
`final.tsx` is that cut with slots for shot footage ([SHOOT-LIST.md](SHOOT-LIST.md)). Its timeline is in this
file's history.
