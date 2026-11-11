// groups (270 frames): one printer, every group. First two requests from two group chats, each in its group's
// colour, and the sentence they add up to; then what the plugin is, as four numbers. Starts and ends on empty ink.
import { AbsoluteFill, useCurrentFrame } from "raea";
import { Bubble, Count, F, IN, INOUT, Label, OUT, P, Stage, T, Words, pop, ramp } from "../kit";

export const DURATION = 270;

// ---- first half: the two chats (frame px, once the chats have made room for the words) ----
const FAM = { text: "A key tag, red please.", left: 150, top: 134, width: 1000, size: 72 };
const LAB = { text: "A cable clip for the garage?", left: 570, top: 336, width: 1200, size: 72 };
// the middle of the two bubbles together, at rest, and where that middle sits while they are the whole picture
const PAIR = { x: 960, y: 342 };
const OPEN = { y: 512, k: 1.06 };

const T_FAM = 3;
const T_LAB = 30;
const T_PULL = 38; // the chats move up and make room
const PULL_FRAMES = 22;
const T_WORDS = 44;
const OUT_FAM = 121;
const OUT_LAB = 123;
const OUT_WORDS = 124;
const OUT_ALL = 125; // the first half is gone, the frame is empty ink

// ---- second half: four numbers, stepping down across the frame to the 0 ----
const NUMS = [
  { to: 14, label: "tools", count: 20 },
  { to: 4, label: "hooks", count: 16 },
  { to: 1, label: "screen in Hermes Desktop", count: 12 },
  { to: 0, label: "slicers opened", count: 0 },
];
const ROW = { left: 150, top: 168, col: 405, step: 124, rule: 361 };
const T_NUM = 128; // the first number; the next two follow 8 frames apart
const EACH = 8;
const T_ZERO = 160; // the 0 lands last, after the others have stopped counting
const OUT_NUM = 253; // the row starts to leave
const LABEL_SIZE = 42;

function Stat({ i }: { i: number }) {
  const f = useCurrentFrame();
  const n = NUMS[i];
  const zero = n.to === 0;
  const at = zero ? T_ZERO - 8 : T_NUM + i * EACH;
  const rule = ramp(f, at, at + 14, OUT);
  // a counted number comes down from behind its hairline; the 0 lands with the kit's pop
  const drop = ramp(f, at + 2, at + 15, OUT);
  const land = pop(f, T_ZERO, 14);
  const labelAt = (zero ? T_ZERO : at) + 8;
  const label = ramp(f, labelAt, labelAt + 10, OUT);
  const o = OUT_NUM + i * 2;
  const gone = ramp(f, o, o + 9, IN);
  return (
    <div style={{ position: "absolute", left: ROW.left + i * ROW.col, top: ROW.top + i * ROW.step, width: ROW.col, opacity: 1 - gone, transform: `translateY(${26 * gone}px)` }}>
      <div style={{ width: ROW.rule, height: 4, background: P.ink3, transform: `scaleX(${Math.max(0.001, rule)})`, transformOrigin: "0% 50%", opacity: rule > 0 ? 1 : 0 }} />
      <div style={{ boxSizing: "border-box", height: T.huge + 26, paddingTop: 26, overflow: zero ? "visible" : "hidden" }}>
        <div
          style={{
            height: T.huge, fontFamily: F.display, fontWeight: 800, fontSize: T.huge, lineHeight: 1, letterSpacing: -0.018 * T.huge, whiteSpace: "nowrap", color: zero ? P.red : P.bone,
            transform: zero ? `scale(${Math.max(0.001, land)})` : `translateY(${(drop - 1) * (T.huge + 30)}px)`, transformOrigin: "8% 78%", opacity: zero ? (land > 0 ? 1 : 0) : drop > 0 ? 1 : 0,
          }}
        >
          {zero ? "0" : <Count at={at + 2} frames={n.count} to={n.to} />}
        </div>
      </div>
      <div style={{ width: ROW.col - 30, marginTop: 12, fontFamily: F.text, fontWeight: 500, fontSize: LABEL_SIZE, lineHeight: 1.16, color: P.mist, opacity: label, transform: `translateY(${(label - 1) * 16}px)` }}>{n.label}</div>
    </div>
  );
}

export default function Groups() {
  const f = useCurrentFrame();

  // The two chats are the picture first (a little larger, in the middle), then move up to make room for the words.
  const pull = ramp(f, T_PULL, T_PULL + PULL_FRAMES, INOUT);
  const k = OPEN.k + (1 - OPEN.k) * pull;
  const midY = OPEN.y + (PAIR.y - OPEN.y) * pull;
  const tx = PAIR.x - k * PAIR.x;
  const ty = midY - k * PAIR.y;

  // each bubble slides in from its own side while it pops, and leaves to that side
  const famX = -150 * (1 - ramp(f, T_FAM, T_FAM + 16, OUT)) - 180 * ramp(f, OUT_FAM - 9, OUT_FAM, IN);
  const labX = 150 * (1 - ramp(f, T_LAB, T_LAB + 16, OUT)) + 180 * ramp(f, OUT_LAB - 9, OUT_LAB, IN);

  return (
    <Stage frames={DURATION} drift={0.06}>
      {f < OUT_ALL + 1 && (
        <>
          <AbsoluteFill style={{ transformOrigin: "0 0", transform: `translate(${tx}px, ${ty}px) scale(${k})`, opacity: 1 }}>
            <div style={{ position: "absolute", left: FAM.left, top: FAM.top, width: FAM.width, transform: `translateX(${famX}px)`, opacity: 1 }}>
              <Bubble text={FAM.text} who="Mum" group="Family" color={P.red} at={T_FAM} out={OUT_FAM} size={FAM.size} width={FAM.width} />
            </div>
            <div style={{ position: "absolute", left: LAB.left, top: LAB.top, width: LAB.width, transform: `translateX(${labX}px)`, opacity: 1 }}>
              <Bubble text={LAB.text} who="Dad" group="Family" color={P.red} side="right" at={T_LAB} out={OUT_LAB} size={LAB.size} width={LAB.width} />
            </div>
          </AbsoluteFill>
          <div style={{ position: "absolute", left: 150, top: 606, display: "flex", flexDirection: "column", alignItems: "flex-start" }}>
            <Words text="One of the family." at={T_WORDS} each={3} out={OUT_WORDS} size={T.display} />
            <Words text="It knows who asked." at={T_WORDS + 6} each={3} out={OUT_WORDS} size={T.display} />
          </div>
          <Label kind="chat" at={12} out={OUT_FAM} style={{ left: "auto", right: 80, bottom: "auto", top: 130 }} />
        </>
      )}
      {f >= T_NUM - 2 && NUMS.map((_, i) => <Stat key={i} i={i} />)}
    </Stage>
  );
}
