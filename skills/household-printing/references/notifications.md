# Notifications and tone: owner vs family

Two audiences, two tones. Examples use the placeholder names "Mum" (a family member, addressed as
"Anneciğim" in Turkish) and "Sam" (the owner); real names come from the settings.

## Who gets what
| | Family (requester) | Owner |
|---|---|---|
| Tone | warm, plain, 1-2 lines, by name | technical, still short |
| Content | done / stuck / what happens next | state, layer, temperatures, HMS code + wiki link, preview link, approval command |
| Photo | only with a finished part | with every finish or problem |
| Language | household `language`, no foreign words | household `language` (technical terms are fine) |

- The watcher sends the event messages by itself (started, finished, dropped off, stayed on the plate,
  failed, paused, HMS, offline, ready for the next job, upgrade proposals). Don't repeat them; answer
  questions about them. The family only hears about jobs a family member asked for.
- Message on change, problem or done. No progress pings ("40 %, all fine") unless someone asks.
- No @-tags. Use `address_as` from the context ("Anneciğim", "Dad").
- Nothing in English inside a Turkish family chat, including the short notes you write between tool
  calls: gateways deliver those too. Stay silent between calls or write them in the household language.

## Household words (tr)
otomatik düşürme (auto-eject), tabla (build plate), kenar şeridi (brim), destek (support), sıra (queue),
makara (spool), katman (layer), önizleme (preview), başlangıç çizgisi (purge line). Say "hazırladım"
rather than "dilimledim" (sliced) to the family.

## Links and photos
- Preview links: copy `preview_url` from the `home3d_slice` result. It uses the configured public URL.
  Never type a bare IP address, and never reuse an old link from chat history.
- Photos: put the `media_line` from `home3d_camera` (`MEDIA:/abs/path.jpg`) on its own line. The tool
  re-encodes camera frames; raw printer frames show up broken on phones, so never attach them directly.
- Parents decide from pictures. Send the picture, not only a link.
- HMS repair steps: only from the official page, with the link, never from memory:
  `https://wiki.bambulab.com/en/a1/troubleshooting/hmscode/<CODE_WITH_UNDERSCORES>`. Read the section for
  the household's printer model only; the same page also lists steps for other models.

## Family examples
Offering options:
- tr: "Anneciğim, üç tane buldum, resimleri aşağıda:\n1) Fırçalık, 2 saat 10 dakika\n2) Döner düzenleyici, 3 saat 40 dakika\n3) Küçük kutu, 1 saat 5 dakika\nHangisi olsun?"
- en: "Mum, I found three, pictures below:\n1) Brush holder, 2 h 10 min\n2) Rotating organiser, 3 h 40 min\n3) Small box, 1 h 5 min\nWhich one?"

One question about size:
- tr: "Şu an 10 × 8 × 5 cm. 12 × 10 × 5 cm yapayım mı?"
- en: "It's 10 × 8 × 5 cm now. Shall I make it 12 × 10 × 5 cm?"

Ready to print:
- tr: "Hazır: yaklaşık 1 saat 20 dakika, 35 gram kırmızı. Bitince kendi düşecek. Basayım mı?"
- en: "Ready: about 1 h 20 min, 35 g of red. It will drop off by itself. Shall I print it?"

Will not drop off by itself:
- tr: "Bu parça ince, kendi düşmez; bitince yazıcıdan alınması gerekecek."
- en: "This one is thin and won't drop off by itself; someone will need to take it off."

Waiting for the owner:
- tr: "Sıraya ekledim. Sam onaylayınca başlıyor."
- en: "It's in the queue. It starts as soon as Sam approves."

Someone else's job first:
- tr: "Önce Sam'ın işi var, o bitince seninki başlıyor (yaklaşık 2 saat sonra)."
- en: "Sam's job is first; yours starts after it, in about 2 hours."

Voice note with a start word:
- tr: "Sesli mesajda \"bas\" dediğini duydum. Başlatayım mı? Yazıyla \"evet\" yazman yeterli."
- en: "I heard \"print it\" in your voice note. Shall I start? Just write \"yes\"."

Stopped on request:
- tr: "Durdurdum. Fotoğraf ekte, parça yarım kaldı."
- en: "Stopped. Photo attached; the part is half done."

Owning a mistake:
- tr: "Haklısın, renk yanlıştı; takılı makarayı kontrol etmeden sıraya eklemişim. Kırmızıyla yeniden hazırladım: 1 saat 20 dakika. Basayım mı?"
- en: "You're right, the colour was wrong; I queued it without checking the loaded spool. Redone in red: 1 h 20 min. Shall I print it?"

What the watcher already sent (for reference, don't resend):
- tr: "✅ Anneciğim, \"Fırçalık\" bitti. Otomatik düşürüldü, kutudan alabilirsin."
- en: "✅ Mum, \"Brush holder\" is done. It dropped off by itself, you can take it from the box."
- tr: "🙏 Anneciğim, \"Fırçalık\" bitti ama tablada kaldı, kendi düşmedi. Müsait olunca alabilir misin?"
- en: "🙏 Mum, \"Brush holder\" is done but stayed on the plate. Could you take it off when you have a moment?"
- tr: "⚠️ Anneciğim, yazıcı durdu, \"Fırçalık\" yarıda kaldı (%40). Sam'a haber verdim."
- en: "⚠️ Mum, the printer stopped, \"Brush holder\" didn't finish (40%). I told Sam."

## Owner examples
Slice report:
- tr: "Fırçalık (#41): 0.20 mm, PLA kırmızı (tepsi 2), 1 sa 20 dk, 35 g. Otomatik düşürme açık (taban 32 × 40 mm, yükseklik 48 mm). Önizleme: <preview_url>"
- en: "Brush holder (#41): 0.20 mm, PLA red (tray 2), 1 h 20 min, 35 g. Auto-eject on (footprint 32 × 40 mm, 48 mm tall). Preview: <preview_url>"

Approval needed:
- tr: "Fırçalık (Anne için) sırada (#12). Başlatmak için: /home3d approve start 12"
- en: "Brush holder for Mum is queued (#12). To start it: /home3d approve start 12"

Pause with an HMS code:
- tr: "⏸️ Duraklatıldı: Fırçalık · katman 112/300 · %37 · HMS 0700-2000-0002-0001 (filament bitti) · <wiki link> · foto ekte"
- en: "⏸️ Paused: Brush holder · layer 112/300 · 37% · HMS 0700-2000-0002-0001 (filament ran out) · <wiki link> · photo attached"

Upgrade proposal (once, when it appears):
- tr: "Son 30 günde 3 kez biten parçayı elle almak gerekti. Öneri: yazıcıyı basılı bir tabanla öne ~15° eğip sağlam PLA parçalar için otomatik düşürmeyi açmak. Parçalar: https://makerworld.com/en/models/2335000. Basayım mı?"
- en: "Three times in 30 days someone had to take a finished part off. Proposal: tilt the printer ~15° forward on a printed base and turn on auto-eject for sturdy PLA parts. Parts: https://makerworld.com/en/models/2335000. Shall I print them?"

## Timing
- A long print that would end in the middle of the night: offer the morning, unless the owner said to run
  it overnight. Nobody can clear the plate or react to a failure while everyone sleeps.
- A scheduled job never starts prints. It may only report.
