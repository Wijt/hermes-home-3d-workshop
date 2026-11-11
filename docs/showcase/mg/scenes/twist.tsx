// twist (370 frames): it printed its own upgrade. Four pictures, cut on motion: a real photo from six weeks of
// printing, the plugin's real screen (the same hand-off three times, then the upgrade it proposed), a real photo of
// that upgrade printed, and real footage of the printer pushing parts off its plate into the box, with the owner's
// one line.
import type { ReactNode } from "react";
import { AbsoluteFill, Sequence, Video, interpolate, staticFile, useCurrentFrame } from "raea";
import { Bubble, F, FONTS, INOUT, Label, OUT, P, Photo, Screen, Words, clamp, ramp } from "../kit";

export const DURATION = 370;

// the four parts (scene frames); inside each part frames are local
const T_WEEKS = 0;
const T_SCREEN = 80;
const T_PARTS = 170;
const T_EMPTY = 250;

const TOP_RIGHT = { left: "auto", right: 64, bottom: "auto", top: 124 } as const;
const TOP_LEFT = { bottom: "auto", top: 124 } as const;

/** A scrim over a photo: ink at one edge fading to nothing, so words keep 3:1 where the photo is bright. */
function Shade({ deg, a, reach }: { deg: number; a: number; reach: number }) {
  return <AbsoluteFill style={{ backgroundImage: `linear-gradient(${deg}deg, rgba(18,19,22,${a}) 0%, rgba(18,19,22,0) ${reach}%)` }} />;
}

/** A colour between two "#RRGGBB" colours (t = 0: a, t = 1: b). */
function mix(a: string, b: string, t: number): string {
  const ch = (c: string, i: number) => parseInt(c.slice(1 + 2 * i, 3 + 2 * i), 16);
  const v = [0, 1, 2].map((i) => Math.round(ch(a, i) + (ch(b, i) - ch(a, i)) * t));
  return `rgb(${v[0]}, ${v[1]}, ${v[2]})`;
}

// ---------------------------------------------------------------------------------------------------------------
// 1. Six weeks on a real printer at home. The words sit on the wall; the rose and the box keep the plate.
// ---------------------------------------------------------------------------------------------------------------
function Weeks() {
  return (
    <AbsoluteFill>
      <Photo file="real/rose-box-on-bed.jpg" focus={[0.56, 1]} from={1.04} to={1.12} frames={80} dim={0.34} />
      <Shade deg={180} a={0.58} reach={64} />
      <div style={{ position: "absolute", left: 150, top: 146, display: "flex", flexDirection: "column", alignItems: "flex-start" }}>
        <Words text="Six weeks" at={3} each={3} size={176} />
        <Words text="on a real printer" at={10} each={2} size={88} style={{ marginTop: 18 }} />
        <Words text="at home." at={17} each={2} size={88} />
      </div>
      <Label kind="photo" style={TOP_RIGHT} />
    </AbsoluteFill>
  );
}

// ---------------------------------------------------------------------------------------------------------------
// 2. The plugin's real screen: the three rows that needed a person, then the upgrade it proposed
// ---------------------------------------------------------------------------------------------------------------
const ROWS = [338, 432, 525]; // capture y of the three "Take a finished part off the plate" rows
const T_ROWS = 6; // the first row's marker; the next two follow 5 frames apart
const T_MOVE = 30; // the camera leaves the rows
const T_ARRIVE = 54; // and is on the proposal
const T_SECOND = 44; // the bar's second line opens (5 words, 1.5 s to the cut)
const T_PROPOSAL = 50; // the proposal's marker
const LINE = 68; // the bar's line height
const BAR_BOTTOM = 116; // the bar's box ends 4 px under the safe line; its words stay inside it

function Asked() {
  const f = useCurrentFrame();
  // The camera: a slow creep the whole time, and one eased move from the rows down and in to the proposal.
  // Both resting places are measured, not guessed. On the rows the bar sits in the gap under the third row and
  // hides the next heading whole (the creep is a push on the bar's own middle, so that holds). On the proposal the
  // right-hand column is just out of frame, the label sits in the gap between two rows (clear of their small
  // print), the proposal's last line clears the bar, and the bar hides the heading under it whole.
  const go = ramp(f, T_MOVE, T_ARRIVE, INOUT);
  const pre = Math.min(1, f / T_MOVE);
  const post = Math.max(0, (f - T_ARRIVE) / (T_PARTS - T_SCREEN - T_ARRIVE));
  const sc = 1.5 + 0.02 * pre + 0.365 * go + 0.015 * post;
  const cx = 850 - 33 * go;
  const cy = 372 + 3.2 * pre + 316.5 * go + 0.2 * post;
  // where a capture pixel lands in the frame (the rule the kit's Screen uses)
  const tx = Math.min(0, Math.max(1920 - 1920 * sc, 960 - cx * sc));
  const ty = Math.min(0, Math.max(1080 - 1080 * sc, 540 - cy * sc));
  // a red marker in the margin beside a row: it is ours, not the screen's
  const mark = (key: string, y0: number, y1: number, at: number) => {
    const t = ramp(f, at, at + 9, OUT);
    const w = 8 * sc;
    return (
      <div
        key={key}
        style={{
          position: "absolute", left: tx + 414 * sc, top: ty + y0 * sc, width: w, height: (y1 - y0) * sc, borderRadius: w / 2, background: P.red,
          transform: `scaleY(${Math.max(0.001, t)})`, transformOrigin: "50% 0%", opacity: t > 0 ? 1 : 0,
        }}
      />
    );
  };
  // the bar: one line, then a second line opens under it and the first goes quiet
  const inn = ramp(f, 1, 9, OUT);
  const open = ramp(f, T_SECOND, T_SECOND + 9, OUT);
  return (
    <AbsoluteFill>
      <Screen file="screen/twist.png" cam={[{ at: 0, x: cx, y: cy, scale: sc }]} />
      {ROWS.map((y, i) => mark(`row${i}`, y - 19, y + 50, T_ROWS + i * 5))}
      {mark("proposal", 660, 810, T_PROPOSAL)}
      <div style={{ position: "absolute", left: 80, bottom: BAR_BOTTOM, display: "flex", flexDirection: "row", opacity: inn, transform: `translateY(${(1 - inn) * 30}px)` }}>
        <div style={{ boxSizing: "border-box", padding: "16px 40px 20px", borderRadius: 24, background: P.ink, fontFamily: F.text, fontWeight: 600, fontSize: 60, lineHeight: `${LINE}px`, letterSpacing: -0.5, whiteSpace: "nowrap" }}>
          <div style={{ height: LINE, color: mix(P.bone, P.mist, open) }}>It kept needing a person to clear the plate.</div>
          <div style={{ height: LINE * open, overflow: "hidden", opacity: open }}>
            <div style={{ height: LINE, color: P.bone, transform: `translateY(${(1 - open) * 20}px)` }}>So it proposed an upgrade.</div>
          </div>
        </div>
      </div>
      <Label kind="screen" style={TOP_RIGHT} />
    </AbsoluteFill>
  );
}

// ---------------------------------------------------------------------------------------------------------------
// 3. A tilted base. The printer printed it. The words fill the corner of the plate under the two parts.
// ---------------------------------------------------------------------------------------------------------------
function Printed() {
  return (
    <AbsoluteFill>
      <Photo file="real/tilted-base-parts-on-bed.jpg" focus={[0, 1]} from={1.12} to={1.22} frames={80} dim={0.22} />
      <div style={{ position: "absolute", right: 224, bottom: 120, display: "flex", flexDirection: "column", alignItems: "flex-end" }}>
        <Words text="A tilted base." at={4} each={3} size={150} align="right" />
        <Words text="The printer printed it." at={16} each={2} size={88} align="right" style={{ marginTop: 14 }} />
      </div>
      <Label kind="photo" style={TOP_LEFT} />
    </AbsoluteFill>
  );
}

// ---------------------------------------------------------------------------------------------------------------
// 4. "it fell in by itself": real footage of the printer at home, as two upright panels (the phone's own shape).
//    First the head pushing the cooled parts forward on the tilted plate; then, beside it, the box under the shelf
//    with the parts in it and the printer's own name plate. The owner's line is the picture's title.
// ---------------------------------------------------------------------------------------------------------------
const T_BUBBLE = 12; // the footage is seen first, then the owner's line lands beside it
const T_PANEL2 = 58; // the second panel arrives
const PANEL = { top: 150, width: 408, height: 734, gap: 26, left: 1034 }; // 480 x 864 footage, shown a little smaller

function Clip({ file, startFrom, frames, zoom, origin }: { file: string; startFrom: number; frames: number; zoom: [number, number]; origin: string }) {
  const f = useCurrentFrame();
  // a slow push-in inside the panel, so nothing in the beat is still
  const k = interpolate(f, [0, frames], zoom, clamp);
  return <Video src={staticFile(file)} muted startFrom={startFrom} style={{ position: "absolute", left: 0, top: 0, width: PANEL.width, height: PANEL.height, objectFit: "cover", transform: `scale(${k})`, transformOrigin: origin }} />;
}

function Panel({ i, at, children }: { i: 0 | 1; at: number; children: ReactNode }) {
  const f = useCurrentFrame();
  const inn = ramp(f, at, at + 14, OUT);
  return (
    <div style={{ position: "absolute", left: PANEL.left + i * (PANEL.width + PANEL.gap), top: PANEL.top + (1 - inn) * 46, width: PANEL.width, height: PANEL.height, borderRadius: 26, overflow: "hidden", background: "#000", opacity: inn }}>
      {children}
    </div>
  );
}

function Fell() {
  const beat = DURATION - T_EMPTY;
  return (
    <AbsoluteFill style={{ background: P.ink }}>
      <Panel i={0} at={0}>
        {/* closer on the bed: the parts are small */}
        <Clip file="footage/real-push.mp4" startFrom={46} frames={beat} zoom={[1.5, 1.66]} origin="40% 36%" />
      </Panel>
      <Panel i={1} at={T_PANEL2}>
        <Sequence from={T_PANEL2} layout="none">
          <Clip file="footage/real-sign.mp4" startFrom={4} frames={beat - T_PANEL2} zoom={[1.02, 1.1]} origin="55% 45%" />
        </Sequence>
      </Panel>
      <div style={{ position: "absolute", left: 150, top: 318 }}>
        <Bubble text="it fell in by itself" who="The owner" color={P.blue} at={T_BUBBLE} size={92} width={840} />
      </div>
      <div style={{ position: "absolute", left: 150, top: 606, width: 840 }}>
        <Words text="Now it clears its own plate." at={T_PANEL2 + 8} each={3} size={88} />
      </div>
      <Label kind="footage" style={TOP_LEFT} />
    </AbsoluteFill>
  );
}

export default function Twist() {
  return (
    <AbsoluteFill style={{ background: P.ink }}>
      <style>{FONTS}</style>
      <Sequence from={T_WEEKS} durationInFrames={T_SCREEN - T_WEEKS}>
        <Weeks />
      </Sequence>
      <Sequence from={T_SCREEN} durationInFrames={T_PARTS - T_SCREEN}>
        <Asked />
      </Sequence>
      <Sequence from={T_PARTS} durationInFrames={T_EMPTY - T_PARTS}>
        <Printed />
      </Sequence>
      <Sequence from={T_EMPTY} durationInFrames={DURATION - T_EMPTY}>
        <Fell />
      </Sequence>
    </AbsoluteFill>
  );
}
