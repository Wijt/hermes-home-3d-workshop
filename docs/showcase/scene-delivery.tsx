// Preview root for scene 5 alone: raea render scene-delivery.tsx --at 15,90 -o stills/delivery/ ; raea check scene-delivery.tsx --quick
// Generated; do not put scene code here (edit scenes/5-delivery.tsx).
import { Composition, registerRoot } from "raea";
import Scene, { DURATION } from "./scenes/5-delivery";

registerRoot(() => <Composition id="scene-delivery" component={Scene} width={1920} height={1080} fps={30} durationInFrames={DURATION} />);
