// Preview root for the "approve" scene of the motion-graphics film.
import { Composition, registerRoot } from "raea";
import Scene, { DURATION } from "./mg/scenes/approve";

registerRoot(() => <Composition id="approve" component={Scene} width={1920} height={1080} fps={30} durationInFrames={DURATION} />);
