# Demo video plan (under 90 seconds)

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
m:ss. Subtitle cues end at 1:24.5; the end card holds to 1:26.

| Time | Shot | Picture | Audio (English subtitle text) |
|---|---|---|---|
| 0:00-0:07 | 1. Hook | The A1 on its tilted base. The bed moves, a finished part slides off into the box in front. | VO: "My mum doesn't know CAD or 3D printers. She just talks to Mıstık." |
| 0:07-0:21 | 2. Request | Phone, family chat. Mum's voice note plays for 3 s. Mıstık answers with two MakerWorld pictures and print times. Mum picks one. Mıstık says it queued it. | Voice note: "Mıstık, can you print me a little gift box for flowers?" Then chat captions (see the SRT files). No VO. |
| 0:21-0:31 | 3. Safety | Mum: "Lovely, print it please!" A red "blocked" overlay on the agent's tool call. The owner's phone: `/home3d approve start 7`, reply "Started #7". | Chat captions, then VO: "The rules are in code. Only the owner starts. Anyone can stop." |
| 0:31-0:40 | 4. Watch | Camera timelapse of the print. Small overlay: "watcher: every 2 min, 0 tokens". | VO: "A watcher checks the printer every two minutes. No model calls, no tokens. It writes only when something happens." |
| 0:40-0:52 | 5. Done | Family chat: "Mum, the flower box is done..." with the photo. Owner chat: the technical note with the photo (2 s). Cut to the printer: the bed has cooled, the nozzle pushes the part, it slides into the box. | Chat caption, then VO: "When the bed cools, the printer pushes the part off by itself." |
| 0:52-1:10 | 6. The twist | Photos with dates: the first push test, the part stuck at the front edge (25 Oct); the tilted base parts on the plate; the base installed. Then the `/home3d upgrades` screen with the proposal. | VO: "We asked it to clear the plate without a person. It tried a push, and the part got stuck at the front. It found a tilted base and printed its own upgrade. The plugin makes this a rule: when a human task repeats, it proposes an upgrade." |
| 1:10-1:20 | 7. Try it | Terminal: `hermes plugins install Wijt/hermes-home-3d-workshop`, then `hermes home3d demo` scrolls fast. | VO: "No printer? Try it with the simulator. One command: hermes home3d demo." |
| 1:20-1:26 | 8. End card | "home-3d-workshop · a Hermes Agent plugin · github.com/Wijt/hermes-home-3d-workshop". | VO: "Mıstık. The home's 3D workshop." |

### Chat lines on screen (Turkish)

These are the persona's real message forms (from `hermes home3d demo --lang tr`). Use them as they are
when you re-enact shots 2, 3 and 5. Put the real queue number and times in place of `#7` and the times.

| Shot | Who | Text on screen | English subtitle |
|---|---|---|---|
| 2 | Mıstık | Anneciğim, iki tane buldum (resimler aşağıda): 1) çiçek kutusu, yaklaşık 2 saat 16 dakika 2) saksı, yaklaşık 4 saat 34 dakika. Hangisi olsun? | Mum, I found two. 1) Flower box, about 2 h 16 min. 2) Plant pot, about 4 h 34 min. Which one? |
| 2 | Mum | İlki olsun, beyaz kutu. | The first one, a white box. |
| 2 | Mıstık | Sıraya ekledim (#7). Yazıcının sahibi onaylayınca başlıyor. | Queued (#7). It starts when the owner approves. |
| 3 | Mum | Çok güzel, bas lütfen! | Lovely, print it please! |
| 3 | Owner | /home3d approve start 7 → ▶️ #7 "<model name>" başladı (Mum). | Started #7. |
| 5 | Mıstık (family chat) | ✅ Anneciğim, "çiçek kutusu" bitti. Otomatik düşürüldü, kutudan alabilirsin. | Mum, the flower box is done. Pushed off: pick it up from the box. |

## Shot list

| # | Length | What to capture | Source | How |
|---|---|---|---|---|
| 1 | 7 s | Part slides off the tilted A1 into the box | Real printer | Phone on a tripod, landscape 1080p, at plate height. Frame only the printer and the box. |
| 2a | 3 s | Mum's voice note in the chat | Real chat (with consent) or re-enacted | Phone screen recording. |
| 2b | 11 s | Mıstık's reply with two model pictures; Mum's pick; "queued, starts once approved" | Real plugin on the household gateway (planned) or re-enacted test chat | Phone screen recording, scroll slowly. |
| 3a | 4 s | Mum: "Lovely, print it please!" and the blocked start | Same as 2b, or the `hermes home3d demo` step "Mum says print it" | Add the red "blocked" overlay in the edit. |
| 3b | 6 s | Owner sends `/home3d approve start <id>` and gets "Started" | Owner's own chat with Hermes (real) | Phone screen recording. Simulated printer: label "simulator". |
| 4 | 9 s | Print timelapse | Real printer (Bambuddy timelapse or archive) | Export from Bambuddy, speed up. |
| 5a | 5 s | Family notice with the photo | Real watcher on the real printer (planned) or the simulator outbox | Phone screen recording. Simulator: label "simulator". |
| 5b | 2 s | Owner notice: layers, temperatures, photo | Same as 5a | Phone screen recording. |
| 5c | 5 s | Bed cooled, nozzle pushes, part slides into the box | Real printer | Same tripod as shot 1. Real time, then speed up the cooling wait. |
| 6a | 12 s | Push-test photo, base parts printing, base installed | Real archive photos (Bambuddy archive, chat photos) | Ken Burns pan, date captions. Label "original setup, Oct 2026". |
| 6b | 6 s | `/home3d upgrades` with "Auto-eject: tilted base + push preset, 3x" | `hermes home3d demo` or a real chat after real moments | Label "simulator" unless it is real. |
| 7 | 10 s | Install and `hermes home3d demo` | Terminal, simulator by design | Font 18 pt or more, 100 columns, light theme. Record in a throwaway `HERMES_HOME`. |
| 8 | 6 s | End card | Edit | Plain background, repo link, "#NousResearch". |

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
| Auto-eject push (shots 1 and 5c) | Yes. The printer preset's end G-code pushes, not the plugin; the plugin picks that preset and checks the plate after. | - |
| The story in shot 6 (push test, research, printed base) | Yes, with the original setup, Oct 2026 | - |
| Chat between Mum and Mıstık with this plugin | Only after the plugin runs on the household gateway (planned) and Mum agrees | Otherwise re-enacted in a test chat |
| Owner approval with `/home3d approve` | Yes, in the owner's own chat | The printer behind it may be the simulator |
| Watcher notices from the real printer | Planned | Otherwise the simulator outbox |
| `/home3d upgrades` proposal | Only if real moments reach the threshold | Otherwise from `hermes home3d demo` |
| `hermes home3d demo` | The plugin's own code | It runs on the simulator. Its scripted parts are marked `[staged]`. |

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
- The subtitle numbers match the real slice.
- No names, phone numbers, group ids, IP addresses or serial numbers on screen.
- The X post links the repo and tags @NousResearch.
