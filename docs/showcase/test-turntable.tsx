// test-turntable: PartTurntable with the MUM name tag, 2 s, with a caption over it. Not part of the film.
import { AbsoluteFill, Composition, registerRoot } from "raea";
import { Caption } from "./components";
import { PartTurntable } from "./components/PartTurntable";

function Test() {
  return (
    <AbsoluteFill>
      <PartTurntable offset={0} />
      <Caption text="A name tag that says MUM, from the plugin's template." from={4} />
    </AbsoluteFill>
  );
}

registerRoot(() => <Composition id="test-turntable" component={Test} width={1920} height={1080} fps={30} durationInFrames={60} />);
