// approve (330 frames): a person presses Start. The plugin's real screen (screen/backroom.mp4, the scene's frame
// is the source frame). The camera starts on the whole screen, pushes in on the top card, leans toward the Start
// button for the press at frame 210 and eases up to the framing the next scene starts on.
//
// The camera and the pointer are worked out here, frame by frame, and handed to the kit's Screen as one key each:
// that way a move between two framings can ease while a slow creep never stops under it.
//
// Every framing is chosen so the two things drawn over the screen sit on parts of it that say nothing. The label
// lands on the empty strip to the right of the card's tabs. The ink bar lands on the dark foot of the 3D preview
// (it hides the size chip whole) with the Start button level with it, in the clear to its right. The top edge of
// the frame stays between the page's header and the card, the bottom edge above the first "Up next" row. Together
// those leave a narrow window: the card at 1.485 to 1.57, held left of its middle while the long first bar is up.
// Any closer and the label sits on the job's own lines and the bar on the "Up next" list. The second bar leaves as
// the card turns to "Printing" at 282, because on that card it would sit across the "Up next" heading.
import { AbsoluteFill, useCurrentFrame } from "raea";
import { F, FONTS, IN, INOUT, Label, OUT, P, Screen, T, Words, ramp } from "../kit";

export const DURATION = 330;
const LAST = DURATION - 1;

// What the capture does (source frames): the button reads "Sending..." from 210, the card turns to "Printing" at 282.
const T_PRESS = 210;
const T_FLIP = 282;

// ---------------------------------------------------------------------------------------------------------------
// Camera: four shots, each one a slow creep of its own; between two shots the picture is an eased mix of both, so
// the creep carries through the move and the camera is never at rest.
// ---------------------------------------------------------------------------------------------------------------
type Cam = { x: number; y: number; scale: number };

/** The framing the next scene (print) starts on. The last frame is exactly this. */
const END: Cam = { x: 1090, y: 420, scale: 1.5 };

const T_IN = 48; // on the card (the size chip is under the bar by the time the bar has risen)
const T_GO = 150; // leans toward the button
const T_NEAR = 190; // there
const T_BACK = 270; // starts up to END (the old card's foot stays under the bar until that card is gone at 282)
const T_SETTLE = 302; // on END's framing, the last of the move dying away

/** A framing from the capture x at the frame's middle, the capture y at the frame's top edge, and the scale. */
const framed = (x: number, top: number, scale: number): Cam => ({ x, y: top + 540 / scale, scale });

/** 0: the whole screen, already leaning in. */
const wide = (f: number): Cam => ({ x: 960, y: 540, scale: 1 + 0.0009 * f });
/** 1: the top card. Left of the card's middle, so the Start button is clear of the first, long bar. */
const card = (f: number): Cam => framed(1041 + 0.0637 * (f - T_IN), 110 + 0.0706 * (f - T_IN), 1.485 + 0.000196 * (f - T_IN));
/** 2: nearer the Start button, the frame's top edge held where it is; a small push on the press itself. */
const near = (f: number): Cam => framed(1072, 122, 1.535 + 0.00018 * (f - T_NEAR) + 0.016 * ramp(f, T_PRESS, T_PRESS + 12, OUT));
/** 3: up on the card, settling onto END: the move dies away exactly on the last frame. */
const back = (f: number): Cam => {
  const q = Math.pow(Math.max(0, (LAST - f) / (LAST - T_SETTLE)), 2);
  return { x: END.x, y: END.y + 5 * q, scale: END.scale + 0.018 * q };
};

const mix = (a: Cam, b: Cam, w: number): Cam => ({ x: a.x + (b.x - a.x) * w, y: a.y + (b.y - a.y) * w, scale: a.scale + (b.scale - a.scale) * w });

function camera(f: number): Cam {
  if (f < T_IN) return mix(wide(f), card(f), ramp(f, 0, T_IN, INOUT));
  if (f < T_GO) return card(f);
  if (f < T_NEAR) return mix(card(f), near(f), ramp(f, T_GO, T_NEAR, INOUT));
  if (f < T_BACK) return near(f);
  if (f < T_SETTLE) return mix(near(f), back(f), ramp(f, T_BACK, T_SETTLE, INOUT));
  return back(f);
}

// ---------------------------------------------------------------------------------------------------------------
// Pointer: in from the right, a look at the part, down to Start, the press, and out to the right again.
// Points are capture pixels.
// ---------------------------------------------------------------------------------------------------------------
type Pt = [number, number];
const soft = (t: number) => 0.5 - 0.5 * Math.cos(Math.PI * Math.min(1, Math.max(0, t)));

/** from -> to between frames a and b on a slightly bowed path (`bow` px to the right of the direction of travel) */
function glide(f: number, a: number, b: number, from: Pt, to: Pt, bow = 0): Pt {
  const e = soft((f - a) / (b - a));
  const dx = to[0] - from[0];
  const dy = to[1] - from[1];
  const len = Math.hypot(dx, dy) || 1;
  const k = Math.sin(Math.PI * e) * bow;
  return [from[0] + dx * e - (dy / len) * k, from[1] + dy * e + (dx / len) * k];
}

const PTR_IN = 96;
const PTR_LOOK = 134; // arrives by the preview
const PTR_GO = 172; // leaves for the button
const PTR_ON = 202; // on the button
const PTR_LEAVE = 228;
const PTR_OUT = 262;

const P_OFF_RIGHT: Pt = [1790, 436];
const P_LOOK: Pt = [1010, 570]; // just off the tag's lower right corner, on the plate
const P_LOOK_END: Pt = [1001, 579]; // the hand is never quite still
const P_START: Pt = [1208, 719]; // on the Start button, the tip just under its words
const P_AWAY: Pt = [1840, 650];

function pointer(f: number): Pt {
  if (f < PTR_LOOK) return glide(f, PTR_IN, PTR_LOOK, P_OFF_RIGHT, P_LOOK, -26);
  if (f < PTR_GO) return glide(f, PTR_LOOK, PTR_GO, P_LOOK, P_LOOK_END);
  if (f < PTR_LEAVE) return glide(f, PTR_GO, PTR_ON, P_LOOK_END, P_START, 14);
  return glide(f, PTR_LEAVE, PTR_OUT, P_START, P_AWAY, -22);
}

// ---------------------------------------------------------------------------------------------------------------
// The ink bar: the words over the screen. The box rises, then its words come up inside it.
// ---------------------------------------------------------------------------------------------------------------
function Bar({ text, at, out }: { text: string; at: number; out: number }) {
  const f = useCurrentFrame();
  const up = ramp(f, at, at + 10);
  const gone = ramp(f, out - 8, out, IN);
  const o = Math.min(ramp(f, at, at + 6, (t) => t), 1 - gone);
  return (
    <div style={{ position: "absolute", left: 80, bottom: 120, display: "flex", flexDirection: "row", opacity: o, transform: `translateY(${(1 - up) * 34 + gone * 18}px)` }}>
      <div style={{ display: "flex", flexDirection: "row", alignItems: "center", boxSizing: "border-box", height: 108, padding: "0 34px", borderRadius: 28, background: P.ink }}>
        <Words text={text} at={at + 3} each={2} size={T.read} weight={600} font={F.text} color={P.bone} lineHeight={1.12} />
      </div>
    </div>
  );
}

export default function Approve() {
  const f = useCurrentFrame();
  const c = camera(f);
  const [px, py] = pointer(f);
  return (
    <AbsoluteFill style={{ background: "#F4F5F7", overflow: "hidden" }}>
      <style>{FONTS}</style>
      <Screen file="screen/backroom.mp4" cam={[{ at: 0, x: c.x, y: c.y, scale: c.scale }]} ptr={[{ at: PTR_IN, x: px, y: py }]} ptrOut={PTR_OUT} clicks={[T_PRESS]} />
      {/* when the card turns to "Printing" its Pause and Stop sit where the label was: the label steps down onto the banner's empty end */}
      <Label kind="screen" at={8} tone="dark" style={{ left: "auto", right: 64, bottom: "auto", top: 124 + 62 * ramp(f, 272, 294, INOUT) }} />
      <Bar text="It is all in Hermes Desktop." at={24} out={150} />
      <Bar text="Start from the chat, or here." at={160} out={T_FLIP + 8} />
    </AbsoluteFill>
  );
}
