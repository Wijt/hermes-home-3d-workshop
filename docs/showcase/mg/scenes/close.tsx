// close (300 frames): the end card. The tagline is the picture; under it how to install the plugin and where it
// lives; on the right the finished tag on a small plate, turning for the whole scene. Starts on empty ink and holds.
import { AbsoluteFill, useCurrentFrame } from "raea";
import { Chip, Iso, Line, OUT, P, Stage, Words, plateSlabs, ramp, tagSlabs, type View } from "../kit";

export const DURATION = 300;

const LEFT = 150;
const TOP = 196;
const SIZE = 190;

const T_PLATE = 0;
const T_WORDS = 6;
const T_CHIP = 50;
const T_LINE = 70;
const T_URL = 78;

// the small plate: 70 mm of sheet, just bigger than the tag, so the whole of it turns inside the frame
const PLATE = { size: 280, grid: 56, cx: 1560, cy: 374, scale: 1.42, yaw0: -0.9, turn: 0.004 };

export default function Close() {
  const f = useCurrentFrame();

  // the plate comes up into its place while it is already turning
  const up = ramp(f, T_PLATE, T_PLATE + 26, OUT);
  const view: View = { cx: PLATE.cx, cy: PLATE.cy + (1 - up) * 70, scale: PLATE.scale * (0.9 + 0.1 * up), yaw: PLATE.yaw0 + PLATE.turn * f, pitch: 0.56 };
  const slabs = [...plateSlabs({ size: PLATE.size, grid: PLATE.grid, shadow: { x: 6, y: 9, w: 244, h: 110 } }), ...tagSlabs({ printed: 1 })];

  return (
    <Stage frames={DURATION}>
      <AbsoluteFill style={{ opacity: ramp(f, T_PLATE, T_PLATE + 14, (t) => t), transform: "translateY(0px)" }}>
        <Iso view={view} slabs={slabs} />
      </AbsoluteFill>
      <div style={{ position: "absolute", left: LEFT, top: TOP, display: "flex", flexDirection: "column", alignItems: "flex-start" }}>
        <Words text="Ask. It's in" at={T_WORDS} each={3} size={SIZE} />
        <Words text="the box." at={T_WORDS + 9} each={3} size={SIZE} />
        <Chip at={T_CHIP} mono size={40} style={{ marginTop: 74 }}>
          hermes plugins install Wijt/hermes-home-3d-workshop
        </Chip>
        <Line at={T_LINE} size={60} weight={500} color={P.bone} style={{ marginTop: 40, marginLeft: 4, whiteSpace: "nowrap" }}>
          home-3d-workshop, a plugin for Hermes Agent
        </Line>
        <Line at={T_URL} size={46} weight={500} color={P.mist} style={{ marginTop: 8, marginLeft: 4, whiteSpace: "nowrap" }}>
          github.com/Wijt/hermes-home-3d-workshop
        </Line>
      </div>
    </Stage>
  );
}
