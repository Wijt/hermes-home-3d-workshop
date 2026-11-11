// Small icons drawn as inline SVG (colour emoji may not render here). Each takes size (px) and color.
import { C } from "../theme";

type P = { size?: number; color?: string; style?: React.CSSProperties };

export function Heart({ size = 48, color = C.rose, style }: P) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" style={style}>
      <path d="M12 21s-7.5-4.6-9.6-9.3C.9 8.3 3 4.5 6.7 4.5c2.2 0 3.6 1.3 5.3 3.2 1.7-1.9 3.1-3.2 5.3-3.2 3.7 0 5.8 3.8 4.3 7.2C19.5 16.4 12 21 12 21z" fill={color} />
    </svg>
  );
}

export function Rose({ size = 48, color = C.rose, style }: P) {
  return (
    <svg width={size} height={size} viewBox="5 2.6 14 20" style={style}>
      <path d="M12 13.5v8" stroke={C.leaf} strokeWidth="1.8" strokeLinecap="round" fill="none" />
      <path d="M12 18c-2.6-.2-4.2-1.6-4.6-3.6 2.4-.2 4 .9 4.6 3.6z" fill={C.leaf} />
      <path d="M12 3.2c2.6 0 5.6 1.8 5.6 5.2 0 3.2-2.6 5.4-5.6 5.4S6.4 11.6 6.4 8.4c0-3.4 3-5.2 5.6-5.2z" fill={color} />
      <path d="M9.2 7.4c1.2-1.6 4.4-1.7 5.4.3.8 1.7-.6 3.4-2.4 3.3-1.4-.1-2.1-1.2-1.5-2.1" stroke="rgba(255,255,255,0.55)" strokeWidth="1.1" fill="none" strokeLinecap="round" />
    </svg>
  );
}

export function Check({ size = 48, color = C.leaf, style }: P) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" style={style}>
      <circle cx="12" cy="12" r="10.5" fill={color} />
      <path d="M7 12.4l3.2 3.2L17.2 8.6" stroke="#fff" strokeWidth="2.4" fill="none" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

/** A plain arrow pointer; its tip is at the top-left corner of the box. */
export function Pointer({ size = 56, color = C.ink, style }: P) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" style={style}>
      <path d="M2 1.5l15.5 11.2-6.9.9 4 7.7-3 1.5-4-7.7L2.6 19.6z" fill={color} stroke="#fff" strokeWidth="1.4" strokeLinejoin="round" />
    </svg>
  );
}

export function Camera({ size = 32, color = "currentColor", style }: P) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" style={style}>
      <path d="M3 7.5h4l1.6-2.5h6.8L17 7.5h4v12H3z" fill="none" stroke={color} strokeWidth="2" strokeLinejoin="round" />
      <circle cx="12" cy="13.2" r="3.6" fill="none" stroke={color} strokeWidth="2" />
    </svg>
  );
}

export function Bubble({ size = 32, color = "currentColor", style }: P) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" style={style}>
      <path d="M4 4.5h16v11H10l-4.5 4v-4H4z" fill="none" stroke={color} strokeWidth="2" strokeLinejoin="round" />
    </svg>
  );
}

export function WindowIcon({ size = 32, color = "currentColor", style }: P) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" style={style}>
      <rect x="3" y="4.5" width="18" height="15" rx="2" fill="none" stroke={color} strokeWidth="2" />
      <path d="M3 9h18" stroke={color} strokeWidth="2" />
    </svg>
  );
}

export function Home({ size = 40, color = "currentColor", style }: P) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" style={style}>
      <path d="M3.5 11.5L12 4l8.5 7.5M6 10v9.5h4.5v-5h3v5H18V10" fill="none" stroke={color} strokeWidth="2" strokeLinejoin="round" strokeLinecap="round" />
    </svg>
  );
}

export function Flask({ size = 40, color = "currentColor", style }: P) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" style={style}>
      <path d="M9 3.5h6M10 3.5v6L4.8 18.3c-.8 1.4.2 2.7 1.7 2.7h11c1.5 0 2.5-1.3 1.7-2.7L14 9.5v-6M7.5 14.5h9" fill="none" stroke={color} strokeWidth="2" strokeLinejoin="round" strokeLinecap="round" />
    </svg>
  );
}

export function Play({ size = 40, color = "currentColor", style }: P) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" style={style}>
      <path d="M7 4.5v15l12.5-7.5z" fill={color} />
    </svg>
  );
}

/** Icon by name, for props that take a string. */
export const ICONS = { heart: Heart, rose: Rose, check: Check, camera: Camera, bubble: Bubble, window: WindowIcon, home: Home, flask: Flask, play: Play } as const;
export type IconName = keyof typeof ICONS;
