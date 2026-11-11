// BigWords: one or two large serif lines over a photo or a colour, with a scrim for separation.
// Put it after a PhotoStage (or alone, with bg) inside the same AbsoluteFill or Sequence.
import { AbsoluteFill, interpolate, useCurrentFrame } from "raea";
import { C, FONT, LH, SAFE, SCRIM, SIZE, W } from "../theme";
import { IN, OUT, clamp, inOut, ramp } from "./timing";

export type BigWordsProps = {
  /** one line, or two (each its own line; the second may enter later with lineDelay) */
  lines: string | string[];
  /** local frame the first line starts entering (default 0) */
  from?: number;
  /** local frame everything is gone (default: stays) */
  to?: number;
  /** frames between the first and the second line entering (default 18) */
  lineDelay?: number;
  /** "display" (112 px, short lines) | "title" (88 px, longer lines). Default: display for one line, title for two */
  size?: "display" | "title";
  /** vertical position of the block: "bottom" (default, over the scrim) | "center" | "top" */
  position?: "bottom" | "center" | "top";
  align?: "left" | "center";
  /** what is behind: "photo" (default; light text over a scrim) | "paper" (ink on paper) | "night" (light on dark) */
  over?: "photo" | "paper" | "night";
  /** the scrim over a photo: matches position by default; "none" to skip */
  scrim?: "bottom" | "top" | "full" | "none";
  /** a word or phrase in the lines to set in the accent colour (paper ground only, where it has contrast) */
  accent?: string;
};

export function BigWords({ lines, from = 0, to, lineDelay = 18, size, position = "bottom", align = "left", over = "photo", scrim, accent }: BigWordsProps) {
  const f = useCurrentFrame();
  const list = Array.isArray(lines) ? lines : [lines];
  const px = SIZE[size ?? (list.length > 1 ? "title" : "display")];
  const lh = size === "display" || (!size && list.length === 1) ? LH.display : LH.title;
  const color = over === "paper" ? C.ink : C.onNight;
  const scrimKind = scrim ?? (over === "photo" ? (position === "center" ? "full" : position) : "none");
  const scrimO = inOut(f, from - 6, to, 14, 10);
  const exit = to === undefined ? 0 : ramp(f, to - 8, to, IN);
  const bg = over === "paper" ? C.paper : over === "night" ? C.night : undefined;
  const justify = position === "bottom" ? "flex-end" : position === "top" ? "flex-start" : "center";
  return (
    <AbsoluteFill style={{ background: bg }}>
      {scrimKind !== "none" && (
        <AbsoluteFill
          style={{
            opacity: scrimO,
            background: scrimKind === "full" ? SCRIM.full : SCRIM[scrimKind],
            ...(scrimKind === "bottom" ? { top: "35%" } : scrimKind === "top" ? { bottom: "35%" } : {}),
          }}
        />
      )}
      <AbsoluteFill
        style={{
          justifyContent: justify, alignItems: align === "center" ? "center" : "flex-start",
          padding: `${SAFE.top + 10}px ${SAFE.side}px ${SAFE.bottom + 10}px`, boxSizing: "border-box", gap: 10,
        }}
      >
        {list.map((line, i) => {
          const at = from + i * lineDelay;
          const o = Math.min(ramp(f, at, at + 12, OUT), 1 - exit);
          const y = interpolate(ramp(f, at, at + 16, OUT), [0, 1], [34, 0], clamp);
          return (
            <div
              key={i}
              style={{
                maxWidth: 1680, fontFamily: FONT.serif, fontWeight: W.bold, fontSize: px, lineHeight: lh,
                letterSpacing: -1, color, textAlign: align, opacity: o, transform: `translateY(${y}px)`,
                textShadow: over === "photo" ? "0 2px 18px rgba(30,25,21,0.45)" : "none",
              }}
            >
              {accent && over === "paper" && line.includes(accent) ? (
                <>
                  {line.slice(0, line.indexOf(accent))}
                  <span style={{ color: C.rose }}>{accent}</span>
                  {line.slice(line.indexOf(accent) + accent.length)}
                </>
              ) : (
                line
              )}
            </div>
          );
        })}
      </AbsoluteFill>
    </AbsoluteFill>
  );
}
