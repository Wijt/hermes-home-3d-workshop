"""Writes media/grain/grain.png: a 512 x 512 tile of fine, faint noise (pure Python, no packages).

The film's studio ground is a soft light on near-black. Eight-bit video draws such a gradient as rings; a little
noise over it breaks the rings up. The tile is fixed (seeded), so every render is the same.

usage: python3 -I tools/make_grain.py
"""
import pathlib
import random
import struct
import zlib

SIZE = 512
rng = random.Random(20261111)
rows = []
for _ in range(SIZE):
    row = bytearray([0])  # filter type 0
    for _ in range(SIZE):
        if rng.random() < 0.5:
            row += bytes((255, 255, 255, rng.randrange(0, 9)))  # a lighter speck
        else:
            row += bytes((0, 0, 0, rng.randrange(0, 26)))  # a darker speck
    rows.append(bytes(row))


def chunk(kind: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)


png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", SIZE, SIZE, 8, 6, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(b"".join(rows), 9)) + chunk(b"IEND", b"")
out = pathlib.Path(__file__).resolve().parent.parent / "media" / "grain" / "grain.png"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_bytes(png)
print(out, len(png), "bytes")
