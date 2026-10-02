#!/usr/bin/env python3
"""Generate social preview cards into src/assets/og/ (needs Pillow). Run when program data changes.

Design (after studying ogimage.gallery): the historical engraving of the Log College on the right,
fading into a dark field; one large serif title; a small cabin mark. No small text: it does not
survive thumbnails, and platforms print the site name and description under the image anyway.

Cards are rendered at 2x (2400x1260) so text stays crisp on high-density screens and after the
platforms recompress them. The 1200x630 ratio is what Facebook, LinkedIn, X and WhatsApp expect.
"""
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

ROOT = Path(__file__).parent
OUT = ROOT / "src" / "assets" / "og"; OUT.mkdir(parents=True, exist_ok=True)
SITE = json.loads((ROOT / "data" / "site.json").read_text())
S = 2                                   # render scale
W, H = 1200 * S, 630 * S
FONT = str(ROOT / "src" / "og" / "fonts" / "EBGaramond.ttf")
WHITE, ACCENT, FIELD = (255, 255, 255), (122, 31, 36), (22, 17, 13)

def garamond(size, weight="SemiBold"):
    f = ImageFont.truetype(FONT, size)
    f.set_variation_by_name(weight)
    return f

# Background: engraving at full height on the right, sepia, softened, fading into a dark left field
src = Image.open(ROOT / "src" / "og" / "log-college-engraving.jpg").convert("L")
ew = int(src.width * H / src.height)
soft = src.resize((ew, H), Image.LANCZOS).filter(ImageFilter.GaussianBlur(1.4 * S))
eng = ImageOps.colorize(soft, black=(40, 32, 26), white=(226, 212, 186)).convert("RGBA")
BG = Image.new("RGBA", (W, H), FIELD + (255,))
ex = W - ew + 40 * S
BG.paste(eng, (ex, 0))
fade = Image.new("L", (W, H))
fd = ImageDraw.Draw(fade)
for x in range(W):
    t = (x - ex - 30 * S) / (480 * S)
    a = 1 if t <= 0 else max(0.0, 1 - t) ** 1.25
    fd.line([(x, 0), (x, H)], fill=int(255 * max(a, 0.18)))
BG = Image.composite(Image.new("RGBA", (W, H), FIELD + (255,)), BG, fade)

# Brand mark: the cabin from the logo, in white
cab = Image.open(ROOT / "src" / "assets" / "cabin.png").convert("RGBA")
cab = cab.resize((104 * S, int(cab.height * 104 * S / cab.width)), Image.LANCZOS)
mark = Image.new("RGBA", cab.size, WHITE + (0,)); mark.putalpha(cab.getchannel("A"))

def wrap(d, text, font, width):
    """Greedy wrap, then narrow the measure while the line count holds: balanced lines, no orphans."""
    def greedy(wd):
        lines, cur = [], ""
        for w in text.split():
            t = (cur + " " + w).strip()
            if d.textlength(t, font=font) <= wd or not cur: cur = t
            else: lines.append(cur); cur = w
        lines.append(cur); return lines
    best = greedy(width); n = len(best); wd = width
    while wd > 120 * S:
        trial = greedy(wd - 10 * S)
        if len(trial) != n: break
        best, wd = trial, wd - 10 * S
    return best

def card(title, name):
    im = BG.copy(); d = ImageDraw.Draw(im)
    x, maxw = 72 * S, 560 * S
    im.paste(mark, (x, 64 * S), mark)
    size = 112 * S
    while True:
        f = garamond(size); lines = wrap(d, title, f, maxw)
        if len(lines) <= 3 and all(d.textlength(l, font=f) <= maxw for l in lines): break
        size -= 4 * S
    lh = int(size * 1.02)
    y = H - 84 * S - lh * len(lines)
    for ln in lines:
        d.text((x, y), ln, font=f, fill=WHITE); y += lh
    d.rectangle([0, H - 12 * S, W, H], fill=ACCENT)
    im.convert("RGB").save(OUT / f"{name}.jpg", quality=88, subsampling=0, optimize=True, progressive=True)

card("Seminary education, freely given", "default")
for p in SITE["programs"]:
    d = json.loads((ROOT / "data" / "programs" / f"{p['slug']}.json").read_text())
    card(d["name"], p["slug"])
print("cards:", len(list(OUT.glob("*.jpg"))), "at", f"{W}x{H}")
