// The motion-graphics film: nine scenes cut together, 79 s at 1920 x 1080, 30 fps. The board is mg/BOARD.md.
// Each scene draws the whole frame and knows its own length; scenes are cut with no crossfade (each one ends on
// the picture the next one starts on, or on a move).
import { AbsoluteFill, Composition, Series, registerRoot } from "raea";
import { P } from "./mg/kit";
import Ask, { DURATION as ASK } from "./mg/scenes/ask";
import Title, { DURATION as TITLE } from "./mg/scenes/title";
import Make, { DURATION as MAKE } from "./mg/scenes/make";
import Approve, { DURATION as APPROVE } from "./mg/scenes/approve";
import Print, { DURATION as PRINT } from "./mg/scenes/print";
import Box, { DURATION as BOX } from "./mg/scenes/box";
import Twist, { DURATION as TWIST } from "./mg/scenes/twist";
import Groups, { DURATION as GROUPS } from "./mg/scenes/groups";
import Close, { DURATION as CLOSE } from "./mg/scenes/close";

const SCENES = [
  { id: "ask", C: Ask, d: ASK },
  { id: "title", C: Title, d: TITLE },
  { id: "make", C: Make, d: MAKE },
  { id: "approve", C: Approve, d: APPROVE },
  { id: "print", C: Print, d: PRINT },
  { id: "box", C: Box, d: BOX },
  { id: "twist", C: Twist, d: TWIST },
  { id: "groups", C: Groups, d: GROUPS },
  { id: "close", C: Close, d: CLOSE },
] as const;

export const FILM_FRAMES = SCENES.reduce((n, sc) => n + sc.d, 0);

function Film() {
  return (
    <AbsoluteFill style={{ background: P.ink }}>
      <Series>
        {SCENES.map((sc) => (
          <Series.Sequence key={sc.id} durationInFrames={sc.d} name={sc.id}>
            <sc.C />
          </Series.Sequence>
        ))}
      </Series>
    </AbsoluteFill>
  );
}

registerRoot(() => <Composition id="film" component={Film} width={1920} height={1080} fps={30} durationInFrames={FILM_FRAMES} />);
