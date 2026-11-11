// final: the whole showcase, for when the owner has shot real footage.
// Same 88 s, same timing, same crossfades, same captions as fallback.tsx. For each beat, if its clip is in
// media/footage/ (and tools/scan_media.py has been run) the clip replaces the fallback visual; otherwise the
// fallback visual stays. No code edits are needed: see "Real footage" in README.md.
// Clips are cover-fitted and cut to the beat. Only clip 02 (the voice note) keeps its sound; the rest are muted.
import { AbsoluteFill, Composition, Sequence, registerRoot, useCurrentFrame } from "raea";
import { Caption, EndCard, Footage, Label, ramp, s, sceneFrames, FILM_FRAMES, SCENES, XFADE, hasClip, type SceneId } from "./components";
import { C } from "./theme";
import Hook, { HookWords } from "./scenes/1-hook";
import Ask from "./scenes/2-ask";
import Backroom from "./scenes/3-backroom";
import Watch from "./scenes/4-watch";
import Delivery, { ChatBeat, PushBeat } from "./scenes/Delivery";
import Twist, { SCREEN_AT, ScreenBeat, TwistWords } from "./scenes/Twist";
import Group from "./scenes/7-group";
import Close from "./scenes/8-close";

/** Clip 03 is a screen recording of the Workshop screen. It keeps the "simulated printer" chip unless it was shot on
 *  the real printer: then set this to false (see README.md). */
const LABEL_CLIP_03_AS_SIMULATED = true;

function FadeIn({ frames, children }: { frames: number; children: React.ReactNode }) {
  const f = useCurrentFrame();
  return <AbsoluteFill style={{ opacity: frames > 0 ? ramp(f, 0, frames) : 1 }}>{children}</AbsoluteFill>;
}

// 1 Hook: clip 01 under the two lines.
function HookBeat() {
  if (!hasClip("hook")) return <Hook />;
  return (
    <AbsoluteFill>
      <Footage clip="hook" frames={sceneFrames("hook")} dim={0.18} />
      <HookWords />
    </AbsoluteFill>
  );
}

// 2 Ask: clip 02 with its own sound, the line subtitled in English, then the caption.
function AskBeat() {
  if (!hasClip("ask")) return <Ask />;
  return (
    <AbsoluteFill>
      <Footage clip="ask" frames={sceneFrames("ask")} sound fadeIn={XFADE} />
      <Caption text="Mıstık, bana bir gül kutusu yapar mısın?" place="top" size={40} from={40} to={200} />
      <Caption text="Mıstık, can you make me a rose box?" from={40} to={200} />
      <Caption text="She asks. No app, no slicer." from={245} />
    </AbsoluteFill>
  );
}

// 3 Back room: clip 03, same two captions.
function BackroomBeat() {
  if (!hasClip("backroom")) return <Backroom />;
  const split = s(8.2);
  return (
    <AbsoluteFill>
      <Footage clip="backroom" frames={sceneFrames("backroom")} />
      {LABEL_CLIP_03_AS_SIMULATED && <Label kind="screen" at="tl" tone="light" from={4} />}
      <Caption text="The agent prepares everything." from={26} to={split} />
      <Caption text="A person presses Start." from={split} />
    </AbsoluteFill>
  );
}

// 4 Watch: clip 04, same two captions.
function WatchBeat() {
  if (!hasClip("watch")) return <Watch />;
  const split = s(6.3);
  return (
    <AbsoluteFill>
      <Footage clip="watch" frames={sceneFrames("watch")} />
      <Caption text="Watched by the plugin." from={26} to={split} />
      <Caption text="Zero model calls." from={split} />
    </AbsoluteFill>
  );
}

// 5 Delivery: clip 05 replaces the two photos (frames 0..220), clip 06 replaces the chat (frame 208 on).
function DeliveryBeat() {
  if (!hasClip("push") && !hasClip("message")) return <Delivery />;
  const D = sceneFrames("delivery");
  return (
    <AbsoluteFill style={{ background: C.night }}>
      {hasClip("push") ? (
        <Sequence from={0} durationInFrames={220}>
          <Footage clip="push" frames={220} />
          <Caption text="Pushed into the done box." from={30} />
        </Sequence>
      ) : (
        <PushBeat />
      )}
      <Sequence from={208} durationInFrames={D - 208}>
        {hasClip("message") ? (
          <AbsoluteFill>
            <Footage clip="message" frames={D - 208} fadeIn={12} />
            <Caption text="The person who asked is told." from={40} />
          </AbsoluteFill>
        ) : (
          <ChatBeat />
        )}
      </Sequence>
    </AbsoluteFill>
  );
}

// 6 Twist: clip 07 under the two lines; the Workshop capture beat stays.
function TwistBeat() {
  if (!hasClip("tilted")) return <Twist />;
  const D = sceneFrames("twist");
  return (
    <AbsoluteFill style={{ background: C.night }}>
      <Sequence from={0} durationInFrames={SCREEN_AT + 12}>
        <Footage clip="tilted" frames={SCREEN_AT + 12} dim={0.3} />
        <TwistWords />
      </Sequence>
      <Sequence from={SCREEN_AT} durationInFrames={D - SCREEN_AT}>
        <ScreenBeat />
      </Sequence>
    </AbsoluteFill>
  );
}

// 7 Group: clip 08 with the caption.
function GroupBeat() {
  if (!hasClip("lab")) return <Group />;
  return (
    <AbsoluteFill>
      <Footage clip="lab" frames={sceneFrames("group")} />
      <Caption text="Same plugin. My R&D lab asked for one." from={60} />
    </AbsoluteFill>
  );
}

// 8 Close: clip 09 plays for the first 2.5 s under the line, then the end card (same words, held at least 3.5 s).
const OBJECTS_FRAMES = 75;
function CloseBeat() {
  if (!hasClip("objects")) return <Close />;
  const D = sceneFrames("close");
  return (
    <AbsoluteFill>
      <Sequence from={0} durationInFrames={OBJECTS_FRAMES + 10}>
        <Footage clip="objects" frames={OBJECTS_FRAMES + 10} dim={0.3} />
      </Sequence>
      <Sequence from={OBJECTS_FRAMES} durationInFrames={D - OBJECTS_FRAMES}>
        <FadeIn frames={10}>
          <EndCard line="Ask. It’s in the box." name="home-3d-workshop" sub="a Hermes Agent plugin" url="github.com/Wijt/hermes-home-3d-workshop" nameAt={40} ground="paper" />
        </FadeIn>
      </Sequence>
    </AbsoluteFill>
  );
}

const PARTS: Record<SceneId, () => JSX.Element> = { hook: HookBeat, ask: AskBeat, backroom: BackroomBeat, watch: WatchBeat, delivery: DeliveryBeat, twist: TwistBeat, group: GroupBeat, close: CloseBeat };

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

registerRoot(() => <Composition id="final" component={Film} width={1920} height={1080} fps={30} durationInFrames={FILM_FRAMES} />);
