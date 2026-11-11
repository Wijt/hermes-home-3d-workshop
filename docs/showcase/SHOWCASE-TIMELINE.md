# Showcase timeline (84 seconds)

The film makes one argument: **anyone in the chat can ask for an object, in their own words, and it ends up
in the box.** Nobody opens a slicer. It follows one request, Mum's key tag, through what the agent does for
her (finds models, shows the options, makes the chosen one hers, prepares the print), the owner's one tap on
the plugin's own screen, the print, and the box. Then the twist (the printer printed its own upgrade, with
real footage of it clearing its plate), then what the plugin is.

It is a motion-graphics film. The drawn scenes take their look from the plugin: the dark studio and the
bronze build plate of the Workshop screen, the red of the filament, the blue of the Start button, and a chat
bubble in the group's colour. The plugin itself is never redrawn: it appears as real captures of the Workshop
screen, full frame.

Rules the film keeps:

- Under 90 seconds (hackathon rule). This cut is 84 s.
- It works with the sound off: every beat has its words on screen. The sound is a marimba bed and a few
  sounds on physical moments (a message landing, the press of Start, the part dropping into the box).
- Nothing is invented. See "What is real" at the end.

## Second by second

| # | Time | Scene | Picture | Words on screen |
|---|---|---|---|---|
| 1 | 0:00 to 0:06.5 | `ask` | Mum's message types itself into a red bubble; Mıstık answers from the right. Mum's red then grows until it fills the frame. | "Mıstık, can you make me a key tag with MUM on it? Red please." and "On it. I'll find a few and show you." |
| 2 | 0:06.5 to 0:11 | `title` | Red ground, big words. | "A 3D printer in the group chat." and "Anyone in the chat can ask. Nobody opens a slicer." |
| 3 | 0:11 to 0:22.5 | `make` | Four of the plugin's tools, one at a time. Three models it found, as cards; Mum picks one; that model lands on a tile of the build plate, gets her name and turns red; its 21 layers lift apart; it waits under a blue note. | `home3d_find_models` "Finds models online and shows the options.", Mum: "The second one.", `home3d_customize` "Makes it hers: her name, in red.", `home3d_slice` "21 layers, 13 minutes, 4 g of PLA", `home3d_queue` "Six safety checks, then the owner's OK.", note "Waiting for the owner's OK" |
| 4 | 0:22.5 to 0:33.5 | `approve` | The real Workshop screen, full frame: the card with the part turning in 3D and the six checks. The camera moves in; the pointer presses Start; the card changes to Printing. | "The owner sees the part in 3D." then "One tap starts the print." |
| 5 | 0:33.5 to 0:43.5 | `print` | The real screen while the percent rises, then the drawn plate: the tag printed layer by layer under the print head, a giant percent counting to 100. | "Then the plugin watches the print.", "0 model calls while it prints." and "A scheduled job checks the printer. If something is off, it tells the owner." |
| 6 | 0:43.5 to 0:53 | `box` | The print head pushes the finished tag off the plate; it drops into the done box. Mıstık tells Mum. | "Mum, your key tag is in the box." then "Ask. It's in the box." |
| 7 | 0:53 to 1:05.3 | `twist` | A real photo of prints on the real bed; the real screen's list of moments that needed a person and the upgrade it proposed; a real photo of the tilted-base parts; then real footage: the printer at home pushing parts off its plate, and the box with the parts in it. | "Six weeks on a real printer at home.", "It kept needing a person to clear the plate.", "So it proposed an upgrade.", "A tilted base. The printer printed it.", the owner: "it fell in by itself", and "Now it clears its own plate." |
| 8 | 1:05.3 to 1:14.3 | `groups` | A red message from Family and a blue one from Lab; then four numbers. | "One printer. Every group chat.", then 14 tools, 4 hooks, 1 screen in Hermes Desktop, 0 model calls to watch a print |
| 9 | 1:14.3 to 1:24.3 | `close` | The end card, with the finished tag turning on its plate. | "Ask. It's in the box.", `hermes plugins install Wijt/hermes-home-3d-workshop`, "home-3d-workshop, a plugin for Hermes Agent", "github.com/Wijt/hermes-home-3d-workshop" |

The exact frames and the rules every scene keeps are in [mg/BOARD.md](mg/BOARD.md).

## Why this order

1. **One person, one request.** The film opens on Mum's message and follows it until the part is in the box.
2. **The agent does the work, in her words.** Scene 3 is the point of the plugin for the people who ask: it
   finds models, shows the options, takes "the second one" for an answer, makes it hers and prepares the
   print. Nobody learns a slicer.
3. **The owner's screen is the proof of the plugin.** Scenes 4 and 5 are where a judge sees the plugin itself:
   the part in 3D, the checks, one tap, and a watcher that needs no model and tells the owner when something
   is off.
4. **The twist earns the second half.** The machine printed the part that lets it deliver, and the footage
   shows it doing so.
5. **The second group makes it useful beyond one home.** One line, four numbers, then the end card.

## What is real

| Picture | What it is | Label on screen |
|---|---|---|
| The chat bubbles | Re-created from real chats, names changed | "Re-created from real chats. Names changed." |
| The Workshop screen (scenes 4, 5 and 7) | Real captures of the plugin in Hermes on its built-in simulated printer | "The plugin's real screen, on its simulated printer" |
| The photos (scene 7) | From the real printer's camera | "Real photo from the printer's camera" |
| The footage (scene 7) | Filmed at home on a phone: the real printer pushing parts off its plate, and the box | "Real footage of the printer at home" |
| The key tag, the three model cards, the plate, the print head, the box | Drawings | none |

The numbers are read off the capture (58 × 24 × 4.2 mm, 21 layers, 13 minutes, 4 g of PLA) or off the plugin
(14 tools, 4 hooks, the watcher's 0 model calls). "it fell in by itself" is the owner's own line, from the story
in the main README.

What the film must not say:

- That the plugin's own start, stop or auto-eject was verified on the real printer, until it has been. The
  real photos and the footage come from the same agent running this printer at home with scripts and skills,
  which the plugin packages. The key tag's push into the box is a drawing; the footage shows other parts.
- That a search found particular models: the three cards are drawings of the step, not search results.
- Any number that was not measured.
- Any real name, phone number or group name.

## The first cut

The earlier film (86 s, silent: photos and captions on paper) is still here as `fallback.tsx`, and
`final.tsx` is that cut with slots for shot footage ([SHOOT-LIST.md](SHOOT-LIST.md)). Its timeline is in this
file's history.
