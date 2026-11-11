# Showcase timeline (88 seconds)

The film makes one argument: **the interface to the machine is a member of the group chat. Ask, and it
is in the box.** It follows one request from a voice note to an object in a box, then shows that the
agent improved its own printer and that a second group now uses the same plugin.

Rules the film keeps:

- Under 90 seconds (hackathon rule). This cut is 88 s.
- It works with the sound off. Every beat has its words burned in.
- It shows the plugin working. Screen captures of the Workshop screen are real captures, never redrawn.
- Nothing is invented. See "Labels" at the end.

## Second by second

| # | Time | Picture | Words on screen | Sound | Clip (fallback if the clip is missing) |
|---|---|---|---|---|---|
| 1 | 0:00–0:05 | **The drop.** The finished part slides off the tilted bed into the box. Nobody is in the frame. | "My mother has never opened a slicer." then "She asked a group chat for this." | Room sound, the part landing | `01_hook_drop.mp4` (real photo of the rose box on the bed) |
| 2 | 0:05–0:19 | **The ask.** Mum, phone in hand, records a voice note to the family group. Cut to the chat: her voice note, Mıstık's reply with a picture of the part, her "Yes". | Subtitle of her words in English (original line small above it). Caption: "She asks. No app, no slicer." | Her real voice | `02_mum_voice_note.mp4` (re-created chat) |
| 3 | 0:19–0:33 | **The back room.** Hermes Desktop, the Workshop screen: the card "Waiting for you", the part turning in 3D, the checklist. The owner presses Start. | "The agent prepares everything. A person presses Start." | Click | `03_screen_start.mp4` (capture on the simulated printer) |
| 4 | 0:33–0:45 | **The watch.** Timelapse of the print. The Workshop screen shows progress and the camera frame. | "Watched by the plugin. Zero model calls." | None | `04_printing_timelapse.mp4` (capture on the simulated printer) |
| 5 | 0:45–0:58 | **The delivery.** The bed cools, the nozzle pushes, the part lands in the box. Mum's phone lights up with the message and the photo. She takes the part from the box. | "Pushed into the done box. The person who asked is told." | The push, the notification | `05_push_into_box.mp4`, `06_mum_gets_message.mp4` (real photos: part on the bed, empty bed; re-created chat) |
| 6 | 0:58–1:10 | **The twist.** Slow pan along the tilted base under the printer. Then the Workshop screen's "needed a human" list and the upgrade proposal. | "It kept needing a human to clear the plate." then "So it proposed an upgrade, and the printer printed it." | None | `07_tilted_base.mp4` (real photo of the base parts on the bed; capture on the simulated printer) |
| 7 | 1:10–1:20 | **Another group.** A second chat, an R&D lab: an engineer describes a bracket, the agent answers with a short plan and a preview. | "Same plugin. My R&D lab asked for one." | None | `08_lab_chat.mp4` (re-created chat) |
| 8 | 1:20–1:28 | **Close.** The real objects on a table. Then the end card, held 2.5 s. | "Ask. It's in the box." then "home-3d-workshop, a Hermes Agent plugin" and "github.com/Wijt/hermes-home-3d-workshop" | None | `09_objects.mp4` (end card on colour) |

## Why this order

1. **The result first.** A part falling into a box with nobody near the printer is the picture no other
   entry has. The first two seconds must not be a logo or a title.
2. **One person, one request.** The film follows Mum's request and nothing else until it is in her hand.
3. **The owner's screen is the proof of the plugin.** Beats 3 and 4 are where a judge sees code that a
   prompt or a skill could not be: a rule that waits for a person, and a watcher that needs no model.
4. **The twist earns the second half.** The machine printed the part that lets it deliver.
5. **The lab makes it useful beyond one home.** One line, one picture, then stop.

## Labels

Each kind of picture that is not live footage carries a small label on screen:

| Picture | Label |
|---|---|
| A chat that was typed again for the film | "Re-created from real chats. Names changed." |
| A photo from the printer's camera archive | "Real photo from the printer's camera" |
| The Workshop screen on the simulator | "Plugin running on its built-in simulated printer" |

What the film must not say:

- That the plugin's own start, stop or auto-eject was verified on the real printer, until it has been.
  The real photos come from six weeks of the same agent running this printer with scripts and skills,
  which the plugin packages.
- Any number that was not measured.
- Any real name, phone number or group name.

## Two versions

- **`fallback.tsx`** needs no new footage: real photos, re-created chats and simulator captures. It is the
  film to post if there is no time to shoot.
- **`final.tsx`** is the same film. Each beat uses the clip named in the table when that file is in
  `media/footage/`, and the fallback picture when it is not. So one good clip already improves the film,
  and a missing clip never breaks it.

The exact render commands are in [README.md](README.md). What to shoot is in [SHOOT-LIST.md](SHOOT-LIST.md).
