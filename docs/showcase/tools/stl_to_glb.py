# STL (binary or ASCII, millimetres, Z up) to a .glb (metres, Y up), one mesh with flat normals and one material.
# usage: python3 -I stl_to_glb.py IN.stl OUT.glb [#RRGGBB] [--center]
# --center moves the part so its footprint is centred on the origin and it stands on y = 0 (a turntable turns it in place).
import json, struct, sys
args = [a for a in sys.argv[1:] if a != "--center"]
center = "--center" in sys.argv
src, out = args[0], args[1]
colour = args[2] if len(args) > 2 else "#e86a1c"
data = open(src, "rb").read()
tris = []
count = struct.unpack("<I", data[80:84])[0] if len(data) >= 84 else 0
if len(data) == 84 + 50 * count and count > 0:  # binary
    for i in range(count):
        tris.append(struct.unpack("<9f", data[84 + 50 * i + 12: 84 + 50 * i + 48]))
else:  # ASCII
    nums = [float(p) for line in data.decode("ascii", "replace").splitlines() if line.strip().startswith("vertex") for p in line.split()[1:4]]
    tris = [tuple(nums[i:i + 9]) for i in range(0, len(nums) - 8, 9)]
if not tris: sys.exit("FAILED  no triangles in " + src)
pos, nor = [], []
for t in tris:
    p = [(t[i] * 0.001, t[i + 2] * 0.001, -t[i + 1] * 0.001) for i in (0, 3, 6)]  # mm to m, Z up to Y up
    u = [p[1][k] - p[0][k] for k in range(3)]; v = [p[2][k] - p[0][k] for k in range(3)]
    n = (u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2], u[0]*v[1]-u[1]*v[0]); l = (n[0]**2 + n[1]**2 + n[2]**2) ** 0.5 or 1.0
    n = (n[0]/l, n[1]/l, n[2]/l)
    for q in p: pos.append(q); nor.append(n)
lo = [min(p[k] for p in pos) for k in range(3)]; hi = [max(p[k] for p in pos) for k in range(3)]
if center:
    off = ((lo[0] + hi[0]) / 2, lo[1], (lo[2] + hi[2]) / 2)
    pos = [(p[0] - off[0], p[1] - off[1], p[2] - off[2]) for p in pos]
    lo = [min(p[k] for p in pos) for k in range(3)]; hi = [max(p[k] for p in pos) for k in range(3)]
binp = b"".join(struct.pack("<3f", *p) for p in pos); binn = b"".join(struct.pack("<3f", *n) for n in nor)
rgb = [int(colour[i:i + 2], 16) / 255 for i in (1, 3, 5)]; lin = [((c + 0.055) / 1.055) ** 2.4 if c > 0.04045 else c / 12.92 for c in rgb]
gltf = {
    "asset": {"version": "2.0", "generator": "stl_to_glb.py"}, "scene": 0, "scenes": [{"nodes": [0]}],
    "nodes": [{"mesh": 0, "name": "part"}],
    "meshes": [{"primitives": [{"attributes": {"POSITION": 0, "NORMAL": 1}, "material": 0}]}],
    "materials": [{"name": "Print", "pbrMetallicRoughness": {"baseColorFactor": lin + [1.0], "metallicFactor": 0.0, "roughnessFactor": 0.6}}],
    "buffers": [{"byteLength": len(binp) + len(binn)}],
    "bufferViews": [{"buffer": 0, "byteOffset": 0, "byteLength": len(binp), "target": 34962}, {"buffer": 0, "byteOffset": len(binp), "byteLength": len(binn), "target": 34962}],
    "accessors": [{"bufferView": 0, "componentType": 5126, "count": len(pos), "type": "VEC3", "min": lo, "max": hi}, {"bufferView": 1, "componentType": 5126, "count": len(nor), "type": "VEC3"}],
}
js = json.dumps(gltf, separators=(",", ":")).encode(); js += b" " * (-len(js) % 4)
body = binp + binn; body += b"\0" * (-len(body) % 4)
with open(out, "wb") as f:
    f.write(struct.pack("<4sII", b"glTF", 2, 12 + 8 + len(js) + 8 + len(body)))
    f.write(struct.pack("<I4s", len(js), b"JSON") + js); f.write(struct.pack("<I4s", len(body), b"BIN\0") + body)
print("wrote", out, len(tris), "triangles, box (m)", [round(x, 4) for x in lo], [round(x, 4) for x in hi])
