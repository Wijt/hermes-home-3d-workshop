// test-components: every shared 2D component on screen once, for `raea check --quick` and stills.
// Not part of the film. 3D has its own root: test-turntable.tsx.
// Segments (frames): 0 photo+bigwords, 90 chat, 330 screen (image), 450 screen (placeholder), 540 caption+label on paper,
// 630 end card, 750 lab chat (me = right side, scrolling). The test plan text is placeholder copy, not a storyboard line.
import { AbsoluteFill, Composition, Sequence, registerRoot } from "raea";
import { BigWords, Caption, Chat, EndCard, Label, PhotoStage, ScreenStage, s, type ChatMessage } from "./components";
import { C } from "./theme";

const ASK: ChatMessage[] = [
  {
    from: "Mum", at: 10, kind: "voice", duration: "0:05", play: 50,
    transcript: { original: "Mıstık, bana bir gül kutusu yapar mısın?", english: "Mıstık, can you make me a rose box?", at: 40 },
  },
  { from: "Mıstık", at: 110, typing: 24, kind: "image", image: "real/rose-box-slicer-render.png", imageWidth: 420, text: "Like this, Mum?" },
  { from: "Mum", at: 160, text: "Yes!", icon: "heart" },
  { from: "Mıstık", at: 200, typing: 18, text: "I've asked the owner to approve it." },
];

const LAB: ChatMessage[] = [
  { from: "Engineer", at: 5, text: "Need a bracket for the sensor rail: 40 mm wide, two M3 holes." },
  { from: "Mıstık", at: 50, typing: 20, text: "Plan:\n1. L-bracket, 40 mm wide\n2. Two M3 holes, 20 mm apart\n3. PETG, flat on the bed" },
  { from: "Owner", at: 110, text: "Looks right.", icon: "check" },
];

function Test() {
  return (
    <AbsoluteFill style={{ background: C.paper }}>
      <Sequence from={0} durationInFrames={90} name="photo">
        <PhotoStage file="real/rose-box-on-bed.jpg" frames={90} focus={{ x: 0.42, y: 0.66 }} />
        <BigWords lines="My mother has never opened a slicer." from={6} />
      </Sequence>
      <Sequence from={90} durationInFrames={240} name="chat">
        <Chat title="Family" subtitle="Mum, Dad, Sam, Mıstık" messages={ASK} />
        <Caption text={"She asks.\nNo app, no slicer."} place="right" from={150} look="ink" />
      </Sequence>
      <Sequence from={330} durationInFrames={120} name="screen-image">
        <ScreenStage
          file="real/latticed-box-on-tilted-bed.jpg"
          pointer={[{ at: 10, x: 300, y: 900 }, { at: 50, x: 700, y: 640 }]}
          clicks={[60]}
          zoom={[{ at: 0, x: 768, y: 540, scale: 1 }, { at: 70, x: 700, y: 640, scale: 1.4 }]}
        />
        <Caption text="The agent prepares everything. A person presses Start." from={20} />
      </Sequence>
      <Sequence from={450} durationInFrames={90} name="screen-placeholder">
        <ScreenStage file="screen/waiting-for-you.png" pointer={[{ at: 10, x: 400, y: 300 }, { at: 40, x: 1400, y: 800 }]} clicks={[50]} />
        <Caption text="Watched by the plugin. Zero model calls." from={10} />
      </Sequence>
      <Sequence from={540} durationInFrames={90} name="paper-words">
        <BigWords lines={["It kept needing a human", "to clear the plate."]} over="paper" position="center" accent="a human" />
        <Label kind="photo" at="br" tone="light" />
      </Sequence>
      <Sequence from={750} durationInFrames={150} name="lab-chat">
        <Chat title="R&D lab" subtitle="Engineer, Owner, Mıstık" group="lab" me="Engineer" messages={LAB} />
        <Caption text="Same plugin. My R&D lab asked for one." place="right" look="ink" from={70} />
      </Sequence>
      <Sequence from={630} durationInFrames={s(4)} name="end">
        <EndCard line="Ask. It’s in the box." name="home-3d-workshop" sub="a Hermes Agent plugin" url="github.com/Wijt/hermes-home-3d-workshop" nameAt={30} />
      </Sequence>
    </AbsoluteFill>
  );
}

registerRoot(() => <Composition id="test-components" component={Test} width={1920} height={1080} fps={30} durationInFrames={900} />);
