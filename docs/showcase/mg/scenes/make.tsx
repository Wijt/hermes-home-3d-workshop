// make (345 frames): the agent does the work, so nobody needs to know how a 3D printer is used. Four of the
// plugin's tools, one at a time on the left. On the right: three models it found, and the one Mum picks; that one on
// a tile of the build plate, made hers (her name, in red); its 21 layers lifted apart; and her yes, which starts
// the print. The lifted layers are the scene's one bold moment.
import type { ReactNode } from "react";
import { AbsoluteFill, useCurrentFrame } from "raea";
import { Bubble, F, IN, INOUT, Iso, Line, OUT, P, Stage, T, Wipe, keys, plateSlabs, project, ramp, tagSlabs, type View } from "../kit";

export const DURATION = 345;

const STEPS = [
  { at: 6, tool: "home3d_find_models", lines: ["Finds models online", "and shows the options."] },
  { at: 96, tool: "home3d_customize", lines: ["Makes it hers:", "her name, in red."] },
  { at: 170, tool: "home3d_slice", lines: ["21 layers, 13 minutes,", "4 g of PLA"] },
  { at: 255, tool: "home3d_queue", lines: ["Six safety checks.", "She says yes, it prints."] },
] as const;

const COL = { left: 120, top: 410, width: 760 };
const SLOT = 92; // how far an earlier tool's name moves up when the next one arrives
const T_WIPE = 331;
const SCREEN = "#F4F5F7";

// the three options (frame px) and Mum's answer
const CARD = { w: 250, h: 290, top: 336, lefts: [1000, 1280, 1560] };
const T_CARDS = 16; // the first card; the next two follow 5 frames apart
const T_PICK = 54; // Mum's answer lands
const T_CHOSEN = 66; // the second card is marked
const T_LAND = 78; // the cards leave and the chosen one goes onto the plate
const T_PLATE = 74;

// a model as the agent found it: no name, no colour yet
const GREY = { top: "#BFC3CC", side: "#8D919B", dark: "#5C6069" };
const PLAIN = 15 / 21; // the tag without its letters (the base's 15 layers of 21)

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

/** The outline of a found model, seen from above: three different key tags. */
function Shape({ kind }: { kind: 0 | 1 | 2 }) {
  const fill = "#C3C7D0";
  const hole = (left: number, top: number) => <div style={{ position: "absolute", left, top, width: 20, height: 20, borderRadius: 10, background: P.ink2 }} />;
  let body: ReactNode;
  if (kind === 0) {
    // a round medal
    body = (
      <>
        <div style={{ position: "absolute", left: 41, top: 6, width: 118, height: 118, borderRadius: 59, background: fill }} />
        {hole(90, 18)}
      </>
    );
  } else if (kind === 1) {
    // the plain rounded tag
    body = (
      <>
        <div style={{ position: "absolute", left: 12, top: 30, width: 176, height: 72, borderRadius: 20, background: fill }} />
        {hole(28, 56)}
      </>
    );
  } else {
    // a luggage label with a pointed end
    body = (
      <>
        <div style={{ position: "absolute", left: 58, top: 30, width: 130, height: 72, borderRadius: 10, background: fill }} />
        <div style={{ position: "absolute", left: 33, top: 40.5, width: 51, height: 51, borderRadius: 8, background: fill, transform: "rotate(45deg)" }} />
        {hole(40, 56)}
      </>
    );
  }
  return <div style={{ position: "absolute", left: 25, top: 44, width: 200, height: 130 }}>{body}</div>;
}

function Card({ i, to }: { i: 0 | 1 | 2; to: [number, number] }) {
  const f = useCurrentFrame();
  const at = T_CARDS + i * 5;
  const inn = ramp(f, at, at + 12, OUT);
  const chosen = i === 1;
  const mark = chosen ? ramp(f, T_CHOSEN, T_CHOSEN + 8, OUT) : 0;
  const dim = chosen ? 0 : ramp(f, T_CHOSEN, T_CHOSEN + 10, INOUT);
  const go = ramp(f, T_LAND, T_LAND + 18, chosen ? INOUT : IN);
  const left = CARD.lefts[i];
  // the chosen card travels to the plate and gives way to the part itself; the others just leave
  const dx = chosen ? (to[0] - CARD.w / 2 - left) * go : 0;
  const dy = chosen ? (to[1] - CARD.h / 2 - CARD.top) * go : 30 * go;
  const k = chosen ? 1 - 0.45 * go : 1;
  const o = inn * (1 - 0.72 * dim) * (1 - go);
  return (
    <div style={{ position: "absolute", left, top: CARD.top, width: CARD.w, height: CARD.h, opacity: o, transform: `translate(${dx}px, ${dy + (1 - inn) * 44}px) scale(${k})`, transformOrigin: "50% 50%" }}>
      <div style={{ position: "absolute", left: 0, top: 0, width: CARD.w, height: CARD.h, borderRadius: 30, background: P.ink2, boxSizing: "border-box", border: `5px solid ${mark > 0 ? P.red : P.ink3}` }} />
      <Shape kind={i} />
      <div style={{ position: "absolute", left: 30, top: 196, fontFamily: F.display, fontWeight: 800, fontSize: 64, lineHeight: 1, color: mark > 0 ? P.red : P.bone }}>{i + 1}</div>
    </div>
  );
}

export default function Make() {
  const f = useCurrentFrame();

  // the tile turns slowly the whole time; the camera moves in for the lifted layers and settles back
  const zoom = keys(f, [[0, 1.9], [164, 1.9], [200, 2.5], [228, 2.56], [252, 2.02], [344, 2.1]]);
  const view: View = {
    cx: keys(f, [[0, 1420], [164, 1420], [200, 1470], [228, 1470], [252, 1440], [344, 1440]]),
    cy: keys(f, [[0, 660], [164, 660], [200, 790], [228, 790], [252, 660], [344, 660]]),
    scale: zoom,
    yaw: -0.5 + 0.0014 * f,
    pitch: 0.56,
  };
  const centre = project(view, 0, 0, 0);

  // find: the chosen model lands on the plate as a plain tag
  const landed = ramp(f, T_LAND + 6, T_LAND + 26, INOUT);
  // customize: her name rises out of it and it turns red
  const named = ramp(f, 110, 134, INOUT);
  const red = ramp(f, 106, 122, INOUT);
  const printed = landed * (PLAIN + (1 - PLAIN) * named);
  // slice: the layers lift apart, breathe, and close
  const spread = 1 + 2.5 * ramp(f, 178, 200, OUT) * (1 - ramp(f, 224, 242, INOUT)) + 0.06 * Math.sin((f - 200) * 0.16) * ramp(f, 200, 206) * (1 - ramp(f, 218, 224));
  const tile = ramp(f, T_PLATE, T_PLATE + 16, OUT);

  const plate = plateSlabs({ size: 440, grid: 110, shadow: landed > 0.05 ? { x: 10, y: 12, w: 246, h: 110, o: 0.34 * landed } : undefined });
  const tag = (c: { top: string; side: string; dark: string }, id: string) => (printed > 0 ? tagSlabs({ printed, spread, top: c.top, side: c.side, dark: c.dark, id }) : []);

  // queue: Mum's yes lands over the part
  const [nx, ny] = project(view, 0, 0, 44);

  return (
    <Stage frames={DURATION} drift={0.02}>
      <AbsoluteFill style={{ opacity: tile, transform: `translateY(${(1 - tile) * 40}px)` }}>
        <Iso view={view} slabs={plate} />
        {/* the plain model and the customised one are the same part: one fades into the other */}
        {red < 1 && (
          <AbsoluteFill style={{ opacity: 1 }}>
            <Iso view={view} slabs={tag(GREY, "plain")} />
          </AbsoluteFill>
        )}
        {red > 0 && (
          <AbsoluteFill style={{ opacity: red }}>
            <Iso view={view} slabs={tag({ top: P.red, side: P.redDeep, dark: P.redDark }, "hers")} />
          </AbsoluteFill>
        )}
      </AbsoluteFill>

      {/* the options, and Mum's answer */}
      {f < T_LAND + 20 && (
        <>
          <Card i={0} to={centre} />
          <Card i={1} to={centre} />
          <Card i={2} to={centre} />
          <div style={{ position: "absolute", left: 1250, top: 132, width: 560 }}>
            <Bubble text="The second one." who="Mum" group="Family" at={T_PICK} out={T_LAND + 10} size={58} width={560} />
          </div>
        </>
      )}

      {/* her yes */}
      <div style={{ position: "absolute", left: nx - 250, top: ny - 300, width: 520 }}>
        <Bubble text="Yes, print it." who="Mum" group="Family" at={267} size={60} width={520} />
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
