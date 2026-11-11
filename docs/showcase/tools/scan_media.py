# Writes media/manifest.json: every file under media/ (except the manifest itself), with its size in bytes and,
# for PNG and JPEG images, its width and height in pixels.
#
# Why: a composition cannot ask the disk whether a file exists, and an <Img> or <Video> of a missing file fails the
# whole render. The components import media/manifest.json and use media.ts's has(path) to decide whether to show a
# file or a neutral placeholder. Run this after adding, renaming or removing anything in media/:
#
#     python3 -I tools/scan_media.py
#
# Standard library only.
import json, os, struct, sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "media")
OUT = os.path.join(ROOT, "manifest.json")
SKIP = {"manifest.json", ".DS_Store", ".gitkeep"}


def png_size(b):
    if b[:8] == b"\x89PNG\r\n\x1a\n" and b[12:16] == b"IHDR":
        return struct.unpack(">II", b[16:24])
    return None


def jpeg_size(path):
    with open(path, "rb") as f:
        if f.read(2) != b"\xff\xd8":
            return None
        while True:
            m = f.read(2)
            if len(m) < 2 or m[0] != 0xFF:
                return None
            if m[1] in (0xD8, 0x01) or 0xD0 <= m[1] <= 0xD7:
                continue
            n = struct.unpack(">H", f.read(2))[0]
            if m[1] in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                h, w = struct.unpack(">xHH", f.read(5))
                return (w, h)
            f.seek(n - 2, 1)


files = {}
for dirpath, dirnames, filenames in os.walk(ROOT):
    dirnames[:] = sorted(d for d in dirnames if not d.startswith("."))
    for name in sorted(filenames):
        if name in SKIP or name.startswith("."):
            continue
        full = os.path.join(dirpath, name)
        rel = os.path.relpath(full, ROOT).replace(os.sep, "/")
        entry = {"bytes": os.path.getsize(full)}
        low = name.lower()
        try:
            size = None
            if low.endswith(".png"):
                with open(full, "rb") as f:
                    size = png_size(f.read(24))
            elif low.endswith((".jpg", ".jpeg")):
                size = jpeg_size(full)
            if size:
                entry["w"], entry["h"] = int(size[0]), int(size[1])
        except Exception as e:  # a broken image is still listed; it just has no size
            print("warning: no size for", rel, e, file=sys.stderr)
        files[rel] = entry

with open(OUT, "w") as f:
    json.dump({"files": files}, f, indent=1, sort_keys=True)
    f.write("\n")
print("wrote media/manifest.json:", len(files), "files")
for rel in files:
    print("  ", rel, files[rel])
