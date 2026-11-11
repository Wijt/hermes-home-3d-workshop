import { Composition, Sequence, registerRoot } from "raea";
import Hook, { DURATION as H } from "./scenes/1-hook";
import Ask, { DURATION as A } from "./scenes/2-ask";
import Close, { DURATION as X } from "./scenes/8-close";

registerRoot(() => (
  <Composition id="preview" width={1920} height={1080} fps={30} durationInFrames={H + A + X} component={() => (
    <>
      <Sequence from={0} durationInFrames={H}><Hook /></Sequence>
      <Sequence from={H} durationInFrames={A}><Ask /></Sequence>
      <Sequence from={H + A} durationInFrames={X}><Close /></Sequence>
    </>
  )} />
));
