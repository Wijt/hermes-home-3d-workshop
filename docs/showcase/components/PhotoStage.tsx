// PhotoStage: a real photo from the printer's camera, cover-fit to the frame, always slowly moving, with its label.
// A missing file shows a neutral placeholder instead of failing the render.
import { AbsoluteFill, Img, interpolate, useCurrentFrame } from "raea";
import { C, FONT, SIZE, W } from "../theme";
import { Label, type Corner } from "./Label";
import { has, src } from "./media";
import { DRIFT, clamp, inOut } from "./timing";

export type PhotoMove = "push" | "pull" | "pan-left" | "pan-right" | "none";

export type PhotoStageProps = {
  /** path under media/, e.g. "real/rose-box-on-bed.jpg" */
  file: string;
  /** frames the move takes (default 150 = 5 s); it starts at frame 0 of the enclosing Sequence */
  frames?: number;
  /** "push" (default: slow zoom in) | "pull" (zoom out) | "pan-left" | "pan-right" (drift across at 1.12 zoom) | "none" */
  move?: PhotoMove;
  /** zoom at start and end for push/pull (default [1.0, 1.1]; pull reverses it) */
  zoom?: [number, number];
  /** the point the push-in heads for, 0..1 across and down (default 0.5, 0.55) */
  focus?: { x: number; y: number };
  /** the honesty chip: true (default, "Real photo from the printer's camera") | false to hide (only when another label is on screen) */
  label?: boolean;
  /** chip corner, default "tl" */
  labelAt?: Corner;
  /** local frames for a fade in and out of the whole stage (default: no fade in, never out) */
  fadeIn?: number;
  to?: number;
  /** a warm-dark veil over the photo, 0..1 (default 0), e.g. 0.25 under a chat card */
  dim?: number;
  /** a CSS filter on the photo itself, e.g. "brightness(1.25)" */
  filter?: string;
  /** annotation drawn in the photo's own frame (1920 x 1080 cover-fit space); it moves and zooms with the photo */
  children?: React.ReactNode;
};

export function PhotoStage({ file, frames = 150, move = "push", zoom = [1.0, 1.1], focus = { x: 0.5, y: 0.55 }, label = true, labelAt = "tl", fadeIn = 0, to, dim = 0, filter, children }: PhotoStageProps) {
  const f = useCurrentFrame();
  const t = interpolate(f, [0, frames], [0, 1], { ...clamp, easing: DRIFT });
  let scale = 1;
  let tx = 0;
  if (move === "push") scale = zoom[0] + (zoom[1] - zoom[0]) * t;
  else if (move === "pull") scale = zoom[1] - (zoom[1] - zoom[0]) * t;
  else if (move === "pan-left" || move === "pan-right") {
    scale = 1.12;
    const span = 1920 * 0.05; // stays inside the 12% overscan
    tx = move === "pan-left" ? span - 2 * span * t : -span + 2 * span * t;
  }
  const o = fadeIn > 0 || to !== undefined ? inOut(f, 0, to, Math.max(1, fadeIn), 10) : 1;
  const url = src(file);
  return (
    <AbsoluteFill style={{ background: C.night, opacity: o, overflow: "hidden" }}>
      {url ? (
        <AbsoluteFill style={{ transform: `translateX(${tx}px) scale(${scale})`, transformOrigin: `${focus.x * 100}% ${focus.y * 100}%` }}>
          <Img src={url} style={{ width: "100%", height: "100%", objectFit: "cover", filter }} />
          {children}
        </AbsoluteFill>
      ) : (
        <Placeholder text="Real photo goes here" file={file} />
      )}
      {dim > 0 && <AbsoluteFill style={{ background: `rgba(30,25,21,${dim})` }} />}
      {label && has(file) && <Label kind="photo" at={labelAt} />}
    </AbsoluteFill>
  );
}

/** The neutral card shown wherever a media file is not there yet. */
export function Placeholder({ text, file, style }: { text: string; file: string; style?: React.CSSProperties }) {
  return (
    <AbsoluteFill
      style={{
        background: C.paperDeep, justifyContent: "center", alignItems: "center", gap: 20,
        backgroundImage: `repeating-linear-gradient(135deg, rgba(43,36,32,0.05) 0 2px, transparent 2px 28px)`,
        ...style,
      }}
    >
      <div style={{ fontFamily: FONT.sans, fontWeight: W.bold, fontSize: 60, lineHeight: 1.1, color: C.inkSoft, textAlign: "center" }}>{text}</div>
      <div style={{ fontFamily: FONT.mono, fontWeight: W.regular, fontSize: SIZE.label, lineHeight: 1.2, color: C.inkSoft }}>media/{file}</div>
    </AbsoluteFill>
  );
}
