// Look test for the motion-graphics kit: one frame of each idea. Not part of the film.
import { AbsoluteFill, Composition, registerRoot, useCurrentFrame } from "raea";
import { Bubble, Chip, Iso, Label, Line, Nozzle, P, Stage, T, Words, boxSlabs, nozzleAt, plateSlabs, tagSlabs, type View } from "./mg/kit";

function Look() {
  const f = useCurrentFrame();
  const printed = Math.min(1, f / 80);
  const view: View = { cx: 1290, cy: 640, scale: 1.9, yaw: -0.5 + f * 0.004, pitch: 0.56 };
  const slabs = [...plateSlabs({ shadow: { x: 8, y: 10, w: 250, h: 112 } }), ...tagSlabs({ printed }), ...boxSlabs({ x: 520, y: 0, z: -34 })];
  return (
    <Stage frames={120}>
      <Iso view={view} slabs={slabs}>
        {printed < 1 && <Nozzle view={view} at={nozzleAt(printed, f)} />}
      </Iso>
      <div style={{ position: "absolute", left: 110, top: 120 }}>
        <Bubble text="Mıstık, can you make me a key tag with MUM on it? Red please." who="Mum" group="Family" at={0} width={820} />
      </div>
      <div style={{ position: "absolute", left: 110, top: 560 }}>
        <Words text="Ask. It's in the box." at={6} size={T.display} width={820} />
        <Line at={20} style={{ marginTop: 26 }}>Layer {Math.floor(printed * 21)} of 21</Line>
        <Chip at={24} mono style={{ marginTop: 26 }}>home3d_design</Chip>
      </div>
      <Label kind="chat" at={10} />
    </Stage>
  );
}

registerRoot(() => <Composition id="look" component={Look} width={1920} height={1080} fps={30} durationInFrames={120} />);
