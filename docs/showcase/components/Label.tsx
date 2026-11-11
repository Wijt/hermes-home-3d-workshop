// Label: the small honesty chip. Every re-created chat, real photo and Workshop capture carries one.
import { useCurrentFrame } from "raea";
import { C, FONT, LABELS, LH, R, SAFE, SIZE, W, type LabelKind } from "../theme";
import { Bubble, Camera, WindowIcon } from "./Icons";
import { inOut } from "./timing";

export type Corner = "tl" | "tr" | "bl" | "br";

export type LabelProps = {
  /** which honesty line: "chat" | "photo" | "screen" (the exact strings live in theme.ts LABELS) */
  kind: LabelKind;
  /** override the text (rarely; the three standard lines are the rule) */
  text?: string;
  /** corner of the frame: "tl" (default) | "tr" | "bl" | "br" */
  at?: Corner;
  /** "dark" chip with light text (default, for photos) | "light" chip with ink text (for paper grounds) */
  tone?: "dark" | "light";
  /** local frame it fades in (default 0) and out (default never) */
  from?: number;
  to?: number;
  /** extra style on the outer box, e.g. a different position */
  style?: React.CSSProperties;
};

const ICON = { chat: Bubble, photo: Camera, screen: WindowIcon } as const;

export function Label({ kind, text, at = "tl", tone = "dark", from = 0, to, style }: LabelProps) {
  const f = useCurrentFrame();
  const o = inOut(f, from, to, 8, 6);
  const dark = tone === "dark";
  const Icon = ICON[kind];
  const pos: React.CSSProperties = {
    position: "absolute",
    ...(at[0] === "t" ? { top: SAFE.top } : { bottom: SAFE.bottom }),
    ...(at[1] === "l" ? { left: SAFE.minSide + 12 } : { right: SAFE.minSide + 12 }),
  };
  return (
    <div style={{ ...pos, opacity: o, ...style }}>
      <div
        style={{
          boxSizing: "border-box", display: "flex", flexDirection: "row", alignItems: "center", gap: 12,
          padding: "10px 22px 10px 16px", borderRadius: R.chip,
          background: dark ? "rgba(30,25,21,0.78)" : "rgba(255,252,247,0.92)",
          border: dark ? "none" : `2px solid ${C.line}`,
          color: dark ? C.onNight : C.ink,
        }}
      >
        <Icon size={30} color={dark ? C.onNight : C.inkSoft} />
        <div style={{ fontFamily: FONT.sans, fontWeight: W.regular, fontSize: SIZE.label, lineHeight: LH.label, whiteSpace: "nowrap" }}>
          {text ?? LABELS[kind]}
        </div>
      </div>
    </div>
  );
}
