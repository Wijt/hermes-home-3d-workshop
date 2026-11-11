// Scene 8, Close (1:16 to 1:26): the line, then the plugin's name and address. Holds the full card for about 8 s, drifting slightly.
import { EndCard, sceneFrames } from "../components";

export const DURATION = sceneFrames("close");

export default function SceneClose() {
  return <EndCard line="Ask. It’s in the box." name="home-3d-workshop" sub="a Hermes Agent plugin" url="github.com/Wijt/hermes-home-3d-workshop" nameAt={60} driftEnd={DURATION} ground="paper" />;
}
