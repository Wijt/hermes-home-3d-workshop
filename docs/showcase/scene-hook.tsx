// Preview root for scene 1 alone: raea render scene-hook.tsx --at 15,90 -o stills/hook/ ; raea check scene-hook.tsx --quick
// Generated; do not put scene code here (edit scenes/1-hook.tsx).
import { Composition, registerRoot } from "raea";
import Scene, { DURATION } from "./scenes/1-hook";

registerRoot(() => <Composition id="scene-hook" component={Scene} width={1920} height={1080} fps={30} durationInFrames={DURATION} />);
