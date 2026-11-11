// Scene 7, Another group (1:06 to 1:16): a words-only card. The lab exchange is not shown: nothing here may suggest
// a chat that was not captured. No chat label, no picture. (Re-create it only if the exchange really happened and
// the lab agrees; then use the engineer's real words, names changed, and the plugin's own render.)
import { AbsoluteFill } from "raea";
import { BigWords, Caption, sceneFrames } from "../components";

export const DURATION = sceneFrames("group");

export default function SceneLab() {
  return (
    <AbsoluteFill>
      <BigWords lines={["Same plugin.", "A second group."]} over="paper" position="center" size="display" lineDelay={36} from={10} to={DURATION - 12} />
      <Caption text="My manager asked for one for an R&D lab." place="bottom" from={120} to={DURATION - 12} />
    </AbsoluteFill>
  );
}
