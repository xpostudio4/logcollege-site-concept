#!/usr/bin/env python3
"""Generate 1200x630 social preview cards into src/assets/og/ (needs Pillow). Run when program data changes."""
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).parent
OUT = ROOT / "src" / "assets" / "og"; OUT.mkdir(parents=True, exist_ok=True)
SITE = json.loads((ROOT / "data" / "site.json").read_text())
W, H = 1200, 630
PAPER, INK, MUTED, ACCENT, GOLD = (251, 248, 242), (29, 27, 24), (107, 101, 92), (122, 31, 36), (154, 117, 54)
SERIF = "/System/Library/Fonts/Supplemental/Georgia.ttf"
SANS = "/System/Library/Fonts/Helvetica.ttc"

engr = Image.open(ROOT / "src" / "og" / "log-college-engraving.jpg").convert("RGB")
logo = Image.open(ROOT / "src" / "assets" / "logo.png").convert("RGBA")

def wrap(draw, text, font, width):
    lines, cur = [], ""
    for w in text.split():
        t = (cur + " " + w).strip()
        if draw.textlength(t, font=font) <= width: cur = t
        else: lines.append(cur); cur = w
    lines.append(cur); return lines

def card(eyebrow, title, facts, name):
    im = Image.new("RGB", (W, H), PAPER)
    left = ImageOps.fit(engr, (560, H), centering=(0.45, 0.5))
    im.paste(left, (0, 0))
    d = ImageDraw.Draw(im)
    x, maxw = 616, W - 616 - 56
    lg = logo.copy(); lg.thumbnail((maxw, 90)); im.paste(lg, (x, 56), lg)
    d.text((x, 196), eyebrow.upper(), font=ImageFont.truetype(SANS, 20), fill=GOLD, spacing=4)
    size = 54
    while True:
        f = ImageFont.truetype(SERIF, size); lines = wrap(d, title, f, maxw)
        if len(lines) <= 4 or size <= 36: break
        size -= 4
    y = 236
    for ln in lines:
        d.text((x, y), ln, font=f, fill=INK); y += int(size * 1.2)
    d.text((x, H - 96), facts, font=ImageFont.truetype(SANS, 24), fill=MUTED)
    d.rectangle([0, H - 10, W, H], fill=ACCENT)
    im.save(OUT / f"{name}.png", optimize=True)

card("Reformed seminary education", "Free, mentored seminary training in your own church",
     "11 degree programs  ·  Online  ·  Tuition-free", "default")
levels = {"undergraduate": "Undergraduate", "graduate": "Graduate", "doctoral": "Doctoral"}
for p in SITE["programs"]:
    d = json.loads((ROOT / "data" / "programs" / f"{p['slug']}.json").read_text())
    card(f"{p['abbr']}  ·  {levels[p['level']]} program", d["name"],
         f"{d['credit_hours']} credit hours  ·  Online  ·  Tuition-free", p["slug"])
print("cards:", sorted(x.name for x in OUT.glob("*.png")))
