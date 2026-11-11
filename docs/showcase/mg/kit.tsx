// The motion-graphics film's kit: one palette, one type family, one way of moving. Every scene in mg/scenes/ draws
// only with what is exported here, so the film reads as one piece.
//
// The look comes from the plugin itself: the dark studio and the bronze build plate of its Workshop screen, the red
// of the filament in slot 2 (#C12E1F on the real screen), the blue of its Start button, and chat bubbles in each
// group's colour. Type is Bricolage Grotesque (OFL, files in media/fonts/): the 96pt cut for big words, the text
// cut for everything read at small size.
//
// Frame: 1920 x 1080, 30 fps. Floor sizes: text that must be read is 60 px or more, small print 32 px or more.
import type { CSSProperties, ReactNode } from "react";
import { AbsoluteFill, Easing, Img, Video, interpolate, staticFile, useCurrentFrame } from "raea";

// ---------------------------------------------------------------------------------------------------------------
// Palette
// ---------------------------------------------------------------------------------------------------------------
export const P = {
  /** the studio: the ground of every drawn scene */
  ink: "#121316",
  /** a panel one step up from the studio */
  ink2: "#1D1F24",
  /** hairlines on the studio */
  ink3: "#30333A",
  /** main type on the studio */
  bone: "#F3F1EC",
  /** quiet type on the studio (4.9:1 on ink) */
  mist: "#9A9EA8",
  /** filament red: Mum, the Family group, the printed part */
  red: "#E0402B",
  redDeep: "#A8281A",
  redDark: "#6F170E",
  /** the Start button's blue: the owner, the Lab group */
  blue: "#2E63F6",
  blueDeep: "#1C3FA8",
  /** the build plate (PEI sheet) and the bed under it */
  plate: "#7C6D5A",
  plateLine: "#8D7E69",
  plateEdge: "#4B4136",
  bed: "#26272B",
  /** done: one green, for a finished print only */
  green: "#3FAE6B",
  /** the done box (cardboard) */
  box: "#B98F5E",
  boxDeep: "#8A6740",
  boxDark: "#5E4529",
} as const;

// ---------------------------------------------------------------------------------------------------------------
// Type
// ---------------------------------------------------------------------------------------------------------------
const face = (family: string, file: string, weight: number) =>
  `@font-face { font-family: "${family}"; src: url("${staticFile(`fonts/${file}`)}"); font-weight: ${weight}; font-style: normal; }`;

/** Put <style>{FONTS}</style> once at the top of a composition (Stage does it). */
export const FONTS = [
  face("BG Display", "BricolageGrotesque96pt-ExtraBold.ttf", 800),
  face("BG Display", "BricolageGrotesque96pt-Bold.ttf", 700),
  face("BG Text", "BricolageGrotesque-Regular.ttf", 400),
  face("BG Text", "BricolageGrotesque-Medium.ttf", 500),
  face("BG Text", "BricolageGrotesque-SemiBold.ttf", 600),
  face("BG Text", "BricolageGrotesque-Bold.ttf", 700),
].join("\n");

export const F = {
  /** big words: weights 700 and 800 */
  display: "'BG Display', 'DejaVu Sans', sans-serif",
  /** everything else: weights 400, 500, 600, 700 */
  text: "'BG Text', 'DejaVu Sans', sans-serif",
  /** a command line or a tool name, nothing else */
  mono: "'DejaVu Sans Mono', monospace",
} as const;

/** Sizes in px. Nothing that must be read goes under `read`; `small` is the floor for small print. */
export const T = { giant: 300, huge: 200, display: 132, title: 96, read: 60, body: 46, small: 34 } as const;

// ---------------------------------------------------------------------------------------------------------------
// Time
// ---------------------------------------------------------------------------------------------------------------
export const FPS = 30;
/** seconds to frames */
export const s = (sec: number) => Math.round(sec * FPS);
export const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
export const OUT = Easing.out(Easing.cubic);
export const INOUT = Easing.inOut(Easing.cubic);
export const IN = Easing.in(Easing.cubic);
const QUINT = Easing.out(Easing.poly(5));

/** 0 before a, 1 after b, eased between. */
export function ramp(f: number, a: number, b: number, easing: (t: number) => number = OUT): number {
  return interpolate(f, [a, Math.max(a + 1, b)], [0, 1], { ...clamp, easing });
}
/** a value that moves from `from` to `to` between frames a and b */
export function tween(f: number, a: number, b: number, from: number, to: number, easing: (t: number) => number = OUT): number {
  return from + (to - from) * ramp(f, a, b, easing);
}
/** an overshooting settle for things that pop: 0 -> about 1.06 -> 1 over `frames` */
export function pop(f: number, at: number, frames = 12): number {
  const t = interpolate(f, [at, at + frames], [0, 1], clamp);
  if (t <= 0) return 0;
  const c = 1.70158 * 1.25;
  return 1 + (c + 1) * Math.pow(t - 1, 3) + c * Math.pow(t - 1, 2);
}
/** 1 while a thing is on screen, with a short fade at both ends (to === undefined: never leaves) */
export function hold(f: number, from: number, to?: number, fadeIn = 6, fadeOut = 6): number {
  const a = ramp(f, from, from + fadeIn, (t) => t);
  const b = to === undefined ? 1 : 1 - ramp(f, to - fadeOut, to, (t) => t);
  return Math.min(a, b);
}
/** piecewise-linear keys with easing between them: keys = [[frame, value], ...] */
export function keys(f: number, k: Array<[number, number]>, easing: (t: number) => number = INOUT): number {
  if (f <= k[0][0]) return k[0][1];
  for (let i = 0; i < k.length - 1; i++) {
    const [fa, va] = k[i];
    const [fb, vb] = k[i + 1];
    if (f <= fb) return va + (vb - va) * ramp(f, fa, fb, easing);
  }
  return k[k.length - 1][1];
}

// ---------------------------------------------------------------------------------------------------------------
// Stage: the ground of a drawn scene
// ---------------------------------------------------------------------------------------------------------------
export type StageProps = {
  /** ground colour (default the studio) */
  bg?: string;
  /** the soft light from above that the studio has (default true on ink) */
  light?: boolean;
  /** a slow push-in over the scene so no frame is perfectly still: total scale gained over `frames` (default 0.035) */
  drift?: number;
  frames?: number;
  children?: ReactNode;
};

export function Stage({ bg = P.ink, light, drift = 0.035, frames = 300, children }: StageProps) {
  const f = useCurrentFrame();
  const k = 1 + drift * interpolate(f, [0, frames], [0, 1], clamp);
  const lit = light ?? bg === P.ink;
  return (
    <AbsoluteFill style={{ background: bg, overflow: "hidden" }}>
      <style>{FONTS}</style>
      {lit && (
        <AbsoluteFill style={{ backgroundImage: "radial-gradient(ellipse 70% 60% at 50% 34%, rgba(92,96,108,0.34) 0%, rgba(92,96,108,0.10) 55%, rgba(92,96,108,0) 100%)" }} />
      )}
      {lit && <Grain />}
      <AbsoluteFill style={{ transform: `scale(${k})`, transformOrigin: "50% 50%" }}>{children}</AbsoluteFill>
    </AbsoluteFill>
  );
}

/** Fine, faint noise over the studio's light, so eight-bit video does not draw the gradient as rings. */
function Grain() {
  const src = staticFile("grain/grain.png");
  const tiles: ReactNode[] = [];
  for (let y = 0; y < 3; y++) for (let x = 0; x < 4; x++) tiles.push(<Img key={`${x}-${y}`} src={src} style={{ position: "absolute", left: x * 512, top: y * 512, width: 512, height: 512 }} />);
  return <AbsoluteFill>{tiles}</AbsoluteFill>;
}

// ---------------------------------------------------------------------------------------------------------------
// Words: a line that arrives word by word from behind its own baseline
// ---------------------------------------------------------------------------------------------------------------
export type WordsProps = {
  text: string;
  /** local frame the first word starts; each next word starts `each` frames later (default 2) */
  at?: number;
  each?: number;
  /** local frame the line leaves (fades and lifts); undefined = stays */
  out?: number;
  size?: number;
  weight?: number;
  color?: string;
  font?: string;
  lineHeight?: number;
  tracking?: number;
  align?: "left" | "center" | "right";
  /** box width in px: the line wraps inside it */
  width?: number;
  /** words to paint in another colour: { "box.": P.red } (match is on the word as written) */
  tint?: Record<string, string>;
  style?: CSSProperties;
};

export function Words({ text, at = 0, each = 2, out, size = T.display, weight = 800, color = P.bone, font = F.display, lineHeight = 0.98, tracking, align = "left", width, tint, style }: WordsProps) {
  const f = useCurrentFrame();
  const words = text.split(" ");
  const gone = out === undefined ? 0 : ramp(f, out - 8, out, IN);
  const ls = tracking ?? (size >= 90 ? -0.018 * size : -0.008 * size);
  return (
    <div
      style={{
        display: "flex", flexDirection: "row", flexWrap: "wrap", justifyContent: align === "center" ? "center" : align === "right" ? "flex-end" : "flex-start",
        width, columnGap: size * 0.24, rowGap: 0, fontFamily: font, fontWeight: weight, fontSize: size, lineHeight, letterSpacing: ls, color,
        opacity: 1 - gone, transform: `translateY(${-24 * gone}px)`, ...style,
      }}
    >
      {words.map((w, i) => {
        const t = ramp(f, at + i * each, at + i * each + 11, QUINT);
        return (
          <span key={i} style={{ display: "block", overflow: "hidden", height: size * lineHeight * 1.12, marginBottom: -size * lineHeight * 0.12 }}>
            <span style={{ display: "block", whiteSpace: "nowrap", color: tint?.[w] ?? color, transform: `translateY(${(1 - t) * size * 1.15}px)`, opacity: t > 0 ? 1 : 0 }}>{w}</span>
          </span>
        );
      })}
    </div>
  );
}

/** A plain block of text that fades and rises a little: for small print and second lines. */
export function Line({ children, at = 0, out, size = T.body, weight = 500, color = P.mist, font = F.text, style }: { children: ReactNode; at?: number; out?: number; size?: number; weight?: number; color?: string; font?: string; style?: CSSProperties }) {
  const f = useCurrentFrame();
  const t = ramp(f, at, at + 10);
  const gone = out === undefined ? 0 : ramp(f, out - 8, out, IN);
  return (
    <div style={{ fontFamily: font, fontWeight: weight, fontSize: size, lineHeight: 1.18, color, opacity: t * (1 - gone), transform: `translateY(${(1 - t) * 18 - gone * 14}px)`, ...style }}>{children}</div>
  );
}

// ---------------------------------------------------------------------------------------------------------------
// Bubble: a chat message in its group's colour (the plugin's own rule for a request)
// ---------------------------------------------------------------------------------------------------------------
export type BubbleProps = {
  text: string;
  /** who wrote it and in which group: shown above the bubble as "Mum  Family" */
  who?: string;
  group?: string;
  /** bubble colour and text colour (default red with bone text) */
  color?: string;
  ink?: string;
  /** "left" = somebody else's message, "right" = the agent's reply */
  side?: "left" | "right";
  /** local frame it pops in; `out` = local frame it leaves */
  at?: number;
  out?: number;
  /** type size (default T.read) and the bubble's width */
  size?: number;
  width?: number;
  /** show the words being typed, starting at `at + 6`, `cps` characters per second (0 = all at once) */
  cps?: number;
  style?: CSSProperties;
};

export function Bubble({ text, who, group, color = P.red, ink = P.bone, side = "left", at = 0, out, size = T.read, width = 900, cps = 0, style }: BubbleProps) {
  const f = useCurrentFrame();
  const k = pop(f, at, 13);
  const gone = out === undefined ? 0 : ramp(f, out - 7, out, IN);
  const shown = cps > 0 ? Math.max(0, Math.min(text.length, Math.floor(((f - at - 6) / FPS) * cps))) : text.length;
  const r = Math.round(size * 0.62);
  const corner = side === "left" ? `${r}px ${r}px ${r}px ${Math.round(r * 0.22)}px` : `${r}px ${r}px ${Math.round(r * 0.22)}px ${r}px`;
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: side === "left" ? "flex-start" : "flex-end", width, opacity: (k > 0 ? 1 : 0) * (1 - gone), transform: `translateY(${-30 * gone}px)`, ...style }}>
      {who && (
        <div style={{ display: "flex", flexDirection: "row", alignItems: "center", gap: 14, marginBottom: 14, opacity: ramp(f, at + 2, at + 10), fontFamily: F.text, fontSize: T.small, lineHeight: 1, color: P.mist, fontWeight: 500 }}>
          <span style={{ width: 44, height: 44, borderRadius: 22, background: color, color: ink, display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 700, fontSize: 24 }}>{who.slice(0, 1)}</span>
          <span style={{ color: P.bone, fontWeight: 700 }}>{who}</span>
          {group && <span>{group}</span>}
        </div>
      )}
      <div
        style={{
          boxSizing: "border-box", maxWidth: width, padding: `${Math.round(size * 0.5)}px ${Math.round(size * 0.72)}px ${Math.round(size * 0.56)}px`, borderRadius: corner, background: color, color: ink,
          fontFamily: F.text, fontWeight: 600, fontSize: size, lineHeight: 1.16, letterSpacing: -0.01 * size,
          transform: `scale(${Math.max(0.001, k)})`, transformOrigin: side === "left" ? "0% 0%" : "100% 0%",
        }}
      >
        <span>{text.slice(0, shown)}</span>
        <span style={{ opacity: 0 }}>{text.slice(shown)}</span>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------------------------------------------
// Chip: one small fact (a tool name, a label). Not for decoration.
// ---------------------------------------------------------------------------------------------------------------
export function Chip({ children, at = 0, out, color = P.bone, bg = P.ink2, mono = false, size = T.small, style }: { children: ReactNode; at?: number; out?: number; color?: string; bg?: string; mono?: boolean; size?: number; style?: CSSProperties }) {
  const f = useCurrentFrame();
  const t = ramp(f, at, at + 9);
  const gone = out === undefined ? 0 : ramp(f, out - 6, out, IN);
  return (
    <div style={{ display: "flex", flexDirection: "row", opacity: t * (1 - gone), transform: `translateX(${(1 - t) * -24}px)`, ...style }}>
      <div
        style={{
          display: "flex", flexDirection: "row", alignItems: "center", boxSizing: "border-box", height: Math.round(size * 1.9), padding: `0 ${Math.round(size * 0.7)}px`, borderRadius: Math.round(size * 0.5),
          background: bg, color, fontFamily: mono ? F.mono : F.text, fontWeight: mono ? 700 : 600, fontSize: size, lineHeight: 1, whiteSpace: "nowrap",
        }}
      >
        {children}
      </div>
    </div>
  );
}

/** The honesty label for a picture that is not live footage. Bottom-left by default. */
export const LABELS = {
  chat: "Re-created from real chats. Names changed.",
  photo: "Real photo from the printer's camera",
  screen: "The plugin's real screen, on its simulated printer",
  footage: "Real footage of the printer at home",
} as const;

export function Label({ kind, at = 0, out, tone = "dark", style }: { kind: keyof typeof LABELS; at?: number; out?: number; tone?: "dark" | "light"; style?: CSSProperties }) {
  const f = useCurrentFrame();
  const o = hold(f, at, out, 8, 6);
  const dark = tone === "dark";
  return (
    <div
      style={{
        position: "absolute", left: 64, bottom: 124, height: 54, padding: "0 22px", borderRadius: 12, display: "flex", alignItems: "center",
        background: dark ? "rgba(18,19,22,0.82)" : "rgba(243,241,236,0.92)", color: dark ? P.bone : P.ink, fontFamily: F.text, fontWeight: 600, fontSize: 32, lineHeight: 1, whiteSpace: "nowrap", opacity: o, ...style,
      }}
    >
      {LABELS[kind]}
    </div>
  );
}

// ---------------------------------------------------------------------------------------------------------------
// Wipe: a colour that grows from a point until it is the whole frame. A scene ends on the next scene's ground.
// ---------------------------------------------------------------------------------------------------------------
export function Wipe({ at, frames = 14, x = 960, y = 540, color, reverse = false }: { at: number; frames?: number; x?: number; y?: number; color: string; reverse?: boolean }) {
  const f = useCurrentFrame();
  const t = reverse ? 1 - ramp(f, at, at + frames, INOUT) : ramp(f, at, at + frames, INOUT);
  if (t <= 0) return null;
  const far = Math.hypot(Math.max(x, 1920 - x), Math.max(y, 1080 - y)) + 40;
  const r = far * t;
  return <div style={{ position: "absolute", left: x - r, top: y - r, width: 2 * r, height: 2 * r, borderRadius: r, background: color }} />;
}

// ---------------------------------------------------------------------------------------------------------------
// Screen: a real capture of the plugin's screen, full frame, with a camera and a pointer
// ---------------------------------------------------------------------------------------------------------------
export type CamKey = { at: number; x: number; y: number; scale: number };
export type PtrKey = { at: number; x: number; y: number };

function track<K extends { at: number }>(ks: K[], f: number, pick: (k: K) => number[]): number[] {
  if (ks.length === 1 || f <= ks[0].at) return pick(ks[0]);
  for (let i = 0; i < ks.length - 1; i++) {
    const a = ks[i];
    const b = ks[i + 1];
    if (f <= b.at) {
      const t = ramp(f, a.at, b.at, INOUT);
      const pa = pick(a);
      const pb = pick(b);
      return pa.map((v, j) => v + (pb[j] - v) * t);
    }
  }
  return pick(ks[ks.length - 1]);
}

export type ScreenProps = {
  /** path under media/: "screen/backroom.mp4", "screen/watch.mp4" or "screen/twist.png" (all 1920 x 1080) */
  file: string;
  /** for a video: the source frame to start at */
  startFrom?: number;
  /** camera keys in capture pixels: the point to centre and the scale (1 = the whole screen fills the frame) */
  cam?: CamKey[];
  /** pointer keys in capture pixels; hidden before the first key and after `ptrOut` */
  ptr?: PtrKey[];
  ptrOut?: number;
  /** local frames where the pointer clicks */
  clicks?: number[];
  /** ring colour of a click (default the Start button's blue) */
  ring?: string;
};

/** The capture drawn 1:1 in the 1920 x 1080 frame and moved by the camera. Put captions over it yourself. */
export function Screen({ file, startFrom, cam, ptr, ptrOut, clicks = [], ring = P.blue }: ScreenProps) {
  const f = useCurrentFrame();
  const W = 1920;
  const H = 1080;
  const [zx, zy, zs] = cam && cam.length ? track(cam, f, (c) => [c.x, c.y, c.scale]) : [W / 2, H / 2, 1];
  // the point (zx, zy) goes to the middle of the frame; never show beyond the capture's edge when zoomed in
  const tx = zs >= 1 ? Math.min(0, Math.max(W - W * zs, W / 2 - zx * zs)) : W / 2 - zx * zs;
  const ty = zs >= 1 ? Math.min(0, Math.max(H - H * zs, H / 2 - zy * zs)) : H / 2 - zy * zs;
  const url = staticFile(file);
  let pointer: ReactNode = null;
  if (ptr && ptr.length && f >= ptr[0].at && (ptrOut === undefined || f < ptrOut)) {
    const [px, py] = track(ptr, f, (p) => [p.x, p.y]);
    const sx = tx + px * zs;
    const sy = ty + py * zs;
    const o = Math.min(ramp(f, ptr[0].at, ptr[0].at + 6), ptrOut === undefined ? 1 : 1 - ramp(f, ptrOut - 6, ptrOut));
    let dip = 1;
    const rings: ReactNode[] = [];
    for (const c of clicks) {
      if (f >= c - 3 && f < c + 6) dip = Math.min(dip, interpolate(f, [c - 3, c, c + 6], [1, 0.82, 1], clamp));
      if (f >= c && f < c + 20) {
        const t = ramp(f, c, c + 20);
        const r = 16 + 70 * t;
        rings.push(<div key={c} style={{ position: "absolute", left: sx - r, top: sy - r, width: 2 * r, height: 2 * r, borderRadius: r, border: `7px solid ${ring}`, boxSizing: "border-box", opacity: 1 - t }} />);
      }
    }
    pointer = (
      <>
        {rings}
        <div style={{ position: "absolute", left: sx - 6, top: sy - 4, opacity: o, transform: `scale(${dip})`, transformOrigin: "6px 4px" }}>
          <Pointer size={72} />
        </div>
      </>
    );
  }
  return (
    <AbsoluteFill style={{ background: "#F4F5F7", overflow: "hidden" }}>
      <div style={{ position: "absolute", left: 0, top: 0, width: W, height: H, transformOrigin: "0 0", transform: `translate(${tx}px, ${ty}px) scale(${zs})` }}>
        {/\.mp4$/i.test(file) ? <Video src={url} muted startFrom={startFrom} style={{ width: W, height: H }} /> : <Img src={url} style={{ width: W, height: H }} />}
      </div>
      {pointer}
    </AbsoluteFill>
  );
}

/** An arrow pointer, drawn (a pointer is not a logo). Tip at (6, 4) of its box at size 72. */
export function Pointer({ size = 72 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24">
      <path d="M2 1.5 L2 19.5 L7 15 L10.3 22.3 L13.6 20.8 L10.4 13.7 L17 13.7 Z" fill="#121316" stroke="#FFFFFF" strokeWidth="1.6" strokeLinejoin="round" />
    </svg>
  );
}

// ---------------------------------------------------------------------------------------------------------------
// Iso: the build plate as a stage, drawn in layers. Everything on it is a slab at a height; slabs are painted from
// the lowest up, so a part hides what is behind it and a box's front wall hides what falls into it.
// ---------------------------------------------------------------------------------------------------------------
/** Plate units: 1 unit = 0.25 mm. The tag is 58 x 24 mm = 232 x 96 units. */
export const MM = 4;

export type View = {
  /** where the plate's centre sits in the frame */
  cx: number;
  cy: number;
  /** screen px per plate unit (2 = the tag is 464 px wide) */
  scale: number;
  /** turn of the plate in radians (0 = the tag reads left to right) */
  yaw: number;
  /** how far down the camera looks: 0.5 = classic, 0.62 = more from above */
  pitch?: number;
};

export type Slab = { z: number; key: string; el: ReactNode };

const vz = (v: View) => Math.sqrt(1 - (v.pitch ?? 0.56) ** 2);

/** Where a plate point (units) at height z (units) lands in the frame. */
export function project(v: View, x: number, y: number, z = 0): [number, number] {
  const k = v.pitch ?? 0.56;
  const c = Math.cos(v.yaw);
  const sn = Math.sin(v.yaw);
  return [v.cx + v.scale * (x * c - y * sn), v.cy + v.scale * k * (x * sn + y * c) - v.scale * vz(v) * z];
}

/** Draws slabs, lowest first. Children of a slab are positioned in plate units from the plate's centre. */
export function Iso({ view, slabs, children }: { view: View; slabs: Slab[]; children?: ReactNode }) {
  const k = view.pitch ?? 0.56;
  const c = Math.cos(view.yaw);
  const sn = Math.sin(view.yaw);
  const a = view.scale * c;
  const b = view.scale * k * sn;
  const cc = -view.scale * sn;
  const d = view.scale * k * c;
  const sorted = [...slabs].sort((p, q) => p.z - q.z);
  return (
    <AbsoluteFill>
      {sorted.map((sl) => (
        <div key={sl.key} style={{ position: "absolute", left: 0, top: 0, width: 0, height: 0, transformOrigin: "0 0", transform: `matrix(${a}, ${b}, ${cc}, ${d}, ${view.cx}, ${view.cy - view.scale * vz(view) * sl.z})` }}>{sl.el}</div>
      ))}
      {children}
    </AbsoluteFill>
  );
}

const rect = (x: number, y: number, w: number, h: number, r: number, bg: string, extra?: CSSProperties): ReactNode => (
  <div style={{ position: "absolute", left: x - w / 2, top: y - h / 2, width: w, height: h, borderRadius: r, background: bg, boxSizing: "border-box", ...extra }} />
);

/** The plate: a bronze sheet with its grid on a dark bed. `size` in units (default 1024 = 256 mm). */
export function plateSlabs({ size = 1024, grid = 128, shadow }: { size?: number; grid?: number; shadow?: { x: number; y: number; w: number; h: number; o?: number } } = {}): Slab[] {
  const out: Slab[] = [];
  // the bed under the sheet
  for (let i = 0; i < 5; i++) out.push({ z: -34 + i * 4, key: `bed${i}`, el: rect(0, 0, size + 44, size + 44, 30, i === 4 ? "#2E3035" : P.bed) });
  // the sheet's edge
  for (let i = 0; i < 4; i++) out.push({ z: -12 + i * 3, key: `edge${i}`, el: rect(0, 0, size, size, 22, P.plateEdge) });
  const lines: ReactNode[] = [];
  const n = Math.floor(size / 2 / grid);
  for (let i = -n; i <= n; i++) {
    const major = i % 2 === 0;
    const w = major ? 3 : 1.6;
    const col = major ? P.plateLine : "rgba(141,126,105,0.55)";
    lines.push(<div key={`v${i}`} style={{ position: "absolute", left: i * grid - w / 2, top: -size / 2 + 14, width: w, height: size - 28, background: col }} />);
    lines.push(<div key={`h${i}`} style={{ position: "absolute", top: i * grid - w / 2, left: -size / 2 + 14, height: w, width: size - 28, background: col }} />);
  }
  out.push({
    z: 0,
    key: "sheet",
    el: (
      <>
        {rect(0, 0, size, size, 22, P.plate)}
        {lines}
        {shadow && rect(shadow.x, shadow.y, shadow.w, shadow.h, 34, `rgba(20,14,8,${shadow.o ?? 0.38})`)}
      </>
    ),
  });
  return out;
}

export type TagProps = {
  /** 0..1: how much of the 21 layers is printed (1 = finished) */
  printed?: number;
  /** where the tag's centre is on the plate (units) and how high its underside is */
  x?: number;
  y?: number;
  z?: number;
  /** the word on it */
  word?: string;
  /** colours: top face, sides, letters' top */
  top?: string;
  side?: string;
  dark?: string;
  /** a key prefix when more than one tag is on screen */
  id?: string;
  /** 1 = solid; more than 1 lifts the layers apart so each one can be seen (the sliced look) */
  spread?: number;
};

/** Sizes of the tag in units, and its heights (drawn 2.5 times the real 4.2 mm so the layers can be seen). */
export const TAG = { w: 232, h: 96, r: 26, hole: 11, holeX: -86, base: 15, layers: 21, layerZ: 2.1, font: 62 } as const;

/** The name tag as slabs: a base of 15 layers with a hole, then 6 layers of letters. */
export function tagSlabs({ printed = 1, x = 0, y = 0, z = 0, word = "MUM", top = P.red, side = P.redDeep, dark = P.redDark, id = "tag", spread = 1 }: TagProps = {}): Slab[] {
  const out: Slab[] = [];
  const total = TAG.layers;
  const done = Math.max(0, Math.min(total, printed * total));
  const full = Math.floor(done);
  const part = done - full; // how much of the next layer is laid down
  const hole = (col: string) => <div style={{ position: "absolute", left: x + TAG.holeX - TAG.hole, top: y - TAG.hole, width: TAG.hole * 2, height: TAG.hole * 2, borderRadius: TAG.hole, background: col }} />;
  const letters = (col: string) => (
    <div style={{ position: "absolute", left: x - TAG.w / 2 + 48, top: y - TAG.h / 2, width: TAG.w - 62, height: TAG.h, display: "flex", alignItems: "center", justifyContent: "center", fontFamily: F.display, fontWeight: 800, fontSize: TAG.font, lineHeight: 1, letterSpacing: 2, color: col, whiteSpace: "nowrap" }}>{word}</div>
  );
  const layer = (i: number, frac: number, cap: boolean): ReactNode => {
    // frac < 1: only the left part of this layer exists yet (the nozzle is laying it down)
    const isBase = i < TAG.base;
    const body = isBase ? (
      <>
        {rect(x, y, TAG.w, TAG.h, TAG.r, cap ? top : side)}
        {hole(dark)}
      </>
    ) : (
      letters(cap ? "#F4705C" : side)
    );
    if (frac >= 1) return body;
    return <div style={{ position: "absolute", left: x - TAG.w / 2, top: y - TAG.h / 2, width: TAG.w * frac, height: TAG.h, overflow: "hidden" }}><div style={{ position: "absolute", left: TAG.w / 2 - x, top: TAG.h / 2 - y, width: 0, height: 0 }}>{body}</div></div>;
  };
  for (let i = 0; i < full; i++) {
    const isTopOfBase = i === Math.min(full, TAG.base) - 1 && i < TAG.base;
    const isTopOfLetters = i === full - 1 && i >= TAG.base;
    // two slabs per layer so the wall has no gaps
    // spread > 1: every layer is its own lit sheet with air under it
    const cap = spread > 1.02 ? true : isTopOfBase || isTopOfLetters;
    out.push({ z: z + (i * spread + (spread > 1.02 ? 0.1 : 0.5)) * TAG.layerZ, key: `${id}a${i}`, el: layer(i, 1, false) });
    out.push({ z: z + (i * spread + 1) * TAG.layerZ, key: `${id}b${i}`, el: layer(i, 1, cap) });
  }
  if (part > 0 && full < total) out.push({ z: z + (full * spread + 1) * TAG.layerZ, key: `${id}p`, el: layer(full, part, true) });
  return out;
}

/** Where the nozzle is while layer `printed * 21` is being laid: [x, y, z] in units. */
export function nozzleAt(printed: number, f: number, x = 0, y = 0, z = 0): [number, number, number] {
  const done = Math.max(0, Math.min(TAG.layers, printed * TAG.layers));
  const part = done - Math.floor(done);
  return [x - TAG.w / 2 + TAG.w * part, y + Math.sin(f * 1.9) * TAG.h * 0.42, z + (Math.floor(done) + 1) * TAG.layerZ];
}

/** The print head, drawn in the frame at a projected point (not a slab: it is above everything). */
export function Nozzle({ view, at, o = 1 }: { view: View; at: [number, number, number]; o?: number }) {
  const [sx, sy] = project(view, at[0], at[1], at[2]);
  const k = view.scale / 2;
  return (
    <div style={{ position: "absolute", left: sx, top: sy, width: 0, height: 0, opacity: o }}>
      {/* the hot tip */}
      <div style={{ position: "absolute", left: -7 * k, top: -26 * k, width: 14 * k, height: 26 * k, background: "#C9CDD6", borderRadius: `${2 * k}px ${2 * k}px ${7 * k}px ${7 * k}px` }} />
      {/* the heater block and the head */}
      <div style={{ position: "absolute", left: -26 * k, top: -62 * k, width: 52 * k, height: 38 * k, background: "#3A3D45", borderRadius: 8 * k }} />
      <div style={{ position: "absolute", left: -58 * k, top: -196 * k, width: 116 * k, height: 138 * k, background: "#22242A", borderRadius: 18 * k, border: `${3 * k}px solid #3A3D45`, boxSizing: "border-box" }} />
      <div style={{ position: "absolute", left: -34 * k, top: -170 * k, width: 68 * k, height: 68 * k, borderRadius: 34 * k, background: "#16171B", border: `${3 * k}px solid #3A3D45`, boxSizing: "border-box" }} />
      {/* the dot of molten filament */}
      <div style={{ position: "absolute", left: -5 * k, top: -5 * k, width: 10 * k, height: 10 * k, borderRadius: 5 * k, background: "#FF8A6B" }} />
    </div>
  );
}

/** The done box: an open cardboard box as slabs (hollow walls), `w` x `d` units, `h` units tall, centred at (x, y). */
export function boxSlabs({ x = 0, y = 0, z = 0, w = 330, d = 250, h = 120, id = "box" }: { x?: number; y?: number; z?: number; w?: number; d?: number; h?: number; id?: string } = {}): Slab[] {
  const out: Slab[] = [];
  out.push({ z: z + 1, key: `${id}floor`, el: rect(x, y, w, d, 14, P.boxDark) });
  const n = Math.round(h / 3);
  for (let i = 1; i <= n; i++) {
    const top = i === n;
    out.push({ z: z + i * 3, key: `${id}w${i}`, el: rect(x, y, w, d, 14, "transparent", { border: `9px solid ${top ? P.box : P.boxDeep}` }) });
  }
  return out;
}

// ---------------------------------------------------------------------------------------------------------------
// Small parts
// ---------------------------------------------------------------------------------------------------------------
/** A number that counts from `from` to `to` between two frames. */
export function Count({ at, frames = 24, from = 0, to, digits = 0 }: { at: number; frames?: number; from?: number; to: number; digits?: number }) {
  const f = useCurrentFrame();
  const v = tween(f, at, at + frames, from, to, OUT);
  return <>{v.toFixed(digits)}</>;
}

/** A photo that fills the frame (cover) and pushes in slowly. `focus` is the point kept in view, 0..1 each way. */
export function Photo({ file, focus = [0.5, 0.5], from = 1.06, to = 1.16, frames = 120, dim = 0 }: { file: string; focus?: [number, number]; from?: number; to?: number; frames?: number; dim?: number }) {
  const f = useCurrentFrame();
  const k = interpolate(f, [0, frames], [from, to], clamp);
  return (
    <AbsoluteFill style={{ overflow: "hidden", background: "#000" }}>
      <Img src={staticFile(file)} style={{ position: "absolute", left: 0, top: 0, width: 1920, height: 1080, objectFit: "cover", transform: `scale(${k})`, transformOrigin: `${focus[0] * 100}% ${focus[1] * 100}%` }} />
      {dim > 0 && <AbsoluteFill style={{ background: `rgba(18,19,22,${dim})` }} />}
    </AbsoluteFill>
  );
}
