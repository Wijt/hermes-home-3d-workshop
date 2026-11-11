/**
 * The Workshop's stylesheet, rendered as a <style> element INSIDE the plugin's own tree (so it mounts and
 * unmounts with the page or card, and nothing is added to the document head). Every selector is scoped
 * under `.h3w`. Colours come from the app's theme variables; each fallback is a CSS system colour mix
 * (Canvas / CanvasText follow the page's colour scheme), so nothing assumes light or dark.
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
  color: var(--w-fg);
  font-size: 13px;
  line-height: 1.45;
  -webkit-font-smoothing: antialiased;
}
.h3w *, .h3w *::before, .h3w *::after { box-sizing: border-box; }
.h3w button { font: inherit; color: inherit; }
.h3w :focus-visible { outline: 2px solid var(--w-accent); outline-offset: 2px; border-radius: 6px; }
.h3w h1, .h3w h2, .h3w h3, .h3w p { margin: 0; }
.h3w .num { font-variant-numeric: tabular-nums; }
.h3w .muted { color: var(--w-fg2); }
.h3w .faint { color: var(--w-fg3); }
.h3w .ellipsis { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; min-width: 0; }

/* tones */
.h3w .t-neutral { --tone: var(--w-fg2); }
.h3w .t-accent { --tone: var(--w-accent); }
.h3w .t-good { --tone: var(--w-green); }
.h3w .t-warn { --tone: var(--w-yellow); }
.h3w .t-bad { --tone: var(--w-red); }

/* page frame */
.h3w-scroll { height: 100%; overflow: auto; }
.h3w.w-page { container: h3w / inline-size; max-width: 1320px; margin: 0 auto; padding: 22px 28px 56px; }
.h3w .w-top { display: flex; align-items: flex-end; gap: 16px; flex-wrap: wrap; margin-bottom: 16px; }
.h3w .w-title { font-size: 20px; font-weight: 650; letter-spacing: -0.01em; }
.h3w .w-sub { color: var(--w-fg2); margin-top: 2px; }
.h3w .w-top-right { margin-left: auto; display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.h3w .w-fresh { display: inline-flex; align-items: center; gap: 6px; color: var(--w-fg3); font-size: 12px; }
.h3w .w-fresh.stale { color: var(--w-yellow); }
.h3w .w-pulse { width: 7px; height: 7px; border-radius: 50%; background: var(--w-green); box-shadow: 0 0 0 3px color-mix(in srgb, var(--w-green) 18%, transparent); }
.h3w .w-fresh.stale .w-pulse { background: var(--w-yellow); box-shadow: 0 0 0 3px color-mix(in srgb, var(--w-yellow) 18%, transparent); }

.h3w .w-banner { display: flex; align-items: flex-start; gap: 10px; padding: 9px 12px; border-radius: 10px; margin-bottom: 12px;
  border: 1px solid color-mix(in srgb, var(--tone) 35%, transparent); background: color-mix(in srgb, var(--tone) 8%, transparent); color: var(--w-fg); }
.h3w .w-banner > svg { color: var(--tone); margin-top: 2px; }
.h3w .w-sim { display: inline-flex; align-items: center; gap: 6px; padding: 3px 10px 3px 8px; border-radius: 999px; font-size: 12px; font-weight: 550;
  color: var(--w-orange); border: 1px dashed color-mix(in srgb, var(--w-orange) 55%, transparent); background: color-mix(in srgb, var(--w-orange) 7%, transparent); }

/* buttons */
.h3w .w-btn { display: inline-flex; align-items: center; justify-content: center; gap: 6px; height: 30px; padding: 0 12px; border-radius: 8px;
  border: 1px solid var(--w-line2); background: transparent; font-weight: 550; font-size: 12.5px; cursor: pointer; white-space: nowrap; transition: background .12s, border-color .12s; }
.h3w .w-btn:hover:not(:disabled) { background: var(--w-hover); }
.h3w .w-btn:disabled { opacity: .5; cursor: not-allowed; }
.h3w .w-btn.ghost { border-color: transparent; color: var(--w-fg2); }
.h3w .w-btn.ghost:hover:not(:disabled) { color: var(--w-fg); }
.h3w .w-btn.sm { height: 26px; padding: 0 9px; font-size: 12px; border-radius: 7px; }
.h3w .w-btn.primary { height: 40px; padding: 0 20px; font-size: 14px; font-weight: 650; border: 0; border-radius: 10px;
  background: var(--w-accent); color: var(--w-on-accent); box-shadow: 0 1px 0 color-mix(in srgb, #000 12%, transparent), inset 0 1px 0 color-mix(in srgb, #fff 18%, transparent); }
.h3w .w-btn.primary:hover:not(:disabled) { background: color-mix(in srgb, var(--w-accent) 88%, var(--w-fg)); }
.h3w .w-btn.primary.muted-primary { background: transparent; color: var(--w-accent); border: 1px solid color-mix(in srgb, var(--w-accent) 55%, transparent); box-shadow: none; }
.h3w .w-btn.danger { color: var(--w-red); border-color: color-mix(in srgb, var(--w-red) 45%, transparent); }
.h3w .w-btn.danger:hover:not(:disabled) { background: color-mix(in srgb, var(--w-red) 9%, transparent); }
.h3w .w-btn.danger-solid { color: #fff; background: var(--w-red); border-color: var(--w-red); }
.h3w .w-btn.danger-solid:hover:not(:disabled) { background: color-mix(in srgb, var(--w-red) 88%, #000); }
.h3w .w-link { border: 0; background: none; padding: 0; color: var(--w-accent); cursor: pointer; font-weight: 550; display: inline-flex; align-items: center; gap: 4px; }
.h3w .w-link:hover { text-decoration: underline; }

/* tags, people */
.h3w .w-tag { display: inline-flex; align-items: center; gap: 4px; padding: 1px 8px; border-radius: 999px; font-size: 11.5px; font-weight: 550; white-space: nowrap;
  color: var(--tone); background: color-mix(in srgb, var(--tone) 11%, transparent); }
.h3w .w-tag.outline { background: transparent; border: 1px solid color-mix(in srgb, var(--tone) 40%, transparent); }
.h3w .w-person { display: inline-flex; align-items: baseline; gap: 5px; white-space: nowrap; }
.h3w .w-person b { font-weight: 600; color: var(--w-fg); }
.h3w .w-person .grp { color: var(--w-fg2); display: inline-flex; align-items: center; gap: 4px; }
.h3w .w-person .grp::before { content: ''; width: 6px; height: 6px; border-radius: 50%; background: var(--g, var(--w-fg3)); transform: translateY(-1px); }
.h3w .g-family { --g: var(--w-orange); }
.h3w .g-team { --g: var(--w-blue); }

/* hero */
.h3w .w-hero { border: 1px solid var(--w-line); border-radius: 16px; background: var(--w-card); overflow: hidden; }
.h3w .w-strip { display: flex; align-items: center; gap: 14px; padding: 12px 16px; flex-wrap: wrap; }
.h3w .w-strip + .w-hero-body, .h3w .w-strip + .w-reply { border-top: 1px solid var(--w-line); }
.h3w .w-state { display: inline-flex; align-items: center; gap: 7px; font-weight: 650; font-size: 13.5px; color: var(--tone); }
.h3w .w-state .dot { width: 9px; height: 9px; border-radius: 50%; background: var(--tone); box-shadow: 0 0 0 4px color-mix(in srgb, var(--tone) 16%, transparent); }
.h3w .w-state.live .dot { animation: h3w-breathe 2.4s ease-in-out infinite; }
@keyframes h3w-breathe { 50% { box-shadow: 0 0 0 7px color-mix(in srgb, var(--tone) 6%, transparent); } }
@media (prefers-reduced-motion: reduce) { .h3w .w-state.live .dot { animation: none; } }
.h3w .w-strip-job { display: flex; align-items: baseline; gap: 8px; min-width: 0; flex: 1 1 220px; }
.h3w .w-strip-job .name { font-weight: 600; }
.h3w .w-strip-meta { display: flex; align-items: center; gap: 14px; color: var(--w-fg2); font-size: 12.5px; flex-wrap: wrap; }
.h3w .w-strip-meta span { display: inline-flex; align-items: center; gap: 5px; }
.h3w .w-strip-actions { display: flex; gap: 8px; margin-left: auto; }
.h3w .w-strip-bar { height: 3px; background: color-mix(in srgb, var(--w-fg) 8%, transparent); }
.h3w .w-strip-bar > i { display: block; height: 100%; background: var(--w-accent); transition: width .6s ease; }

.h3w .w-hero-body { display: grid; grid-template-columns: minmax(0, 1.05fr) minmax(0, 1fr); gap: 22px; padding: 18px; }
.h3w .w-hero-body.single { grid-template-columns: minmax(0, 1fr); }
@container h3w (max-width: 760px) { .h3w .w-hero-body { grid-template-columns: minmax(0, 1fr); } .h3w .w-hero-body > .w-media { aspect-ratio: 16 / 9; } }
.h3w .w-kicker { display: inline-flex; align-items: center; gap: 6px; font-size: 11.5px; font-weight: 650; letter-spacing: .06em; text-transform: uppercase; color: var(--tone, var(--w-fg3)); }
.h3w .w-big { font-size: 22px; font-weight: 650; letter-spacing: -0.01em; line-height: 1.2; margin-top: 4px; }
.h3w .w-asked { margin-top: 6px; color: var(--w-fg2); display: flex; flex-wrap: wrap; gap: 4px 6px; align-items: baseline; }
.h3w .w-quote { margin: 10px 0 0; padding: 2px 0 2px 10px; border-left: 2px solid var(--w-line2); color: var(--w-fg2); font-style: italic; }
.h3w .w-facts { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 1px; margin: 16px 0 14px; border-radius: 10px; overflow: hidden;
  border: 1px solid var(--w-line); background: var(--w-line); }
.h3w .w-fact { background: var(--w-raise); padding: 8px 11px; min-width: 0; }
.h3w .w-fact dt { font-size: 11px; color: var(--w-fg3); text-transform: uppercase; letter-spacing: .05em; font-weight: 600; }
.h3w .w-fact dd { margin: 2px 0 0; font-weight: 600; display: flex; align-items: center; gap: 6px; min-width: 0; }
.h3w .w-swatch { width: 12px; height: 12px; border-radius: 50%; flex-shrink: 0; background: var(--sw, transparent); box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--w-fg) 22%, transparent); }
.h3w .w-checks { list-style: none; margin: 0 0 16px; padding: 0; display: grid; gap: 6px; }
.h3w .w-checks li { display: grid; grid-template-columns: 18px minmax(0, 1fr); gap: 6px; align-items: start; }
.h3w .w-checks li > svg { margin-top: 2px; }
.h3w .w-checks .ok > svg { color: var(--w-green); }
.h3w .w-checks .no > svg { color: var(--w-red); }
.h3w .w-checks .detail { color: var(--w-fg3); font-size: 12px; }
.h3w .w-go { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.h3w .w-go-explain { color: var(--w-fg2); font-size: 12.5px; flex: 1 1 200px; }
.h3w .w-cmd { font-family: var(--font-mono, ui-monospace, SFMono-Regular, Menlo, monospace); font-size: 11.5px; color: var(--w-fg3); }
.h3w .w-tabs { display: flex; gap: 6px; padding: 10px 16px 0; flex-wrap: wrap; }
.h3w .w-tab { border: 1px solid var(--w-line); background: transparent; border-radius: 999px; padding: 3px 10px; font-size: 12px; cursor: pointer; color: var(--w-fg2); }
.h3w .w-tab[aria-selected="true"] { border-color: var(--w-accent); color: var(--w-accent); background: color-mix(in srgb, var(--w-accent) 8%, transparent); font-weight: 600; }

.h3w .w-pct { font-size: 44px; font-weight: 700; letter-spacing: -0.03em; line-height: 1; }
.h3w .w-pct small { font-size: 20px; font-weight: 600; color: var(--w-fg2); margin-left: 2px; }
.h3w .w-bigbar { height: 8px; border-radius: 4px; background: color-mix(in srgb, var(--w-fg) 9%, transparent); overflow: hidden; margin: 14px 0 12px; }
.h3w .w-bigbar > i { display: block; height: 100%; border-radius: 4px; background: var(--w-accent); transition: width .6s ease; }
.h3w .w-lines { display: grid; gap: 7px; color: var(--w-fg2); }
.h3w .w-lines > div { display: flex; gap: 8px; align-items: center; }
.h3w .w-lines b { color: var(--w-fg); font-weight: 600; }

.h3w .w-confirm { margin-top: 12px; padding: 12px; border-radius: 10px; border: 1px solid color-mix(in srgb, var(--w-red) 40%, transparent);
  background: color-mix(in srgb, var(--w-red) 6%, transparent); display: grid; gap: 10px; }
.h3w .w-confirm .row { display: flex; gap: 8px; flex-wrap: wrap; }
.h3w .w-reply { display: flex; gap: 10px; align-items: flex-start; padding: 10px 16px; font-size: 12.5px; background: color-mix(in srgb, var(--tone) 7%, transparent); }
.h3w .w-reply > svg { color: var(--tone); margin-top: 2px; }
.h3w .w-reply pre { margin: 0; white-space: pre-wrap; font: inherit; flex: 1; min-width: 0; }
.h3w .w-reply-inline { margin-top: 8px; border-radius: 8px; padding: 8px 10px; }

.h3w .w-idle { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 300px); gap: 22px; align-items: center; padding: 18px; }
@container h3w (max-width: 760px) { .h3w .w-idle { grid-template-columns: minmax(0, 1fr); } }
.h3w .w-idle .w-big { font-size: 19px; }

/* media: viewer, camera, thumbnails */
.h3w .w-media { position: relative; border-radius: 12px; overflow: hidden; background: var(--w-well); border: 1px solid var(--w-line); aspect-ratio: 4 / 3; min-height: 200px; }
.h3w .w-media.wide { aspect-ratio: 16 / 10; }
.h3w .w-media.short { aspect-ratio: auto; height: 180px; min-height: 0; }
.h3w .w-media .stage { position: absolute; inset: 0; cursor: grab; }
.h3w .w-media .stage:active { cursor: grabbing; }
.h3w .w-media img.fill { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: contain; }
.h3w .w-media img.cover { object-fit: cover; }
.h3w .w-media .center { position: absolute; inset: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 10px; color: var(--w-fg3); text-align: center; padding: 16px; }
.h3w .w-media .over { position: absolute; display: flex; gap: 6px; align-items: center; }
.h3w .w-media .over.tl { top: 8px; left: 8px; }
.h3w .w-media .over.tr { top: 8px; right: 8px; }
.h3w .w-media .over.bl { bottom: 8px; left: 8px; }
.h3w .w-media .over.br { bottom: 8px; right: 8px; }
.h3w .w-glass { padding: 3px 8px; border-radius: 7px; font-size: 11.5px; font-weight: 550; color: var(--w-fg); background: color-mix(in srgb, var(--w-raise) 82%, transparent);
  border: 1px solid var(--w-line); backdrop-filter: blur(6px); display: inline-flex; align-items: center; gap: 5px; }
.h3w button.w-glass { cursor: pointer; }
.h3w button.w-glass:hover { background: var(--w-raise); }
.h3w .w-photo-cap { padding: 3px 8px; border-radius: 7px; font-size: 11.5px; font-weight: 550; color: #fff; background: rgba(0, 0, 0, .55); display: inline-flex; align-items: center; gap: 5px; }
.h3w .w-view3d { display: inline-flex; align-items: center; gap: 6px; padding: 7px 13px; border-radius: 999px; font-weight: 600; font-size: 12.5px; cursor: pointer;
  border: 1px solid var(--w-line2); background: var(--w-raise); color: var(--w-fg); }
.h3w .w-view3d:hover { border-color: var(--w-accent); color: var(--w-accent); }
.h3w .w-thumb { width: 52px; height: 52px; border-radius: 8px; object-fit: cover; background: var(--w-well); border: 1px solid var(--w-line); flex-shrink: 0; display: flex; align-items: center; justify-content: center; color: var(--w-fg3); overflow: hidden; }
.h3w .w-thumb img { width: 100%; height: 100%; object-fit: cover; }
.h3w .w-skel { background: linear-gradient(90deg, var(--w-well), color-mix(in srgb, var(--w-fg) 8%, transparent), var(--w-well)); background-size: 200% 100%; animation: h3w-shimmer 1.4s linear infinite; border-radius: 8px; }
@keyframes h3w-shimmer { to { background-position: -200% 0; } }
@media (prefers-reduced-motion: reduce) { .h3w .w-skel { animation: none; } }

/* lower grid */
.h3w .w-grid { display: grid; grid-template-columns: minmax(0, 1.5fr) minmax(0, 1fr); gap: 30px 40px; margin-top: 28px; }
@container h3w (max-width: 900px) { .h3w .w-grid { grid-template-columns: minmax(0, 1fr); } }
.h3w .w-col { display: grid; grid-template-columns: minmax(0, 1fr); gap: 30px; align-content: start; min-width: 0; }
.h3w .w-sec-head { display: flex; align-items: center; gap: 8px; padding-bottom: 8px; border-bottom: 1px solid var(--w-line2); }
.h3w .w-sec-head h2 { font-size: 13.5px; font-weight: 650; display: inline-flex; align-items: center; gap: 7px; }
.h3w .w-sec-head h2 svg { color: var(--w-fg3); }
.h3w .w-sec-head .count { color: var(--w-fg3); font-weight: 500; }
.h3w .w-sec-head .aside { margin-left: auto; font-size: 12px; display: inline-flex; align-items: center; gap: 6px; }
.h3w .w-sec-q { color: var(--w-fg3); font-size: 12px; margin-top: 2px; }
.h3w .w-empty { padding: 14px 2px 4px; color: var(--w-fg3); display: flex; gap: 8px; align-items: flex-start; }
.h3w .w-empty > svg { margin-top: 2px; }
.h3w .w-rows { list-style: none; margin: 0; padding: 0; }
.h3w .w-row { display: flex; align-items: center; gap: 12px; padding: 10px 2px; border-bottom: 1px solid var(--w-line); min-width: 0; }
.h3w .w-row:last-child { border-bottom: 0; }
.h3w .w-row .main { flex: 1; min-width: 0; display: grid; gap: 2px; }
.h3w .w-row .title { font-weight: 600; display: flex; align-items: center; gap: 8px; min-width: 0; }
.h3w .w-row .sub { color: var(--w-fg2); font-size: 12.5px; display: flex; gap: 4px 10px; flex-wrap: wrap; align-items: baseline; }
.h3w .w-row .end { display: flex; align-items: center; gap: 8px; flex-shrink: 0; }
.h3w .w-pos { width: 22px; height: 22px; border-radius: 50%; display: inline-flex; align-items: center; justify-content: center; font-size: 11.5px; font-weight: 650;
  color: var(--w-fg2); border: 1px solid var(--w-line2); flex-shrink: 0; }
.h3w .w-row.next .w-pos { background: var(--w-accent); color: var(--w-on-accent); border-color: var(--w-accent); }

.h3w .w-slots { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 10px; padding-top: 12px; }
.h3w .w-slot { border: 1px solid var(--w-line); border-radius: 12px; padding: 10px 11px; display: grid; gap: 6px; background: var(--w-card); }
.h3w .w-slot.empty { border-style: dashed; background: transparent; color: var(--w-fg3); }
.h3w .w-slot .top { display: flex; align-items: center; gap: 8px; }
.h3w .w-slot .spool { width: 26px; height: 26px; border-radius: 50%; background: var(--sw); flex-shrink: 0;
  box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--w-fg) 22%, transparent), inset 0 0 0 7px color-mix(in srgb, #000 10%, transparent); position: relative; }
.h3w .w-slot .spool::after { content: ''; position: absolute; inset: 9px; border-radius: 50%; background: var(--w-raise); box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--w-fg) 20%, transparent); }
.h3w .w-slot .lvl { height: 4px; border-radius: 2px; background: color-mix(in srgb, var(--w-fg) 9%, transparent); overflow: hidden; }
.h3w .w-slot .lvl > i { display: block; height: 100%; background: var(--w-fg2); }
.h3w .w-slot .lvl.low > i { background: var(--w-red); }

.h3w .clamp2, .h3w .clamp3 { display: -webkit-box; -webkit-box-orient: vertical; overflow: hidden; }
.h3w .clamp2 { -webkit-line-clamp: 2; }
.h3w .clamp3 { -webkit-line-clamp: 3; }
.h3w .w-dot { width: 7px; height: 7px; border-radius: 50%; background: var(--tone); flex-shrink: 0; margin-top: 6px; }
.h3w .w-camthumb { width: 68px; height: 42px; border-radius: 7px; overflow: hidden; flex-shrink: 0; border: 1px solid var(--w-line); background: var(--w-well); padding: 0; cursor: pointer; position: relative; }
.h3w .w-camthumb img { width: 100%; height: 100%; object-fit: cover; display: block; }
.h3w .w-summary { display: flex; align-items: center; gap: 8px; padding: 12px 0 4px; font-weight: 600; }
.h3w .w-summary > svg { color: var(--tone); }
.h3w details.w-more summary { cursor: pointer; color: var(--w-fg2); font-size: 12.5px; padding: 6px 0; list-style: none; display: inline-flex; gap: 6px; align-items: center; }
.h3w details.w-more summary::-webkit-details-marker { display: none; }
.h3w details.w-more summary::before { content: '▸'; font-size: 10px; transition: transform .15s; }
.h3w details.w-more[open] summary::before { transform: rotate(90deg); }
.h3w .w-fix { margin-top: 3px; font-size: 12px; color: var(--w-fg2); display: flex; gap: 6px; align-items: baseline; }
.h3w .w-fix code { font-family: var(--font-mono, ui-monospace, SFMono-Regular, Menlo, monospace); font-size: 11.5px; padding: 1px 5px; border-radius: 5px; background: var(--w-well); color: var(--w-fg); }
.h3w .w-zero { display: inline-flex; align-items: center; gap: 6px; font-size: 12px; padding: 2px 9px; border-radius: 999px; border: 1px solid var(--w-line2); color: var(--w-fg2); }
.h3w .w-zero b { color: var(--w-green); font-weight: 700; }

.h3w .w-design { padding: 12px 0; border-bottom: 1px solid var(--w-line); display: grid; gap: 10px; }
.h3w .w-design:last-child { border-bottom: 0; }
.h3w .w-design-head { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.h3w .w-vers { display: flex; gap: 4px; flex-wrap: wrap; }
.h3w .w-ver { min-width: 34px; height: 26px; padding: 0 8px; border-radius: 7px; border: 1px solid var(--w-line); background: transparent; cursor: pointer; font-size: 12px; font-weight: 600; color: var(--w-fg2); }
.h3w .w-ver:hover { border-color: var(--w-line2); color: var(--w-fg); }
.h3w .w-ver[aria-pressed="true"] { border-color: var(--w-accent); color: var(--w-accent); background: color-mix(in srgb, var(--w-accent) 8%, transparent); }
.h3w .w-design-body { display: grid; grid-template-columns: minmax(0, 1.2fr) minmax(0, 1fr); gap: 14px; align-items: start; }
@container h3w (max-width: 620px) { .h3w .w-design-body { grid-template-columns: minmax(0, 1fr); } }
.h3w .w-strip-thumbs { display: flex; gap: 6px; flex-wrap: wrap; }
.h3w .w-strip-thumbs button { padding: 0; border: 1px solid var(--w-line); border-radius: 8px; background: none; cursor: pointer; overflow: hidden; width: 56px; height: 42px; }
.h3w .w-strip-thumbs button[aria-pressed="true"] { border-color: var(--w-accent); box-shadow: 0 0 0 1px var(--w-accent); }
.h3w .w-strip-thumbs img { width: 100%; height: 100%; object-fit: cover; display: block; }

/* standalone states */
.h3w .w-state-page { max-width: 560px; margin: 8vh auto 0; text-align: left; display: grid; gap: 12px; padding: 24px; border: 1px solid var(--w-line); border-radius: 16px; background: var(--w-card); }
.h3w .w-state-page h2 { font-size: 17px; font-weight: 650; display: flex; gap: 8px; align-items: center; }
.h3w .w-state-page ol { margin: 0; padding-left: 18px; display: grid; gap: 8px; color: var(--w-fg2); }
.h3w .w-code { display: flex; align-items: center; gap: 8px; padding: 6px 8px 6px 10px; border-radius: 8px; background: var(--w-well); border: 1px solid var(--w-line); }
.h3w .w-code code { flex: 1; font-family: var(--font-mono, ui-monospace, SFMono-Regular, Menlo, monospace); font-size: 12px; color: var(--w-fg); overflow-x: auto; white-space: nowrap; }

/* transcript card */
.h3w.w-card { border: 1px solid var(--w-line); border-radius: 14px; padding: 10px; margin: 6px 0; max-width: 520px; background: var(--w-card); display: grid; gap: 10px; }
.h3w.w-card .head { display: flex; align-items: center; gap: 8px; }
.h3w.w-card .head .name { font-weight: 650; }
.h3w.w-card .facts { display: flex; gap: 6px; flex-wrap: wrap; }

/* status-bar chip */
.h3w.w-chip { display: inline-flex; align-items: center; gap: 5px; height: 100%; padding: 0 6px; border: 0; background: transparent; cursor: pointer;
  font-size: 11px; color: var(--w-fg3); white-space: nowrap; border-radius: 4px; }
.h3w.w-chip:hover { color: var(--w-fg); background: var(--w-hover); }
.h3w.w-chip .d { width: 6px; height: 6px; border-radius: 50%; background: var(--tone); }
.h3w.w-chip.t-accent { color: var(--w-accent); font-weight: 600; }
`
