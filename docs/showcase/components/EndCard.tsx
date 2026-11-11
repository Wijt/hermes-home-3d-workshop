// EndCard: the close. A big serif line lands first; at `nameAt` it rises to make room and the plugin's name,
// a short line and the repository address come in under it. Hold the full card at least 2.5 s (75 frames).
import { AbsoluteFill, interpolate, useCurrentFrame } from "raea";
import { C, FONT, SIZE, W } from "../theme";
import { Rose } from "./Icons";
import { OUT, INOUT, clamp, ramp } from "./timing";

export type EndCardProps = {
  /** the big line, e.g. "Ask. It's in the box." */
  line: string;
  /** the plugin's name, e.g. "home-3d-workshop" */
  name: string;
  /** under the name, e.g. "a Hermes Agent plugin" */
  sub?: string;
  /** the address, e.g. "github.com/Wijt/hermes-home-3d-workshop" */
  url?: string;
  /** local frame the name block comes in (default 60 = 2 s) */
  nameAt?: number;
  /** "paper" (default) | "night" */
  ground?: "paper" | "night";
  /** local frame the card's slow drift (scale 1.00 to 1.02, linear) ends; it starts 30 frames after the name. Default: no drift */
  driftEnd?: number;
};

export function EndCard({ line, name, sub, url, nameAt = 60, ground = "paper", driftEnd }: EndCardProps) {
  const f = useCurrentFrame();
  const paper = ground === "paper";
  const ink = paper ? C.ink : C.onNight;
  const soft = paper ? C.inkSoft : "rgba(247,241,232,0.78)";
  const lineIn = ramp(f, 0, 16, OUT);
  const lift = ramp(f, nameAt - 4, nameAt + 18, INOUT);
  const nameIn = ramp(f, nameAt + 4, nameAt + 20, OUT);
  const urlIn = ramp(f, nameAt + 14, nameAt + 30, OUT);
  const drift = driftEnd === undefined ? 0 : ramp(f, nameAt + 30, driftEnd, (x) => x);
  return (
    <AbsoluteFill style={{ background: paper ? C.paper : C.night, justifyContent: "center", alignItems: "center" }}>
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", transform: `translateY(${interpolate(lift, [0, 1], [150, 0], clamp)}px) scale(${1 + 0.02 * drift})` }}>
        <div style={{ opacity: lineIn, transform: `translateY(${interpolate(lineIn, [0, 1], [30, 0], clamp)}px) scale(${interpolate(lift, [0, 1], [1, 0.86], clamp)})`, display: "flex", flexDirection: "column", alignItems: "center", gap: 26 }}>
          <Rose size={92} />
          <div style={{ fontFamily: FONT.serif, fontWeight: W.bold, fontSize: 132, lineHeight: 1, letterSpacing: -2, color: ink, whiteSpace: "nowrap" }}>{line}</div>
        </div>
        <div style={{ height: 70 }} />
        <div style={{ opacity: nameIn, transform: `translateY(${interpolate(nameIn, [0, 1], [24, 0], clamp)}px)`, display: "flex", flexDirection: "column", alignItems: "center", gap: 14 }}>
          <div style={{ width: 120, height: 5, borderRadius: 3, background: C.rose, marginBottom: 22 }} />
          <div style={{ fontFamily: FONT.sans, fontWeight: W.bold, fontSize: 76, lineHeight: 1.05, color: ink, whiteSpace: "nowrap" }}>{name}</div>
          {sub && <div style={{ fontFamily: FONT.sans, fontWeight: W.regular, fontSize: SIZE.caption, lineHeight: 1.1, color: soft, whiteSpace: "nowrap" }}>{sub}</div>}
        </div>
        {url && (
          <div style={{ marginTop: 40, opacity: urlIn, fontFamily: FONT.mono, fontWeight: W.bold, fontSize: 52, lineHeight: 1.1, color: paper ? C.rose : "#F2A08E", whiteSpace: "nowrap" }}>{url}</div>
        )}
      </div>
    </AbsoluteFill>
  );
}
