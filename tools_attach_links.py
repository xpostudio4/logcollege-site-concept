#!/usr/bin/env python3
"""Attach the hyperlinks from the original PDF guides to items in data/programs/*.json.

Input: press/<slug>.json = list of pages from Google Drive's viewer (exact text with word boxes + link boxes).
Each link is matched to the words under its rectangle, then to the JSON item (in document order)
whose title best matches that link text. Writes item["url"]; prints a report of unmatched links/items.
"""
import json, re, sys, difflib
from pathlib import Path

PRESS = Path(sys.argv[1])
DATA = Path(__file__).parent / "data" / "programs"
DRY = "--dry" in sys.argv

def n(s):
    s = (s or "").lower().replace("’", "'").replace("–", "-").replace("—", "-")
    return re.sub(r"[^a-z0-9]+", " ", s).strip()

def page_links(pages):
    out = []
    for pi, j in enumerate(pages):
        words = []
        for line in (j[3] or []):
            for seg in (line[1] if len(line) > 1 and line[1] else []):
                for w in (seg[1] if len(seg) > 1 and seg[1] else []):
                    if isinstance(w, list) and len(w) > 1 and isinstance(w[0], list):
                        words.append(w)
        for L in (j[5] if len(j) > 5 and j[5] else []):
            t, l, h, w = L[1]
            url = (L[3] if len(L) > 3 and L[3] else None) or L[0]
            if not isinstance(url, str):
                continue
            m = re.match(r"https://www\.google\.com/url\?sa=D&q=([^&]+)", url)
            if m:
                from urllib.parse import unquote
                url = unquote(m.group(1))
            ws = [x[1] for x in words if t - 2 <= x[0][0] + x[0][2] / 2 <= t + h + 2 and l - 2 <= x[0][1] + x[0][3] / 2 <= l + w + 2]
            text = re.sub(r"\s*[–—-]\s*$", "", " ".join(ws)).strip()
            if url.startswith("mailto:") or not text:
                continue
            out.append({"page": pi + 1, "text": text, "url": url})
    return out

def score(link_text, item_title):
    a, b = n(link_text), n(item_title)
    if not a or not b:
        return 0
    if b.startswith(a) or a.startswith(b):
        return 1.0 if min(len(a), len(b)) >= 4 else 0.6
    return difflib.SequenceMatcher(None, a, b[: len(a) + 8]).ratio()

total_ok = total_items = 0
for f in sorted(DATA.glob("*.json")):
    slug = f.stem
    pf = PRESS / f"{slug}.json"
    if not pf.exists():
        continue
    d = json.loads(f.read_text())
    links = page_links(json.loads(pf.read_text()))
    items = [(c["code"], it) for c in d["courses"] for s in c["sections"] for it in s["items"]]
    titles = {n(li.get("title")) for li in d["course_list"]}
    li = 0
    ok = 0
    unmatched_items = []
    used = set()
    for code, it in items:
        best, bi = 0, None
        for k in range(max(0, li - 15), min(li + 40, len(links))):
            if k in used:
                continue
            sc = score(links[k]["text"], it.get("title"))
            if k < li:
                sc -= 0.05
            if sc > best:
                best, bi = sc, k
        it.pop("url", None); it.pop("urls", None)
        if best >= 0.74:
            it["url"] = links[bi]["url"]
            used.add(bi)
            li = bi + 1
            ok += 1
            # volume links: following links whose text is just "1", "2", "Vol. 2"...
            extra = []
            k = bi + 1
            while k < len(links) and re.fullmatch(r"(vol\.?\s*)?[0-9ivx]{1,3}", n(links[k]["text"])) and links[k]["page"] == links[bi]["page"]:
                extra.append({"label": "Vol. " + re.sub(r"(?i)vol\.?\s*", "", links[k]["text"]).strip(), "url": links[k]["url"]})
                used.add(k); k += 1
            if extra:
                it["urls"] = extra
                li = k
        else:
            unmatched_items.append((code, it.get("title")))
    left = [l for k, l in enumerate(links) if k not in used and n(l["text"]) not in titles]
    total_ok += ok
    total_items += len(items)
    print(f"{slug}: {ok}/{len(items)} items linked; {len(left)} links unused")
    for code, t in unmatched_items[:6]:
        print(f"   no link: {code} {t}")
    for l in left[:6]:
        print(f"   unused: p{l['page']} {l['text'][:60]}")
    if not DRY:
        f.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n")
print(f"TOTAL {total_ok}/{total_items}")
