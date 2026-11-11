import { Composition, Sequence, registerRoot } from "raea";
import BackRoom, { DURATION as B } from "./scenes/3-backroom";
import Watch, { DURATION as W } from "./scenes/4-watch";

registerRoot(() => (
  <Composition id="preview-bw" width={1920} height={1080} fps={30} durationInFrames={B + W} component={() => (
    <>
      <Sequence from={0} durationInFrames={B}><BackRoom /></Sequence>
      <Sequence from={B} durationInFrames={W}><Watch /></Sequence>
    </>
  )} />
));
