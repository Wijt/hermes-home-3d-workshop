// Time helpers shared by every scene: seconds to frames, clamped ramps, the film's easings and the scene table.
import { Easing, interpolate } from "raea";
import { FRAME } from "../theme";

export const FPS = FRAME.fps;

/** Seconds to frames at 30 fps, rounded. s(1.5) === 45. */
export const s = (seconds: number) => Math.round(seconds * FPS);

/** Clamp option for interpolate. */
export const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;

/** The film's easings. OUT settles (entrances), IN leaves (exits), INOUT for camera moves that start and stop. */
export const OUT = Easing.out(Easing.cubic);
export const IN = Easing.in(Easing.cubic);
export const INOUT = Easing.inOut(Easing.cubic);
/** For slow camera drift (push-ins): nearly linear, so the shot never stops moving. */
export const DRIFT = Easing.bezier(0.3, 0.1, 0.7, 0.9);

/** 0 to 1 between frames a and b, clamped, with an easing (OUT by default). */
export function ramp(f: number, a: number, b: number, easing = OUT) {
  if (b <= a) return f >= a ? 1 : 0;
  return interpolate(f, [a, b], [0, 1], { ...clamp, easing });
}

/**
 * Enter and exit in one number, 0..1..0: rises over `inFrames` from `from`, falls over `outFrames` ending at `to`.
 * `to` undefined means it never exits.
 */
export function inOut(f: number, from: number, to: number | undefined, inFrames = 10, outFrames = 8) {
  const a = ramp(f, from, from + inFrames, OUT);
  const b = to === undefined ? 1 : 1 - ramp(f, to - outFrames, to, IN);
  return Math.min(a, b);
}

/** Frames a line of `words` words needs to be read twice-ish: 0.3 s a word, at least 1 s, plus 0.5 s to land. */
export const readFrames = (words: number) => s(Math.max(1, words * 0.3) + 0.5);

/** Words in a string, for readFrames(words(text)). */
export const words = (text: string) => text.trim().split(/\s+/).filter(Boolean).length;

/** Crossfade length between scenes, in frames. A scene starts XFADE frames before the previous ends and fades in. */
export const XFADE = 10;

/**
 * The storyboard, in seconds of the film (86 s, 2580 frames). `from` and `to` are where each scene owns the
 * screen; film.tsx starts each scene XFADE frames early (except the first) so it can fade in over the join.
 */
export const SCENES = [
  { id: "hook", from: 0, to: 5.5 },
  { id: "ask", from: 5.5, to: 18.5 },
  { id: "backroom", from: 18.5, to: 29.5 },
  { id: "watch", from: 29.5, to: 37.5 },
  { id: "delivery", from: 37.5, to: 50.5 },
  { id: "twist", from: 50.5, to: 66 },
  { id: "group", from: 66, to: 76 },
  { id: "close", from: 76, to: 86 },
] as const;
export type SceneId = (typeof SCENES)[number]["id"];

/** A scene's length in frames, including the XFADE lead-in it gets in film.tsx (none for the first). */
export function sceneFrames(id: SceneId) {
  const i = SCENES.findIndex((x) => x.id === id);
  const sc = SCENES[i];
  return s(sc.to - sc.from) + (i === 0 ? 0 : XFADE);
}

/** Film length in frames. */
export const FILM_FRAMES = s(SCENES[SCENES.length - 1].to);
