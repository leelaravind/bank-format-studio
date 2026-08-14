"""Generate the product icon set from the original logo sheet (build tooling).

Reads assets/logo/logo.png (an AI-generated presentation sheet; NEVER modified)
and produces:
  - assets/logo/app-icon-master.png  : the main icon tile, cleaned (rounded-
    square alpha, presentation-sheet background removed), 710x710.
  - packaging/logo.ico               : Windows icon. 128/256 use the master
    artwork; 16/32/48/64 use a simplified text-free treatment (document +
    conversion arrow + structured table), because the product-name text is
    unreadable at small sizes.
  - packaging/wizard-small*.bmp      : Inno Setup wizard corner logo
    (WizardSmallImageFile, shown on every installer page; 55 px uses the
    simplified artwork, 110 px the master).
  - packaging/wizard-image*.bmp      : Inno Setup wizard banner
    (WizardImageFile, welcome/finish pages), master artwork on white.

Usage:  python tools/make_icon.py
Requires Pillow (requirements-build.in, build-time only).
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "assets" / "logo" / "logo.png"
MASTER = ROOT / "assets" / "logo" / "app-icon-master.png"
ICO = ROOT / "packaging" / "logo.ico"

# The main icon tile inside the presentation sheet (absolute source coords,
# found by dark-pixel bounding-box analysis of the 1254x1254 sheet).
TILE_BOX = (60, 51, 770, 751)  # 710 x 700
TILE_CORNER_RADIUS = 118  # measured from the tile's rounded corners
EDGE_INSET = 2  # shave the anti-aliased fringe against the white sheet

# Simplified small-size treatment: a naturally square tile region holding the
# symbol group (bank document, pixel-dissolve conversion arrow, structured
# table, swoosh) with the wordmark blocks erased (tile-local coords, measured
# by pixel scan: "BANK" y497-547, "STATEMENT" y548-610, teal line y610+; the
# swoosh stays above y483 in those x-bands).
SYMBOL_BOX = (28, 8, 652, 632)
TEXT_BLOCKS = (  # tile-local rects to erase; swoosh and table stay untouched
    (150, 483, 392, 552),  # BANK (x 162-379)
    (112, 552, 570, 612),  # STATEMENT (x 160-560; swoosh tail stays above y536)
    (100, 612, 565, 632),  # FORMAT STUDIO (x 162-553), upper part inside crop
)
ERASE_SAMPLE_OFFSET = 14  # sample fill colour this far left of each block

ICO_SIZES = (256, 128, 64, 48, 32, 16)
SIMPLIFIED_MAX = 64  # sizes <= this use the text-free treatment

# Inno Setup wizard bitmaps (BMP, no alpha; Inno picks the best size per
# display scaling from a comma-separated list in installer.iss).
WIZARD_SMALL = (("wizard-small.bmp", 55), ("wizard-small-2x.bmp", 110))
WIZARD_BANNER = (("wizard-image.bmp", (164, 314)), ("wizard-image-2x.bmp", (328, 628)))
WIZARD_BACKGROUND = (255, 255, 255)  # matches the modern wizard's white panes


def rounded_alpha(img: Image.Image, radius: int, inset: int) -> Image.Image:
    """Apply a rounded-rectangle alpha mask (drawn 4x and downsampled for AA)."""
    w, h = img.size
    big = Image.new("L", (w * 4, h * 4), 0)
    ImageDraw.Draw(big).rounded_rectangle(
        (inset * 4, inset * 4, w * 4 - 1 - inset * 4, h * 4 - 1 - inset * 4),
        radius=radius * 4,
        fill=255,
    )
    out = img.convert("RGBA")
    out.putalpha(big.resize((w, h), Image.LANCZOS))
    return out


def build_master(tile: Image.Image) -> Image.Image:
    """Clean full tile (with wordmark) on a square transparent canvas."""
    rounded = rounded_alpha(tile, TILE_CORNER_RADIUS, EDGE_INSET)
    side = max(tile.size)
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    canvas.paste(rounded, ((side - tile.width) // 2, (side - tile.height) // 2))
    return canvas


def build_simplified(tile: Image.Image) -> Image.Image:
    """Text-free symbol-only icon for small sizes.

    Erases the wordmark row by row with background colour sampled just left of
    each block, so the fill follows the tile's gradient without seams.
    """
    work = tile.copy()
    px = work.load()
    for x0, y0, x1, y1 in TEXT_BLOCKS:
        for y in range(y0, y1):
            fill = px[x0 - ERASE_SAMPLE_OFFSET, y]
            for x in range(x0, x1):
                px[x, y] = fill
    symbol = work.crop(SYMBOL_BOX)
    assert symbol.width == symbol.height, "SYMBOL_BOX must be square"
    return rounded_alpha(symbol, round(symbol.width * 0.165), 0)


def flatten_on(art: Image.Image, canvas_size: tuple[int, int],
               icon_fraction: float) -> Image.Image:
    """Centre the RGBA artwork on an opaque canvas (BMP carries no alpha)."""
    w, h = canvas_size
    canvas = Image.new("RGB", (w, h), WIZARD_BACKGROUND)
    side = round(min(w, h) * icon_fraction)
    icon = art.resize((side, side), Image.LANCZOS)
    canvas.paste(icon, ((w - side) // 2, (h - side) // 2), icon)
    return canvas


def build_wizard_bitmaps(master: Image.Image, simplified: Image.Image) -> None:
    for name, size in WIZARD_SMALL:
        art = simplified if size <= SIMPLIFIED_MAX else master
        path = ICO.parent / name
        flatten_on(art, (size, size), 1.0).save(path, format="BMP")
        print(f"wizard: {path} {size}x{size}")
    for name, (w, h) in WIZARD_BANNER:
        path = ICO.parent / name
        flatten_on(master, (w, h), 0.8).save(path, format="BMP")
        print(f"wizard: {path} {w}x{h}")


def main() -> None:
    sheet = Image.open(SOURCE).convert("RGB")
    tile = sheet.crop(TILE_BOX)

    master = build_master(tile)
    master.save(MASTER)
    print(f"master: {MASTER} {master.size}")

    simplified = build_simplified(tile)
    build_wizard_bitmaps(master, simplified)
    frames = []
    for size in ICO_SIZES:
        art = simplified if size <= SIMPLIFIED_MAX else master
        frames.append(art.resize((size, size), Image.LANCZOS))
    frames[0].save(
        ICO,
        format="ICO",
        append_images=frames[1:],
        sizes=[(s, s) for s in ICO_SIZES],
    )
    print(f"ico: {ICO} sizes {[f.size for f in frames]}")


if __name__ == "__main__":
    main()
