#!/usr/bin/env python3
"""Generate 1200x630 social preview cards into src/assets/og/ (needs Pillow). Run when program data changes.

Design (after studying ogimage.gallery): the historical engraving full-bleed in sepia, darkened on the
left so one large serif title reads at thumbnail size; one gold line of facts; the brand mark small.
"""
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).parent
OUT = ROOT / "src" / "assets" / "og"; OUT.mkdir(parents=True, exist_ok=True)
SITE = json.loads((ROOT / "data" / "site.json").read_text())
W, H = 1200, 630
FONT = str(ROOT / "src" / "og" / "fonts" / "EBGaramond.ttf")
SANS = "/System/Library/Fonts/Helvetica.ttc"
WHITE, CREAM, GOLD, ACCENT = (255, 255, 255), (238, 228, 210), (214, 178, 112), (122, 31, 36)

def garamond(size, weight="Medium"):
    f = ImageFont.truetype(FONT, size)
    f.set_variation_by_name(weight)
    return f

# Background: engraving at full height on the right, sepia duotone, fading into a dark left side
src = Image.open(ROOT / "src" / "og" / "log-college-engraving.jpg").convert("L")
eh = H; ew = int(src.width * eh / src.height)
eng = ImageOps.colorize(src.resize((ew, eh), Image.LANCZOS), black=(24, 19, 15), white=(240, 228, 206)).convert("RGBA")
BG = Image.new("RGBA", (W, H), (22, 17, 13, 255))
ex = W - ew + 40
BG.paste(eng, (ex, 0))
fade = Image.new("L", (W, H))
fd = ImageDraw.Draw(fade)
for x in range(W):
    t = (x - ex - 30) / 480     # 0 just inside the engraving's left edge, 1 after 480px
    a = 1 if t <= 0 else max(0.0, 1 - t) ** 1.6
    a = max(a, 0.18)             # keep the whole picture slightly toned down
    fd.line([(x, 0), (x, H)], fill=int(255 * a))
BG = Image.composite(Image.new("RGBA", (W, H), (22, 17, 13, 255)), BG, fade)

# Brand mark: the cabin from the logo, in white
cab = Image.open(ROOT / "src" / "assets" / "cabin.png").convert("RGBA")
cab.thumbnail((64, 50))
white_cab = Image.new("RGBA", cab.size, WHITE + (0,)); white_cab.putalpha(cab.getchannel("A"))

def wrap(d, text, font, width):
    """Greedy wrap, then narrow the measure as long as the line count holds: balanced lines, no orphans."""
    def greedy(wd):
        lines, cur = [], ""
        for w in text.split():
            t = (cur + " " + w).strip()
            if d.textlength(t, font=font) <= wd or not cur: cur = t
            else: lines.append(cur); cur = w
        lines.append(cur); return lines
    best = greedy(width); n = len(best); wd = width
    while wd > 120:
        trial = greedy(wd - 10)
        if len(trial) != n: break
        best, wd = trial, wd - 10
    return best

def card(eyebrow, title, facts, name):
    im = BG.copy(); d = ImageDraw.Draw(im)
    x, maxw = 72, 520
    im.paste(white_cab, (x, 56), white_cab)
    d.text((x + white_cab.width + 16, 56 + white_cab.height // 2), "THE LOG COLLEGE & SEMINARY",
           font=ImageFont.truetype(SANS, 19), fill=CREAM, anchor="lm")
    size = 92
    while True:
        f = garamond(size); lines = wrap(d, title, f, maxw)
        if len(lines) <= 3 and all(d.textlength(l, font=f) <= maxw for l in lines): break
        size -= 4
    lh = int(size * 1.04)
    block = lh * len(lines)
    y = H - 118 - block
    if eyebrow:
        d.text((x, y - 44), eyebrow.upper(), font=ImageFont.truetype(SANS, 20), fill=GOLD)
    for ln in lines:
        d.text((x, y), ln, font=f, fill=WHITE); y += lh
    d.text((x, H - 86), facts, font=ImageFont.truetype(SANS, 23), fill=CREAM)
    d.rectangle([0, H - 8, W, H], fill=ACCENT)
    im.convert("RGB").save(OUT / f"{name}.png", optimize=True)

card("A Reformed seminary", "Seminary education, freely given", "11 degree programs  ·  Online  ·  Mentored  ·  Tuition-free", "default")
levels = {"undergraduate": "Undergraduate", "graduate": "Graduate", "doctoral": "Doctoral"}
for p in SITE["programs"]:
    d = json.loads((ROOT / "data" / "programs" / f"{p['slug']}.json").read_text())
    card(f"{p['abbr']}  ·  {levels[p['level']]} program", d["name"],
         f"{d['credit_hours']} credit hours  ·  Online  ·  Tuition-free", p["slug"])
print("cards:", len(list(OUT.glob("*.png"))))
