// Scene 3, The back room (0:18.5 to 0:29.5): the Workshop screen's "Waiting for you" card, the pointer presses Start.
//
// CAPTURE THIS (media/screen/backroom.mp4, or backroom.png for a still):
//   1920x1080, 30 fps, no audio, 12 s (360 frames; the scene uses source frames 0..340, so 12 s is safe).
//   Hermes Desktop, Workshop page, full window, simulated printer, no personal names or ids in view.
//   0:00  the "Waiting for you" card is already on screen: part name, 3D preview, checklist, the Start button.
//   0:00-0:04  turn the 3D preview slowly once with the mouse (the pointer is drawn by the film, so keep the real
//              cursor hidden or out of the way if you can).
//   0:04-0:06.5  checklist ticks visible. Leave the Start button in view and still.
//   ~0:07 (source frame 210)  Start is pressed; 0:07-0:12 the card changes to printing / "Started".
//   The film draws its own pointer and click ring at frame 210. If the real press lands at another moment,
//   change `clicks` and the last pointer key to match, and put the Start button's pixel centre in
//   `startButton` (capture pixels). The defaults below are GUESSES until the capture exists.
// A still (backroom.png) also works: the pointer and zoom still run on top of it.
import { AbsoluteFill } from "raea";
import { Caption, ScreenStage, has, s, sceneFrames, type PointerKey, type ZoomKey } from "../components";
import { C } from "../theme";

export const DURATION = sceneFrames("backroom");

export type BackRoomProps = {
  /** the capture, default: media/screen/backroom.mp4 if present, else backroom.png, else the placeholder */
  file?: string;
  /** capture pixel size (needed for mp4; default 1920x1080) */
  size?: [number, number];
  startFrom?: number;
  endAt?: number;
  /** pixel centre of the Start button in the capture (DEFAULT IS A GUESS) */
  startButton?: { x: number; y: number };
  /** pixel centre of the 3D preview in the capture (DEFAULT IS A GUESS) */
  preview?: { x: number; y: number };
  /** pointer path; default is built from `preview` and `startButton` */
  pointer?: PointerKey[];
  /** local frames where the pointer clicks (default: the press at 210) */
  clicks?: number[];
  /** camera inside the window; default eases from the whole card to the preview to the Start button */
  zoom?: ZoomKey[];
};

export default function SceneBackroom({
  file,
  size = [1920, 1080],
  startFrom,
  endAt,
  startButton = { x: 1500, y: 760 },
  preview = { x: 600, y: 480 },
  pointer,
  clicks = [210],
  zoom,
}: BackRoomProps = {}) {
  const path = file ?? (has("screen/backroom.mp4") ? "screen/backroom.mp4" : has("screen/backroom.png") ? "screen/backroom.png" : "screen/backroom.mp4");
  const press = clicks[0] ?? 210;
  const ptr: PointerKey[] = pointer ?? [
    { at: 40, x: 960, y: 620 },
    { at: 90, x: preview.x + 120, y: preview.y + 80 },
    { at: 130, x: preview.x - 100, y: preview.y },
    { at: press - 40, x: startButton.x - 260, y: startButton.y - 120 },
    { at: press, x: startButton.x, y: startButton.y },
  ];
  const cam: ZoomKey[] = zoom ?? [
    { at: 0, x: 960, y: 540, scale: 1 },
    { at: 40, x: 960, y: 540, scale: 1 },
    { at: 90, x: preview.x, y: preview.y, scale: 1.4 },
    { at: 140, x: preview.x, y: preview.y, scale: 1.4 },
    { at: press - 20, x: startButton.x - 200, y: startButton.y - 100, scale: 1.6 },
    { at: press + 60, x: startButton.x - 200, y: startButton.y - 100, scale: 1.6 },
    { at: press + 110, x: 960, y: 540, scale: 1 },
  ];
  const split = s(5.5);
  return (
    <AbsoluteFill style={{ background: C.paper }}>
      <ScreenStage
        file={path}
        size={size}
        startFrom={startFrom}
        endAt={endAt}
        box={{ top: 190, maxHeight: 625 }}
        pointer={has(path) ? ptr : undefined}
        pointerTo={press + 60}
        clicks={clicks}
        zoom={cam}
        from={4}
      />
      <Caption text="The agent prepares everything." from={26} to={split} />
      <Caption text="A person presses Start." from={split} to={DURATION - 2} />
    </AbsoluteFill>
  );
}
