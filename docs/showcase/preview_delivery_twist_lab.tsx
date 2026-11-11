import { Composition, Sequence, registerRoot } from "raea";
import Delivery, { DURATION as D1 } from "./scenes/Delivery";
import Twist, { DURATION as D2 } from "./scenes/Twist";
import Lab, { DURATION as D3 } from "./scenes/Lab";

function All() {
  return (
    <>
      <Sequence from={0} durationInFrames={D1}><Delivery /></Sequence>
      <Sequence from={D1} durationInFrames={D2}><Twist /></Sequence>
      <Sequence from={D1 + D2} durationInFrames={D3}><Lab /></Sequence>
    </>
  );
}
registerRoot(() => <Composition id="preview" component={All} width={1920} height={1080} fps={30} durationInFrames={D1 + D2 + D3} />);
