# Demo video plan (under 90 seconds)

> **This plan is the earlier one.** The current film, its second-by-second timeline, the shoot list and
> the project that renders it are in [`showcase/`](showcase/): see
> [SHOWCASE-TIMELINE.md](showcase/SHOWCASE-TIMELINE.md) and [SHOOT-LIST.md](showcase/SHOOT-LIST.md).
> The honesty rules below still apply.

Goal: show the plugin working, in a real home, in 86 seconds. Real footage beats animation. The audio is
Turkish (the household language) with English subtitles. Subtitle files:

- [`demo/subtitles.en.srt`](demo/subtitles.en.srt): the audio and the Turkish chat text on screen, in
  English.
- [`demo/subtitles.tr.srt`](demo/subtitles.tr.srt): the Turkish audio only (voice-over and voice note).
  The chat on screen is already Turkish, so this file does not repeat it.

The owner records the footage. This file gives the script, the shot list, what is real and what is
staged, and an anonymised variant.

## Honesty rules

1. Never show simulator output as if it came from the real printer. Every simulator screen gets the
   label **"simulator"** in a corner.
2. Every re-enacted scene (a person reads a line again, a test chat stands in for the family chat) gets
   the label **"re-enacted"**.
3. Footage and photos from before the plugin existed get the label **"original setup, Oct 2026"**. The
   plugin did not exist then. Do not say that the plugin did it.
4. Show a blocked action as blocked. Do not cut it out.
5. Use the real numbers from the real slice (time, grams). Then update the subtitle files.

## Script (86 s)

VO = voice-over by the owner, in Turkish. The owner reads the Turkish lines in
[`demo/subtitles.tr.srt`](demo/subtitles.tr.srt). The table gives the English subtitle text. Times are
m:ss. Subtitle cues end at 1:25.0; the end card holds to 1:26. Every cue runs at 17 characters per
second or slower, so it can be read while the chat is on screen. If you change a cue, keep that limit.

| Time | Shot | Picture | Audio (English subtitle text) |
|---|---|---|---|
| 0:00-0:07 | 1. Hook | The A1 on its tilted base. The bed moves, a finished part slides off into the box in front. | VO: "My mum doesn't know CAD or 3D printers. She just talks to Mıstık." |
| 0:07-0:19 | 2. Request | Phone, family chat. Mum's voice note plays for 3 s. Mıstık answers with two MakerWorld pictures and print times. Mum picks one. | Voice note: "Mıstık, can you print me a little gift box for flowers?" Then chat captions (see the SRT files). No VO. |
| 0:19-0:36 | 3. Safety | Mum: "Lovely, print it please!" A red "blocked" overlay on the agent's tool call. Mıstık: queued, passed on to the owner. The owner's phone: the watcher's message "Mum asks to start #7", then `/home3d approve start 7` and the reply "Started". | Chat captions, then VO: "The rules are in code. Only the owner starts. Anyone can stop." |
| 0:36-0:44 | 4. Watch | Camera timelapse of the print. Small overlay: "watcher: every 2 min, 0 tokens". | VO: "A watcher checks the printer every two minutes. No model calls, no tokens. It writes only when something happens." |
| 0:44-0:55 | 5. Done | The printer at the end of the print: the bed has cooled, the nozzle pushes the part, it slides into the box. Then the family chat: "Mum, the flower box is done..." with the photo taken before the push. Then the owner chat: the technical note with the photo (2 s). | VO: "At the end, the bed cools and the printer pushes the part off." Then chat captions. |
| 0:55-1:12 | 6. The twist | Photos with dates: the first push test, the part stuck at the front edge (25 Oct); the tilted base parts on the plate; the base installed. Then the `/home3d upgrades` screen with the proposal. | VO: "We asked it to clear the plate without a person. It tried a push, and the part got stuck at the front. It found a tilted base and printed its own upgrade. The plugin makes this a rule: when a human task repeats, it proposes an upgrade." |
| 1:12-1:21 | 7. Try it | Terminal: `hermes plugins install Wijt/hermes-home-3d-workshop --enable`, then `hermes home3d demo` scrolls fast. | VO: "No printer? Try it with the simulator. Install it with --enable, then run hermes home3d demo." |
| 1:21-1:26 | 8. End card | "home-3d-workshop · a Hermes Agent plugin · github.com/Wijt/hermes-home-3d-workshop". | VO: "Mıstık. The home's 3D workshop." |

### Chat lines on screen (Turkish)

These lines follow `hermes home3d demo --lang tr`. Two kinds of text are in it:

- **Scripted persona lines** (Mıstık's replies in shots 2 and 3). The demo prints them as `[staged]`.
  In a real chat the model words its own replies, so the real words can differ. They must say the same
  thing: never that a print will start.
- **The plugin's own text** (the watcher's request to the owner, the `/home3d approve` reply and the
  family notice in shot 5). The plugin writes these words itself. Use them as they are.

Put the real queue number, model name and times in place of `#7`, `<model name>` and the times. "Sam" is
the demo's owner name; the real chat shows the configured `owner_name`.

| Shot | Who | Text on screen | Source | English subtitle |
|---|---|---|---|---|
| 2 | Mıstık | Anneciğim, iki tane buldum (resimler aşağıda): 1) çiçek kutusu, yaklaşık 2 saat 16 dakika 2) saksı, yaklaşık 4 saat 34 dakika. Hangisi olsun? | scripted | Mum, I found two. 1) Flower box, 2 h 16 min. 2) Plant pot, 4 h 34 min. Which one? |
| 2 | Mum | İlki olsun, beyaz kutu. | Mum | The first one, a white box. |
| 3 | Mum | Çok güzel, bas lütfen! | Mum | Lovely, print it please! |
| 3 | Mıstık | Sıraya ekledim (#7). Sam'a ilettim, ne zaman başlayacağına o karar verecek. | scripted | Queued, and I told the owner. The owner decides when it starts. |
| 3 | Mıstık (owner chat) | 🙋 Annem #7 "<model name>" işinin başlatılmasını istiyor (2 sa 16 dk, 77 g). Başlatmak için: /home3d approve start 7 | plugin (watcher) | Mum asks to start #7. |
| 3 | Owner | /home3d approve start 7 → ▶️ #7 "<model name>" başladı (Annem). Bitişi ve tablayı izleyip haber vereceğim. | plugin (`/home3d`) | Owner approves: Started #7. |
| 5 | Mıstık (family chat) | ✅ Anneciğim, "çiçek kutusu" bitti. Otomatik düşürüldü, kutudan alabilirsin. | plugin (watcher) | Mum, the flower box is done. It dropped off: take it from the box. |

When the printer is free and the camera thinks the plate is empty, the watcher puts the request into its
"next job ready" message instead ("Annem başlatılmasını istedi."). Either message is real.

## Shot list

| # | Length | What to capture | Source | How |
|---|---|---|---|---|
| 1 | 7 s | Part slides off the tilted A1 into the box | Real printer | Phone on a tripod, landscape 1080p, at plate height. Frame only the printer and the box. |
| 2a | 3 s | Mum's voice note in the chat | Real chat (with consent) or re-enacted | Phone screen recording. |
| 2b | 9 s | Mıstık's reply with two model pictures; Mum's pick | Real plugin on the household gateway (planned) or re-enacted test chat | Phone screen recording, scroll slowly. |
| 3a | 8 s | Mum: "Lovely, print it please!", the blocked start, Mıstık: "queued, passed on to the owner" | Same as 2b, or the `hermes home3d demo` steps 7 and 8 | Add the red "blocked" overlay in the edit. |
| 3b | 5 s | The owner's chat: the watcher's request with the command, then `/home3d approve start <id>` and "Started" | Owner's own chat with Hermes (real) | Phone screen recording. Simulated printer: label "simulator". |
| 3c | 4 s | Hold on the owner's chat for the VO | Same as 3b | - |
| 4 | 8 s | Print timelapse | Real printer (Bambuddy timelapse or archive) | Export from Bambuddy, speed up. |
| 5a | 4 s | Bed cooled, nozzle pushes, part slides into the box (the end of the print) | Real printer | Same tripod as shot 1. Real time, then speed up the cooling wait. |
| 5b | 5 s | Family notice with the photo taken before the push | Real watcher on the real printer (planned) or the simulator outbox | Phone screen recording. Simulator: label "simulator". |
| 5c | 2 s | Owner notice: layers, temperatures, photo | Same as 5b | Phone screen recording. |
| 6a | 11 s | Push-test photo, base parts printing, base installed | Real archive photos (Bambuddy archive, chat photos) | Ken Burns pan, date captions. Label "original setup, Oct 2026". |
| 6b | 6 s | `/home3d upgrades` with "Auto-eject: tilted base + push-off preset, 3x" | `hermes home3d demo` or a real chat after real moments | Label "simulator" unless it is real. |
| 7 | 9 s | `hermes plugins install Wijt/hermes-home-3d-workshop --enable`, then `hermes home3d demo` | Terminal, simulator by design | Font 18 pt or more, 100 columns, light theme. Record in a throwaway `HERMES_HOME`. Type exactly this install command: without `--enable`, `hermes home3d` is not found. |
| 8 | 5 s | End card | Edit | Plain background, repo link, "#NousResearch". |

Prepare the terminal and simulator material in a throwaway profile:

```bash
export HERMES_HOME=$(mktemp -d)
hermes plugins install Wijt/hermes-home-3d-workshop --enable
hermes home3d demo --lang tr --keep      # keeps the photos, the outbox and the database
```

## What is real and what is staged

| Item | Real | Staged or simulated |
|---|---|---|
| The household, the A1 on a self-printed tilted base, the box in front | Yes | - |
| Auto-eject push (shots 1 and 5a) | Yes. The printer preset's end G-code pushes at the end of the print, not the plugin; the plugin picks that preset and checks the plate at FINISH, after the push. | - |
| The story in shot 6 (push test, research, printed base) | Yes, with the original setup, Oct 2026 | - |
| Chat between Mum and Mıstık with this plugin | Only after the plugin runs on the household gateway (planned) and Mum agrees | Otherwise re-enacted in a test chat |
| The family member's request reaching the owner | The watcher's own message, once the plugin runs on the household gateway | Otherwise the simulator outbox, labelled "simulator" |
| Owner approval with `/home3d approve` | Yes, in the owner's own chat | The printer behind it may be the simulator |
| Watcher notices from the real printer | Planned | Otherwise the simulator outbox |
| `/home3d upgrades` proposal | Only if real moments reach the threshold | Otherwise from `hermes home3d demo` |
| `hermes home3d demo` | The plugin's own code | It runs on the simulator. Its scripted parts (what people say, Mıstık's chat replies, the owner's tap on "approve") are marked `[staged]`. |

The real-hardware loop with this plugin is planned. If it is not done when you record, use the
fallbacks and the labels. Do not start a real print for the video while a family job waits in the
queue. The owner approves each real start.

## Anonymised variant

Use this cut when the family does not want to appear, or for any public post before they agree.

- **No family voices, faces or names.** The owner reads Mum's line, or the chat shows it as text.
  Label it "re-enacted". Mum, Dad and the sibling appear only as "Mum", "Dad" and "Sibling".
- **Test chat.** Record shots 2 and 3 in a test group that holds only the owner and the Hermes number.
  Rename the contacts to "Mum" and "Dad". Or show the simulator outbox in a chat mock, labelled
  "simulator".
- **Hide identifiers.** Blur or crop phone numbers, group names, profile pictures, the LAN address in
  the browser bar, the printer serial number and access code in Bambuddy, and banners from other apps.
- **Hide the home.** Frame only the printer, the plate and the box. No windows, family photos or
  documents in the picture.
- **Audio.** The owner's voice-over stays. If the owner prefers, use the English subtitle text as an
  English voice-over (text-to-speech is fine; say so in the post).
- **Same script and timings.** The subtitle files work for both cuts. Change the speaker labels only if
  the picture shows different names.

## Checklist before you post

- Total length under 90 s (target 86 s).
- Every simulator screen says "simulator". Every re-enacted scene says "re-enacted".
- The subtitle numbers match the real slice. Every cue runs at 17 characters per second or slower.
- The install command on screen ends with `--enable`.
- No Mıstık line promises a start. The owner decides when a print starts.
- No names, phone numbers, group ids, IP addresses or serial numbers on screen.
- The X post links the repo and tags @NousResearch.
