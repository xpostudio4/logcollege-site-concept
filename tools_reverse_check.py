#!/usr/bin/env python3
"""List item-like lines in the live PDF text (press/<slug>.json) that are missing from data/programs/<slug>.json."""
import json, re, sys
from pathlib import Path
PRESS = Path(sys.argv[1]); DATA = Path(__file__).parent / "data" / "programs"
def n(s):
    s = (s or "").lower().replace("’", "'")
    return re.sub(r"[^a-z0-9]+", "", s)
def lines(slug):
    out = []
    for pi, j in enumerate(json.loads((PRESS / f"{slug}.json").read_text())):
        for line in (j[3] or []):
            ws = [w[1] for seg in (line[1] if len(line) > 1 and line[1] else []) for w in (seg[1] if len(seg) > 1 and seg[1] else []) if isinstance(w, list) and len(w) > 1 and isinstance(w[1], str)]
            out.append((pi + 1, " ".join(ws)))
    return out
grand = 0
for f in sorted(DATA.glob("*.json")):
    d = json.loads(f.read_text())
    have = set()
    for c in d["courses"]:
        for s in c["sections"]:
            for it in s["items"]:
                have.add(n(it.get("title"))[:25])
    miss = []
    for p, l in lines(f.stem):
        if re.search(r"\s[–—-]\s", l) and re.search(r"\[[^\]]+\]\s*$|\[\d", l) and not re.match(r"^\d+\.", l):
            title = re.split(r"\s[–—-]\s", l)[0]
            key = n(title)[:25]
            if key and not any(key[:18] in h or h[:18] in key for h in have):
                miss.append((p, l))
    grand += len(miss)
    print(f"{f.stem}: {len(miss)} live lines not in data")
    for m in miss[:12]: print("    p%d %s" % m)
print("TOTAL missing", grand)
