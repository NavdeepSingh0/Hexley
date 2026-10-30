"""
generate_icons.py — generates simple PNG icons for the extension toolbar.
Draws the mascot's face: dark rounded rect body + violet screen + two bar eyes.
No external dependencies beyond Python standard library.
"""

import struct, zlib, math

def png(w, h, pixels):
    """Encode pixels (list of [R,G,B,A] rows) as a minimal PNG."""
    def chunk(name, data):
        c = zlib.crc32(name + data) & 0xFFFFFFFF
        return struct.pack('>I', len(data)) + name + data + struct.pack('>I', c)

    raw = b''
    for row in pixels:
        raw += b'\x00'
        for r, g, b, a in row:
            raw += bytes([r, g, b, a])

    compressed = zlib.compress(raw, 9)
    ihdr = struct.pack('>IIBBBBB', w, h, 8, 2 | (1 << 2), 0, 0, 0)  # RGBA

    # Recalculate properly
    ihdr = struct.pack('>II', w, h) + bytes([8, 6, 0, 0, 0])  # bit depth=8, color=RGBA

    def make_chunk(tag, data):
        crc = zlib.crc32(tag + data) & 0xFFFFFFFF
        return struct.pack('>I', len(data)) + tag + data + struct.pack('>I', crc)

    sig   = b'\x89PNG\r\n\x1a\n'
    ihdr_data = struct.pack('>II', w, h) + bytes([8, 6, 0, 0, 0])
    idat_data = zlib.compress(raw, 9)
    iend_data = b''

    return (sig +
            make_chunk(b'IHDR', ihdr_data) +
            make_chunk(b'IDAT', idat_data) +
            make_chunk(b'IEND', iend_data))


def draw_icon(size):
    """Draw the Sentinel mascot face icon at `size` x `size` pixels."""
    s = size
    pixels = [[[0, 0, 0, 0] for _ in range(s)] for _ in range(s)]

    def set_px(x, y, r, g, b, a=255):
        if 0 <= x < s and 0 <= y < s:
            pixels[y][x] = [r, g, b, a]

    def fill_rect(x0, y0, x1, y1, r, g, b, a=255, radius=0):
        for y in range(y0, y1):
            for x in range(x0, x1):
                if radius > 0:
                    # corner rounding via distance
                    cx = max(x0 + radius, min(x1 - radius, x))
                    cy = max(y0 + radius, min(y1 - radius, y))
                    dist = math.sqrt((x - cx)**2 + (y - cy)**2)
                    if dist > radius:
                        continue
                set_px(x, y, r, g, b, a)

    # Scale factors
    p = s / 36  # design is 36px base

    # Body (rounded rect, light grey)
    bx0, by0 = int(2*p), int(2*p)
    bx1, by1 = int(34*p), int(34*p)
    brad = max(1, int(6*p))
    fill_rect(bx0, by0, bx1, by1, 220, 218, 235, 255, radius=brad)

    # Screen (dark rounded rect)
    sx0, sy0 = int(6*p), int(10*p)
    sx1, sy1 = int(30*p), int(26*p)
    srad = max(1, int(3*p))
    fill_rect(sx0, sy0, sx1, sy1, 7, 7, 10, 255, radius=srad)

    # Eyes: two vertical bars in violet
    # Left eye
    ew = max(1, int(2*p))
    eh = max(2, int(5*p))
    ex_l = int(11*p)
    ex_r = int(22*p)
    ey   = int(15*p)
    fill_rect(ex_l, ey, ex_l + ew, ey + eh, 169, 139, 255, 255)
    fill_rect(ex_r, ey, ex_r + ew, ey + eh, 169, 139, 255, 255)

    # Badge dot (bottom right, violet)
    dot_r = max(1, int(2*p))
    dot_x = int(26*p)
    dot_y = int(28*p)
    for dy in range(-dot_r, dot_r+1):
        for dx in range(-dot_r, dot_r+1):
            if dx*dx + dy*dy <= dot_r*dot_r:
                set_px(dot_x+dx, dot_y+dy, 169, 139, 255, 255)

    return pixels


import os, sys

script_dir = os.path.dirname(os.path.abspath(__file__))
icons_dir  = os.path.join(script_dir, '..', 'icons')
os.makedirs(icons_dir, exist_ok=True)

for size in [16, 48, 128]:
    pixels = draw_icon(size)
    data   = png(size, size, pixels)
    path   = os.path.join(icons_dir, f'icon{size}.png')
    with open(path, 'wb') as f:
        f.write(data)
    print(f'Written {path} ({size}x{size})')

