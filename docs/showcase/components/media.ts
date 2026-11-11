// Which media files exist, known at render time from media/manifest.json (written by tools/scan_media.py).
// A composition cannot ask the disk, and an <Img> or <Video> of a missing file fails the whole render, so every
// component that shows an optional file asks has() first and shows a placeholder when it is absent.
import { staticFile } from "raea";
import manifest from "../media/manifest.json";

type Entry = { bytes: number; w?: number; h?: number };
const FILES = (manifest as { files: Record<string, Entry> }).files;

/** True when media/<path> was there the last time tools/scan_media.py ran. path is relative to media/. */
export function has(path: string): boolean {
  return Object.prototype.hasOwnProperty.call(FILES, path);
}

/** The manifest entry (bytes, and w and h for PNG and JPEG), or undefined. */
export function info(path: string): Entry | undefined {
  return has(path) ? FILES[path] : undefined;
}

/** staticFile(path) when the file exists, else undefined. */
export function src(path: string): string | undefined {
  return has(path) ? staticFile(path) : undefined;
}

/** True for a video by its extension. */
export const isVideo = (path: string) => /\.(mp4|mov|m4v|webm)$/i.test(path);

/** Every listed path under a folder, e.g. list("screen/"). */
export const list = (prefix: string) => Object.keys(FILES).filter((k) => k.startsWith(prefix)).sort();
