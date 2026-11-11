// ask (195 frames): one message. Mum's red bubble is the picture; Mıstık answers from the right; then Mum's red
// grows from her bubble until it is the whole frame, which is the ground the title starts on.
import { AbsoluteFill, interpolate, useCurrentFrame } from "raea";
import { Bubble, IN, INOUT, Label, OUT, P, Stage, Wipe, clamp, ramp } from "../kit";

export const DURATION = 195;

const MUM = "Mıstık, can you make me a key tag with MUM on it? Red please.";
const REPLY = "On it. I'll find a few and show you.";

// Where things rest once the reply is in (frame px, camera at rest).
const MUM_AT = { left: 150, top: 150, width: 1150, size: 84 };
const REPLY_AT = { left: 890, top: 648, width: 880, size: 64 };
// The middle of Mum's bubble (the red box itself, not her name row): the wipe grows from here.
const MUM_MID = { x: 725, y: 398 };

const T_MUM = 8;
const T_PULL = 78; // the camera starts to open up for the reply
const PULL_FRAMES = 30;
const T_REPLY = 94;
const T_PUSH = 164; // the camera starts to fall into Mum's bubble
const T_WIPE = 178;
const LAST = DURATION - 1;

export default function Ask() {
  const f = useCurrentFrame();

  // One camera for the whole scene, as a scale k and a shift (tx, ty) of the chat.
  // 1. It opens close on Mum's message (the message is the picture) and creeps in while she types.
  const creep = interpolate(f, [0, T_PULL + 10], [0, 1], clamp);
  const closeK = 1.15 + 0.035 * creep;
  const closeX = 900 - closeK * MUM_MID.x;
  const closeY = 520 - closeK * (MUM_MID.y - 20);
  // 2. It pulls back and up to the left, so the reply has room to arrive from the right.
  const pull = ramp(f, T_PULL, T_PULL + PULL_FRAMES, INOUT);
  let k = closeK + (1 - closeK) * pull;
  let tx = closeX * (1 - pull);
  let ty = closeY * (1 - pull);
  // 3. It never stops: a slow push on the frame's middle while the two messages are read.
  const drift = 1 + 0.03 * interpolate(f, [T_PULL + PULL_FRAMES - 8, LAST], [0, 1], clamp);
  k *= drift;
  tx = 960 + (tx - 960) * drift;
  ty = 540 + (ty - 540) * drift;
  // 4. At the end it falls into Mum's bubble, and her red grows from the bubble's middle to fill the frame.
  const midX = tx + k * MUM_MID.x;
  const midY = ty + k * MUM_MID.y;
  const push = 1 + 0.5 * ramp(f, T_PUSH, LAST, IN);
  k *= push;
  tx = midX + (tx - midX) * push;
  ty = midY + (ty - midY) * push;

  // the reply slides in from the right while it pops
  const slide = (1 - ramp(f, T_REPLY, T_REPLY + 16, OUT)) * 120;

  return (
    <Stage drift={0}>
      <AbsoluteFill style={{ transformOrigin: "0 0", transform: `translate(${tx}px, ${ty}px) scale(${k})`, opacity: 1 }}>
        <div style={{ position: "absolute", left: MUM_AT.left, top: MUM_AT.top, width: MUM_AT.width }}>
          <Bubble text={MUM} who="Mum" group="Family" at={T_MUM} size={MUM_AT.size} width={MUM_AT.width} cps={30} />
        </div>
        <div style={{ position: "absolute", left: REPLY_AT.left, top: REPLY_AT.top, width: REPLY_AT.width, transform: `translateX(${slide}px)`, opacity: 1 }}>
          <Bubble text={REPLY} who="Mıstık" color={P.bone} ink={P.ink} side="right" at={T_REPLY} size={REPLY_AT.size} width={REPLY_AT.width} />
        </div>
      </AbsoluteFill>
      <Label kind="chat" at={30} />
      <Wipe at={T_WIPE} frames={LAST - T_WIPE} x={midX} y={midY} color={P.red} />
    </Stage>
  );
}
