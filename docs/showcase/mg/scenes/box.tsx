// box (285 frames): it is in the box. It starts on the picture "print" ended on (the finished tag, close). The
// view eases out and over to the plate's right edge and the done box beside it; the print head comes down behind
// the tag and pushes it off the edge; it drops into the box. Mıstık says so in the chat, and the tagline lands.
import { useCurrentFrame } from "raea";
import { Bubble, IN, INOUT, Iso, Label, Nozzle, OUT, P, Stage, Words, boxSlabs, plateSlabs, ramp, tagSlabs, type Slab, type View } from "../kit";
import { END_VIEW, TAG_SHADOW, TURN } from "./print";

export const DURATION = 285;
const LAST = DURATION - 1;

// --- times -----------------------------------------------------------------------------------------------------
const T_HEAD = 40; // the print head starts down
const T_TOUCH = 54; // it is behind the tag
const T_PUSH = 58; // the tag starts to move
const SPEED = 24; // plate units a frame once it is moving
const ACCEL = 14; // frames to reach that speed
const X_EDGE = 600; // the tag's centre when it lets go of the plate (the sheet ends at 512)
const T_FALL = T_PUSH + ACCEL + (X_EDGE - 0.5 * SPEED * ACCEL) / SPEED; // 90
const FALL = 9;
const T_LAND = T_FALL + FALL; // 99
const T_BACK = 104; // the view pulls back to the whole plate and the box
const T_BUBBLE = 118;
const T_TAGLINE = 170;
const T_BUBBLE_OUT = 228;

// --- the box: just past the plate's right edge (the bed ends at 534), its floor below the plate, its rim near it
const BOX = { x: 747, y: 40, z: -110, w: 400, d: 300, h: 120 };
const REST = { x: 760, z: BOX.z + 2, rot: 5 }; // where the tag lies in it

/** The tag: pushed along x, then a fall with a little turn, then one small settle. */
function tagAt(f: number) {
  const t = f - T_PUSH;
  let x = t <= 0 ? 0 : t <= ACCEL ? (0.5 * SPEED * t * t) / ACCEL : 0.5 * SPEED * ACCEL + SPEED * (t - ACCEL);
  let z = 0;
  let rot = 0;
  const u = f - T_FALL;
  if (u > 0) {
    const fu = Math.min(u, FALL);
    const xLand = X_EDGE + SPEED * FALL - 0.9 * FALL * FALL;
    x = X_EDGE + SPEED * fu - 0.9 * fu * fu;
    z = REST.z * (fu / FALL) ** 2;
    rot = 7 * (fu / FALL);
    if (u > FALL) {
      const v = Math.min(1, (u - FALL) / 9);
      x = xLand + (REST.x - xLand) * ramp(u, FALL, FALL + 9, OUT);
      z = REST.z + 8 * Math.sin(Math.PI * v) * (1 - v);
      rot = 7 + (REST.rot - 7) * ramp(u, FALL, FALL + 12, OUT);
    }
  }
  return { x, z, rot };
}

/** The print head's tip: down behind the tag's left end, with it to the edge, then up and away. */
function headAt(f: number, tagX: number): { at: [number, number, number]; o: number } {
  const X_STOP = 430; // it lets the tag go here and stops before the edge
  const tStop = T_PUSH + ACCEL + (X_STOP + 122 - 0.5 * SPEED * ACCEL) / SPEED; // 88
  const x = f <= tStop ? tagX - 122 : X_STOP + 44 * ramp(f, tStop, tStop + 6, OUT);
  const down = ramp(f, T_HEAD, T_TOUCH, OUT);
  const up = ramp(f, tStop + 5, tStop + 21, IN);
  const z = 6 + 230 * (1 - down) + 240 * up;
  const o = Math.min(ramp(f, T_HEAD, T_HEAD + 7, (t) => t), 1 - ramp(f, tStop + 13, tStop + 21, (t) => t));
  return { at: [x, 0, z], o };
}

// --- the view --------------------------------------------------------------------------------------------------
// 1: the action (the tag, the edge, the box). 2: the whole plate and the box, on the right, for the words.
const ACTION = { cx: 410, cy: 730, scale: 1.45, follow: -110 };
const SLOW = 0.0008; // the turn's speed (radians a frame) once it has slowed
const WHOLE = { cx: 935, cy: 836, scale: 0.9, rise: -24 };

function viewAt(f: number): View {
  if (f <= 0) return END_VIEW;
  // the turn goes on from "print" at the same speed and slows; it never stops
  const yaw = END_VIEW.yaw + SLOW * f + ((TURN - SLOW) * 60 * (1 - (1 - Math.min(1, f / 60)) ** 2)) / 2;
  const a = ramp(f, 0, 50, INOUT); // out and over
  const b = ramp(f, 46, T_LAND + 2, INOUT); // with the push
  const c = ramp(f, T_BACK, 152, INOUT); // back to the whole
  const d = ramp(f, T_BUBBLE_OUT - 6, T_BUBBLE_OUT + 28, INOUT); // up a little once the bubble has gone
  const creep = ramp(f, 150, LAST, (t) => t);
  const actionX = ACTION.cx + ACTION.follow * b;
  return {
    cx: END_VIEW.cx + (actionX - END_VIEW.cx) * a + (WHOLE.cx - actionX) * c,
    cy: END_VIEW.cy + (ACTION.cy - END_VIEW.cy) * a + (WHOLE.cy - ACTION.cy) * c + WHOLE.rise * d,
    scale: END_VIEW.scale * (ACTION.scale / END_VIEW.scale) ** a * (WHOLE.scale / ACTION.scale) ** c * (1 + 0.045 * creep),
    yaw,
    pitch: END_VIEW.pitch,
  };
}

/** The tag's slabs turned a little about the tag's own centre (the kit's tag only slides). */
function turned(slabs: Slab[], x: number, rot: number): Slab[] {
  return slabs.map((sl) => ({ ...sl, el: <div style={{ position: "absolute", left: x, top: 0, width: 0, height: 0, transform: `rotate(${rot}deg)` }}>{sl.el}</div> }));
}

const SIZE = 190;

export default function Box() {
  const f = useCurrentFrame();
  const view = viewAt(f);
  const tag = tagAt(f);
  const head = headAt(f, tag.x);

  // the tag's shadow stays on the sheet: it is cut at the sheet's edge and goes when the tag drops
  const left = tag.x + TAG_SHADOW.x - TAG_SHADOW.w / 2;
  const right = Math.min(tag.x + TAG_SHADOW.x + TAG_SHADOW.w / 2, 506);
  const shadowO = TAG_SHADOW.o * (1 - ramp(f, T_FALL, T_FALL + 3, (t) => t));
  const shadow = right - left > 4 && shadowO > 0 ? { x: (left + right) / 2, y: TAG_SHADOW.y, w: right - left, h: TAG_SHADOW.h, o: shadowO } : undefined;

  const slabs = [
    ...plateSlabs({ shadow }),
    ...(tag.rot === 0 ? tagSlabs({ printed: 1, x: tag.x, z: tag.z }) : turned(tagSlabs({ printed: 1, z: tag.z }), tag.x, tag.rot)),
    ...boxSlabs(BOX),
  ];

  return (
    <Stage drift={0}>
      <Iso view={view} slabs={slabs}>
        {head.o > 0 && <Nozzle view={view} at={head.at} o={head.o} />}
      </Iso>

      {/* Mıstık tells the chat */}
      <div style={{ position: "absolute", right: 80, top: 128, width: 720 }}>
        <Bubble text="Mum, your key tag is in the box." who="Mıstık" group="Family" color={P.bone} ink={P.ink} side="right" at={T_BUBBLE} out={T_BUBBLE_OUT} size={60} width={720} />
      </div>
      <Label kind="chat" at={T_BUBBLE + 8} out={T_BUBBLE_OUT} style={{ left: "auto", right: 80, bottom: "auto", top: 414 }} />

      {/* the tagline */}
      <div style={{ position: "absolute", left: 120, top: 150, display: "flex", flexDirection: "column", alignItems: "flex-start" }}>
        <div style={{ display: "flex", flexDirection: "row", columnGap: SIZE * 0.24 }}>
          <Words text="Ask." at={T_TAGLINE} size={SIZE} />
          <Words text="It's in" at={T_TAGLINE + 13} each={3} size={SIZE} />
        </div>
        <Words text="the box." at={T_TAGLINE + 19} each={3} size={SIZE} />
      </div>
    </Stage>
  );
}
