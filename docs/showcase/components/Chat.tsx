// Chat: a phone-shaped group chat in the film's own neutral style (not any real messaging app's look).
// The phone stands in the frame from y 90 and runs off the bottom edge; messages live in a viewport that ends on the
// safe line (y 960). The column is anchored to the bottom, so the newest message is always in view and older ones
// scroll up and out; each new message grows in over 9 frames so the scroll is smooth.
import { AbsoluteFill, Img, interpolate, useCurrentFrame } from "raea";
import { C, FONT, LH, PEOPLE, R, SHADOW, SIZE, W } from "../theme";
import { Flask, Home, ICONS, Play, type IconName } from "./Icons";
import { Label, type Corner } from "./Label";
import { info, src } from "./media";
import { OUT, clamp, inOut, ramp } from "./timing";

export type ChatMessage = {
  /** sender: "Mum", "Dad", "Sam", "Owner", "Engineer", "Mıstık" (never a real name) */
  from: string;
  /** local frame the message lands */
  at: number;
  /** "text" (default) | "voice" (a voice note with waveform) | "image" (a picture, with optional text under it) */
  kind?: "text" | "voice" | "image";
  /** the message text (text kind; for image, a line under the picture) */
  text?: string;
  /** an icon drawn after the text, at text size: "heart" | "rose" | "check" | ... (see Icons.tsx) */
  icon?: IconName;
  /** frames of the typing indicator before `at` (default 0 = none) */
  typing?: number;
  /** voice: duration shown on the bubble, e.g. "0:06" */
  duration?: string;
  /** voice: frames the playback sweep takes after landing (default 60) */
  play?: number;
  /** voice: the transcript under the bubble: original (small, e.g. the Turkish line) and english (large) */
  transcript?: { original?: string; english: string; at?: number };
  /** image: path under media/, e.g. "real/rose-box-slicer-render.png" */
  image?: string;
  /** image: shown width in px (default 460) */
  imageWidth?: number;
};

export type ChatProps = {
  /** the group's name in the header, e.g. "Family" */
  title: string;
  /** a line under the name, e.g. "Mum, Dad, Sam, Mıstık" */
  subtitle?: string;
  /** the header's round icon: "home" (default) | "lab" */
  group?: "home" | "lab";
  messages: ChatMessage[];
  /** whose phone this is: that person's messages sit on the right, without a name. Default: nobody (all left) */
  me?: string;
  /** the agent's name: its bubbles are pale rose (default "Mıstık") */
  agent?: string;
  /** phone's left edge in px (default 130); width (default 880). The default leaves x 1100..1860 free for a Caption place="right" */
  x?: number;
  width?: number;
  /** honesty chip (default true) and its corner (default: bottom corner on the side away from the phone) */
  label?: boolean;
  labelAt?: Corner;
  /** local frames: the phone rises in from `from` (default 0), fades out by `to` (default never) */
  from?: number;
  to?: number;
  /** ground behind the phone (default paper); pass "transparent" to put the phone over a PhotoStage */
  bg?: string;
};

const TOP = 90;
const VIEW_BOTTOM = 960;
const HEADER = 132;
const BEZEL = 14;
const PAD = 30;

/** A rough height for a message, so it can grow in without measuring. Generous on purpose: a low guess clips. */
function estimate(m: ChatMessage, textW: number, showName: boolean) {
  const lines = (t: string, px: number) => t.split("\n").reduce((n, p) => n + Math.max(1, Math.ceil((p.length * px * 0.6) / textW)), 0);
  let h = showName ? SIZE.chatSmall * 1.3 + 8 : 0;
  const kind = m.kind ?? "text";
  if (kind === "text") h += lines(m.text ?? "", SIZE.chat) * SIZE.chat * LH.chat + 48;
  if (kind === "voice") {
    h += 120;
    if (m.transcript) h += 40 + (m.transcript.original ? lines(m.transcript.original, SIZE.chatSmall) * SIZE.chatSmall * 1.25 + 12 : 0) + lines(m.transcript.english, SIZE.chat) * SIZE.chat * LH.chat + 40;
  }
  if (kind === "image") {
    const meta = m.image ? info(m.image) : undefined;
    const w = m.imageWidth ?? 460;
    h += (meta?.w && meta?.h ? (w * meta.h) / meta.w : w * 0.75) + 36 + (m.text ? lines(m.text, SIZE.chat) * SIZE.chat * LH.chat + 16 : 0);
  }
  return Math.ceil(h * 1.25 + 30);
}

/** The waveform's bar heights, fixed by index so they hold still from frame to frame. */
const BARS = Array.from({ length: 30 }, (_, i) => 0.25 + 0.75 * Math.abs(Math.sin(i * 1.7) * Math.cos(i * 0.6 + 1)));

function Waveform({ progress, color, rest }: { progress: number; color: string; rest: string }) {
  return (
    <div style={{ display: "flex", flexDirection: "row", alignItems: "center", gap: 6, height: 64 }}>
      {BARS.map((b, i) => (
        <div key={i} style={{ width: 7, height: Math.round(10 + 50 * b), borderRadius: 4, background: i / BARS.length < progress ? color : rest }} />
      ))}
    </div>
  );
}

function TypingDots({ f }: { f: number }) {
  return (
    <div style={{ display: "flex", flexDirection: "row", gap: 12, padding: "8px 6px", alignItems: "center", height: SIZE.chat * LH.chat }}>
      {[0, 1, 2].map((i) => {
        const p = (Math.sin((f - i * 5) / 4) + 1) / 2;
        return <div key={i} style={{ width: 16, height: 16, borderRadius: 999, background: C.inkSoft, opacity: 0.35 + 0.55 * p, transform: `translateY(${-6 * p}px)` }} />;
      })}
    </div>
  );
}

export function Chat({ title, subtitle, group = "home", messages, me, agent = "Mıstık", x = 130, width = 880, label = true, labelAt, from = 0, to, bg = C.paper }: ChatProps) {
  const f = useCurrentFrame();
  const screenW = width - 2 * BEZEL;
  const bubbleMax = Math.round(screenW * 0.8);
  const textW = bubbleMax - 2 * 32;
  const o = inOut(f, from, to, 12, 10);
  const rise = interpolate(ramp(f, from, from + 18, OUT), [0, 1], [60, 0], clamp);
  const GroupIcon = group === "lab" ? Flask : Home;

  // what is on screen now: landed messages, plus a typing bubble for the next one when its typing window is open
  type Row = { m: ChatMessage; typingOnly: boolean; at: number };
  const rows: Row[] = [];
  for (const m of messages) {
    if (f >= m.at) rows.push({ m, typingOnly: false, at: m.at });
    else if (m.typing && f >= m.at - m.typing) rows.push({ m, typingOnly: true, at: m.at - m.typing });
  }

  return (
    <AbsoluteFill style={{ background: bg }}>
      <div
        style={{
          position: "absolute", left: x, top: TOP, width, height: 1080 - TOP + 80, boxSizing: "border-box",
          borderRadius: R.phone, background: C.night, padding: BEZEL, boxShadow: SHADOW,
          opacity: o, transform: `translateY(${rise}px)`,
        }}
      >
        <div style={{ position: "relative", width: "100%", height: "100%", borderRadius: R.phone - BEZEL, overflow: "hidden", background: C.paperDeep }}>
          {/* header */}
          <div style={{ position: "absolute", left: 0, right: 0, top: 0, height: HEADER, boxSizing: "border-box", padding: "0 36px", display: "flex", flexDirection: "row", alignItems: "center", gap: 24, background: C.card, borderBottom: `2px solid ${C.line}` }}>
            <div style={{ width: 76, height: 76, borderRadius: 999, background: C.paperDeep, display: "flex", alignItems: "center", justifyContent: "center", color: C.ink }}>
              <GroupIcon size={44} color={C.ink} />
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 4, minWidth: 0 }}>
              <div style={{ fontFamily: FONT.sans, fontWeight: W.bold, fontSize: SIZE.chatSmall + 4, lineHeight: 1.1, color: C.ink, whiteSpace: "nowrap" }}>{title}</div>
              {subtitle && <div style={{ fontFamily: FONT.sans, fontWeight: W.regular, fontSize: SIZE.label, lineHeight: 1.15, color: C.inkSoft, whiteSpace: "nowrap" }}>{subtitle}</div>}
            </div>
          </div>
          {/* messages: anchored to the bottom of the viewport */}
          <div
            style={{
              position: "absolute", left: 0, right: 0, top: HEADER, height: VIEW_BOTTOM - TOP - BEZEL - HEADER,
              overflow: "hidden", display: "flex", flexDirection: "column", justifyContent: "flex-end",
              boxSizing: "border-box", padding: `0 ${PAD}px 24px`,
            }}
          >
            {rows.map((row, i) => {
              const m = row.m;
              const mine = me !== undefined && m.from === me;
              const isAgent = m.from === agent;
              const prev = rows[i - 1]?.m;
              const showName = !mine && (!prev || prev.from !== m.from);
              const est = estimate(row.typingOnly ? { from: m.from, at: m.at, text: "..." } : m, textW, showName);
              const grow = ramp(f, row.at, row.at + 9, OUT);
              const settled = grow >= 1;
              const bubbleBg = mine ? "#E3D2BC" : isAgent ? C.roseSoft : C.card;
              const kind = m.kind ?? "text";
              const IconC = m.icon ? ICONS[m.icon] : null;
              const nameColor = (PEOPLE as Record<string, { color: string }>)[m.from]?.color ?? C.inkSoft;
              return (
                <div
                  key={`${i}-${row.typingOnly ? "t" : "m"}`}
                  style={{
                    flexShrink: 0, overflow: settled ? "visible" : "hidden", maxHeight: settled ? 4000 : est * grow,
                    display: "flex", flexDirection: "column", alignItems: mine ? "flex-end" : "flex-start", paddingTop: showName ? 22 : 12,
                    opacity: ramp(f, row.at + 2, row.at + 10, OUT),
                  }}
                >
                  {showName && (
                    <div style={{ fontFamily: FONT.sans, fontWeight: W.bold, fontSize: SIZE.chatSmall, lineHeight: 1.3, color: nameColor, margin: "0 0 8px 6px" }}>{m.from}</div>
                  )}
                  <div
                    style={{
                      boxSizing: "border-box", maxWidth: bubbleMax, padding: kind === "image" ? 16 : "16px 32px 18px",
                      borderRadius: R.bubble, background: bubbleBg,
                      border: isAgent && !mine ? `2px solid rgba(181,50,31,0.18)` : `2px solid rgba(43,36,32,0.06)`,
                      fontFamily: FONT.sans, fontWeight: W.regular, fontSize: SIZE.chat, lineHeight: LH.chat, color: C.ink,
                      whiteSpace: "pre-line",
                    }}
                  >
                    {row.typingOnly ? (
                      <TypingDots f={f} />
                    ) : kind === "voice" ? (
                      <div style={{ display: "flex", flexDirection: "row", alignItems: "center", gap: 22, padding: "6px 0" }}>
                        <div style={{ width: 72, height: 72, borderRadius: 999, background: C.rose, display: "flex", alignItems: "center", justifyContent: "center" }}>
                          <Play size={36} color={C.card} />
                        </div>
                        <Waveform progress={interpolate(f, [m.at + 8, m.at + 8 + (m.play ?? 60)], [0, 1], clamp)} color={C.ink} rest="rgba(43,36,32,0.25)" />
                        <div style={{ fontFamily: FONT.sans, fontWeight: W.regular, fontSize: SIZE.chatSmall, lineHeight: 1, color: C.inkSoft }}>{m.duration ?? ""}</div>
                      </div>
                    ) : kind === "image" ? (
                      <ImageBody m={m} />
                    ) : (
                      IconC ? (
                        <div style={{ display: "flex", flexDirection: "row", alignItems: "center", gap: 14 }}>
                          <span>{m.text}</span>
                          <IconC size={Math.round(SIZE.chat * 0.92)} />
                        </div>
                      ) : (
                        <span>{m.text}</span>
                      )
                    )}
                  </div>
                  {!row.typingOnly && kind === "voice" && m.transcript && <Transcript t={m.transcript} f={f} at={m.transcript.at ?? m.at + 20} max={bubbleMax} />}
                </div>
              );
            })}
          </div>
          {/* the input bar: a plain field, no text */}
          <div style={{ position: "absolute", left: 0, right: 0, top: VIEW_BOTTOM - TOP - BEZEL, bottom: 0, background: C.card, borderTop: `2px solid ${C.line}` }}>
            <div style={{ margin: "22px 30px", height: 64, borderRadius: 999, background: C.paperDeep }} />
          </div>
        </div>
      </div>
      {label && <Label kind="chat" at={labelAt ?? (x + width / 2 < 960 ? "br" : "bl")} tone="light" from={from} to={to} />}
    </AbsoluteFill>
  );
}

function ImageBody({ m }: { m: ChatMessage }) {
  const w = m.imageWidth ?? 460;
  const meta = m.image ? info(m.image) : undefined;
  const h = Math.round(meta?.w && meta?.h ? (w * meta.h) / meta.w : w * 0.75);
  const url = m.image ? src(m.image) : undefined;
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      <div style={{ width: w, height: h, borderRadius: R.bubble - 12, overflow: "hidden", background: "#FFFFFF" }}>
        {url ? (
          <Img src={url} style={{ width: w, height: h, objectFit: "cover" }} />
        ) : (
          <div style={{ width: w, height: h, display: "flex", alignItems: "center", justifyContent: "center", background: C.paperDeep, fontFamily: FONT.sans, fontSize: SIZE.label, color: C.inkSoft }}>image missing</div>
        )}
      </div>
      {m.text && (
        <div style={{ padding: "0 16px 6px", maxWidth: w }}>
          {m.text}
        </div>
      )}
    </div>
  );
}

function Transcript({ t, f, at, max }: { t: NonNullable<ChatMessage["transcript"]>; f: number; at: number; max: number }) {
  const o = ramp(f, at, at + 10, OUT);
  return (
    <div style={{ marginTop: 14, maxWidth: max + 40, opacity: o, paddingLeft: 10, borderLeft: `5px solid ${C.rose}`, boxSizing: "border-box" }}>
      {t.original && (
        <div style={{ fontFamily: FONT.sans, fontWeight: W.regular, fontSize: SIZE.chatSmall, lineHeight: 1.25, color: C.inkSoft, padding: "2px 0 10px 16px" }}>{t.original}</div>
      )}
      <div style={{ fontFamily: FONT.sans, fontWeight: W.bold, fontSize: SIZE.chat, lineHeight: LH.chat, color: C.ink, padding: "0 0 4px 16px" }}>{t.english}</div>
    </div>
  );
}
