// The film's look, in one place. Every component and scene takes its colours, faces, sizes and margins from here.
//
// Direction: warm, real, slightly handmade. A family and a machine in a lit room, not a dark tech demo.
// Paper and ink, with one red that is the red of the filament in the real photos. Serif for the story's voice
// (big words, the end card), sans for what is read off a screen (captions, chat, labels).
//
// Frame: 1920 x 1080, 30 fps. Sizes follow raea's floor: text that must be read is at least 60 px on the
// 1080 px side, small print at least 32 px, contrast at least 3:1 against what is behind each glyph.

export const FRAME = { width: 1920, height: 1080, fps: 30 } as const;

/** Colours. Contrast on PAPER: INK 14:1, INK_SOFT 5.6:1, ROSE 5.4:1. PAPER on NIGHT 15:1. */
export const C = {
  /** the ground: warm off-white paper */
  paper: "#F4EDE2",
  /** a step darker: the chat screen, cards on paper */
  paperDeep: "#E9DFD0",
  /** a bubble or card that sits on paperDeep */
  card: "#FFFCF7",
  /** main text */
  ink: "#2B2420",
  /** secondary text (sender names, durations, small print on paper) */
  inkSoft: "#6B5E54",
  /** hairlines and frames */
  line: "#D3C6B4",
  /** the one accent: the red of the printed rose */
  rose: "#B5321F",
  /** the agent's bubble: a pale rose */
  roseSoft: "#F6DDD3",
  /** dark ground for scrims and the dark side of the film */
  night: "#1E1915",
  /** text on night */
  onNight: "#F7F1E8",
  /** a calm green for a done check mark only */
  leaf: "#4E6B45",
} as const;

/** Faces. Only DejaVu is installed: an unknown family silently becomes DejaVu Serif, so use these strings only. */
export const FONT = {
  /** the story's voice: BigWords, EndCard title. Weights 400 and 700 exist. */
  serif: "'DejaVu Serif', serif",
  /** what is read off a screen: Caption, Chat, Label. Weights 400 and 700 exist. */
  sans: "'DejaVu Sans', sans-serif",
  /** the repository address on the end card. Weights 400 and 700 exist. */
  mono: "'DejaVu Sans Mono', monospace",
} as const;

/** Weights that really exist in the installed faces. Anything else is synthesised. */
export const W = { regular: 400, bold: 700 } as const;

/** Type sizes in px for the 1920 x 1080 frame. */
export const SIZE = {
  /** BigWords, one short line */
  display: 112,
  /** BigWords, two lines or a longer line */
  title: 88,
  /** burned-in captions: the argument for a muted viewer */
  caption: 64,
  /** chat message text (inside the phone) */
  chat: 60,
  /** the Turkish original under a voice note, sender names, the phone header */
  chatSmall: 40,
  /** honesty labels and other small print: the floor is 32 */
  label: 32,
} as const;

/** Line heights. */
export const LH = { display: 1.02, title: 1.06, caption: 1.18, chat: 1.24, label: 1.2 } as const;

/** Safe margins (raea floor for 16:9: top and bottom 120, sides 60). We keep wider sides for a calmer frame. */
export const SAFE = { top: 120, bottom: 120, side: 120, minSide: 60 } as const;

/** Corner radii and spacing. */
export const R = { bubble: 34, card: 28, chip: 999, phone: 72, window: 22 } as const;
export const GAP = { xs: 8, s: 16, m: 28, l: 48, xl: 80 } as const;

/** Scrim gradients for type over photos. */
export const SCRIM = {
  bottom: "linear-gradient(180deg, rgba(30,25,21,0) 0%, rgba(30,25,21,0.55) 45%, rgba(30,25,21,0.82) 100%)",
  top: "linear-gradient(0deg, rgba(30,25,21,0) 0%, rgba(30,25,21,0.55) 45%, rgba(30,25,21,0.82) 100%)",
  full: "rgba(30,25,21,0.58)",
} as const;

/** Soft shadow for the phone and windows (separation, not decoration). */
export const SHADOW = "0 24px 60px rgba(43,36,32,0.22), 0 4px 14px rgba(43,36,32,0.12)";

/** The three honesty labels. Use these exact strings (Label's `kind` prop picks one). */
export const LABELS = {
  chat: "Re-created from real chats. Names changed.",
  photo: "Real photo from the printer's camera",
  screen: "Plugin running on its built-in simulated printer",
} as const;
export type LabelKind = keyof typeof LABELS;

/** People in the chats. Never a real name. Colours are for sender names only. */
export const PEOPLE = {
  Mum: { color: "#8A4B2E" },
  Dad: { color: "#3F5C6E" },
  Sam: { color: "#5E5A2A" },
  Owner: { color: "#4B4F6B" },
  Engineer: { color: "#3F5C6E" },
  "Mıstık": { color: C.rose },
} as const;
