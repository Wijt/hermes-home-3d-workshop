// Scene 6, The twist (0:50.5 to 1:06): the tilted-base parts, two lines of words, then the Workshop capture.
// The capture is media/screen/twist.png or twist.mp4; until one exists ScreenStage shows its placeholder card.
import { AbsoluteFill, Sequence, useCurrentFrame } from "raea";
import { BigWords, PhotoStage, ScreenStage, has, ramp, sceneFrames } from "../components";
import { C } from "../theme";

export const DURATION = sceneFrames("twist");

const CAPTURE = has("screen/twist.mp4") ? "screen/twist.mp4" : "screen/twist.png";
export const SCREEN_AT = 260;

/** An annotation, not part of the photo: a rose outline traced around the two printed base parts (drawn in the photo's
 *  1920 x 1080 cover-fit space, so it stays on the parts as the photo pushes in). */
function BaseOutline() {
  const f = useCurrentFrame();
  const draw = ramp(f, 30, 66);
  const d = "M240 735 L1175 440 L1328 462 L1322 508 L312 870 L235 825 Z";
  return (
    <svg viewBox="0 0 1920 1080" width="1920" height="1080" style={{ position: "absolute", left: 0, top: 0, opacity: draw > 0 ? 1 : 0 }}>
      <path d={d} fill="none" stroke={C.rose} strokeWidth={5} strokeLinejoin="round" strokeLinecap="round" pathLength={1} strokeDasharray={1} strokeDashoffset={1 - draw} />
    </svg>
  );
}

export function ScreenBeat() {
  const f = useCurrentFrame();
  return (
    <AbsoluteFill style={{ opacity: ramp(f, 0, 12), background: C.paper }}>
      <ScreenStage file={CAPTURE} title="Workshop" zoom={[{ at: 0, x: 960, y: 540, scale: 1 }, { at: DURATION - SCREEN_AT, x: 960, y: 540, scale: 1.12 }]} />
    </AbsoluteFill>
  );
}

/** The two lines over the photo (local frames 12 to SCREEN_AT + 4). final.tsx puts them over clip 07. */
export function TwistWords() {
  return (
    <>
      <BigWords lines="It kept needing a human to clear the plate." size="title" from={12} to={118} />
      <BigWords lines="So it proposed a tilted base. The printer printed its own upgrade." size="title" from={122} to={SCREEN_AT + 4} />
    </>
  );
}

export default function SceneTwist() {
  return (
    <AbsoluteFill style={{ background: C.night }}>
      <Sequence from={0} durationInFrames={SCREEN_AT + 12}>
        <PhotoStage file="real/tilted-base-parts-on-bed.jpg" frames={SCREEN_AT + 12} move="push" zoom={[1.7, 1.78]} focus={{ x: 0.3, y: 1.0 }} filter="brightness(1.3)">
          <BaseOutline />
        </PhotoStage>
        <TwistWords />
      </Sequence>
      <Sequence from={SCREEN_AT} durationInFrames={DURATION - SCREEN_AT}>
        <ScreenBeat />
      </Sequence>
    </AbsoluteFill>
  );
}
