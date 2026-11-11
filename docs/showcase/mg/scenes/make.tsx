// make (225 frames): the agent does the work. Three of the plugin's tools, one at a time on the left; on the right
// the key tag on a tile of the build plate: it rises out of the sheet (design), its 21 layers lift apart (slice),
// and it waits under a blue note (queue). The lifted layers are the scene's one bold moment.
import { AbsoluteFill, useCurrentFrame } from "raea";
import { F, IN, INOUT, Iso, Line, OUT, P, Stage, T, Wipe, keys, plateSlabs, pop, project, ramp, tagSlabs, tween, type View } from "../kit";

export const DURATION = 225;

const STEPS = [
  { at: 6, tool: "home3d_design", lines: ["Designs the part.", "58 × 24 × 4.2 mm"] },
  { at: 78, tool: "home3d_slice", lines: ["21 layers, 13 minutes,", "4 g of PLA"] },
  { at: 153, tool: "home3d_queue", lines: ["Queues it. It cannot", "start a print by itself."] },
] as const;

const COL = { left: 120, top: 388, width: 700 };
const SLOT = 92; // how far an earlier tool's name moves up when the next one arrives
const T_WIPE = 211;
const SCREEN = "#F4F5F7";

/** A tool's name: bone while it is the current step, a quiet chip once the next one has arrived. */
function Tool({ name, at, next, slots }: { name: string; at: number; next?: number; slots: number[] }) {
  const f = useCurrentFrame();
  const inn = ramp(f, at, at + 10, OUT);
  // each later step pushes this one up a slot
  let y = (1 - inn) * 26;
  for (const s0 of slots) y -= SLOT * ramp(f, s0, s0 + 14, INOUT);
  const old = next === undefined ? 0 : ramp(f, next, next + 12, INOUT);
  const box = (bg: string, color: string, o: number) => (
    <div style={{ position: "absolute", left: 0, top: 0, display: "flex", flexDirection: "row", opacity: o }}>
      <div style={{ display: "flex", alignItems: "center", height: 72, padding: "0 26px", borderRadius: 18, background: bg, color, fontFamily: F.mono, fontWeight: 700, fontSize: 38, lineHeight: 1, whiteSpace: "nowrap" }}>{name}</div>
    </div>
  );
  return (
    <div style={{ position: "absolute", left: 0, top: 0, width: COL.width, height: 72, opacity: inn, transform: `translateY(${y}px)` }}>
      {box(P.ink2, P.mist, old)}
      {box(P.bone, P.ink, 1 - old)}
    </div>
  );
}

export default function Make() {
  const f = useCurrentFrame();

  // the tile turns slowly the whole time; the camera moves in for the lifted layers and settles back
  const zoom = keys(f, [[0, 1.86], [70, 1.9], [104, 2.5], [136, 2.56], [160, 2.02], [224, 2.08]]);
  const view: View = { cx: keys(f, [[0, 1420], [70, 1420], [104, 1470], [136, 1470], [160, 1440], [224, 1440]]), cy: keys(f, [[0, 640], [70, 640], [104, 790], [136, 790], [160, 660], [224, 660]]), scale: zoom, yaw: -0.52 + 0.0021 * f, pitch: 0.56 };

  // design: the part rises out of the sheet
  const grown = ramp(f, 18, 46, INOUT);
  // slice: the layers lift apart, breathe, and close
  const spread = 1 + 2.5 * ramp(f, 84, 106, OUT) * (1 - ramp(f, 132, 150, INOUT)) + 0.06 * Math.sin((f - 106) * 0.16) * ramp(f, 106, 112) * (1 - ramp(f, 126, 132));
  const tile = ramp(f, 0, 14, OUT);

  const slabs = [...plateSlabs({ size: 440, grid: 110, shadow: grown > 0.05 ? { x: 10, y: 12, w: 246, h: 110, o: 0.34 * grown } : undefined }), ...(grown > 0 ? tagSlabs({ printed: grown, spread }) : [])];

  // queue: a blue note over the part, on a short stem
  const noteK = pop(f, 165, 13);
  const [nx, ny] = project(view, 0, 0, 44);
  const NOTE_W = 560;
  const stem = 96 * ramp(f, 163, 173, OUT);

  return (
    <Stage frames={DURATION} drift={0.02}>
      <AbsoluteFill style={{ opacity: tile, transform: `translateY(${(1 - tile) * 40}px)` }}>
        <Iso view={view} slabs={slabs} />
      </AbsoluteFill>

      {/* the note */}
      <div style={{ position: "absolute", left: nx - 2, top: ny - stem, width: 4, height: stem, background: P.blue, opacity: stem > 0 ? 1 : 0 }} />
      <div style={{ position: "absolute", left: nx - NOTE_W / 2, top: ny - 96 - 84, width: NOTE_W, height: 84, display: "flex", alignItems: "center", justifyContent: "center", borderRadius: 22, background: P.blue, color: "#FFFFFF", fontFamily: F.text, fontWeight: 700, fontSize: 40, lineHeight: 1, whiteSpace: "nowrap", transform: `scale(${Math.max(0.001, noteK)})`, transformOrigin: "50% 100%", opacity: noteK > 0 ? 1 : 0 }}>
        Waiting for the owner's OK
      </div>

      {/* the tools, one at a time */}
      <div style={{ position: "absolute", left: COL.left, top: COL.top, width: COL.width }}>
        {STEPS.map((st, i) => (
          <Tool key={st.tool} name={st.tool} at={st.at} next={STEPS[i + 1]?.at} slots={STEPS.slice(i + 1).map((n) => n.at)} />
        ))}
        {STEPS.map((st, i) => (
          <div key={st.tool} style={{ position: "absolute", left: 0, top: 104, width: COL.width }}>
            <Line at={st.at + 8} out={STEPS[i + 1] ? STEPS[i + 1].at + 2 : undefined} size={T.read} weight={600} color={P.bone} font={F.text} style={{ lineHeight: 1.12, letterSpacing: -0.6 }}>
              {st.lines.map((l) => (
                <span key={l} style={{ display: "block", whiteSpace: "nowrap" }}>{l}</span>
              ))}
            </Line>
          </div>
        ))}
      </div>

      <Wipe at={T_WIPE} frames={DURATION - 1 - T_WIPE} x={nx} y={ny - 140} color={SCREEN} />
    </Stage>
  );
}
