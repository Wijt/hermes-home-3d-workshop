// Preview root for scene 6 alone: raea render scene-twist.tsx --at 15,90 -o stills/twist/ ; raea check scene-twist.tsx --quick
// Generated; do not put scene code here (edit scenes/6-twist.tsx).
import { Composition, registerRoot } from "raea";
import Scene, { DURATION } from "./scenes/6-twist";

registerRoot(() => <Composition id="scene-twist" component={Scene} width={1920} height={1080} fps={30} durationInFrames={DURATION} />);
