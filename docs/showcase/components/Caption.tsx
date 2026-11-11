// Caption: the burned-in line that carries the argument for a muted viewer.
// A dark plate with light sans text, rising in and fading out. "\n" in the text forces a line break (break by
// sense, one idea per line). A line too long for the box is split in two at the space nearest its middle, so no
// single word is left alone on a last line.
import { interpolate, useCurrentFrame } from "raea";
import { C, FONT, LH, R, SAFE, SIZE, W } from "../theme";
import { IN, OUT, clamp, inOut, ramp } from "./timing";

export type CaptionPlace = "bottom" | "top" | "right" | "left";

export type CaptionProps = {
  text: string;
  /** local frame it starts entering (default 0) */
  from?: number;
  /** local frame it is fully gone (default: stays) */
  to?: number;
  /**
   * where it sits:
   * "bottom" (default): centred, its bottom edge on the safe line (120 px up), max 1500 wide
   * "top": centred, top edge 120 px down, max 1500 wide
   * "right": the column x 1120..1840, vertically centred (beside a Chat phone on the left)
   * "left": the column x 120..840, vertically centred (beside something on the right)
   */
  place?: CaptionPlace;
  /** text alignment: centre for bottom/top, left for the side columns, unless given */
  align?: "left" | "center";
  /** font size, default SIZE.caption (64). Do not go under 60. */
  size?: number;
  /** "plate" (default): light text on a dark plate, works over anything | "ink": ink text, no plate, for paper grounds */
  look?: "plate" | "ink";
  /** override the box: any of left, top, bottom, width (px) */
  box?: { left?: number; top?: number; bottom?: number; width?: number };
};

const PLACES: Record<CaptionPlace, React.CSSProperties & { width: number }> = {
  bottom: { left: 210, width: 1500, bottom: SAFE.bottom, alignItems: "center" },
  top: { left: 210, width: 1500, top: SAFE.top, alignItems: "center" },
  right: { left: 1120, width: 720, top: 0, bottom: 0, justifyContent: "center", alignItems: "flex-start" },
  left: { left: SAFE.side, width: 720, top: 0, bottom: 0, justifyContent: "center", alignItems: "flex-start" },
};

/** DejaVu Sans Bold averages about 0.63 em a character; 0.66 leaves room for wide letters. */
const CHAR = 0.66;

/**
 * Break each too-long line into the fewest lines that fit, of even length, preferring breaks after punctuation
 * ("No app, | no slicer." rather than "No app, no | slicer."), so no word is left alone on a line.
 */
export function balance(text: string, size: number, width: number) {
  const max = Math.max(1, Math.floor(width / (size * CHAR)));
  return text
    .split("\n")
    .map((line) => {
      if (line.length <= max) return line;
      const words = line.split(" ");
      // try n lines, n = 2, 3, ...: choose breaks by dynamic programming on the cost (longest line, punctuation bonus)
      for (let n = Math.ceil(line.length / max); n <= words.length; n++) {
        const best = split(words, n, max);
        if (best) return best.join("\n");
      }
      return line;
    })
    .join("\n");
}

/** Best split of words into exactly n lines each at most max chars; null when impossible. */
function split(words: string[], n: number, max: number): string[] | null {
  const W = words.length;
  const len = (a: number, b: number) => words.slice(a, b).join(" ").length;
  const memo = new Map<string, { cost: number; lines: string[] } | null>();
  const go = (start: number, left: number): { cost: number; lines: string[] } | null => {
    const key = `${start},${left}`;
    if (memo.has(key)) return memo.get(key)!;
    let res: { cost: number; lines: string[] } | null = null;
    if (left === 1) {
      const l = len(start, W);
      res = l <= max ? { cost: l, lines: [words.slice(start).join(" ")] } : null;
    } else {
      for (let end = start + 1; end <= W - left + 1; end++) {
        const l = len(start, end);
        if (l > max) break;
        const rest = go(end, left - 1);
        if (!rest) continue;
        const bonus = /[,.;:!?]$/.test(words[end - 1]) ? 4 : 0;
        const cost = Math.max(l - bonus, rest.cost);
        if (!res || cost < res.cost) res = { cost, lines: [words.slice(start, end).join(" "), ...rest.lines] };
      }
    }
    memo.set(key, res);
    return res;
  };
  return go(0, n)?.lines ?? null;
}

export function Caption({ text, from = 0, to, place = "bottom", align, size = SIZE.caption, look = "plate", box }: CaptionProps) {
  const f = useCurrentFrame();
  const o = inOut(f, from, to, 10, 8);
  const y = interpolate(ramp(f, from, from + 12, OUT), [0, 1], [22, 0], clamp) + (to !== undefined ? 8 * ramp(f, to - 8, to, IN) : 0);
  const side = place === "left" || place === "right";
  const textAlign = align ?? (side ? "left" : "center");
  const plate = look === "plate";
  const width = box?.width ?? PLACES[place].width;
  const shown = balance(text, size, width - (plate ? 80 : 0));
  return (
    <div
      style={{
        position: "absolute", display: "flex", flexDirection: "column",
        ...PLACES[place], ...box,
        opacity: o, transform: `translateY(${y}px)`,
      }}
    >
      <div
        style={{
          boxSizing: "border-box", maxWidth: "100%",
          padding: plate ? "22px 40px 26px" : 0, borderRadius: R.card,
          background: plate ? "rgba(30,25,21,0.86)" : "transparent",
          fontFamily: FONT.sans, fontWeight: W.bold, fontSize: size, lineHeight: LH.caption,
          color: plate ? C.onNight : C.ink, textAlign, whiteSpace: "pre-line",
        }}
      >
        {shown}
      </div>
    </div>
  );
}
