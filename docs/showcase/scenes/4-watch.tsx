// Scene 4, The watch (0:29.5 to 0:37.5): the Workshop screen while the print runs: progress, camera frame.
//
// CAPTURE THIS (media/screen/watch.mp4, or watch.png for a still):
//   1920x1080, 30 fps, no audio, 9 s (270 frames; the scene uses source frames 0..250).
//   Same window and the same simulated printer as the back-room capture, right after Start.
//   0:00-0:03  the job is "Printing": a visible progress bar and percentage moving up, layer or time left.
//   0:03-0:06  the camera frame (the printer's camera snapshot panel) updates at least once.
//   0:06-0:09  progress keeps rising; if the screen lists the watcher or its "model calls: 0" counter, keep
//              it in view. Do not show real names or ids.
//   The film zooms onto `progress` (frames 40 to 110) and then `camera` (130 to 220); put their pixel centres
//   in the capture into those props (DEFAULTS ARE GUESSES until the capture exists).
// A still (watch.png) also works: the zoom still moves over it.
import { AbsoluteFill } from "raea";
import { Caption, ScreenStage, has, s, sceneFrames, type PointerKey, type ZoomKey } from "../components";
import { C } from "../theme";

export const DURATION = sceneFrames("watch");

export type WatchProps = {
  /** the capture, default: media/screen/watch.mp4 if present, else watch.png, else the placeholder */
  file?: string;
  size?: [number, number];
  startFrom?: number;
  endAt?: number;
  /** pixel centre of the progress bar / percentage in the capture (DEFAULT IS A GUESS) */
  progress?: { x: number; y: number };
  /** pixel centre of the camera frame in the capture (DEFAULT IS A GUESS) */
  camera?: { x: number; y: number };
  /** optional pointer path (none by default) */
  pointer?: PointerKey[];
  clicks?: number[];
  zoom?: ZoomKey[];
};

export default function SceneWatch({
  file,
  size = [1920, 1080],
  startFrom,
  endAt,
  progress = { x: 700, y: 360 },
  camera = { x: 1400, y: 540 },
  pointer,
  clicks,
  zoom,
}: WatchProps = {}) {
  const path = file ?? (has("screen/watch.mp4") ? "screen/watch.mp4" : has("screen/watch.png") ? "screen/watch.png" : "screen/watch.mp4");
  const cam: ZoomKey[] = zoom ?? [
    { at: 0, x: 960, y: 540, scale: 1 },
    { at: 30, x: 960, y: 540, scale: 1 },
    { at: 55, x: progress.x, y: progress.y, scale: 1.5 },
    { at: 110, x: progress.x, y: progress.y, scale: 1.5 },
    { at: 135, x: camera.x, y: camera.y, scale: 1.5 },
    { at: 220, x: camera.x, y: camera.y, scale: 1.5 },
    { at: 245, x: 960, y: 540, scale: 1 },
  ];
  const split = s(4);
  return (
    <AbsoluteFill style={{ background: C.paper }}>
      <ScreenStage
        file={path}
        size={size}
        startFrom={startFrom}
        endAt={endAt}
        box={{ top: 190, maxHeight: 625 }}
        pointer={has(path) ? pointer : undefined}
        clicks={clicks}
        zoom={cam}
        from={4}
      />
      <Caption text="Watched by the plugin." from={20} to={split} />
      <Caption text="Zero model calls." from={split} to={DURATION - 2} />
    </AbsoluteFill>
  );
}
