#!/usr/bin/env python3
"""Check every item title/author in data/programs/*.json against the exact PDF text (press/<slug>.json)."""
import json, re, sys
from pathlib import Path
PRESS = Path(sys.argv[1]); DATA = Path(__file__).parent / "data" / "programs"
def n(s):
    s = (s or "").lower().replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    return re.sub(r"[^a-z0-9]+", "", s)
tot = bad = 0
for f in sorted(DATA.glob("*.json")):
    pages = json.loads((PRESS / f"{f.stem}.json").read_text())
    text = ""
    for j in pages:
        for line in (j[3] or []):
            for seg in (line[1] if len(line) > 1 and line[1] else []):
                for w in (seg[1] if len(seg) > 1 and seg[1] else []):
                    if isinstance(w, list) and len(w) > 1 and isinstance(w[1], str):
                        text += w[1]
    T = n(text)
    d = json.loads(f.read_text()); miss = []
    for c in d["courses"]:
        if n(c["title"]) not in T: miss.append(("course", c["code"], c["title"]))
        for s in c["sections"]:
            for it in s["items"]:
                tot += 1
                t = n(it.get("title"))
                # compare the first 30 normalized chars of the title, and the author's last name
                if t[:30] not in T:
                    miss.append(("title", c["code"], it.get("title"))); bad += 1
                elif it.get("by") and n(it["by"].split()[-1]) not in T:
                    miss.append(("by", c["code"], f'{it.get("title")} -- {it["by"]}')); bad += 1
    print(f"{f.stem}: {len(miss)} not found in the PDF text")
    for m in miss[:40]: print("   ", m)
print("items", tot, "flagged", bad)
