# Household intake: voice notes, photos, links, sizes, names

Family members rarely write a spec. They send a voice note, a photo, a short video or a reel and expect
you to understand. Open it yourself before asking: every question costs them a round trip, and an
unanswered voice note usually comes back as another voice note.

## Voice notes
- The Hermes gateway transcribes voice notes before you see them (the transcript arrives as a quoted
  line). Don't transcribe them again and don't install anything.
- If the note arrives untranscribed or empty, ask for the one key detail in writing (a name, a colour, a size).
- Read for intent. Expect misheard words: your own name, "filament", colours, numbers, names. Earlier
  notes in the chat often hold the actual request.
- Names, numbers and start words must be confirmed in writing. Speech-to-text turns casual speech into
  start-like words. Quote what you heard and ask: "I heard 'print it', shall I start?" A print once started
  on a misheard word and had to be stopped.
- Record the channel: `home3d_import ... channel=voice`.
- "You didn't answer" in a voice note: resend your last answer and its picture, don't only re-explain.

## Photos
- First say what you understood ("a hook for the bathroom door, about this size?").
- For a model of something they own, a photo straight from above, in good light, with a scale reference
  lying flat next to the object at the same height:

| Reference | Size (mm) |
|---|---|
| bank card (ISO ID-1) | 85.60 x 53.98 |
| 1 TL coin | 26.15 |
| 50 kuruş coin | 23.85 |
| 1 euro coin | 23.25 |
| 2 euro coin | 25.75 |
| US quarter | 24.26 |
| A4 sheet | 210 x 297 |

- Measure from the photo: correct the phone's rotation, scale = reference size in pixels / its size in mm,
  then read the object's widths. Use the area-equivalent diameter of a coin rather than its bounding box
  (shadows). Check your outline by drawing it over the photo.
- Expect an error on the side where the camera sees the object's thickness (perspective). A top photo
  can't give thickness: ask for a side photo or a ruler measurement.
- For anything that must fit (a tube, a phone, a shelf edge), ask for that one dimension with a ruler or
  calipers. When a person measured for you, log it: `home3d_human_needed action=log kind=measure`.
- A product photo they want copied: count every repeated feature first (legs, slots, ribs) and say the
  counts back; people check counts before anything else. Measure proportions relative to the main
  thickness, and set the absolute size from something in the photo or the listing.

## Short videos and reels
- Video: pull a handful of frames (1-2 per second) into one contact sheet and look at them with vision.
- Instagram / TikTok links: read the page title, description and cover image (a link-preview user agent
  often works where a browser one gets an empty page). Captions are often only hashtags, sometimes in
  another language, so look at the frames too.
- Write down the object's distinctive shape or mechanism, then search MakerWorld with those words. Put a
  frame next to 2-3 candidate covers and offer only the ones that really match.
- If the video shows a seller's product or a paid file: say so, offer look-alikes, list extra hardware
  (LED kit, lamp parts). You can't buy anything; offer to print a file they send.

## Sizes and changes
- Before changing a size, say the current size and propose the new one: "Now 10 x 8 x 5 cm. Make it
  12 x 10 x 5?" Scale only after a yes. `target_size_mm` sets the largest side.
- "Width" is the dimension along the front face (the side with the opening or thumb notch), not
  necessarily the longest side.
- Scaling a box also thickens its walls. If only the inside must grow, say so; that may need design work.
- Lids, snap fits, hinges and threads stop fitting when scaled, even on one axis. The tool asks for
  `confirm_mechanism`; ask the requester, and offer a different profile or the owner's help instead.
- Below about half size, thin parts get weak; the tool warns. Above the 256 mm bed: a profile that fits,
  or a split into parts (design work).
- "The big one", "same as last time": find the earlier job (`home3d_household action=history`) and match it.

## Personalised names
- Get the name in writing, in capitals, and spell it back. Watch special letters (Turkish I/İ, Ş, Ğ, Ç, Ö,
  Ü) and check the font has them.
- Confirm three things before slicing: text, colours, size.
- Simple items: `home3d_customize template=name_tag params={"text": "SAM"}` (key-ring tag) or
  `template=label_box params={"text": "TOYS", "width": 80}` (box with a raised label). Long names shrink
  the font to fit.
- Show a picture first (the render or the slice preview) and wait for approval. Re-render whenever the
  text or colours change.

## A personalised product line (example: named gift boxes)
When the household sells or gifts the same object with different names (a lidded rose box with a name on
it, sold by a family member), treat it as a product, not a one-off:
- Keep one approved source model and its parameters. Every order is generated from the same files, so
  copies are identical. Start from the source profile's own size; "big size" never means an extra scale.
- Letters as separate inlay pieces in a contrasting colour read far better than an engraving in the same
  colour. Print letters face down, slow first layer, small brim (letters must still be pushable).
- Seam at the back, name facing front. Show a render on a dark background for approval.
- Lids and locks are mechanisms: change them only through the design, never by scaling.
- When one printed part has a fault and the order is urgent, fix only that one thing and keep the
  improvement for the next order instead of reprinting everything.
- Check the model's licence before anything is sold (`references/makerworld.md`).
- Keep orders as notes: `home3d_household action=note text="Box for ...: white box, black letters, done"`.

## Who asked, and for whom
- The person speaking is the requester unless they say otherwise ("for Mum"). Pass `requester=` so the
  watcher tells the right person when it is done.
- Several people asking at once: one request each, queued in order. Never jump someone else's job.
