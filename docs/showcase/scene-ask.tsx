// Preview root for scene 2 alone: raea render scene-ask.tsx --at 15,90 -o stills/ask/ ; raea check scene-ask.tsx --quick
// Generated; do not put scene code here (edit scenes/2-ask.tsx).
import { Composition, registerRoot } from "raea";
import Scene, { DURATION } from "./scenes/2-ask";

registerRoot(() => <Composition id="scene-ask" component={Scene} width={1920} height={1080} fps={30} durationInFrames={DURATION} />);
