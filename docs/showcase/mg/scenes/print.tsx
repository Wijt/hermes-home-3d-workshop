// print (300 frames): the print, watched. It opens on the plugin's real screen where "approve" left it (zoomed on
// the top card) and creeps toward the percent. At 48% the number lifts off the screen: the studio's ink opens
// from it, the number grows into the scene's one bold element and counts to 100 while the tag is printed on the
// plate. It ends close on the finished tag (END_VIEW), which is the picture "box" starts on.
import type { ReactNode } from "react";
import { AbsoluteFill, useCurrentFrame } from "raea";
import { Bubble, Chip, F, FONTS, IN, INOUT, Iso, Label, Line, Nozzle, OUT, P, Screen, Stage, T, Words, nozzleAt, plateSlabs, pop, project, ramp, tagSlabs, tween, type CamKey, type View } from "../kit";

export const DURATION = 300;
const LAST = DURATION - 1;

/** The picture this scene ends on and "box" starts on: the finished tag at the plate's centre, nothing else. */
export const END_VIEW: View = { cx: 1180, cy: 640, scale: 2.2, yaw: -0.42, pitch: 0.56 };
/** How fast the plate is turning at the cut, in radians a frame ("box" keeps the same turn going). */
export const TURN = 0.0011;
/** The finished tag's shadow on the sheet. */
export const TAG_SHADOW = { x: 8, y: 10, w: 250, h: 112, o: 0.38 } as const;

// --- the real screen -------------------------------------------------------------------------------------------
// The capture shows 48% from source frame 174 to 186; the scene's frame 0 is source frame 78, so the screen
// reads 48% when the ink opens (frames 100 to 108) and the drawn number can take over from it.
const SRC_START = 78;
const CAM: CamKey[] = [
  { at: 0, x: 1090, y: 420, scale: 1.5 },
  { at: 150, x: 1172, y: 394, scale: 1.88 }, // never reached: the ink covers the screen while it is still moving
];
/** The percent's two digits on the capture (capture px). */
const DIGITS = { x: 1128, y: 337, w: 82, h: 48 };

/** The same sums the kit's Screen does, so a capture point can be followed in the frame. */
function camAt(f: number) {
  const t = ramp(f, CAM[0].at, CAM[1].at, INOUT);
  const zx = CAM[0].x + (CAM[1].x - CAM[0].x) * t;
  const zy = CAM[0].y + (CAM[1].y - CAM[0].y) * t;
  const zs = CAM[0].scale + (CAM[1].scale - CAM[0].scale) * t;
  const tx = Math.min(0, Math.max(1920 - 1920 * zs, 960 - zx * zs));
  const ty = Math.min(0, Math.max(1080 - 1080 * zs, 540 - zy * zs));
  return { tx, ty, zs };
}

// --- times -----------------------------------------------------------------------------------------------------
const T_BAR = 8; // the caption arrives
const T_BAR_OUT = 98;
const T_WIPE = 100; // the ink opens from the percent
const WIPE_FRAMES = 14;
const T_LAND = 126; // the giant percent is in its place
const T_PRINT = 124; // the count and the layers start
const T_DONE = 250; // 100%, the nozzle lifts, "Finished"
const T_LAYER = 134;
const T_WORDS = 150;
const T_LINE = 168;
const T_PUSH = 268; // the camera goes in on the finished tag
const LIN = (t: number) => t;

// --- the drawn part --------------------------------------------------------------------------------------------
const COL = 110; // the left edge of all type
const PCT_TOP = 112;
const SIZE = T.giant;
/** Where the digits' ink starts inside the percent block, and how tall they are (Bricolage 96pt ExtraBold at 300). */
const GLYPH = { x: 8, y: 36, h: 207 };
/** While it prints, the plate's left corner points into the gap between the percent and the words. */
const CORNER = { x: 650, y: 498 };
const K = 0.56;
const CHIP_H = Math.round(T.read * 1.9); // the kit's chip height at this size

function viewAt(f: number): View {
  if (f >= LAST) return END_VIEW;
  const yaw = END_VIEW.yaw - TURN * (LAST - f);
  const c = Math.cos(yaw);
  const sn = Math.sin(yaw);
  // it arrives from the right with a small push in, then holds its corner still while it turns
  const arrive = ramp(f, T_WIPE + 2, T_WIPE + 34, OUT);
  const s = 1.25 + 0.09 * arrive;
  const ax = CORNER.x + 190 * (1 - arrive);
  const wideX = ax + 512 * s * (c - sn);
  const wideY = CORNER.y + 512 * K * s * (c + sn);
  const p = ramp(f, T_PUSH, LAST, INOUT);
  return { cx: wideX + (END_VIEW.cx - wideX) * p, cy: wideY + (END_VIEW.cy - wideY) * p, scale: s + (END_VIEW.scale - s) * p, yaw, pitch: K };
}

/** The drawn scene shown only inside a circle that grows from a point: the kit's Wipe, with a picture in it. */
function Reveal({ at, frames, x, y, children }: { at: number; frames: number; x: number; y: number; children: ReactNode }) {
  const f = useCurrentFrame();
  const t = ramp(f, at, at + frames, INOUT);
  if (t <= 0) return null;
  if (t >= 1) return <AbsoluteFill>{children}</AbsoluteFill>;
  const far = Math.hypot(Math.max(x, 1920 - x), Math.max(y, 1080 - y)) + 40;
  const r = far * t;
  return (
    <div style={{ position: "absolute", left: x - r, top: y - r, width: 2 * r, height: 2 * r, borderRadius: r, overflow: "hidden" }}>
      <div style={{ position: "absolute", left: r - x, top: r - y, width: 1920, height: 1080 }}>{children}</div>
    </div>
  );
}

/** Words over the real screen: an ink bar, bottom left. The same bar "approve" draws: the box rises, then its
 * words come up inside it. */
function Bar({ text, at, out }: { text: string; at: number; out: number }) {
  const f = useCurrentFrame();
  const up = ramp(f, at, at + 10);
  const gone = ramp(f, out - 8, out, IN);
  const o = Math.min(ramp(f, at, at + 6, LIN), 1 - gone);
  return (
    <div style={{ position: "absolute", left: 80, bottom: 120, display: "flex", flexDirection: "row", opacity: o, transform: `translateY(${(1 - up) * 34 + gone * 18}px)` }}>
      <div style={{ display: "flex", flexDirection: "row", alignItems: "center", boxSizing: "border-box", height: 108, padding: "0 34px", borderRadius: 28, background: P.ink }}>
        <Words text={text} at={at + 3} each={2} size={T.read} weight={600} font={F.text} color={P.bone} lineHeight={1.12} />
      </div>
    </div>
  );
}

export default function Print() {
  const f = useCurrentFrame();

  // the capture's percent, followed in the frame
  const cam = camAt(f);
  const digX = cam.tx + DIGITS.x * cam.zs;
  const digY = cam.ty + DIGITS.y * cam.zs;
  const wipeX = cam.tx + (DIGITS.x + DIGITS.w / 2) * cam.zs;
  const wipeY = cam.ty + (DIGITS.y + DIGITS.h / 2) * cam.zs;

  // the print
  const printed = tween(f, T_PRINT, T_DONE, 0.48, 1, LIN);
  const done = f >= T_DONE;
  const pct = done ? 100 : Math.min(99, Math.floor(printed * 100 + 1e-6));
  const layer = done ? 21 : Math.floor(printed * 21 + 1e-6);

  const view = viewAt(f);
  const slabs = [...plateSlabs({ shadow: { ...TAG_SHADOW } }), ...tagSlabs({ printed })];

  // the nozzle lays the layer down, then lifts away from where it stopped
  const lift = ramp(f, T_DONE, T_DONE + 13, INOUT);
  const [nx, ny, nz] = nozzleAt(Math.min(printed, 0.99999), Math.min(f, T_DONE));
  const nozzleO = 1 - ramp(f, T_DONE + 5, T_DONE + 13, LIN);

  // the giant percent: it starts on the capture's own digits, at their size, and grows into its place
  const fly = ramp(f, T_WIPE + 3, T_LAND, INOUT);
  const k0 = (DIGITS.h * cam.zs) / GLYPH.h;
  const pk = k0 + (1 - k0) * fly;
  const px = (digX - (COL + GLYPH.x)) * (1 - fly);
  const py = (digY - (PCT_TOP + GLYPH.y)) * (1 - fly);
  // 100 lands with one small beat, and the whole block leaves before the plate comes under it
  const beat = 1 + 0.035 * pop(f, T_DONE, 10) * (1 - ramp(f, T_DONE + 10, T_DONE + 18, INOUT));
  const pctGone = ramp(f, T_PUSH + 2, T_PUSH + 12, IN);

  // "Finished": over the tag's far edge, a little to the left of where the nozzle lifts away, riding the plate
  const [chipX, chipY] = project(view, -64, -48, 44);

  return (
    <AbsoluteFill style={{ background: P.ink, overflow: "hidden" }}>
      <style>{FONTS}</style>

      {/* frames 0 to 114: the plugin's real screen */}
      {f < T_WIPE + WIPE_FRAMES && (
        <AbsoluteFill>
          <Screen file="screen/watch.mp4" startFrom={SRC_START} cam={CAM} />
          <Label kind="screen" at={-8} out={T_WIPE + 8} style={{ left: "auto", right: 64, bottom: "auto", top: 186 }} />
          <Bar text="Then the plugin watches the print." at={T_BAR} out={T_BAR_OUT} />
        </AbsoluteFill>
      )}

      {/* from frame 100: the studio opens from the percent */}
      <Reveal at={T_WIPE} frames={WIPE_FRAMES} x={wipeX} y={wipeY}>
        <Stage drift={0}>
          <Iso view={view} slabs={slabs}>
            {nozzleO > 0 && <Nozzle view={view} at={[nx, ny, nz + 190 * lift]} o={nozzleO} />}
          </Iso>

          {/* the percent */}
          <div style={{ position: "absolute", left: COL, top: PCT_TOP, transformOrigin: `${GLYPH.x}px ${GLYPH.y}px`, transform: `translate(${px - 50 * pctGone}px, ${py}px) scale(${pk * beat})`, opacity: 1 - pctGone }}>
            <div style={{ display: "flex", flexDirection: "row", alignItems: "flex-start" }}>
              <div style={{ fontFamily: F.display, fontWeight: 800, fontSize: SIZE, lineHeight: 0.9, letterSpacing: -6, color: P.bone, whiteSpace: "nowrap", fontFeatureSettings: '"tnum" 1' }}>{pct}</div>
              <div style={{ fontFamily: F.display, fontWeight: 700, fontSize: 124, lineHeight: 1, color: P.mist, marginLeft: 16, marginTop: 127 }}>%</div>
            </div>
          </div>

          {/* the layer */}
          <div style={{ position: "absolute", left: COL + 6, top: PCT_TOP + 276 }}>
            <Line at={T_LAYER} out={T_PUSH + 8} size={T.read} weight={500} color={P.mist} style={{ whiteSpace: "nowrap", letterSpacing: -0.6 }}>
              Layer <span style={{ color: P.bone, fontWeight: 700 }}>{layer}</span> of 21
            </Line>
          </div>

          {/* the second read */}
          <div style={{ position: "absolute", left: COL, top: 548, display: "flex", flexDirection: "column", alignItems: "flex-start" }}>
            <Words text="Mıstık keeps watch." at={T_WORDS} each={3} out={T_PUSH} size={88} />
            {/* what it says in the family chat while it watches */}
            <div style={{ marginTop: 16 }}>
              <Bubble text="Mum, your key tag has started printing. About 13 minutes to go." who="Mıstık" group="Family" color={P.bone} ink={P.ink} at={T_LINE - 4} out={T_PUSH + 2} size={44} width={790} />
            </div>
            <Line at={T_LINE + 14} out={T_PUSH + 4} size={40} weight={500} color={P.mist} style={{ marginTop: 14, marginLeft: 4 }}>
              <span style={{ display: "block", whiteSpace: "nowrap" }}>If something goes wrong,</span>
              <span style={{ display: "block", whiteSpace: "nowrap" }}>it tells the chat and the owner.</span>
            </Line>
          </div>

          <Label kind="chat" at={T_LINE + 4} out={T_PUSH} style={{ left: "auto", right: 64, bottom: "auto", top: 124 }} />

          {/* done */}
          <div style={{ position: "absolute", left: chipX - 300, top: chipY - 46 - CHIP_H, width: 600, display: "flex", flexDirection: "row", justifyContent: "center" }}>
            <Chip at={T_DONE + 4} out={LAST - 5} bg={P.green} color={P.ink} size={T.read}>Finished</Chip>
          </div>
        </Stage>
      </Reveal>
    </AbsoluteFill>
  );
}
