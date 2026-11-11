// Preview root for scene 7 alone: raea render scene-group.tsx --at 15,90 -o stills/group/ ; raea check scene-group.tsx --quick
// Generated; do not put scene code here (edit scenes/7-group.tsx).
import { Composition, registerRoot } from "raea";
import Scene, { DURATION } from "./scenes/7-group";

registerRoot(() => <Composition id="scene-group" component={Scene} width={1920} height={1080} fps={30} durationInFrames={DURATION} />);
