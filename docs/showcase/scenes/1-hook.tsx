// Scene 1, Hook (0:00 to 0:05.5): the real rose box on the bed, a slow push-in, two lines of words.
import { AbsoluteFill } from "raea";
import { BigWords, PhotoStage, sceneFrames } from "../components";

export const DURATION = sceneFrames("hook");

/** The two lines. Shared with final.tsx, which puts them over the owner's clip when there is one. */
export function HookWords() {
  return (
    <>
      <BigWords lines="My mother has never opened a slicer." from={3} to={78} size="title" position="top" />
      <BigWords lines="She asked a group chat for this." from={82} to={DURATION - 2} size="title" position="top" />
    </>
  );
}

export default function SceneHook() {
  return (
    <AbsoluteFill>
      <PhotoStage file="real/rose-box-on-bed.jpg" frames={DURATION} move="push" zoom={[1.12, 1.24]} focus={{ x: 0.3, y: 0.72 }} labelAt="bl" />
      <HookWords />
    </AbsoluteFill>
  );
}
