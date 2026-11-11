# Showcase film

An 88 s film (1920 x 1080, 30 fps, silent) for the `home-3d-workshop` Hermes Agent plugin, built with raea.
Read `~/.claude/skills/raea/SKILL.md` and `raea guide craft` before editing a composition.

## Layout

| Path | What |
|---|---|
| `theme.ts` | colours, faces, sizes, margins, the three honesty labels, the people's names |
| `components/` | shared parts: `Caption`, `BigWords`, `Chat`, `PhotoStage`, `ScreenStage`, `Label`, `EndCard`, `PartTurntable`, `Icons`, `media.ts`, `timing.ts`; `index.ts` re-exports all but `PartTurntable` |
| `scenes/N-id.tsx` | one file per storyboard scene; each exports a default component and `DURATION` |
| `scene-id.tsx` | a preview root per scene (generated, do not edit) |
| `fallback.tsx` | the film with no new footage (same as `film.tsx`, id `fallback`): the one to render now |
| `final.tsx` | the same film; each beat uses its clip from `media/footage/` when the clip is there, else the fallback picture |
| `components/Footage.tsx` | the clip names (`CLIPS`), where each clip starts (`CLIP_START_SECONDS`), the cover-fit trimmed `Footage` |
| `film.tsx` | the whole film: places each scene at its time from `SCENES` in `components/timing.ts`, crossfades 10 frames |
| `test-components.tsx`, `test-turntable.tsx` | proof roots for the components |
| `media/real/` | real photos from the printer's camera and the slicer render (git-ignored) |
| `media/screen/` | captures of the Workshop screen on the built-in simulated printer, PNG or MP4 (git-ignored) |
| `media/footage/` | any new footage (git-ignored) |
| `media/models/` | `name-tag-mum.stl` and `.glb`, rendered from the plugin's `home3d/templates/name_tag.scad` |
| `media/manifest.json` | what is in `media/`, written by `tools/scan_media.py` (git-ignored) |
| `tools/` | `scan_media.py`, `stl_to_glb.py` |

A root file must sit in this folder: raea serves `media/` from the folder of the file it renders.
A file that calls `registerRoot` cannot be imported by another, so scenes never call it.

## Adding media

1. Put the file in `media/real/`, `media/screen/` or `media/footage/`. Use neutral, descriptive names
   (`waiting-for-you.png`, `printing.mp4`). Never a person's name.
2. Run `python3 -I tools/scan_media.py`. It rewrites `media/manifest.json`.
   Do this after every add, rename or delete. The components read it to know which files exist. A missing
   screen capture shows a "Workshop screen capture goes here" card, and a missing photo shows a placeholder.
   The render does not fail. If the manifest lists a file that has since been deleted, the render fails and
   names it.
3. On a fresh clone, run the scan once before rendering (the manifest is git-ignored).

Captures for scenes 3, 4 and 6 go in `media/screen/`. The names follow SHOOT-LIST.md where it names one:
`03_screen_start.mp4` (or a still, `03_screen_start.png`), `04_printing.mp4`/`.png`, `06_needed_a_human.png`.
Scene authors may pick other names; `ScreenStage` shows the placeholder until the named file exists.
New footage from SHOOT-LIST.md goes in `media/footage/` under the names given there.

## Preview, check, render

```sh
python3 -I tools/scan_media.py
raea render scene-ask.tsx --at 15,120,400 -o stills/ask/     # stills to look at (named frame-00000.png ... in --at order)
raea check scene-ask.tsx --quick                            # clipped text, safe areas, reading time
raea render film.tsx --at 75,600,2600 -o stills/film/
raea media sheet stills/ask/*.png --width 480 -o stills/ask-sheet.png
raea render film.tsx -o out/film.mp4 --quality master       # only when asked: long on this machine
```

This machine has no GPU. A type frame takes about 0.15 s, a clip frame about 0.3 s, a 3D frame about 0.9 s, and
each command adds about 10 s. Render stills while working.
`raea check --quick` has missed text that runs off a phone, so always look at the stills.
`raea check VIDEO.mp4` needs ffprobe, which is not installed: use stills and contact sheets.

## Rules (a critic checks them)

- No real names, numbers, group ids or addresses anywhere, including file names and comments. People are
  Mum, Dad, Sam, Engineer, Owner. The agent is Mıstık.
- Each re-created chat shows "Re-created from real chats. Names changed." (`Chat` adds it).
  Each real photo shows "Real photo from the printer's camera" (`PhotoStage` adds it).
  Each Workshop capture shows "Plugin running on its built-in simulated printer" (`ScreenStage` adds it when the capture exists).
- Do not redraw the Workshop screen. Show real captures only.
- Do not invent numbers, logos, testimonials or footage. Do not say the plugin was verified on the real printer
  for start, stop or auto-eject. The photos come from six weeks of the same agent running this printer with
  scripts and skills, which the plugin now packages.
- No brand logos. Do not copy a real messaging app's look.
- English on screen. Turkish only for Mum's original line.
- Silent: no `<Audio>`.

## Real photos in media/real

| File | Shows | Use |
|---|---|---|
| `rose-box-on-bed.jpg` | red rose and red latticed box on the bed | scene 1 hook |
| `rose-box-slicer-render.png` | slicer render of the rose box, transparent | scene 2, Mıstık's picture |
| `latticed-box-on-tilted-bed.jpg` | the latticed box alone on the bed | scene 5, before the push |
| `empty-bed-after-push.jpg` | empty bed after a part was pushed off | scene 5, after the push |
| `tilted-base-parts-on-bed.jpg` | the two tilted-base parts on the bed | scene 6 twist |
| `rose-and-ring-on-bed.jpg` | rose lid and ring on the bed (1280 x 900) | spare, close or delivery photo |

## Real footage (final.tsx)

`final.tsx` is the same 86 s film as `fallback.tsx`. For each beat, a clip with the agreed name in `media/footage/`
replaces the fallback picture, with the same words and captions on top. A beat with no clip keeps its fallback.
No code edits are needed:

1. Copy the clips into `media/footage/` with exactly these names (any you did not shoot, leave out):
   `01_hook_drop.mp4`, `02_mum_voice_note.mp4`, `03_screen_start.mp4`, `04_printing_timelapse.mp4`,
   `05_push_into_box.mp4`, `06_mum_gets_message.mp4`, `07_tilted_base.mp4`, `08_lab_chat.mp4`, `09_objects.mp4`.
2. Run `python3 -I tools/scan_media.py` (the film reads `media/manifest.json` to know which clips exist).
3. Render: `raea render final.tsx -o out/final.mp4 --quality master`
   (check one frame first: `raea render final.tsx --at 100,500 -o stills/final/`).

How a clip is used: cover-fitted to 1920 x 1080, cut from its start to the length of its beat (hook 5 s, ask 14 s,
back room 14 s, watch 12 s, push 7.3 s, message from 6.9 s to the end of the delivery beat, tilted base 8 s,
lab 10 s, objects 2.5 s under the closing line). Only clip 02 keeps its sound; the others are muted. To start a
clip later in its file, change its number of seconds in `CLIP_START_SECONDS` in `components/Footage.tsx`.

Mapping: 01 hook, 02 ask (with the English subtitle and the Turkish line, so edit those two strings in
`final.tsx` `AskBeat` if she says something else), 03 back room, 04 watch, 05 and 06 delivery (05 replaces the two
photos, 06 replaces the chat), 07 twist (the Workshop capture of the second half stays), 08 group, 09 close.

Honesty with footage: the three labels are not added to clips, except that clip 03 shows "Plugin running on its
built-in simulated printer" because `LABEL_CLIP_03_AS_SIMULATED` in `final.tsx` is true. Set it to false only
if clip 03 was recorded on the real printer. Clip 08 must have names and group titles covered, and if it is a
re-creation, add the re-created label. Do not caption a real-printer clip as the plugin driving it unless the
plugin did.

## Sound for X

`fallback.tsx` has no audio track, so its file can be posted as it is. `final.tsx` keeps the sound of clip
02 (the voice note). raea writes that sound as Opus, and X expects AAC, so convert once (this needs
`ffmpeg`, which is not installed on this machine):

```sh
ffmpeg -i out/final.mp4 -c:v copy -c:a aac -b:a 128k -movflags +faststart out/final-x.mp4
```

See also [SHOWCASE-TIMELINE.md](SHOWCASE-TIMELINE.md) for the film second by second and
[SHOOT-LIST.md](SHOOT-LIST.md) for the nine clips to shoot.
