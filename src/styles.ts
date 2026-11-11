/**
 * The Workshop's stylesheet, rendered as a <style> element INSIDE the plugin's own tree (so it mounts and
 * unmounts with the page or card, and nothing is added to the document head). Every selector is scoped
 * under `.h3w`. Surfaces and text come from the app's theme variables; each fallback is a CSS system colour
 * mix (Canvas / CanvasText follow the page's colour scheme), so nothing assumes light or dark.
 *
 * The look, in four rules:
 *  1. The build plate is the stage. A part is always shown on the printer's own bronze sheet, lit, with a
 *     shadow, in its filament colour. That panel and the camera are the only dark, photographic surfaces.
 *  2. A request looks like what it is: a chat message, in the colour of the group it came from.
 *  3. One filled button per view (Start, or the stop confirmation). Everything else is outlined or text.
 *  4. Lists with hairlines, not cards. Sentence case everywhere. The app's own typeface on one scale:
 *     sizes 12 / 13 / 15 / 19 / 22 (and 64 for the percentage), weights 400 / 600 / 700, radii 6 / 9 / 12 / 16.
 */

export const CSS = `
.h3w {
  --w-fg: var(--ui-text-primary, CanvasText);
  --w-fg2: var(--ui-text-secondary, color-mix(in srgb, CanvasText 72%, transparent));
  --w-fg3: var(--ui-text-tertiary, color-mix(in srgb, CanvasText 52%, transparent));
  --w-line: var(--ui-stroke-secondary, color-mix(in srgb, CanvasText 11%, transparent));
  --w-line2: var(--ui-stroke-primary, color-mix(in srgb, CanvasText 18%, transparent));
  --w-card: var(--ui-bg-card, color-mix(in srgb, CanvasText 3%, transparent));
  --w-raise: var(--ui-bg-elevated, Canvas);
  --w-well: color-mix(in srgb, var(--w-fg) 4%, transparent);
  --w-hover: var(--ui-control-hover-background, color-mix(in srgb, CanvasText 6%, transparent));
  --w-accent: var(--ui-accent, #4f7cff);
  --w-on-accent: var(--ui-accent-foreground, #fff);
  --w-red: var(--ui-red, #d1435b);
  --w-green: var(--ui-green, #2f9a72);
  --w-orange: var(--ui-orange, #db704b);
  --w-yellow: var(--ui-yellow, #c08532);
  --w-blue: var(--ui-blue, #3a6df0);
  /* the workshop's own: the textured build sheet, the heatbed under it, the studio around them */
  --w-plate: #75695a;
  --w-bed: #26272b;
  --w-studio: radial-gradient(95% 85% at 50% 30%, #3b3c41, #17181a);
  --w-on-photo: #fff;
  /* small grey text that still reads at 12 px; --w-fg3 stays for icons and rules */
  --w-quiet: color-mix(in srgb, var(--w-fg) 68%, transparent);
  color: var(--w-fg);
  font-size: 13px;
  line-height: 1.5;
  -webkit-font-smoothing: antialiased;
}
/* Text on the accent: white on a dark accent, a dark tint of it on a light one (dark themes use a light accent). */
@supports (color: oklch(from red l c h)) {
  .h3w { --w-on-accent: var(--ui-accent-foreground, oklch(from var(--w-accent) clamp(0.17, (0.58 - l) * 999, 1) calc(c * 0.35) h)); }
}
.h3w *, .h3w *::before, .h3w *::after { box-sizing: border-box; }
.h3w button { font: inherit; color: inherit; }
.h3w :focus-visible { outline: 2px solid var(--w-accent); outline-offset: 2px; border-radius: 6px; }
.h3w h1, .h3w h2, .h3w h3, .h3w p, .h3w blockquote, .h3w dl, .h3w dd { margin: 0; }
.h3w .num { font-variant-numeric: tabular-nums; }
.h3w .muted { color: var(--w-fg2); }
.h3w .faint { color: var(--w-quiet); }
.h3w .ellipsis { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; min-width: 0; }

/* tones */
.h3w .t-neutral { --tone: var(--w-fg2); }
.h3w .t-accent { --tone: var(--w-accent); }
.h3w .t-good { --tone: var(--w-green); }
.h3w .t-warn { --tone: var(--w-yellow); }
.h3w .t-bad { --tone: var(--w-red); }
/* A tone as text: mixed toward the text colour so small coloured words stay readable in both themes. */
.h3w .t-neutral, .h3w .t-accent, .h3w .t-good, .h3w .t-warn, .h3w .t-bad { --ink: color-mix(in srgb, var(--tone) 64%, var(--w-fg)); }
.h3w .w-ink { color: var(--ink); font-weight: 600; }
/* the group a person asked from */
.h3w .g-family { --g: var(--w-orange); }
.h3w .g-team { --g: var(--w-blue); }
.h3w .g-other { --g: var(--w-fg3); }

/* page frame */
.h3w-scroll { height: 100%; overflow: auto; }
.h3w.w-page { container: h3w / inline-size; max-width: 1280px; margin: 0 auto; padding: 26px 32px 64px; }
@container h3w (max-width: 620px) {
  .h3w.w-page { padding-left: 16px; padding-right: 16px; }
  .h3w .w-strip-job { flex: 1 1 100%; flex-wrap: wrap; order: 3; }
  .h3w .w-spec { grid-template-columns: minmax(0, 1fr); gap: 1px; }
  .h3w .w-spec dd { margin-bottom: 7px; }
}
.h3w .w-top { display: flex; align-items: flex-end; gap: 16px; flex-wrap: wrap; margin-bottom: 18px; }
.h3w .w-title { font-size: 22px; font-weight: 700; letter-spacing: -0.015em; line-height: 1.2; }
.h3w .w-sub { color: var(--w-fg2); margin-top: 4px; font-size: 13px; max-width: 64ch; }
.h3w .w-top-right { margin-left: auto; display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.h3w .w-fresh { display: inline-flex; align-items: center; gap: 7px; color: var(--w-quiet); font-size: 12px; }
.h3w .w-fresh.stale { color: color-mix(in srgb, var(--w-yellow) 64%, var(--w-fg)); }
.h3w .w-pulse { width: 6px; height: 6px; border-radius: 50%; background: var(--w-green); }
.h3w .w-fresh.stale .w-pulse { background: var(--w-yellow); }

.h3w .w-banner { display: flex; align-items: flex-start; gap: 10px; padding: 10px 13px; border-radius: 9px; margin-bottom: 12px;
  border: 1px solid color-mix(in srgb, var(--tone) 30%, transparent); background: color-mix(in srgb, var(--tone) 7%, transparent); color: var(--w-fg); }
.h3w .w-banner > svg { color: var(--tone); margin-top: 3px; }
.h3w .w-banner > span { min-width: 0; overflow-wrap: anywhere; }
.h3w .w-sim { display: inline-flex; align-items: center; gap: 6px; padding: 2px 9px 2px 7px; border-radius: 6px; font-size: 12px; font-weight: 600;
  color: color-mix(in srgb, var(--w-orange) 64%, var(--w-fg)); border: 1px dashed color-mix(in srgb, var(--w-orange) 60%, transparent); }

/* buttons */
.h3w .w-btn { display: inline-flex; align-items: center; justify-content: center; gap: 6px; height: 30px; padding: 0 12px; border-radius: 9px;
  border: 1px solid var(--w-line2); background: transparent; font-weight: 600; font-size: 13px; cursor: pointer; white-space: nowrap; transition: background .12s, border-color .12s; }
.h3w .w-btn:hover:not(:disabled) { background: var(--w-hover); }
.h3w .w-btn:disabled { opacity: .5; cursor: not-allowed; }
.h3w .w-btn.ghost { border-color: transparent; color: var(--w-fg2); }
.h3w .w-btn.ghost:hover:not(:disabled) { color: var(--w-fg); }
.h3w .w-btn.sm { height: 27px; padding: 0 9px; font-size: 12px; border-radius: 9px; }
.h3w .w-btn.primary { height: 44px; padding: 0 22px 0 18px; gap: 9px; font-size: 15px; font-weight: 700; letter-spacing: -0.005em; border: 0; border-radius: 12px;
  background: var(--w-accent); color: var(--w-on-accent);
  box-shadow: 0 1px 1px color-mix(in srgb, #000 14%, transparent), 0 6px 16px -6px color-mix(in srgb, var(--w-accent) 70%, transparent), inset 0 1px 0 color-mix(in srgb, #fff 22%, transparent);
  transition: background .12s, transform .06s; }
.h3w .w-btn.primary:hover:not(:disabled) { background: color-mix(in srgb, var(--w-accent) 90%, var(--w-fg)); }
.h3w .w-btn.primary:active:not(:disabled) { transform: translateY(1px); }
.h3w .w-btn.primary.muted-primary { background: transparent; color: var(--w-accent); border: 1px solid color-mix(in srgb, var(--w-accent) 55%, transparent); box-shadow: none; }
.h3w .w-btn.danger { color: color-mix(in srgb, var(--w-red) 70%, var(--w-fg)); border-color: color-mix(in srgb, var(--w-red) 40%, transparent); }
.h3w .w-btn.danger:hover:not(:disabled) { background: color-mix(in srgb, var(--w-red) 9%, transparent); }
.h3w .w-btn.danger-solid { color: #fff; background: var(--w-red); border-color: var(--w-red); }
.h3w .w-btn.danger-solid:hover:not(:disabled) { background: color-mix(in srgb, var(--w-red) 88%, #000); }
.h3w .w-link { border: 0; background: none; padding: 0; color: var(--w-accent); cursor: pointer; font-weight: 600; display: inline-flex; align-items: center; gap: 4px; }
.h3w .w-link:hover { text-decoration: underline; }

/* tags, people */
.h3w .w-tag { display: inline-flex; align-items: center; gap: 4px; padding: 1px 7px; border-radius: 6px; font-size: 12px; font-weight: 600; white-space: nowrap; line-height: 1.5;
  color: var(--ink, var(--tone)); background: color-mix(in srgb, var(--tone) 10%, transparent); }
.h3w .w-tag.outline { background: transparent; box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--tone) 38%, transparent); }
.h3w .w-person { display: inline-flex; align-items: baseline; gap: 6px; white-space: nowrap; min-width: 0; max-width: 100%; vertical-align: bottom; }
.h3w .w-person b { font-weight: 600; color: var(--w-fg); overflow: hidden; text-overflow: ellipsis; min-width: 0; }
.h3w .w-person .grp { color: var(--w-fg2); display: inline-flex; align-items: center; gap: 4px; min-width: 0; flex-shrink: 2; }
.h3w .w-person .grp > span { overflow: hidden; text-overflow: ellipsis; min-width: 0; }
.h3w .w-person .grp::before { flex-shrink: 0; }
.h3w .w-for { display: inline-flex; align-items: baseline; gap: 5px; min-width: 0; flex-shrink: 4; }
.h3w .w-person .grp::before { content: ''; width: 6px; height: 6px; border-radius: 50%; background: var(--g, var(--w-fg3)); transform: translateY(-1px); }
.h3w .w-ava { width: 26px; height: 26px; border-radius: 50%; flex-shrink: 0; display: inline-flex; align-items: center; justify-content: center;
  font-size: 12px; font-weight: 700; line-height: 1; color: color-mix(in srgb, var(--g, var(--w-fg2)) 60%, var(--w-fg)); background: color-mix(in srgb, var(--g, var(--w-fg3)) 18%, transparent); }
.h3w .w-ava.sm { width: 18px; height: 18px; font-size: 10px; }

/* hero */
.h3w .w-hero { border: 1px solid var(--w-line); border-radius: 16px; background: var(--w-card); overflow: hidden; }
.h3w .w-strip { display: flex; align-items: center; gap: 12px; padding: 11px 20px; min-height: 52px; flex-wrap: wrap; }
.h3w .w-strip + .w-hero-body, .h3w .w-strip + .w-reply, .h3w .w-strip + .w-tabs, .h3w .w-strip + .w-idle { border-top: 1px solid var(--w-line); }
.h3w .w-state { display: inline-flex; align-items: center; gap: 8px; font-weight: 600; font-size: 13px; color: var(--ink, var(--tone)); }
.h3w .w-state .dot { width: 8px; height: 8px; border-radius: 50%; background: var(--tone); box-shadow: 0 0 0 3px color-mix(in srgb, var(--tone) 18%, transparent); }
.h3w .w-state.live .dot { animation: h3w-breathe 2.4s ease-in-out infinite; }
@keyframes h3w-breathe { 50% { box-shadow: 0 0 0 6px color-mix(in srgb, var(--tone) 6%, transparent); } }
@media (prefers-reduced-motion: reduce) { .h3w .w-state.live .dot { animation: none; } }
.h3w .w-strip-job { display: flex; align-items: baseline; gap: 8px; min-width: 0; flex: 1 1 220px; }
.h3w .w-strip-job .name { font-weight: 600; flex-shrink: 1; }
.h3w .w-strip-meta { display: flex; align-items: center; gap: 14px; color: var(--w-fg2); font-size: 12px; flex-wrap: wrap; }
.h3w .w-strip-meta span { display: inline-flex; align-items: center; gap: 5px; }
.h3w .w-strip-actions { display: flex; gap: 8px; margin-left: auto; }
.h3w .w-strip-bar { height: 3px; background: color-mix(in srgb, var(--w-fg) 8%, transparent); }
.h3w .w-strip-bar > i { display: block; height: 100%; background: var(--w-accent); transition: width .6s ease; }

.h3w .w-hero-body { display: grid; grid-template-columns: minmax(0, 1.08fr) minmax(0, 1fr); gap: 28px; padding: 20px; }
.h3w .w-hero-body.single { grid-template-columns: minmax(0, 1fr); }
@container h3w (max-width: 900px) { .h3w .w-hero-body { grid-template-columns: minmax(0, 0.9fr) minmax(0, 1fr); gap: 20px; } }
@container h3w (max-width: 680px) { .h3w .w-hero-body { grid-template-columns: minmax(0, 1fr); gap: 18px; padding: 16px; } }

.h3w .w-tabs { display: flex; align-items: center; gap: 6px; padding: 14px 20px 0; flex-wrap: wrap; }
.h3w .w-tabs-label { color: var(--w-fg2); font-size: 12px; margin-right: 6px; }
.h3w .w-tab { display: inline-flex; align-items: center; gap: 7px; border: 1px solid transparent; background: transparent; border-radius: 9px; padding: 4px 11px 4px 5px;
  font-size: 12px; cursor: pointer; color: var(--w-fg2); max-width: 260px; }
.h3w .w-tab:hover { background: var(--w-hover); }
.h3w .w-tab[aria-pressed="true"] { border-color: var(--w-line2); color: var(--w-fg); background: var(--w-raise); font-weight: 600; }

/* the request: who, their words as a chat bubble, then what was prepared */
.h3w .w-ask { min-width: 0; display: flex; flex-direction: column; }
.h3w .w-sender { display: flex; align-items: center; gap: 9px; min-width: 0; }
.h3w .w-sender > .faint { flex-shrink: 0; white-space: nowrap; }
.h3w .w-bubble { align-self: flex-start; max-width: 100%; margin-top: 9px; padding: 12px 16px 13px; border-radius: 5px 18px 18px 18px;
  font-size: 19px; line-height: 1.4; font-weight: 400; letter-spacing: -0.008em; overflow-wrap: anywhere;
  background: color-mix(in srgb, var(--g, var(--w-fg3)) 10%, var(--w-raise)); box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--g, var(--w-fg3)) 24%, transparent); }
.h3w .w-bubble > .words.clamped { display: -webkit-box; -webkit-box-orient: vertical; -webkit-line-clamp: 5; overflow: hidden; }
.h3w .w-bubble-more { align-self: flex-start; margin-top: 6px; font-size: 12px; }
.h3w .w-bubble.long { font-size: 15px; line-height: 1.45; }
.h3w .w-jobline { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; margin-top: 20px; }
.h3w .w-job { font-size: 15px; font-weight: 600; min-width: 0; overflow-wrap: anywhere; }
.h3w .w-big { font-size: 22px; font-weight: 600; letter-spacing: -0.015em; line-height: 1.22; text-wrap: balance; min-width: 0; overflow-wrap: anywhere; }
.h3w .w-asked { margin-top: 6px; color: var(--w-fg2); display: flex; flex-wrap: wrap; gap: 4px 6px; align-items: baseline; }
.h3w .w-spec { display: grid; grid-template-columns: max-content minmax(0, 1fr); gap: 7px 20px; margin: 12px 0 0; }
.h3w .w-spec dt { color: var(--w-quiet); }
.h3w .w-spec dd { font-weight: 600; display: flex; align-items: center; gap: 7px; min-width: 0; flex-wrap: wrap; }
.h3w .w-spec dd .more { font-weight: 400; color: var(--w-fg2); }
.h3w .w-swatch { width: 12px; height: 12px; border-radius: 50%; flex-shrink: 0; background: var(--sw, transparent); box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--w-fg) 24%, transparent); }
.h3w .w-checks-sum { display: flex; align-items: center; gap: 7px; margin-top: 18px; font-weight: 600; color: var(--ink, var(--tone)); }
.h3w .w-checks { list-style: none; margin: 8px 0 0; padding: 0; display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 6px 20px; }
@container h3w (max-width: 1000px) { .h3w .w-checks { grid-template-columns: minmax(0, 1fr); } }
.h3w .w-checks li { display: grid; grid-template-columns: 16px minmax(0, 1fr); gap: 7px; align-items: start; }
.h3w .w-checks li > svg { margin-top: 3px; }
.h3w .w-checks li > span { min-width: 0; overflow-wrap: anywhere; }
.h3w .w-checks .ok > svg { color: var(--w-green); }
.h3w .w-checks .no { grid-column: 1 / -1; font-weight: 600; }
.h3w .w-checks .no > svg { color: var(--w-red); }
.h3w .w-checks .detail { display: block; color: var(--w-quiet); font-size: 12px; font-weight: 400; }
.h3w .w-go { display: flex; align-items: center; gap: 14px; flex-wrap: wrap; margin-top: auto; padding-top: 20px; }
.h3w .w-go-explain { color: var(--w-fg2); font-size: 12px; flex: 1 1 200px; min-width: 0; overflow-wrap: anywhere; }
.h3w .w-cmd { font-family: var(--font-mono, ui-monospace, SFMono-Regular, Menlo, monospace); font-size: 12px; color: var(--w-quiet); }

/* now printing */
.h3w .w-run { min-width: 0; align-self: center; }
.h3w .w-pct { font-size: 64px; font-weight: 700; letter-spacing: -0.04em; line-height: 1; margin-top: 20px; }
.h3w .w-pct small { font-size: 24px; font-weight: 600; letter-spacing: 0; color: var(--w-fg3); margin-left: 3px; }
.h3w .w-bigbar { height: 10px; border-radius: 6px; background: color-mix(in srgb, var(--w-fg) 9%, transparent); overflow: hidden; margin: 14px 0 16px; }
.h3w .w-bigbar > i { display: block; height: 100%; border-radius: 6px; background: var(--w-accent); transition: width .6s ease; }
.h3w .w-lines { display: grid; gap: 8px; color: var(--w-fg2); }
.h3w .w-lines > div { display: flex; gap: 9px; align-items: center; }
.h3w .w-lines > div > svg { color: var(--w-fg3); }
.h3w .w-lines b { color: var(--w-fg); font-weight: 600; }

.h3w .w-confirm { margin-top: 12px; padding: 12px 14px; border-radius: 9px; border: 1px solid color-mix(in srgb, var(--w-red) 40%, transparent);
  background: color-mix(in srgb, var(--w-red) 6%, transparent); display: grid; gap: 10px; }
.h3w .w-confirm .row { display: flex; gap: 8px; flex-wrap: wrap; }
.h3w .w-reply { display: flex; gap: 10px; align-items: flex-start; padding: 10px 20px; font-size: 12px; background: color-mix(in srgb, var(--tone) 7%, transparent); }
.h3w .w-reply > svg { color: var(--tone); margin-top: 3px; }
.h3w .w-reply pre { margin: 0; white-space: pre-wrap; font: inherit; flex: 1; min-width: 0; }
.h3w .w-reply-inline { margin-top: 8px; border-radius: 9px; padding: 8px 10px; }

.h3w .w-idle { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 320px); gap: 28px; align-items: center; padding: 22px 20px; }
@container h3w (max-width: 680px) { .h3w .w-idle { grid-template-columns: minmax(0, 1fr); } }
.h3w .w-idle .w-big { font-size: 19px; }
.h3w .w-idle p { max-width: 62ch; }

/* media: the plate (3D), the camera, thumbnails */
.h3w .w-media { position: relative; border-radius: 12px; overflow: hidden; background: var(--w-well); border: 1px solid var(--w-line); aspect-ratio: 4 / 3; min-height: 200px; }
.h3w .w-media[data-workshop-viewer="live"], .h3w .w-media[data-workshop-camera] { background: var(--w-studio); border-color: color-mix(in srgb, #000 30%, var(--w-line)); }
.h3w .w-media.wide { aspect-ratio: 16 / 10; }
.h3w .w-media.short { aspect-ratio: auto; height: 190px; min-height: 0; }
.h3w .w-media.tall { aspect-ratio: auto; min-height: 380px; }
@container h3w (max-width: 900px) { .h3w .w-media.tall { min-height: 300px; } }
@container h3w (max-width: 680px) { .h3w .w-media.tall, .h3w .w-media.wide { aspect-ratio: 16 / 10; min-height: 0; max-height: 300px; width: 100%; } }
.h3w .w-media .stage { position: absolute; inset: 0; cursor: grab; }
.h3w .w-media .stage:active { cursor: grabbing; }
.h3w .w-media img.fill { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: contain; }
.h3w .w-media img.cover { object-fit: cover; }
.h3w .w-media .center { position: absolute; inset: 0; z-index: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 10px; color: var(--w-quiet); text-align: center; padding: 16px; }
.h3w .w-media[data-workshop-viewer="live"] .center { color: color-mix(in srgb, var(--w-on-photo) 70%, transparent); }
.h3w .w-media[data-workshop-viewer="live"]::after { content: ''; position: absolute; inset: 0; pointer-events: none;
  background: radial-gradient(ellipse 75% 70% at 50% 46%, transparent 52%, rgba(0, 0, 0, .34)); }
.h3w .w-media .over { position: absolute; z-index: 1; display: flex; gap: 6px; align-items: center; }
.h3w .w-media .over.tl { top: 10px; left: 10px; }
.h3w .w-media .over.tr { top: 10px; right: 10px; }
.h3w .w-media .over.bl { bottom: 10px; left: 10px; }
.h3w .w-media .over.br { bottom: 10px; right: 10px; }
/* labels and controls that sit on a photo or on the plate: always light on dark glass */
.h3w .w-glass, .h3w .w-photo-cap, .h3w .w-view3d { display: inline-flex; align-items: center; gap: 6px; min-height: 26px; padding: 3px 9px; border-radius: 9px; font-size: 12px; font-weight: 600;
  color: var(--w-on-photo); background: rgba(16, 16, 18, .62); border: 1px solid rgba(255, 255, 255, .16); backdrop-filter: blur(8px); -webkit-backdrop-filter: blur(8px); }
.h3w button.w-glass, .h3w .w-view3d { cursor: pointer; }
.h3w button.w-glass { padding: 3px 7px; }
.h3w button.w-glass:hover, .h3w .w-view3d:hover { background: rgba(16, 16, 18, .82); border-color: rgba(255, 255, 255, .32); }
.h3w .w-view3d { padding: 5px 12px; font-weight: 600; }
.h3w .w-glass:focus-visible, .h3w .w-view3d:focus-visible { outline-color: var(--w-on-photo); }
.h3w .w-media canvas:focus-visible { outline: 2px solid var(--w-on-photo); outline-offset: -5px; border-radius: 9px; }
.h3w .w-thumb { width: 48px; height: 48px; border-radius: 9px; object-fit: cover; background: var(--w-well); border: 1px solid var(--w-line); flex-shrink: 0; display: flex; align-items: center; justify-content: center; color: var(--w-fg3); overflow: hidden; }
.h3w .w-thumb img { width: 100%; height: 100%; object-fit: cover; }
.h3w .w-skel { background: linear-gradient(90deg, var(--w-well), color-mix(in srgb, var(--w-fg) 8%, transparent), var(--w-well)); background-size: 200% 100%; animation: h3w-shimmer 1.4s linear infinite; border-radius: 9px; }
@keyframes h3w-shimmer { to { background-position: -200% 0; } }
.h3w .w-spin { animation: h3w-spin 0.9s linear infinite; }
@keyframes h3w-spin { to { transform: rotate(360deg); } }
@media (prefers-reduced-motion: reduce) { .h3w .w-spin { animation: none; } }
@media (prefers-reduced-motion: reduce) { .h3w .w-skel { animation: none; } }

/* lower grid */
.h3w .w-grid { display: grid; grid-template-columns: minmax(0, 1.5fr) minmax(0, 1fr); gap: 36px 48px; margin-top: 34px; }
@container h3w (max-width: 900px) { .h3w .w-grid { grid-template-columns: minmax(0, 1fr); } }
.h3w .w-col { display: grid; grid-template-columns: minmax(0, 1fr); gap: 36px; align-content: start; min-width: 0; }
.h3w .w-sec-head { display: flex; align-items: baseline; gap: 8px; padding-bottom: 9px; border-bottom: 1px solid var(--w-line2); }
.h3w .w-sec-head h2 { font-size: 15px; font-weight: 600; letter-spacing: -0.005em; display: inline-flex; align-items: baseline; gap: 8px; }
.h3w .w-sec-head .count { color: var(--w-quiet); font-weight: 400; font-size: 13px; }
.h3w .w-sec-head .aside { margin-left: auto; font-size: 12px; display: inline-flex; align-items: center; gap: 6px; }
.h3w .w-subhead { font-size: 13px; font-weight: 600; padding: 16px 0 2px; }
.h3w .w-empty { padding: 14px 0 4px; color: var(--w-quiet); display: flex; gap: 8px; align-items: flex-start; max-width: 62ch; }
.h3w .w-empty > svg { margin-top: 3px; }
.h3w .w-rows { list-style: none; margin: 0; padding: 0; }
.h3w .w-row { display: flex; align-items: center; gap: 12px; padding: 11px 0; border-bottom: 1px solid var(--w-line); min-width: 0; }
.h3w .w-row:last-child { border-bottom: 0; }
.h3w .w-row .w-main { flex: 1; min-width: 0; display: grid; gap: 2px; }
.h3w .w-row .title { font-weight: 600; display: flex; align-items: center; gap: 8px; min-width: 0; }
.h3w .w-row .sub { color: var(--w-fg2); font-size: 12px; display: flex; gap: 2px 12px; flex-wrap: wrap; align-items: baseline; }
.h3w .w-row .end { display: flex; align-items: center; gap: 8px; flex-shrink: 0; }
.h3w .w-row .end .state { color: var(--w-quiet); font-size: 12px; }
.h3w .w-facts-line { color: var(--w-fg2); display: flex; gap: 2px 14px; flex-wrap: wrap; }
.h3w .w-facts-line .bad { color: color-mix(in srgb, var(--w-red) 70%, var(--w-fg)); font-weight: 600; }
.h3w .w-facts-line .warn { color: color-mix(in srgb, var(--w-yellow) 64%, var(--w-fg)); }
.h3w .w-row > .lead { flex-shrink: 0; margin-top: 3px; align-self: flex-start; color: var(--tone, var(--w-fg3)); }
.h3w .w-pos { width: 22px; height: 22px; border-radius: 50%; display: inline-flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 600;
  color: var(--w-fg2); box-shadow: inset 0 0 0 1px var(--w-line2); flex-shrink: 0; }
.h3w .w-row.next .w-pos { background: var(--w-accent); color: var(--w-on-accent); box-shadow: none; }

/* filament: the four spools, each wound as full as it is */
.h3w .w-slots { display: grid; grid-template-columns: repeat(auto-fill, minmax(88px, 1fr)); gap: 16px 8px; padding-top: 16px; }
.h3w .w-slot { display: grid; justify-items: center; text-align: center; min-width: 0; }
.h3w .w-slot svg { margin-bottom: 7px; overflow: visible; }
.h3w .w-slot .flange { fill: color-mix(in srgb, var(--w-fg) 12%, transparent); stroke: color-mix(in srgb, var(--w-fg) 26%, transparent); stroke-width: 1; }
.h3w .w-slot .wound { fill: var(--sw, var(--w-fg3)); stroke: color-mix(in srgb, var(--w-fg) 50%, transparent); stroke-width: 1; }
.h3w .w-slot .turn { fill: none; stroke: color-mix(in srgb, #000 13%, transparent); stroke-width: 1; }
.h3w .w-slot .hub { fill: var(--w-raise); stroke: color-mix(in srgb, var(--w-fg) 38%, transparent); stroke-width: 1; }
.h3w .w-slot .hole { fill: color-mix(in srgb, var(--w-fg) 30%, transparent); }
.h3w .w-slot.empty .flange { stroke-dasharray: 3 3; fill: none; }
.h3w .w-slot .mat { font-weight: 600; max-width: 100%; }
.h3w .w-slot .sub { font-size: 12px; color: var(--w-fg2); max-width: 100%; }
.h3w .w-slot .brand { font-size: 12px; line-height: 1.3; color: var(--w-quiet); max-width: 100%; overflow-wrap: anywhere; }
.h3w .w-slot.low .sub { color: color-mix(in srgb, var(--w-red) 70%, var(--w-fg)); font-weight: 600; }

.h3w .clamp2, .h3w .clamp3 { display: -webkit-box; -webkit-box-orient: vertical; overflow: hidden; }
.h3w .clamp2 { -webkit-line-clamp: 2; }
.h3w .clamp3 { -webkit-line-clamp: 3; }
.h3w .w-dot { width: 7px; height: 7px; border-radius: 50%; background: var(--tone); flex-shrink: 0; margin-top: 7px; }
.h3w .w-camthumb { width: 60px; height: 38px; border-radius: 6px; overflow: hidden; flex-shrink: 0; border: 1px solid var(--w-line2); background: var(--w-well); padding: 0; cursor: pointer; position: relative; }
.h3w .w-camthumb img { width: 100%; height: 100%; object-fit: cover; display: block; }
.h3w .w-summary { display: flex; align-items: center; gap: 8px; padding: 12px 0 4px; font-weight: 600; }
.h3w .w-summary > svg { color: var(--tone); }
.h3w .w-watch { display: flex; align-items: center; gap: 4px 14px; flex-wrap: wrap; padding: 4px 0 8px; color: var(--w-fg2); }
.h3w .w-watch .beat { display: inline-flex; align-items: center; gap: 7px; }
.h3w .w-watch .beat::before { content: ''; width: 7px; height: 7px; border-radius: 50%; background: var(--tone); }
.h3w details.w-more summary { cursor: pointer; color: var(--w-fg2); font-size: 12px; padding: 6px 0; list-style: none; display: inline-flex; gap: 6px; align-items: center; }
.h3w details.w-more summary::-webkit-details-marker { display: none; }
.h3w details.w-more summary::before { content: '▸'; font-size: 10px; transition: transform .15s; }
.h3w details.w-more[open] summary::before { transform: rotate(90deg); }
.h3w .w-fix { margin-top: 3px; font-size: 12px; color: var(--w-fg2); display: flex; gap: 6px; align-items: baseline; }
.h3w .w-fix code { font-family: var(--font-mono, ui-monospace, SFMono-Regular, Menlo, monospace); font-size: 12px; padding: 1px 5px; border-radius: 6px; background: var(--w-well); color: var(--w-fg); }
.h3w .w-zero b { font-weight: 700; color: color-mix(in srgb, var(--w-green) 64%, var(--w-fg)); }
.h3w .w-zero.spent b { color: color-mix(in srgb, var(--w-yellow) 64%, var(--w-fg)); }

.h3w .w-design { padding: 14px 0; border-bottom: 1px solid var(--w-line); display: grid; gap: 10px; }
.h3w .w-design:last-child { border-bottom: 0; }
.h3w .w-design-head { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.h3w .w-vers { display: flex; gap: 4px; flex-wrap: wrap; }
.h3w .w-ver { min-width: 34px; height: 26px; padding: 0 8px; border-radius: 9px; border: 1px solid var(--w-line); background: transparent; cursor: pointer; font-size: 12px; font-weight: 600; color: var(--w-fg2); }
.h3w .w-ver:hover { border-color: var(--w-line2); color: var(--w-fg); }
.h3w .w-ver[aria-pressed="true"] { border-color: var(--w-line2); color: var(--w-fg); background: var(--w-raise); }
.h3w .w-design-body { display: grid; grid-template-columns: minmax(0, 1.2fr) minmax(0, 1fr); gap: 16px; align-items: start; }
@container h3w (max-width: 620px) { .h3w .w-design-body { grid-template-columns: minmax(0, 1fr); } }
.h3w .w-strip-thumbs { display: flex; gap: 6px; flex-wrap: wrap; }
.h3w .w-strip-thumbs button { padding: 0; border: 1px solid var(--w-line); border-radius: 9px; background: none; cursor: pointer; overflow: hidden; width: 56px; height: 42px; }
.h3w .w-strip-thumbs button[aria-pressed="true"] { border-color: var(--w-accent); box-shadow: 0 0 0 1px var(--w-accent); }
.h3w .w-strip-thumbs img { width: 100%; height: 100%; object-fit: cover; display: block; }

/* standalone states */
.h3w .w-state-page { max-width: 560px; margin: 8vh auto 0; text-align: left; display: grid; gap: 12px; padding: 26px; border: 1px solid var(--w-line); border-radius: 16px; background: var(--w-card); }
.h3w .w-state-page h2 { font-size: 19px; font-weight: 600; letter-spacing: -0.01em; display: flex; gap: 8px; align-items: center; }
.h3w .w-state-page ol { margin: 0; padding-left: 18px; display: grid; gap: 8px; color: var(--w-fg2); }
.h3w .w-code { display: flex; align-items: center; gap: 8px; padding: 6px 8px 6px 10px; border-radius: 9px; background: var(--w-well); border: 1px solid var(--w-line); }
.h3w .w-code code { flex: 1; font-family: var(--font-mono, ui-monospace, SFMono-Regular, Menlo, monospace); font-size: 12px; color: var(--w-fg); overflow-x: auto; white-space: nowrap; }

/* transcript card */
.h3w.w-card { border: 1px solid var(--w-line); border-radius: 16px; padding: 12px; margin: 6px 0; max-width: 520px; background: var(--w-card); display: grid; gap: 10px; }
.h3w.w-card .head { display: flex; align-items: center; gap: 8px; }
.h3w.w-card .head .name { font-weight: 600; font-size: 15px; }
.h3w.w-card .facts { display: flex; gap: 6px; flex-wrap: wrap; }

/* status-bar chip */
.h3w.w-chip { display: inline-flex; align-items: center; gap: 5px; height: 100%; padding: 0 6px; border: 0; background: transparent; cursor: pointer;
  font-size: 11px; color: var(--w-quiet); white-space: nowrap; border-radius: 4px; }
.h3w.w-chip:hover { color: var(--w-fg); background: var(--w-hover); }
.h3w.w-chip .d { width: 6px; height: 6px; border-radius: 50%; background: var(--tone); }
.h3w.w-chip.t-accent { color: var(--w-accent); font-weight: 600; }
`
