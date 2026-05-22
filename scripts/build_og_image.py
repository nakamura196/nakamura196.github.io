#!/usr/bin/env python3
"""Generate the Open Graph share image (images/og.png, 1200x630).

Local asset generation — needs Pillow and the macOS system fonts. Not part of
the scheduled workflow; re-run by hand only if the headshot or title changes:

    python3 scripts/build_og_image.py
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
W, H = 1200, 630
BG = (243, 243, 243)

ARIAL_BOLD = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
ARIAL = "/System/Library/Fonts/Supplemental/Arial.ttf"
CJK_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc",
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
]


def font(path, size, index=0):
    return ImageFont.truetype(path, size, index=index)


def cjk_font(size):
    for p in CJK_CANDIDATES:
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            continue
    return None


def main():
    img = Image.new("RGB", (W, H), BG)

    # Headshot, square, left side, vertically centered.
    photo = Image.open(ROOT / "images" / "profile.jpg").convert("RGB")
    side = 420
    photo = photo.resize((side, side))
    img.paste(photo, (90, (H - side) // 2))

    d = ImageDraw.Draw(img)
    x = 560
    d.text((x, 150), "Satoru Nakamura", font=font(ARIAL_BOLD, 62), fill=(26, 26, 26))
    cf = cjk_font(34)
    if cf:
        d.text((x + 2, 228), "中村 覚", font=cf, fill=(51, 51, 51))
    d.text((x + 2, 298), "Historiographical Institute,", font=font(ARIAL, 26), fill=(68, 68, 68))
    d.text((x + 2, 334), "The University of Tokyo", font=font(ARIAL, 26), fill=(68, 68, 68))
    d.text((x + 2, 405), "Digital Humanities · IIIF · Linked Data",
           font=font(ARIAL, 28), fill=(106, 106, 106))
    d.text((x + 2, 548), "nakamura196.github.io", font=font(ARIAL, 26), fill=(138, 138, 138))

    out = ROOT / "images" / "og.png"
    img.save(out, "PNG")
    print(f"wrote {out} ({img.size[0]}x{img.size[1]})")


if __name__ == "__main__":
    main()
