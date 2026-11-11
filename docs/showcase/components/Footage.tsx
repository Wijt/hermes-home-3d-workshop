// Footage: the owner's own clips from media/footage/, used by final.tsx in place of a fallback visual.
// A clip is cover-fitted to the frame (it fills 1920 x 1080 and crops the long side), trimmed with source frames
// (30 fps), and silent unless `sound` is set (only clip 02, the voice note, keeps its sound).
// A clip that is not in media/manifest.json is never mounted, so a missing file cannot fail a render.
import { AbsoluteFill, Video, useCurrentFrame } from "raea";
import { C } from "../theme";
import { has, src } from "./media";
import { ramp } from "./timing";

/** The agreed clip names, in media/footage/. Copy a file in with one of these names and run tools/scan_media.py. */
export const CLIPS = {
  hook: "footage/01_hook_drop.mp4",
  ask: "footage/02_mum_voice_note.mp4",
  backroom: "footage/03_screen_start.mp4",
  watch: "footage/04_printing_timelapse.mp4",
  push: "footage/05_push_into_box.mp4",
  message: "footage/06_mum_gets_message.mp4",
  tilted: "footage/07_tilted_base.mp4",
  lab: "footage/08_lab_chat.mp4",
  objects: "footage/09_objects.mp4",
} as const;
export type ClipId = keyof typeof CLIPS;

/** True when the owner has put this clip in media/footage/ and run the scan. */
export const hasClip = (id: ClipId) => has(CLIPS[id]);

/** Where each clip starts in its file, in seconds. Trim here if the useful part is not at the start. */
export const CLIP_START_SECONDS: Record<ClipId, number> = {
  hook: 0, ask: 0, backroom: 0, watch: 0, push: 0, message: 0, tilted: 0, lab: 0, objects: 0,
};

export type FootageProps = {
  clip: ClipId;
  /** frames the clip plays for (it is cut at this length) */
  frames: number;
  /** keep the clip's own sound (only the voice note) */
  sound?: boolean;
  /** 0..1 warm-dark veil, so words over it stay readable */
  dim?: number;
  /** fade in over this many frames */
  fadeIn?: number;
};

export function Footage({ clip, frames, sound = false, dim = 0, fadeIn = 0 }: FootageProps) {
  const f = useCurrentFrame();
  const url = src(CLIPS[clip]);
  if (!url) return null;
  const start = Math.round(CLIP_START_SECONDS[clip] * 30);
  return (
    <AbsoluteFill style={{ background: C.night, opacity: fadeIn > 0 ? ramp(f, 0, fadeIn) : 1 }}>
      <Video src={url} muted={!sound} startFrom={start} endAt={start + frames} style={{ width: 1920, height: 1080, objectFit: "cover" }} />
      {dim > 0 && <AbsoluteFill style={{ background: `rgba(30,25,21,${dim})` }} />}
    </AbsoluteFill>
  );
}
