# Shoot list

Nine clips. Each replaces one fallback picture in the film, so shoot the ones you can and skip the rest:
a missing clip never breaks the film. The three that matter most are **01** (the drop), **02** (the voice
note) and **05** (the push).

All clips: **landscape 16:9, 1080p or 4K, 30 fps**, phone on a tripod or resting on something, exposure
and focus locked, room light on. No vertical video. Shoot each clip longer than needed; the film trims it.

## Before you shoot

1. **Pick the object.** Small, with a name on it, under one hour to print, at least 3 mm tall, no wide
   brim, not round (round parts roll past the box), in a colour that stands out from the plate.
2. **Prove the push once.** Print it once and watch it land in the box. Move the box if it misses.
3. **Check the plugin on the real printer.** This is the first run of the plugin's own start, notice and
   plate check on the real printer, so do it before the camera rolls:
   - Follow "Set up with Bambuddy" in the main [README](../../README.md).
   - Run `hermes home3d doctor` and fix what it reports.
   - Run one small job from request to notice with a person beside the printer.
   - If the plugin's start or notice fails on the real printer, keep the simulator captures for beats 3
     and 4 (they are labelled) and do not caption a real-printer shot as driven by the plugin.
4. **Ask the people in the film.** Mum's voice and hands, and anyone in the lab chat. Phone numbers and
   group names must not be readable: cover them or crop them out.
5. **Phones on do-not-disturb**, other windows closed, notifications off on the computer.

## The clips

| File in `media/footage/` | Beat | Used | Shoot | Camera | What happens |
|---|---|---|---|---|---|
| `01_hook_drop.mp4` | 1 Hook | 5.5 s | 20 s | Tripod at bed height, printer and box in frame, nobody visible | The cooled part is pushed and slides into the box. Start recording before the push. This can be a second angle of clip 05. |
| `02_mum_voice_note.mp4` | 2 The ask | 13 s | 30 s | Over her shoulder, phone screen readable, then hold on the chat | She records a voice note to the family group asking for the object (in the film she asks for a rose box). Mıstık answers with the picture. She answers yes. **Keep the sound**: her voice is the heart of the film. |
| `03_screen_start.mp4` | 3 The back room | 11 s | 30 s | Screen recording, 1920x1080, Hermes Desktop on the Workshop page | The approval card is visible. Turn the 3D preview once with the mouse. Press Start. Wait for the reply. |
| `04_printing_timelapse.mp4` | 4 The watch | 8 s | whole print | Tripod, timelapse mode, or the printer's own timelapse | The object grows on the bed. |
| `05_push_into_box.mp4` | 5 The delivery | 7 s | 30 s | Tripod, side view so the fall is visible | Bed cooled, nozzle pushes, part lands in the box. Real time. |
| `06_mum_gets_message.mp4` | 5 The delivery | 6 s | 20 s | Close on her phone on a table, then her hand at the box | The message with the photo arrives. She takes the part out of the box. |
| `07_tilted_base.mp4` | 6 The twist | 9 s | 30 s | Slow hand-held pan, close | Along the tilted base under the printer, ending on the box. |
| `08_lab_chat.mp4` | 7 A second group | 10 s | 20 s | Screen recording of the lab group chat | The engineer's request and the agent's plan and preview. Only if it really happened and the lab agrees. Otherwise skip it. |
| `09_objects.mp4` | 8 Close | 2.5 s | 20 s | Slow pan over a table | The things this printer made for the family: the rose boxes, the phone dock, the small figure that sits on the printer. |

## If the words change

The film subtitles Mum's voice note with the line in `scenes/Ask.tsx`. If she says something else, change
the two strings there (the original line and its English) so the subtitle is what she said.

## An order that fits one day

| When | Do |
|---|---|
| Morning | Checks 1 to 5 above. Start the test print. |
| While it prints | Clip 03 (screen recording), clip 07 (the base), clip 09 (the objects). |
| Second print | Clip 02 first (the request), then start the print: clip 04 runs by itself. |
| When it finishes | Clips 01 and 05 (two angles of the same push, or two prints), then clip 06. |
| Afternoon | Clip 08 if the lab chat is real by then. Copy the clips, render, watch it once with the sound off. |
| By early evening | Post and submit (below). The deadline is 5 PM EST on November 11, which is 01:00 on November 12 in Istanbul. |

## Make the film

1. Copy the clips into `docs/showcase/media/footage/` with the names above.
2. Render `final.tsx` with the commands in [README.md](README.md).
3. Watch it with the sound off. Every beat should still make sense.
4. The film with her voice has sound. X expects AAC audio; the README gives the one conversion command
   (it needs `ffmpeg`).

No time to shoot? Post the motion-graphics film, `out/home-3d-workshop-film.mp4` (84 seconds, 1920x1080,
with sound, AAC, ready for X; `out/home-3d-workshop-film-silent.mp4` is the same picture with no sound). It
is drawn scenes, real captures of the plugin on its simulated printer, real photos from the printer's
camera and real footage of the printer at home, each labelled as such. [README.md](README.md) says how it is built. The earlier
cut is `out/fallback-final.mp4`.

## Post and submit

1. **Post on X.** The video, under 90 seconds, tagging `@NousResearch`. A text that fits:

   > My mother has never opened a slicer. She asks Mıstık in our family group chat, and it is waiting in
   > the box. home-3d-workshop: a Hermes Agent plugin that makes a 3D printer a member of your group
   > chat. @NousResearch
   > github.com/Wijt/hermes-home-3d-workshop

2. **Submit the form**: https://form.typeform.com/to/FwJLvOln. It asks for the plugin title, a
   description, your email, your Discord username, the X post link and the pull request link.

   - Plugin title: `Home 3D Workshop (home-3d-workshop)`
   - Pull request: https://github.com/NousResearch/hermes-agent/pull/153024
   - A description that fits (it says only what the README's status table supports):

     > Ask. It's in the box. With this plugin a 3D printer becomes one of the family. Anyone in the group
     > chat asks in plain words, often by voice note, and nobody opens a slicer. Mıstık finds models and
     > shows the options, customises one or designs the part in OpenSCAD, slices it and queues it, then
     > tells the person who asked, by name, when it starts and when it is in the box. The owner is the
     > technical contact: he hears about failures and sets the rules, including who may start a print
     > (himself only by default, or the people in the household list for their own jobs). In Hermes
     > Desktop one Workshop screen shows it all: the part in 3D on the build plate, the slice facts, a
     > safety checklist, Start, Pause and Stop, the queue, the done box, messages, filament and a setup
     > check. It works with a Bambu Lab printer through Bambuddy, or with the built-in simulated printer
     > (`hermes home3d demo`).

3. **Add the X link** as a comment on that pull request.
