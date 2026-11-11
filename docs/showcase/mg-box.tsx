import { Composition, registerRoot } from "raea";
import Scene, { DURATION } from "./mg/scenes/box";
registerRoot(() => <Composition id="box" component={Scene} width={1920} height={1080} fps={30} durationInFrames={DURATION} />);
