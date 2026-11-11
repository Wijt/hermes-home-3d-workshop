// Preview root for scene 8 alone: raea render scene-close.tsx --at 15,90 -o stills/close/ ; raea check scene-close.tsx --quick
// Generated; do not put scene code here (edit scenes/8-close.tsx).
import { Composition, registerRoot } from "raea";
import Scene, { DURATION } from "./scenes/8-close";

registerRoot(() => <Composition id="scene-close" component={Scene} width={1920} height={1080} fps={30} durationInFrames={DURATION} />);
