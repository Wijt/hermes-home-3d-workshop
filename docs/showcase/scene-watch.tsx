// Preview root for scene 4 alone: raea render scene-watch.tsx --at 15,90 -o stills/watch/ ; raea check scene-watch.tsx --quick
// Generated; do not put scene code here (edit scenes/4-watch.tsx).
import { Composition, registerRoot } from "raea";
import Scene, { DURATION } from "./scenes/4-watch";

registerRoot(() => <Composition id="scene-watch" component={Scene} width={1920} height={1080} fps={30} durationInFrames={DURATION} />);
