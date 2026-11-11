import { Composition, registerRoot } from "raea";
import Scene, { DURATION } from "./mg/scenes/make";
registerRoot(() => <Composition id="make" component={Scene} width={1920} height={1080} fps={30} durationInFrames={DURATION} />);
