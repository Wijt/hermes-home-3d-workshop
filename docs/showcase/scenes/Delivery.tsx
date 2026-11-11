// Scene 5, The delivery (0:37.5 to 0:50.5): the part on the tilted bed, the empty bed after the push, then the chat message.
// Local frame 0 is 10 frames before the scene's start, so nothing to read before frame 10.
import { AbsoluteFill, Sequence, useCurrentFrame } from "raea";
import { Caption, Chat, Label, PhotoStage, ramp, sceneFrames } from "../components";
import { INOUT } from "../components/timing";

export const DURATION = sceneFrames("delivery");

/** The side the new photo wipes in from. The part slides off the bed toward this side's opposite edge, so the wipe
 *  travels with it. UNCONFIRMED against the real push: flip to "left" if the part leaves toward the left. */
const WIPE_FROM: "right" | "left" = "right";
const WIPE = 10;

export function ChatBeat() {
  const f = useCurrentFrame();
  return (
    <AbsoluteFill style={{ opacity: ramp(f, 0, 12) }}>
      <Chat
        title="Family"
        subtitle="Mum, Dad, Sam, Mıstık"
        messages={[
          {
            from: "Mıstık", at: 24, typing: 18, kind: "image", image: "real/rose-and-ring-on-bed.jpg", imageWidth: 500,
            text: "Your rose box is ready, Mum. Just printed.",
          },
        ]}
      />
      <Label kind="photo" at="tr" tone="light" from={30} />
      <Caption text="The person who asked is told." place="right" look="ink" from={60} to={DURATION - 208 - 2} />
    </AbsoluteFill>
  );
}

function Wipe({ children }: { children: React.ReactNode }) {
  const f = useCurrentFrame();
  const t = ramp(f, 0, WIPE, INOUT);
  const hide = 100 * (1 - t);
  return <AbsoluteFill style={{ clipPath: WIPE_FROM === "right" ? `inset(0 0 0 ${hide}%)` : `inset(0 ${hide}% 0 0)` }}>{children}</AbsoluteFill>;
}

/** The push: the two photos with their captions (local frames 0 to 220). final.tsx swaps clip 05 in for it. */
export function PushBeat() {
  return (
    <>
      <Sequence from={0} durationInFrames={125}>
        <PhotoStage file="real/latticed-box-on-tilted-bed.jpg" frames={125} move="push" zoom={[1.9, 2.0]} focus={{ x: 0.55, y: 1.0 }} labelAt="bl" />
        <Caption text="Printed. Nobody touched the printer." place="right" from={20} to={112} />
      </Sequence>
      <Sequence from={110} durationInFrames={110}>
        <Wipe>
          <PhotoStage file="real/empty-bed-after-push.jpg" frames={110} move="push" zoom={[1.2, 1.3]} focus={{ x: 0.15, y: 0.7 }} labelAt="tl" />
          <Caption text="Pushed into the done box." from={30} />
        </Wipe>
      </Sequence>
    </>
  );
}

export default function SceneDelivery() {
  return (
    <AbsoluteFill style={{ background: "#1E1915" }}>
      <PushBeat />
      <Sequence from={208} durationInFrames={DURATION - 208}>
        <ChatBeat />
      </Sequence>
    </AbsoluteFill>
  );
}
