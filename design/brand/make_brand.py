"""Draws Hexley's pixel logo and mascot from their grids and writes every file that uses them. Run with any Python that has Pillow:

    python design/brand/make_brand.py

The logo (16 cells) is for small places: favicon, MCP icon, Allow page, extension icon. The mascot (40 cells) is the full character for the
extension and the slides; its line is one spiral, from the screen out to the edge, with a speech-bubble tail at the bottom right. Colours are
the design tokens: --brand and --bg. Everything is whole pixels, so a size that is a multiple of the grid stays crisp.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
PURPLE, INK = "#a98bff", "#07070a"

LOGO = [
    "...##########...",
    "..#PPPPPPPPPP#..",
    ".#PPPPPPPPPPPP#.",
    "#PPPPPPPPPPPPPP#",
    "#PPP##PPPP##PPP#",
    "#PPP##PPPP##PPP#",
    "#PPP##PPPP##PPP#",
    "#PPP##PPPP##PPP#",
    "#PPP##PPPP##PPP#",
    "#PPPPPPPPPPPPPP#",
    "#PPPPPPPPPPPPPP#",
    "#PPPP######PPPP#",
    "#PPPPPPPPPPPPPP#",
    ".#PPPPPPPPPPPP#.",
    "..#PPPPPPPPPP#..",
    "...##########...",
]

SIZE = 40
# The face: the same cells the extension draws for its resting state.
EYES = [(x, y) for x in (13, 14, 15, 24, 25, 26) for y in range(11, 20)]
MOUTH = [(x, y) for x in range(15, 25) for y in (23, 24)]


def mascot_line() -> set[tuple[int, int]]:
    """One spiral: from the end of the screen's bottom edge, round the screen, out through the tail, and round the outside."""
    line = set()
    line |= {(x, 30) for x in range(10, 29)} | {(29, 29)}  # the screen's bottom, ending in a small turn up
    line |= {(9, 29), (8, 28)} | {(7, y) for y in range(10, 28)} | {(8, 9), (9, 8)}  # its left side
    line |= {(x, 7) for x in range(10, 30)} | {(30, 8), (31, 9)} | {(32, y) for y in range(10, 37)}  # its top, then down the right
    line |= {(x, 37) for x in range(6, 33)} | {(33, 36), (34, 35), (35, 34), (36, 33)}  # the bottom, and the tail
    line |= {(37, y) for y in range(6, 33)} | {(36, 5), (35, 4), (34, 3), (33, 2)}  # up the outside
    line |= {(x, 2) for x in range(6, 33)} | {(5, 3), (4, 4), (3, 5)}
    line |= {(2, y) for y in range(6, 34)} | {(3, 34), (4, 35), (5, 36)}
    return line


def mascot_grid(face: bool = True) -> list[str]:
    line = mascot_line()
    outside = set()
    todo = [(0, 0)]
    while todo:  # whatever cannot be reached from the corner is inside the line
        x, y = todo.pop()
        if not (0 <= x < SIZE and 0 <= y < SIZE) or (x, y) in outside or (x, y) in line:
            continue
        outside.add((x, y))
        todo += [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
    ink = line | (set(EYES) | set(MOUTH) if face else set())
    return ["".join("#" if (x, y) in ink else "." if (x, y) in outside else "P" for x in range(SIZE)) for y in range(SIZE)]


def path(grid: list[str], cell: str) -> str:
    out = []
    for y, row in enumerate(grid):
        x = 0
        while x < len(row):
            if row[x] != cell:
                x += 1
                continue
            start = x
            while x < len(row) and row[x] == cell:
                x += 1
            out.append(f"M{start} {y}h{x - start}v1h{start - x}z")
    return "".join(out)


def svg(grid: list[str], label: str) -> str:
    n = len(grid)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {n} {n}" shape-rendering="crispEdges" role="img" aria-label="{label}">'
            f'<path fill="{PURPLE}" d="{path(grid, "P")}"/><path fill="{INK}" d="{path(grid, "#")}"/></svg>\n')


def image(grid: list[str], size: int) -> Image.Image:
    n = len(grid)
    colours = {"P": (0xa9, 0x8b, 0xff, 255), "#": (0x07, 0x07, 0x0a, 255), ".": (0, 0, 0, 0)}
    small = Image.new("RGBA", (n, n))
    small.putdata([colours[c] for row in grid for c in row])
    scale = size // n
    big = small.resize((n * scale, n * scale), Image.NEAREST)
    if big.size == (size, size):
        return big
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))  # the size is not a multiple of the grid: pad, never blur
    canvas.paste(big, ((size - n * scale) // 2, (size - n * scale) // 2))
    return canvas


def write(path_: Path, text: str) -> None:
    path_.parent.mkdir(parents=True, exist_ok=True)
    path_.write_text(text, encoding="utf-8", newline="\n")


def main() -> None:
    mascot = mascot_grid()
    brand, public, extension = ROOT / "design" / "brand", ROOT / "site" / "public", ROOT / "extension"
    write(brand / "hexley-logo.svg", svg(LOGO, "Hexley"))
    write(brand / "hexley-mascot.svg", svg(mascot, "Hexley's mascot"))
    image(LOGO, 1024).save(brand / "hexley-logo-1024.png")
    image(mascot, 1000).save(brand / "hexley-mascot-1000.png")

    write(public / "favicon.svg", svg(LOGO, "Hexley"))
    image(LOGO, 512).save(public / "logo-512.png")
    image(LOGO, 192).save(public / "logo-192.png")
    image(LOGO, 180).save(public / "apple-touch-icon.png")
    image(LOGO, 256).save(public / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48), (256, 256)])

    write(extension / "icon.svg", svg(LOGO, "Hexley"))
    for size in (16, 32, 48, 128):
        image(LOGO, size).save(extension / f"icon-{size}.png")
    write(extension / "mascot-art.js", "// Written by design/brand/make_brand.py. Do not edit by hand.\n"
          f"export const GRID = {SIZE}\nexport const FILL_D = '{path(mascot_grid(face=False), 'P')}'\nexport const LINE_D = '{path(mascot_grid(face=False), '#')}'\n")

    inline = (f'<svg viewBox="0 0 16 16" shape-rendering="crispEdges" aria-hidden="true"><path fill="{PURPLE}" d="{path(LOGO, "P")}"/>'
              f'<path fill="{INK}" d="{path(LOGO, "#")}"/></svg>')
    write(ROOT / "src" / "sentinel" / "brand.py", '"""Hexley\'s logo for pages that may load nothing else. Written by design/brand/make_brand.py."""\n\n'
          f"LOGO_SVG = '{inline}'\n")


if __name__ == "__main__":
    main()
