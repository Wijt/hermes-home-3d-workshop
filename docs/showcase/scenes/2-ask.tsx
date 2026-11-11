// Scene 2, The ask (0:05.5 to 0:18.5): Mum's voice note, Mıstık's picture, the approval request.
import { AbsoluteFill } from "raea";
import { Caption, Chat, sceneFrames } from "../components";

export const DURATION = sceneFrames("ask");

export default function SceneAsk() {
  return (
    <AbsoluteFill>
      <Chat
        title="Family"
        subtitle="Mum, Dad, Sam, Mıstık"
        messages={[
          { from: "Mum", at: 22, kind: "voice", duration: "0:05", play: 50, transcript: { original: "Mıstık, bana bir gül kutusu yapar mısın?", english: "Mıstık, can you make me a rose box?", at: 56 } },
          { from: "Mıstık", at: 205, typing: 24, kind: "image", image: "real/rose-box-slicer-render.png", imageWidth: 420, text: "Like this, Mum?" },
          { from: "Mum", at: 285, text: "Yes!", icon: "heart" },
          { from: "Mıstık", at: 330, typing: 18, text: "I've asked the owner to approve it." },
        ]}
      />
      <Caption text="Mıstık is an agent in the family chat." place="right" look="ink" from={70} to={235} />
      <Caption text="It runs the 3D printer. No app, no slicer." place="right" look="ink" from={245} to={DURATION - 2} />
    </AbsoluteFill>
  );
}
