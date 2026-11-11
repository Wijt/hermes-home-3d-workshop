# Showcase timeline (86 seconds)

The film makes one argument: **the interface to the machine is a member of the group chat. Ask, and it
is in the box.** It follows one request from a voice note to an object in a box, then shows that the
agent improved its own printer and that a second group now uses the same plugin.

Rules the film keeps:

- Under 90 seconds (hackathon rule). This cut is 86 s.
- It works with the sound off. Every beat has its words burned in.
- It shows the plugin working. Captures of the Workshop screen are real captures, never redrawn.
- Nothing is invented. See "Labels" at the end.

## Second by second

| # | Time | Picture | Words on screen | Clip that replaces the picture |
|---|---|---|---|---|
| 1 | 0:00–0:05.5 | **Hook.** Real photo of the rose box on the printer bed, slow push-in. With footage: the finished part slides off the tilted bed into the box, nobody in frame. | "My mother has never opened a slicer." then "She asked a group chat for this." | `01_hook_drop.mp4` |
| 2 | 0:05.5–0:18.5 | **The ask.** The family chat: Mum's voice note with its transcript, Mıstık's reply with a picture of the part, her "Yes!", then "I've asked the owner to approve it." With footage: Mum recording the voice note. | Transcript: "Mıstık, can you make me a rose box?" (original line small above it). Captions: "Mıstık is an agent in the family chat." then "It runs the 3D printer. No app, no slicer." | `02_mum_voice_note.mp4` (keeps its sound) |
| 3 | 0:18.5–0:29.5 | **The back room.** The Workshop screen in Hermes: the card waiting for the owner, the part turning in 3D, the checklist. The pointer presses Start. | "The agent prepares everything." then "A person presses Start." | `03_screen_start.mp4` |
| 4 | 0:29.5–0:37.5 | **The watch.** The Workshop screen: printing, progress rising, the camera frame. With footage: a timelapse of the print. | "Watched by the plugin." then "Zero model calls." | `04_printing_timelapse.mp4` |
| 5 | 0:37.5–0:50.5 | **The delivery.** Real photos: the part on the tilted bed, then the empty bed after the push. Then the chat: Mıstık tells Mum it is ready, with the photo. With footage: the push, then her phone and her hand at the box. | "Printed. Nobody touched the printer." then "Pushed into the done box." then "The person who asked is told." | `05_push_into_box.mp4`, `06_mum_gets_message.mp4` |
| 6 | 0:50.5–1:06 | **The twist.** Real photo of the tilted-base parts on the bed. Then the Workshop screen's list of moments that needed a human, and the upgrade it proposed. | "It kept needing a human to clear the plate." then "So it proposed a tilted base. The printer printed its own upgrade." | `07_tilted_base.mp4` (the photo half only) |
| 7 | 1:06–1:16 | **A second group.** Words on paper. With footage: a real exchange in the lab's chat, if there is one and the lab agrees. | "Same plugin. A second group." then "My manager asked for one for an R&D lab." | `08_lab_chat.mp4` |
| 8 | 1:16–1:26 | **Close.** With footage: the real objects on a table for 2.5 s. Then the end card. | "Ask. It's in the box." then "home-3d-workshop, a Hermes Agent plugin" and "github.com/Wijt/hermes-home-3d-workshop" | `09_objects.mp4` |

## Why this order

1. **The result first.** A part in a box with nobody near the printer is the picture no other entry has.
   The first two seconds are never a logo or a title.
2. **One person, one request.** The film follows Mum's request and nothing else until it is done.
3. **The owner's screen is the proof of the plugin.** Beats 3 and 4 are where a judge sees what a prompt
   or a skill could not be: a rule that waits for a person, and a watcher that needs no model.
4. **The twist earns the second half.** The machine printed the part that lets it deliver.
5. **The second group makes it useful beyond one home.** One line, then stop.

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
