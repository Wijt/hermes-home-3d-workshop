// ScreenStage: a real capture of the plugin's Workshop screen (PNG/JPEG or MP4 from media/screen/) in a plain window
// frame on paper, with its honesty chip, an optional camera move inside the window, and an optional pointer that
// glides between points and clicks with a ring. While the file is absent it shows the neutral placeholder card
// "Workshop screen capture goes here", so no redrawn screen can ship by accident.
//
// Coordinates (pointer, clicks, zoom) are in the capture's own pixels: open the capture at full size, read the x and
// y of the button, and use those. Image sizes come from media/manifest.json; give `size` for a video.
import { AbsoluteFill, Img, Video, interpolate, useCurrentFrame } from "raea";
import { C, FONT, R, SHADOW, SIZE, W } from "../theme";
import { Pointer } from "./Icons";
import { Label } from "./Label";
import { Placeholder } from "./PhotoStage";
import { info, isVideo, src } from "./media";
import { INOUT, OUT, clamp, inOut, ramp } from "./timing";

export type PointerKey = { at: number; x: number; y: number };
export type ZoomKey = { at: number; x: number; y: number; scale: number };

export type ScreenStageProps = {
  /** path under media/, e.g. "screen/waiting.png" or "screen/printing.mp4" */
  file: string;
  /** the capture's pixel size; read from the manifest for PNG/JPEG, required for a video (default 1920x1080) */
  size?: [number, number];
  /** for a video: source frame to start at, and to stop at (at 30 fps) */
  startFrom?: number;
  endAt?: number;
  /** the window's title bar text (default "Workshop") */
  title?: string;
  /** the window's box in the frame (default: left 210, top 190, width 1500; height follows the capture's aspect, at most 770) */
  box?: { left?: number; top?: number; width?: number; maxHeight?: number };
  /** pointer keyframes in capture px; it glides (ease in-out) between them and is hidden before the first and after `pointerTo` */
  pointer?: PointerKey[];
  pointerTo?: number;
  /** local frames where the pointer clicks: it dips and a ring spreads from its tip */
  clicks?: number[];
  /** camera inside the window: keyframes of the capture point to centre and the scale (1 = whole capture) */
  zoom?: ZoomKey[];
  /** the honesty chip (default true; shown only when the capture exists, since the placeholder is not a capture) */
  label?: boolean;
  /** local frames: the window rises in from `from` (default 0) and fades by `to` (default never) */
  from?: number;
  to?: number;
  /** ground behind the window (default paper) */
  bg?: string;
};

const BAR = 54;

function track<K extends { at: number }>(keys: K[], f: number, pick: (k: K) => number[]): number[] {
  if (keys.length === 1 || f <= keys[0].at) return pick(keys[0]);
  for (let i = 0; i < keys.length - 1; i++) {
    const a = keys[i];
    const b = keys[i + 1];
    if (f <= b.at) {
      const t = interpolate(f, [a.at, Math.max(a.at + 1, b.at)], [0, 1], { ...clamp, easing: INOUT });
      const pa = pick(a);
      const pb = pick(b);
      return pa.map((v, j) => v + (pb[j] - v) * t);
    }
  }
  return pick(keys[keys.length - 1]);
}

export function ScreenStage({ file, size, startFrom, endAt, title = "Workshop", box, pointer, pointerTo, clicks = [], zoom, label = true, from = 0, to, bg = C.paper }: ScreenStageProps) {
  const f = useCurrentFrame();
  const meta = info(file);
  const url = src(file);
  const [cw, ch] = size ?? (meta?.w && meta?.h ? [meta.w, meta.h] : [1920, 1080]);
  const width = box?.width ?? 1500;
  const maxH = box?.maxHeight ?? 770;
  // fit the capture inside width x (maxH - bar)
  const k = Math.min(width / cw, (maxH - BAR) / ch);
  const vw = Math.round(cw * k);
  const vh = Math.round(ch * k);
  const left = box?.left ?? Math.round((1920 - vw) / 2);
  const top = box?.top ?? 190;

  const o = inOut(f, from, to, 12, 10);
  const rise = interpolate(ramp(f, from, from + 16, OUT), [0, 1], [30, 0], clamp);

  // camera inside the window
  const [zx, zy, zs] = zoom && zoom.length ? track(zoom, f, (z) => [z.x, z.y, z.scale]) : [cw / 2, ch / 2, 1];
  const s = k * zs;
  // translate so (zx, zy) sits in the middle of the viewport, clamped so no empty edge shows
  const tx = Math.min(0, Math.max(vw - cw * s, vw / 2 - zx * s));
  const ty = Math.min(0, Math.max(vh - ch * s, vh / 2 - zy * s));

  // pointer
  let pointerEl = null;
  if (pointer && pointer.length && f >= pointer[0].at && (pointerTo === undefined || f < pointerTo)) {
    const [px, py] = track(pointer, f, (p) => [p.x, p.y]);
    const sx = tx + px * s;
    const sy = ty + py * s;
    const po = Math.min(ramp(f, pointer[0].at, pointer[0].at + 6), pointerTo === undefined ? 1 : 1 - ramp(f, pointerTo - 6, pointerTo));
    let dip = 1;
    const rings = [] as JSX.Element[];
    for (const c of clicks) {
      if (f >= c - 3 && f < c + 5) dip = Math.min(dip, interpolate(f, [c - 3, c, c + 5], [1, 0.84, 1], clamp));
      if (f >= c && f < c + 18) {
        const t = ramp(f, c, c + 18, OUT);
        const r = 14 + 46 * t;
        rings.push(
          <div key={c} style={{ position: "absolute", left: sx - r, top: sy - r, width: 2 * r, height: 2 * r, borderRadius: 999, border: `5px solid ${C.rose}`, opacity: 1 - t, boxSizing: "border-box" }} />,
        );
      }
    }
    pointerEl = (
      <>
        {rings}
        <div style={{ position: "absolute", left: sx - 4, top: sy - 3, opacity: po, transform: `scale(${dip})`, transformOrigin: "4px 3px" }}>
          <Pointer size={60} />
        </div>
      </>
    );
  }

  return (
    <AbsoluteFill style={{ background: bg }}>
      <div
        style={{
          position: "absolute", left, top, width: vw, height: vh + BAR, borderRadius: R.window, overflow: "hidden",
          background: C.card, boxShadow: SHADOW, border: `2px solid ${C.line}`, boxSizing: "content-box",
          opacity: o, transform: `translateY(${rise}px)`,
        }}
      >
        <div style={{ height: BAR, display: "flex", flexDirection: "row", alignItems: "center", padding: "0 24px", gap: 14, background: C.paperDeep, borderBottom: `2px solid ${C.line}` }}>
          <div style={{ fontFamily: FONT.sans, fontWeight: W.bold, fontSize: SIZE.label - 4, lineHeight: 1, color: C.inkSoft }}>{title}</div>
        </div>
        <div style={{ position: "relative", width: vw, height: vh, overflow: "hidden", background: C.paperDeep }}>
          {url ? (
            <div style={{ position: "absolute", left: 0, top: 0, width: cw, height: ch, transformOrigin: "0 0", transform: `translate(${tx}px, ${ty}px) scale(${s})` }}>
              {isVideo(file) ? (
                <Video src={url} muted startFrom={startFrom} endAt={endAt} style={{ width: cw, height: ch }} />
              ) : (
                <Img src={url} style={{ width: cw, height: ch }} />
              )}
            </div>
          ) : (
            <Placeholder text={"Workshop screen capture\ngoes here"} file={file} style={{ whiteSpace: "pre-line" }} />
          )}
          {pointerEl}
        </div>
      </div>
      {label && url && <Label kind="screen" tone="light" from={from} to={to} />}
    </AbsoluteFill>
  );
}
