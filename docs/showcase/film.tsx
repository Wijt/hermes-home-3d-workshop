// film: the whole showcase, 88 s at 1920 x 1080, 30 fps, silent (no Audio anywhere, so the render has no sound).
// Each scene lives in scenes/N-id.tsx; its times come from SCENES in components/timing.ts. Scenes after the first
// start XFADE frames early and fade in over the join (a crossfade), so the cut never shows a hard edge.
import { AbsoluteFill, Composition, Sequence, registerRoot, useCurrentFrame } from "raea";
import { FILM_FRAMES, SCENES, XFADE, ramp, s, sceneFrames, type SceneId } from "./components/timing";
import { C } from "./theme";
import Hook from "./scenes/1-hook";
import Ask from "./scenes/2-ask";
import Backroom from "./scenes/3-backroom";
import Watch from "./scenes/4-watch";
import Delivery from "./scenes/5-delivery";
import Twist from "./scenes/6-twist";
import Group from "./scenes/7-group";
import Close from "./scenes/8-close";

const PARTS: Record<SceneId, () => JSX.Element> = { hook: Hook, ask: Ask, backroom: Backroom, watch: Watch, delivery: Delivery, twist: Twist, group: Group, close: Close };

function FadeIn({ frames, children }: { frames: number; children: React.ReactNode }) {
  const f = useCurrentFrame();
  return <AbsoluteFill style={{ opacity: frames > 0 ? ramp(f, 0, frames) : 1 }}>{children}</AbsoluteFill>;
}

function Film() {
  return (
    <AbsoluteFill style={{ background: C.paper }}>
      {SCENES.map((sc, i) => {
        const lead = i === 0 ? 0 : XFADE;
        const Part = PARTS[sc.id];
        return (
          <Sequence key={sc.id} from={s(sc.from) - lead} durationInFrames={sceneFrames(sc.id)} name={sc.id}>
            <FadeIn frames={lead}>
              <Part />
            </FadeIn>
          </Sequence>
        );
      })}
    </AbsoluteFill>
  );
}

registerRoot(() => <Composition id="film" component={Film} width={1920} height={1080} fps={30} durationInFrames={FILM_FRAMES} />);
