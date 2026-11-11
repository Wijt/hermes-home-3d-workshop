// Preview root for scene 3 alone: raea render scene-backroom.tsx --at 15,90 -o stills/backroom/ ; raea check scene-backroom.tsx --quick
// Generated; do not put scene code here (edit scenes/3-backroom.tsx).
import { Composition, registerRoot } from "raea";
import Scene, { DURATION } from "./scenes/3-backroom";

registerRoot(() => <Composition id="scene-backroom" component={Scene} width={1920} height={1080} fps={30} durationInFrames={DURATION} />);
