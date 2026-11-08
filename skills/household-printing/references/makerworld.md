# MakerWorld: finding, choosing and importing models

Ready models come first. The household should choose from real pictures, not from your description.

## Finding candidates
- There is no MakerWorld search here, and MakerWorld pages block plain fetches. Use your web search:
  `site:makerworld.com <English keywords>`. English keywords work best even for a Turkish request.
- Search for the purpose as well as the object: "makeup brush holder", "pill organizer weekly",
  "toy car track connector". Try 2-3 phrasings if the first misses. Space out searches; engines rate-limit.
- Search result snippets usually carry title, creator, likes and downloads. They are an index snapshot,
  not live numbers.
- From a reel or photo: first write down the distinctive shape or mechanism you saw ("five numbered
  sliders, each pushes one card up"), then search with those words.
- "That model" / "the one we looked at" means an earlier conversation or job. Check
  `home3d_household action=history` (and past sessions if you can search them) before searching the web.
  Offering a fresh list instead of their earlier pick makes them correct you.
- Model links come as `https://makerworld.com/en/models/<id>-<slug>`; the numeric id is enough.

## Reading the cards
`home3d_find_models urls=[...]` (up to 6) resolves each link through Bambuddy and returns: title, cover
picture, creator, licence, likes, downloads, prints, a short summary, the A1 print profiles (profile id,
title, print time, grams, plates) and `already_imported_library_ids`.
- **Prints** is the best reliability signal: thousands of makes means it prints cleanly.
- **A1 profiles** are tuned for this printer. A model with none can still be imported and sliced with
  the household's A1 presets; say that the time is an estimate until it is sliced.
- **Profile titles carry scale and plate info** ("25 cm tall", "0.16 mm detail", "2 plates"). A profile
  already scaled to fit beats rescaling it yourself. Many models are designed bigger than the 256 mm bed.
- Community profiles made on an A1 are often simpler (fewer colours, fixed base) and faster.
- A card that fails to resolve (not found, no instances): skip it and move on.

## Offering options
- 2-4 options. For each: the cover picture, title, print time, size when known, licence in plain words.
- Skip models whose description or comments mention breaking, poor fit or failed prints.
- Parents decide from pictures. Put the pictures in the message; a link alone is not enough. If the photos
  show a different colour than the one you will print, say the real colour.
- Let them choose. Don't pick the most popular one on your own.
- Exception: "find it and add it" (not "show me"). Choose the best fit yourself (A1 profile, many prints,
  matches the stated goal), import, slice, queue, and say why you chose it, with the link. If the choice
  is genuinely uncertain, still show the options.

## Licences in plain words
| Licence | Personal print | Sell prints | Say |
|---|---|---|---|
| Standard Digital File License | yes | no, unless the designer allows it | "for our own use only" |
| CC BY | yes | yes, credit the designer | "free to use, name the designer" |
| CC BY-SA | yes | yes, credit + share remixes alike | "free, remixes stay free" |
| CC BY-NC (-SA/-ND) | yes | no | "not for selling" |
| CC0 | yes | yes | "no restrictions" |
- When someone talks about selling prints (gifts for a stall, a small shop), check the licence first.
  For a non-commercial model, say so plainly and offer a commercial-licence alternative or an original design.
- You never buy files. Paid models: say they are paid and let the owner decide.

## Instances vs profile ids
- A model has several print profiles ("instances"). Each has an instance id and a `profileId`.
- The `#profileId-NNN` fragment in a link someone pastes is the **instance** id, not the profile id.
  Passing it to the import fails (HTTP 400). Use the card's `a1_profiles[].profile_id`, or the profile
  whose instance matches NNN.
- `home3d_import` without `profile_id` picks the first A1 profile. Pass one explicitly when the requester
  chose a specific size or plate set.
- Already imported (`already_imported_library_ids`): the tool reuses the library file instead of importing
  twice.

## Import failures and fallbacks
- **Login problem:** Bambuddy's MakerWorld status says downloads are not possible (`can_download` false).
  The owner signs in to Bambu Cloud again in Bambuddy. Tell the owner, not the family.
- **"No download URL" while downloads are possible:** usually an upstream API change, not a login problem.
  Signing in again won't help. Tell the owner the error text; a Bambuddy update may fix it, and updating
  is the owner's decision.
- **Fallback:** ask the owner to download the 3MF in a browser and add it to the Bambuddy library (upload
  in its web UI). Then continue with that library file id (`home3d_customize` / `home3d_slice`).
- **Don't silently switch to a different model** because the import failed. The requester chose that one.
  If it can't be had at all, say so, then offer look-alikes or a design of your own.
- A tool result that came back unknown (timeout) after an import: check before importing again.

## When nothing fits
- Not on MakerWorld (a seller's product, a paid file elsewhere): say so in one line, show 2-3 look-alikes,
  and list any extra hardware it needs (LED kit, magnets, screws). Offer to print a file they send.
- Designing from scratch is the last resort: ask first ("I couldn't find a ready one, shall I draw it?"),
  and hand complex design work to the owner or a design-capable agent when the household has one.
- Simple personalised items (name tags, labelled boxes) are covered by the `home3d_customize` templates.

## Cost questions
- Filament cost = grams x (price per kg / 1000). Electricity is small (roughly 0.1 kWh per print hour),
  a few percent of the total. Say which prices are assumptions.
- A selling price needs wear and failed prints on top (a small amount per print hour) plus a margin. Say
  it is an estimate, not a market survey, and check the licence first.
