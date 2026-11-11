// title (135 frames): the idea. Starts on the red that "ask" ended on; ends on the studio's ink, lit the way an
// empty Stage is, so the cut into "make" cannot be seen.
import { AbsoluteFill, useCurrentFrame } from "raea";
import { IN, INOUT, Line, P, Stage, Wipe, Words, pop, ramp } from "../kit";

export const DURATION = 135;

const SIZE = 186;
const LEFT = 200;
const TOP = 300;

const T_WORDS = 4;
const T_BUBBLE = 18;
const T_LINE = 48;
const T_WIPE = 120;
const WIPE_FRAMES = DURATION - 1 - T_WIPE;
const WIPE_X = 960;
const WIPE_Y = 1080;

/** The studio's own light, shown only inside the ink wipe's circle, so the last frame is an empty lit Stage. */
function LitWipe({ at, frames, x, y }: { at: number; frames: number; x: number; y: number }) {
  const f = useCurrentFrame();
  const t = ramp(f, at, at + frames, INOUT);
  if (t <= 0) return null;
  // the same circle the kit's Wipe draws
  const far = Math.hypot(Math.max(x, 1920 - x), Math.max(y, 1080 - y)) + 40;
  const r = far * t;
  return (
    <div style={{ position: "absolute", left: x - r, top: y - r, width: 2 * r, height: 2 * r, borderRadius: r, overflow: "hidden" }}>
      <div style={{ position: "absolute", left: r - x, top: r - y, width: 1920, height: 1080 }}>
        <Stage drift={0} />
      </div>
    </div>
  );
}

export default function Title() {
  const f = useCurrentFrame();

  // "group chat." is said inside a chat bubble: it pops from its tail corner just before the two words rise in it
  const k = pop(f, T_BUBBLE, 14);
  const padX = 58;

  // the words are lifted a little by the ink that rises under them
  const lift = ramp(f, T_WIPE - 2, DURATION - 1, IN) * -70;

  return (
    <AbsoluteFill>
      <Stage bg={P.red} frames={DURATION} drift={0.04}>
        <AbsoluteFill style={{ transform: `translateY(${lift}px)`, opacity: 1 }}>
          <div style={{ position: "absolute", left: LEFT, top: TOP, display: "flex", flexDirection: "column", alignItems: "flex-start" }}>
            <Words text="A 3D printer" at={T_WORDS} each={3} size={SIZE} />
            <div style={{ display: "flex", flexDirection: "row", alignItems: "flex-start", marginTop: 30 }}>
              <Words text="in the" at={T_WORDS + 9} each={3} size={SIZE} />
              <div style={{ position: "relative", display: "flex", flexDirection: "row", marginLeft: 40 + padX }}>
                <div
                  style={{
                    position: "absolute", left: -padX, right: -padX, top: -22, bottom: -40, background: P.redDeep, borderRadius: "96px 96px 96px 22px",
                    transform: `scale(${Math.max(0.001, k)})`, transformOrigin: "0% 100%", opacity: k > 0 ? 1 : 0,
                  }}
                />
                <Words text="group chat." at={T_BUBBLE + 3} each={3} size={SIZE} />
              </div>
            </div>
            <Line at={T_LINE} size={60} weight={500} color={P.bone} style={{ marginTop: 84, marginLeft: 6 }}>
              Anyone in the chat can ask. Nobody opens a slicer.
            </Line>
          </div>
        </AbsoluteFill>
      </Stage>
      <Wipe at={T_WIPE} frames={WIPE_FRAMES} x={WIPE_X} y={WIPE_Y} color={P.ink} />
      <LitWipe at={T_WIPE} frames={WIPE_FRAMES} x={WIPE_X} y={WIPE_Y} />
    </AbsoluteFill>
  );
}
