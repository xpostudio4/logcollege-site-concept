#!/usr/bin/env python3
"""Static site generator for The Log College & Seminary program catalog.

Reads data/site.json + data/programs/*.json, writes the site to public/.
No dependencies beyond the Python standard library.  Run:  python3 build.py
"""
import json, re, shutil
from collections import OrderedDict, defaultdict
from html import escape
from pathlib import Path

ROOT = Path(__file__).parent
DATA = ROOT / "data"
OUT = ROOT / "public"

SITE = json.loads((DATA / "site.json").read_text())
META = {p["slug"]: p for p in SITE["programs"]}

PROGRAMS = []
for p in sorted(SITE["programs"], key=lambda p: p["order"]):
    f = DATA / "programs" / f"{p['slug']}.json"
    if f.exists():
        d = json.loads(f.read_text())
        d.update({k: v for k, v in p.items() if k not in ("name",)})
        d.setdefault("name", p.get("name"))
        PROGRAMS.append(d)

DEPTS = OrderedDict([
    ("PRE", "Preparatory Studies"), ("BS", "Biblical Studies"), ("TH", "Theology"), ("HT", "Historical Theology"),
    ("CH", "Church History"), ("PT", "Practical Theology"), ("NC", "Nouthetic Counseling"),
    ("AP", "Apologetics"), ("WV", "Worldview Studies"), ("PH", "Philosophy & History"),
    ("PRT", "Puritan Theology"), ("PM", "Puritan Ministry"), ("PR", "Puritan Classics & Readings"),
    ("LG", "Latin"), ("PS", "Puritan Studies"),
])

def dept_of(code):
    m = re.match(r"[A-Z]+", code or "")
    return m.group(0) if m else "Other"

def dept_name(prefix):
    return DEPTS.get(prefix, prefix)

def slug_code(code):
    return re.sub(r"[^a-z0-9]+", "-", code.lower()).strip("-")

def e(s):
    return escape(str(s)) if s is not None else ""

def plural(n, word, pl=None):
    return f"{n:,} {word if n == 1 else (pl or word + 's')}"

def hours(minutes):
    h = minutes / 60
    return f"{h:,.0f}" if h >= 10 else f"{h:,.1f}".rstrip("0").rstrip(".")

def fmt_extent(it, kind=None):
    m, pg = it.get("minutes"), it.get("pages")
    if m:
        h, mm = divmod(int(round(m)), 60)
        return " ".join(x for x in (f"{h} h" if h else "", f"{mm} min" if mm else "") if x)
    if pg:
        return f"{pg:,} pp."
    return it.get("extent")

LEVEL_LABEL = {k: v["label"] for k, v in SITE["levels"].items()}
PROGRAM_TITLE = {p["slug"]: p["name"] for p in PROGRAMS}

# ---------------------------------------------------------------- icons
ICON = {
    "arrow": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12h14M13 6l6 6-6 6"/></svg>',
    "download": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 4v11M7 10l5 5 5-5M5 20h14"/></svg>',
    "chev": '<svg class="chev" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 9l6 6 6-6"/></svg>',
    "search": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/></svg>',
    "menu": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M4 7h16M4 12h16M4 17h16"/></svg>',
    "external": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M14 4h6v6M20 4l-9 9M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5"/></svg>',
}

# ---------------------------------------------------------------- analysis
def section_minutes(s):
    return sum(i.get("minutes") or 0 for i in s.get("items", []) if s.get("type") in ("lectures",))

def section_pages(s):
    return sum(i.get("pages") or 0 for i in s.get("items", []) if s.get("type") in ("readings",))

WRITE_RE = re.compile(r"\b(write|paper|essay|commentary|sermon|outline|thesis|dissertation)\b", re.I)

def course_stats(c):
    mins = sum(section_minutes(s) for s in c.get("sections", []))
    pages = sum(section_pages(s) for s in c.get("sections", []))
    lectures = sum(len(s["items"]) for s in c.get("sections", []) if s["type"] == "lectures")
    readings = sum(len(s["items"]) for s in c.get("sections", []) if s["type"] in ("readings", "review"))
    papers = sum(1 for s in c.get("sections", []) if s["type"] == "assignment" and WRITE_RE.search(s.get("instruction") or ""))
    return {"minutes": mins, "pages": pages, "lectures": lectures, "readings": readings, "papers": papers}

def program_stats(p):
    tot = defaultdict(int)
    for c in p["courses"]:
        for k, v in course_stats(c).items():
            tot[k] += v
    return tot

# Course index across programs: code -> list of (program, course)
COURSE_OCC = OrderedDict()
for p in PROGRAMS:
    for c in p["courses"]:
        COURSE_OCC.setdefault(c["code"], []).append((p, c))
# also list-only courses (no detail block)
LIST_ONLY = defaultdict(list)
for p in PROGRAMS:
    have = {c["code"] for c in p["courses"]}
    for li in p["course_list"]:
        if li["code"] not in have:
            LIST_ONLY[li["code"]].append((p, li))

def _n(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())

def sig(c):
    return json.dumps([c.get("credits")] + [(s["type"], _n(s.get("instruction"))[:60], [(_n(i.get("title")), _n(i.get("by")), i.get("minutes"), i.get("pages")) for i in s.get("items", [])]) for s in c.get("sections", [])])

def programs_for_code(code):
    seen = OrderedDict()
    for p, _ in COURSE_OCC.get(code, []):
        seen[p["slug"]] = p
    for p, _ in LIST_ONLY.get(code, []):
        seen[p["slug"]] = p
    return list(seen.values())

def prog_label(p):
    name = p["name"]
    if p["abbr"] == "Th.D.":
        return "Th.D. (" + name.replace("Doctor of Theology in ", "") + ")"
    if p["abbr"] == "Th.M.":
        return "Th.M. (Nouthetic Counseling)"
    return p["abbr"]

# Resource library: dedupe by (kind, title, by)
def norm(s):
    return re.sub(r"\s+", " ", (s or "").strip()).lower()

LIB = OrderedDict()
for code, occ in COURSE_OCC.items():
    for p, c in occ:
        for s in c.get("sections", []):
            if s["type"] not in ("lectures", "readings", "review"):
                continue
            kind = "Lecture" if s["type"] == "lectures" else "Reading"
            for it in s.get("items", []):
                key = (kind, _n(it.get("title")), _n(it.get("by")))
                rec = LIB.setdefault(key, {"kind": kind, "title": it.get("title"), "by": it.get("by"),
                                            "extent": fmt_extent(it), "minutes": it.get("minutes"),
                                            "pages": it.get("pages"), "url": it.get("url"), "codes": OrderedDict(), "programs": OrderedDict()})
                if it.get("url") and not rec.get("url"):
                    rec["url"] = it["url"]
                rec["codes"][code] = c.get("title")
                rec["programs"][p["slug"]] = True

UNIQUE_MIN = 0
for code, occ in COURSE_OCC.items():
    UNIQUE_MIN += course_stats(occ[0][1])["minutes"]

# ---------------------------------------------------------------- layout
NAV = [("Programs", "/programs/"), ("Course Catalog", "/courses/"), ("Resource Library", "/library/"),
       ("About", "/about/"), ("Admissions", "/admissions/")]

def page(title, body, active=None, desc=None):
    nav = "".join(
        f'<a href="{href}"{" aria-current=\"page\"" if active == href else ""}>{e(label)}</a>' for label, href in NAV)
    full_title = f"{title} | {SITE['name']}" if title != SITE["name"] else title
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(full_title)}</title>
<meta name="description" content="{e(desc or SITE['tagline'])}">
<meta name="theme-color" content="#7a1f24">
{'<meta name="robots" content="noindex, nofollow">' if SITE.get("concept") else ""}
<link rel="icon" href="/assets/favicon.png">
<link rel="apple-touch-icon" href="/assets/apple-touch-icon.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=EB+Garamond:ital,wght@0,400;0,500;1,400&family=Source+Sans+3:wght@400;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/assets/site.css">
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
{f'<div class="concept">Unofficial redesign concept. Not affiliated with or endorsed by The Log College &amp; Seminary. <a href="{e(SITE["official_url"])}" rel="noopener">Visit the official site</a></div>' if SITE.get("concept") else ""}
<div class="utility"><div class="wrap">
  <div class="pills"><span>Completely Reformed</span><span>Completely online</span><span>Completely free</span></div>
  <div class="contact"><a href="mailto:{e(SITE['email'])}">{e(SITE['email'])}</a></div>
</div></div>
<header class="site-header"><div class="wrap">
  <a class="brand" href="/" aria-label="{e(SITE['name'])}, home"><img src="/assets/logo.png" alt="{e(SITE['name'])}" width="1748" height="313"></a>
  <button class="menu-btn" type="button" aria-expanded="false" aria-controls="site-nav">{ICON['menu']}Menu</button>
  <nav class="nav" id="site-nav" aria-label="Main">
    <div class="nav-head"><img src="/assets/logo.png" alt="" width="1748" height="313"><button class="menu-close" type="button" aria-label="Close menu"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18"/></svg></button></div>
    {nav}<a class="btn btn-primary" href="/admissions/">Apply</a>
    <p class="nav-foot"><a href="mailto:{e(SITE['email'])}">{e(SITE['email'])}</a><br>{e(SITE['address'])}</p>
  </nav>
</div></header>
<main id="main">
{body}
</main>
{cta()}
<footer class="site-footer"><div class="wrap">
  <div class="foot-grid">
    <div>
      <div class="foot-logo"><img src="/assets/logo.png" alt="" width="1748" height="313"></div>
      <p>{e(SITE['address'])}<br><a href="mailto:{e(SITE['email'])}">{e(SITE['email'])}</a></p>
      <p>Affiliate member of the <a href="{e(SITE['arts_url'])}" rel="noopener">Association of Reformed Theological Seminaries</a>.</p>
    </div>
    <div><h4>Programs</h4><ul>{"".join(f'<li><a href="/programs/{p["slug"]}/">{e(p["name"])}</a></li>' for p in PROGRAMS if p["level"] != "doctoral")}</ul></div>
    <div><h4>Doctoral</h4><ul>{"".join(f'<li><a href="/programs/{p["slug"]}/">{e(p["name"])}</a></li>' for p in PROGRAMS if p["level"] == "doctoral")}</ul></div>
    <div><h4>Explore</h4><ul>
      <li><a href="/courses/">Course Catalog</a></li><li><a href="/library/">Resource Library</a></li>
      <li><a href="/about/">About LCS</a></li><li><a href="/admissions/">Admissions</a></li>
      <li><a href="/about/#standards">Statement of Faith</a></li>
      <li><a href="{e(SITE['facebook'])}" rel="noopener">Facebook</a></li></ul></div>
  </div>
  <div class="foot-base">
    <span>&copy; The Log College &amp; Seminary. All rights reserved.</span>
    <span>Course details are transcribed from the official program guides. The PDF guide for each program is authoritative.</span>
  </div>
</div></footer>
<script src="/assets/site.js" defer></script>
</body>
</html>
"""

def cta():
    return f"""<section class="cta"><div class="wrap">
  <div><h2>Study with a mentor, in your own church.</h2><p>No tuition, no relocation, textbooks provided.</p></div>
  <div class="btn-row"><a class="btn btn-light" href="/admissions/">How to apply {ICON['arrow']}</a><a class="btn btn-outline" href="{e(ask_link('Question about LCS programs'))}">Ask a question</a><a class="btn btn-outline" href="/admissions/#mentor-req">Mentor requirements</a></div>
</div></section>"""

def crumbs(*parts):
    out = ['<nav class="crumbs" aria-label="Breadcrumb"><a href="/">Home</a>']
    for label, href in parts:
        out.append('<span aria-hidden="true">/</span>')
        out.append(f'<a href="{href}">{e(label)}</a>' if href else f'<span aria-current="page">{e(label)}</span>')
    out.append("</nav>")
    return "".join(out)

def write(rel, html):
    path = OUT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html)


PATHWAYS = [
    ("Called to pastoral ministry", "Prepare to shepherd God's people as a pastor.",
     [("mdiv", "With a bachelor's degree in any field"), ("bdiv", "For men over 30 without an undergraduate degree")]),
    ("A foundation in Bible and theology", "Study the core biblical and theological disciplines.",
     [("ats", "With a high school diploma or GED"), ("bts", "With an associate degree or equivalent")]),
    ("Graduate study of Scripture or doctrine", "Go deeper after a bachelor's degree.",
     [("mbs", "The canonical books; credits transfer into the M.Div."), ("mts", "Advanced study across the theological fields")]),
    ("Counseling God's people", "Train to counsel from Scripture.",
     [("thm-nc", "After a counseling master's, the LCS MTS, or an M.Div."), ("thd-nc", "After an M.Div., the LCS MTS, or the LCS Th.M.")]),
    ("Already serving as a pastor", "Sharpen your ministry with advanced study.",
     [("dmin", "M.Div. plus three years of ministry after it")]),
    ("Doctoral research", "Scholarship in the Puritans or the history of the church.",
     [("thd-puritan", "After a 60-hour theological master's"), ("thd-church-history", "After a 60-hour theological master's")]),
]

def pathways_block():
    by = {p["slug"]: p for p in PROGRAMS}
    cards = []
    for title, sub, opts in PATHWAYS:
        links = "".join(
            f'<li><a href="/programs/{s}/"><strong>{e(by[s]["name"])}</strong><span>{e(why)}</span></a></li>'
            for s, why in opts if s in by)
        cards.append(f'<div class="path"><h3>{e(title)}</h3><p>{e(sub)}</p><ul>{links}</ul></div>')
    return f'<div class="paths">{"".join(cards)}</div>'

def credit_areas(p):
    areas = OrderedDict()
    for li in p["course_list"]:
        cr = li.get("credits") or 0
        if not cr:
            continue
        d = dept_name(dept_of(li["code"]))
        areas[d] = areas.get(d, 0) + cr
    rows = sorted(areas.items(), key=lambda kv: -kv[1])
    total = sum(areas.values()) or 1
    top = rows[0][1] if rows else 1
    lis = "".join(
        f'<li><span class="a-name">{e(name)}</span><span class="a-bar"><span style="width:{cr / top * 100:.1f}%"></span></span><span class="a-cr">{cr} <small>({cr / total * 100:.0f}%)</small></span></li>'
        for name, cr in rows)
    note = ""
    if any(li.get("group") for li in p["course_list"]):
        note = '<p class="muted" style="font-size:.86rem;margin-top:8px">Includes every concentration listed in the guide; a student completes one.</p>'
    return f'<ul class="areas" aria-label="Credit hours by subject area">{lis}</ul>{note}'

def ask_link(subject):
    from urllib.parse import quote
    return f'mailto:{SITE["email"]}?subject={quote(subject)}'

# ---------------------------------------------------------------- components
def program_card(p):
    st = program_stats(p)
    dur = p["duration"]["full"] + (" full-time" if p["duration"].get("part") else "")
    return f"""<a class="card" href="/programs/{p['slug']}/">
  <span class="go">{ICON['arrow']}</span>
  <span class="abbr">{e(prog_label(p))}</span>
  <h4>{e(p['name'])}</h4>
  <p>{e(p['summary'])}</p>
  <div class="meta"><span>{p['credit_hours']} credit hours</span><span>{plural(len(p['course_list']), 'course')}</span><span>{e(dur)}</span></div>
</a>"""

def programs_by_level():
    out = []
    for lvl in ("undergraduate", "graduate", "doctoral"):
        ps = [p for p in PROGRAMS if p["level"] == lvl]
        if not ps:
            continue
        out.append(f'<div class="level-block" data-level="{lvl}"><h3>{e(LEVEL_LABEL[lvl])} programs</h3><div class="cards">'
                   + "".join(program_card(p) for p in ps) + "</div></div>")
    return "".join(out)

def render_items(items):
    lis = []
    for it in items:
        by = f' <span class="by">&mdash; {e(it["by"])}</span>' if it.get("by") else ""
        note = f'<span class="note">{e(it["note"])}</span>' if it.get("note") else ""
        ext = fmt_extent(it)
        x = f'<span class="x">{e(ext.strip())}</span>' if ext else ""
        title = e(it.get("title"))
        if it.get("url"):
            title = f'<a class="t" href="{e(it["url"])}" target="_blank" rel="noopener">{title}<span class="sr-only"> (opens in a new tab)</span></a>'
        else:
            title = f'<span class="t">{title}</span>'
        vols = "".join(f' <a class="vol" href="{e(v["url"])}" target="_blank" rel="noopener">{e(v["label"])}</a>' for v in it.get("urls", []))
        lis.append(f'<li><span>{title}{vols}{by}{note}</span>{x}</li>')
    return f'<ul class="items">{"".join(lis)}</ul>' if lis else ""

KIND_LABEL = {"lectures": "Lectures", "readings": "Reading", "assignment": "Assignment", "review": "Review"}

def render_course_body(c, show_link=True, programs_note=None):
    parts = []
    pre = c.get("prerequisite") or c.get("prerequisites")
    if pre:
        pre = pre if isinstance(pre, str) else ", ".join(pre)
        parts.append(f'<div class="scripture"><strong>Prerequisite:</strong> {e(pre)}</div>')
    for k in ("note", "notes"):
        v = c.get(k)
        if v:
            for t in ([v] if isinstance(v, str) else v):
                parts.append(f'<div class="scripture">{e(t)}</div>')
    if c.get("scripture_reading"):
        parts.append(f'<div class="scripture"><strong>Scripture reading:</strong> {e(c["scripture_reading"])}</div>')
    for s in c.get("sections", []):
        n = f'<span class="task-n">{e(s["n"])}</span>' if s.get("n") is not None else '<span class="task-n" aria-hidden="true">&middot;</span>'
        head = f'<div class="task-head">{n}<div><div class="task-kind">{KIND_LABEL.get(s["type"], s["type"])}</div><div class="task-ins">{e(s.get("instruction"))}</div></div></div>'
        total = f'<div class="task-total">Total: {e(s["total"])}</div>' if s.get("total") else ""
        parts.append(f'<div class="task">{head}{render_items(s.get("items", []))}{total}</div>')
    st = course_stats(c)
    bits = []
    if st["minutes"]: bits.append(f"{hours(st['minutes'])} lecture hours")
    if st["pages"]: bits.append(f"{st['pages']:,} pages")
    if st["papers"]: bits.append(plural(st["papers"], "written assignment"))
    foot = f'<span>{" &middot; ".join(bits)}</span>' if bits else "<span></span>"
    if show_link:
        foot += f'<a class="btn-ghost" href="/courses/{slug_code(c["code"])}/">Course page {ICON["arrow"].replace("<svg", "<svg width=14 height=14")}</a>'
    return f'<div class="course-body">{"".join(parts)}<div class="foot">{foot}</div></div>'

def render_course_row(code, title, credits, c, open_=False):
    cr = f"{credits} credit hour{'s' if credits != 1 else ''}" if credits else ""
    if c is None:
        return f"""<div class="course"><div style="display:grid;grid-template-columns:82px 1fr auto;gap:14px;padding:15px 18px;align-items:center">
<span class="code">{e(code)}</span><span class="title">{e(title)}<span class="muted" style="display:block;font-weight:400;font-size:.86rem">Course detail not included in this program guide. See the <a href="/courses/{slug_code(code)}/">course page</a>.</span></span><span class="cr">{cr}</span></div></div>"""
    return f"""<details class="course" id="c-{slug_code(code)}"{' open' if open_ else ''}>
<summary><span class="code">{e(code)}</span><span class="title">{e(title)}</span><span class="cr">{cr}</span>{ICON['chev']}</summary>
{render_course_body(c)}
</details>"""

# ---------------------------------------------------------------- pages
def build_home():
    n_courses = len(set(COURSE_OCC) | set(LIST_ONLY))
    stats = f"""<div class="stats">
  <div class="stat"><b>{len(PROGRAMS)}</b><span>degree programs</span></div>
  <div class="stat"><b>{n_courses}</b><span>courses, every one published</span></div>
  <div class="stat"><b>{hours(UNIQUE_MIN)}</b><span>hours of assigned lectures</span></div>
  <div class="stat"><b>{len(LIB):,}</b><span>lectures, books and resources</span></div>
</div>"""
    body = f"""<section class="hero"><div class="wrap">
  <div>
    <p class="eyebrow">Reformed seminary education &middot; Since 2008</p>
    <h1>Continuing a legacy of Reformed education, experientialism, and evangelism</h1>
    <p class="lede">Theological education restored to the local church. Rigorous programs from the associate to the doctoral level, completed under a pastor's mentorship, with no tuition and no debt.</p>
    <div class="btn-row"><a class="btn btn-primary" href="/programs/">Explore programs {ICON['arrow']}</a><a class="btn btn-secondary" href="/admissions/">How to apply</a></div>
  </div>
  <div class="hero-art">
    <img src="/assets/cabin.png" alt="Sketch of the original Log College building at Neshaminy" width="394" height="297">
    <blockquote>&ldquo;What you have heard from me in the presence of many witnesses entrust to faithful men, who will be able to teach others also.&rdquo;<cite>2 Timothy 2:2</cite></blockquote>
  </div>
</div>
<div class="wrap"><div class="pillars">
  <div class="pillar"><h3>Completely Reformed</h3><p>Grounded in the inspired, inerrant Word of God and committed to the Westminster Standards (1788 American Revision).</p></div>
  <div class="pillar"><h3>Completely online</h3><p>Study anytime, from anywhere. No need to relocate or leave your local church fellowship.</p></div>
  <div class="pillar"><h3>Completely free</h3><p>No tuition, no fees, no room and board. Even the textbooks are provided.</p></div>
</div></div></section>

<section class="section"><div class="wrap">
  <div class="section-head"><div><p class="eyebrow">Find your program</p><h2>Where are you headed?</h2></div><p>Start from your calling and the education you already have. Each path lists the programs that fit and what you need to begin.</p></div>
  {pathways_block()}
</div></section>

<section class="section alt"><div class="wrap">
  <div class="section-head"><div><p class="eyebrow">Academics</p><h2>All degree programs</h2></div><p>Every course, lecture, and reading in every program is listed openly, so you can see exactly what you will study before you apply.</p></div>
  {programs_by_level()}
</div></section>

<section class="section"><div class="wrap">
  <div class="section-head"><div><p class="eyebrow">The whole curriculum, in the open</p><h2>Browse what you will study</h2></div></div>
  {stats}
  <div class="btn-row" style="margin-top:24px"><a class="btn btn-secondary" href="/courses/">Open the course catalog</a><a class="btn btn-secondary" href="/library/">Search the resource library</a></div>
</div></section>

<section class="section alt"><div class="wrap cols-2">
  <div><p class="eyebrow">The old Puritan apprenticeship model</p><h2>Taught through mentoring</h2>
  <p>Each student studies under a qualified, experienced pastor within the ministry context of his or her own local church. The mentor guides the studies, grades every assignment, and helps the student apply biblical principles to life.</p>
  <p>LCS does not seek to replace the local church but to serve it, providing curriculum and educational support for equipping the saints for the work of ministry (Ephesians 4:11&ndash;12).</p>
  <a class="btn-ghost" href="/about/">Our history and distinctives {ICON['arrow'].replace('<svg', '<svg width=14 height=14')}</a></div>
  <div class="panel"><h3>How a course works</h3>
    <ol class="numbered">
      <li><h3>Listen</h3><p class="muted">Outline and take notes on the assigned lecture series.</p></li>
      <li><h3>Read</h3><p class="muted">Summarize the assigned books chapter by chapter.</p></li>
      <li><h3>Write</h3><p class="muted">Complete the papers, then submit everything to your mentor for grading.</p></li>
    </ol>
  </div>
</div></section>"""
    write("index.html", page(SITE["name"], body, desc="Free, online, mentored Reformed seminary programs: every course, lecture, and reading listed openly."))

def build_programs_index():
    rows = "".join(f"<tr><td><a href=\"/programs/{p['slug']}/\">{e(p['name'])}</a></td><td>{p['credit_hours']}</td><td>{e(p['duration']['full'])}</td><td>{e(p['duration']['part'] or '—')}</td><td>{e(p.get('admission') or '')}</td></tr>" for p in PROGRAMS)
    standards = "".join(f"<div class=\"panel\"><h3>{e(v['label'])}</h3><ul class=\"checks\">{''.join(f'<li>{e(x)}</li>' for x in v['standard'])}</ul></div>" for v in SITE["levels"].values())
    body = f"""<section class="page-head"><div class="wrap">
  {crumbs(("Programs", None))}
  <p class="eyebrow">Academics</p>
  <h1>Degree programs</h1>
  <p class="lede">Eleven programs, from the Associate of Theological Studies to the Doctor of Theology. Each one is completed online under the oversight of an approved mentor.</p>
</div></section>
<section class="section" style="padding-bottom:24px"><div class="wrap">
  <div class="section-head"><div><p class="eyebrow">Find your program</p><h2>Start from your calling</h2></div></div>
  {pathways_block()}
</div></section>
<section class="section" style="padding-top:24px"><div class="wrap">{programs_by_level()}</div></section>
<section class="section alt" id="standards"><div class="wrap">
  <div class="section-head"><div><p class="eyebrow">Academic standards</p><h2>What each credit hour requires</h2></div><p>The programs are free, but they require dedication and hard work. Standards are high, not for the sake of achievement but for the sake of worship.</p></div>
  <div class="cards">{standards}</div>
</div></section>
<section class="section"><div class="wrap">
  <div class="section-head"><div><p class="eyebrow">At a glance</p><h2>Compare programs</h2></div></div>
  <div style="overflow-x:auto"><table class="table-plain"><thead><tr><th>Program</th><th>Credits</th><th>Full-time</th><th>Part-time</th><th>Admission</th></tr></thead><tbody>{rows}</tbody></table></div>
</div></section>"""
    write("programs/index.html", page("Degree Programs", body, active="/programs/"))

def build_program(p):
    st = program_stats(p)
    groups = OrderedDict()
    for li in p["course_list"]:
        groups.setdefault(li.get("group"), []).append(li)
    detail = {c["code"]: c for c in p["courses"]}
    curr = []
    for g, lis in groups.items():
        if g:
            gcred = sum(li.get("credits") or 0 for li in lis)
            curr.append(f'<h3 class="group-title">{e(g)} &middot; {gcred} credit hours</h3>')
        for li in lis:
            c = detail.get(li["code"])
            curr.append(render_course_row(li["code"], li.get("title") or (c or {}).get("title"), li.get("credits"), c))
    # detail blocks that are not in the course list
    listed = {li["code"] for li in p["course_list"]}
    extra = [c for c in p["courses"] if c["code"] not in listed]
    if extra:
        curr.append('<h3 class="group-title">Additional courses in the guide</h3>')
        for c in extra:
            curr.append(render_course_row(c["code"], c.get("title"), c.get("credits"), c))
    reqs = "".join(f"<li>{e(r)}</li>" for r in p.get("requirements", []) if "broken link" not in r.lower())
    restricted = f'<p class="note-box">{e(p["restricted"])}, as stated in the LCS admission requirements.</p>' if p.get("restricted") else ""
    dur_part = f'<div class="fact"><dt>Part-time</dt><dd>{e(p["duration"]["part"])}</dd></div>' if p["duration"].get("part") else ""
    body = f"""<section class="page-head"><div class="wrap">
  {crumbs(("Programs", "/programs/"), (p["name"], None))}
  <p class="eyebrow">{e(LEVEL_LABEL[p['level']])} program &middot; {e(prog_label(p))}</p>
  <h1>{e(p['name'])}</h1>
  <p class="lede">{e(p['summary'])}</p>
  <dl class="facts">
    <div class="fact"><dt>Credit hours</dt><dd>{p['credit_hours']}</dd></div>
    <div class="fact"><dt>{'Full-time' if p['duration'].get('part') else 'Time to complete'}</dt><dd>{e(p['duration']['full'])}</dd></div>
    {dur_part}
    <div class="fact"><dt>Format</dt><dd>Online, mentored</dd></div>
    <div class="fact"><dt>Tuition</dt><dd>Free</dd></div>
  </dl>
</div></section>
<div class="wrap layout">
  <div class="prose">
    <section id="overview"><h2>Overview</h2><p>{e(p['description'])}</p>
      <div class="load">
        <div><b>{len(p['course_list'])}</b><span>courses</span></div>
        <div><b>{hours(st['minutes'])}</b><span>lecture hours</span></div>
        <div><b>{st['pages']:,}</b><span>pages of reading</span></div>
        <div><b>{st['papers']}</b><span>written assignments</span></div>
      </div>
      <p class="muted" style="margin-top:10px;font-size:.88rem">Totals are added up from the program guide; a few items list no length, so the real load is slightly higher.</p>
    </section>
    <section id="areas"><h2>Credit hours by subject</h2>{credit_areas(p)}</section>
    <section id="admission"><h2>Admission</h2>
      <p><strong>Requirement:</strong> {e(p.get('admission'))}</p>{restricted}
      <p>Every applicant must also be a communing member in good standing of a local church, present a letter of recommendation from a church officer, and propose a qualified mentor. <a href="/admissions/">Full admission requirements</a>.</p>
    </section>
    <section id="requirements"><h2>Program requirements</h2><ul class="checks">{reqs}</ul></section>
    <section id="curriculum"><h2>Curriculum</h2>
      <div class="toolbar"><p class="muted" style="margin:0">Open a course to see its lectures, readings, and assignments.</p><button class="linkish" type="button" data-toggle-all>Expand all</button></div>
      {''.join(curr)}
    </section>
    <section id="guide"><h2>Official program guide</h2>
      <p>The PDF guide from the seminary is the authoritative version of this program and includes a link to every lecture and reading.</p>
      <a class="btn btn-secondary" href="{e(p['pdf'])}" rel="noopener" target="_blank">{ICON['download']}Open the {e(prog_label(p))} guide (PDF)</a>
    </section>
  </div>
  <aside>
    <div class="panel"><h3>Ready to begin?</h3>
      <a class="btn btn-primary" href="/admissions/">How to apply</a>
      <a class="btn btn-secondary" href="{e(p['pdf'])}" rel="noopener" target="_blank">{ICON['download']}Program guide (PDF)</a>
      <a class="btn btn-secondary" href="/programs/{p['slug']}/checklist/">Printable checklist</a>
      <small><a href="{e(ask_link('Question about the ' + p['name']))}">Ask a question about this program</a></small>
    </div>
    <nav class="panel toc" aria-label="On this page"><h3>On this page</h3><ol>
      <li><a href="#overview">Overview</a></li><li><a href="#areas">By subject</a></li><li><a href="#admission">Admission</a></li>
      <li><a href="#requirements">Requirements</a></li><li><a href="#curriculum">Curriculum</a></li><li><a href="#guide">Program guide</a></li></ol></nav>
  </aside>
</div>"""
    write(f"programs/{p['slug']}/index.html", page(p["name"], body, active="/programs/", desc=p["summary"]))
    build_checklist(p)

def task_line(s):
    items = s.get("items", [])
    if s["type"] == "lectures":
        m = sum(i.get("minutes") or 0 for i in items)
        extra = s.get("total") or (f"{hours(m)} hours" if m else "")
        return f"Lectures: {plural(len(items), 'series', 'series')}" + (f" ({extra})" if extra else "")
    if s["type"] == "readings":
        pg = sum(i.get("pages") or 0 for i in items)
        extra = s.get("total") or (f"{pg:,} pages" if pg else "")
        return f"Reading: {plural(len(items), 'title')}" + (f" ({extra})" if extra else "")
    return s.get("instruction") or ""

def build_checklist(p):
    detail = {c["code"]: c for c in p["courses"]}
    rows = []
    group = None
    for li in p["course_list"]:
        if li.get("group") and li.get("group") != group:
            group = li["group"]
            rows.append(f'<tr class="grp"><td colspan="4">{e(group)}</td></tr>')
        c = detail.get(li["code"])
        tasks = ""
        if c:
            ts = [s for s in c.get("sections", []) if s["type"] != "review"]
            tasks = "".join(f'<li><span class="box" aria-hidden="true"></span>{e((str(s["n"]) + ". ") if s.get("n") is not None else "")}{e(task_line(s))}</li>' for s in ts)
            tasks = f'<ul class="tasks">{tasks}</ul>'
        rows.append(f'<tr><td><strong>{e(li["code"])}</strong> {e(li.get("title"))}{tasks}</td><td class="c">{e(li.get("credits") or "")}</td><td class="blank"></td><td class="blank"></td></tr>')
    reqs = "".join(f'<li><span class="box" aria-hidden="true"></span>{e(r)}</li>' for r in p.get("requirements", []) if "broken link" not in r.lower())
    body = f"""<section class="page-head no-print"><div class="wrap">
  {crumbs(("Programs", "/programs/"), (p["name"], f"/programs/{p['slug']}/"), ("Checklist", None))}
  <h1>{e(p['name'])} checklist</h1>
  <p class="lede">Every course and numbered assignment on one sheet, for you and your mentor. Print it, or save it as a PDF from the print dialog.</p>
  <div class="btn-row" style="margin-top:20px"><button class="btn btn-primary" type="button" onclick="window.print()">Print checklist</button><a class="btn btn-secondary" href="/programs/{p['slug']}/">Back to the program</a></div>
</div></section>
<div class="wrap checklist">
  <div class="print-head"><img src="/assets/logo.png" alt="" width="1748" height="313"><div><strong>{e(p['name'])}</strong> &middot; {p['credit_hours']} credit hours</div></div>
  <div class="fields"><span>Student</span><span>Mentor</span><span>Start date</span></div>
  <table><thead><tr><th>Course and assignments</th><th class="c">Credits</th><th>Completed</th><th>Grade</th></tr></thead><tbody>{''.join(rows)}</tbody></table>
  <h2>Program requirements</h2><ul class="tasks reqs">{reqs}</ul>
  <p class="muted src">Transcribed from the official program guide. The guide is authoritative.</p>
</div>"""
    write(f"programs/{p['slug']}/checklist/index.html", page(f"{p['name']} checklist", body, active="/programs/"))

def build_catalog():
    codes = list(OrderedDict.fromkeys(list(COURSE_OCC) + list(LIST_ONLY)))
    def sort_key(code):
        m = re.match(r"([A-Z]+)(\d+)", code)
        order = list(DEPTS).index(m.group(1)) if m and m.group(1) in DEPTS else 99
        return (order, int(m.group(2)) if m else 0, code)
    codes.sort(key=sort_key)
    dept_count = defaultdict(int)
    items = []
    for code in codes:
        occ = COURSE_OCC.get(code)
        c = occ[0][1] if occ else LIST_ONLY[code][0][1]
        progs = programs_for_code(code)
        d = dept_of(code)
        dept_count[d] += 1
        lv = sorted({p["level"] for p in progs})
        st = course_stats(c) if occ else None
        sub = []
        if c.get("credits"): sub.append(f"{c['credits']} credit hours")
        if st and st["minutes"]: sub.append(f"{hours(st['minutes'])} lecture hours")
        if st and st["pages"]: sub.append(f"{st['pages']:,} pages")
        tags = "".join(f'<span class="tag">{e(prog_label(p))}</span>' for p in progs)
        search = " ".join([code, c.get("title") or "", dept_name(d)] + [p["name"] for p in progs])
        items.append(f'<a class="cat-item" href="/courses/{slug_code(code)}/" data-dept="{d}" data-levels="{" ".join(lv)}" data-search="{e(search.lower())}">'
                     f'<span class="code" style="font:700 .85rem ui-monospace,Menlo,monospace;color:var(--accent)">{e(code)}</span>'
                     f'<span><strong>{e(c.get("title"))}</strong><span class="sub">{" &middot; ".join(sub)}</span></span><span class="tags">{tags}</span></a>')
    dopts = "".join(f'<option value="{d}">{e(dept_name(d))} ({dept_count[d]})</option>' for d in sorted(dept_count, key=lambda d: list(DEPTS).index(d) if d in DEPTS else 99))
    lchips = "".join(f'<label class="chip"><input type="radio" name="level" value="{k}">{e(v)}</label>' for k, v in LEVEL_LABEL.items())
    body = f"""<section class="page-head"><div class="wrap">
  {crumbs(("Course Catalog", None))}
  <p class="eyebrow">Academics</p><h1>Course catalog</h1>
  <p class="lede">Every course across all eleven programs, with the programs that require it. Open a course for its full list of lectures, readings, and assignments.</p>
</div></section>
<section class="section" style="padding-top:36px"><div class="wrap" data-filter-root data-item=".cat-item">
  <div class="filters">
    <div class="search">{ICON['search']}<label class="sr-only" for="q">Search courses</label><input id="q" type="search" placeholder="Search by course, code, or program" data-q></div>
    <div class="select"><label class="sr-only" for="dept">Department</label><select id="dept" name="dept"><option value="">All departments</option>{dopts}</select></div>
  </div>
  <div class="filters"><div class="chips" role="radiogroup" aria-label="Level"><label class="chip"><input type="radio" name="level" value="" checked>All levels</label>{lchips}</div></div>
  <p class="result-count" data-count aria-live="polite"></p>
  <div class="cat-list">{''.join(items)}</div>
  <div class="empty" data-empty hidden><p><strong>No courses match.</strong></p><p>Try a different word, or clear the filters.</p><button class="btn btn-secondary" type="button" data-clear>Clear filters</button></div>
</div></section>"""
    write("courses/index.html", page("Course Catalog", body, active="/courses/"))
    return codes

def build_course_pages(codes):
    for code in codes:
        occ = COURSE_OCC.get(code, [])
        progs = programs_for_code(code)
        first = occ[0][1] if occ else LIST_ONLY[code][0][1]
        variants = OrderedDict()
        for p, c in occ:
            variants.setdefault(sig(c), {"c": c, "programs": []})["programs"].append(p)
        blocks = []
        if not occ:
            blocks.append('<div class="empty"><p><strong>No detailed syllabus in the program guides.</strong></p><p>This course appears in a program\'s course list, but the guide does not include its lectures and readings. Check the PDF guide or ask the seminary.</p></div>')
        for v in variants.values():
            if len(variants) > 1:
                blocks.append(f'<h2 style="font-size:1.5rem;margin-top:8px">As assigned in {e(", ".join(prog_label(p) for p in v["programs"]))}</h2>')
            blocks.append(f'<div class="course" style="margin-bottom:28px">{render_course_body(v["c"], show_link=False)}</div>')
        plinks = "".join(f'<li><a href="/programs/{p["slug"]}/#c-{slug_code(code)}">{e(p["name"])}</a></li>' for p in progs)
        st = course_stats(first) if occ else {"minutes": 0, "pages": 0, "papers": 0}
        facts = f'<div class="fact"><dt>Department</dt><dd>{e(dept_name(dept_of(code)))}</dd></div>'
        if first.get("credits"): facts += f'<div class="fact"><dt>Credit hours</dt><dd>{first["credits"]}</dd></div>'
        if st["minutes"]: facts += f'<div class="fact"><dt>Lectures</dt><dd>{hours(st["minutes"])} hours</dd></div>'
        if st["pages"]: facts += f'<div class="fact"><dt>Reading</dt><dd>{st["pages"]:,} pages</dd></div>'
        body = f"""<section class="page-head"><div class="wrap">
  {crumbs(("Course Catalog", "/courses/"), (code, None))}
  <p class="eyebrow">{e(code)} &middot; {e(dept_name(dept_of(code)))}</p>
  <h1>{e(first.get('title'))}</h1>
  <dl class="facts">{facts}</dl>
</div></section>
<div class="wrap layout">
  <div>{''.join(blocks)}</div>
  <aside><div class="panel"><h3>Required in</h3><ul class="checks" style="font-size:.95rem">{plinks}</ul>
  <small>All numbered assignments are submitted to your mentor for grading.</small></div></aside>
</div>"""
        write(f"courses/{slug_code(code)}/index.html", page(f"{code} {first.get('title')}", body, active="/courses/"))

def build_library():
    rows = []
    recs = sorted(LIB.values(), key=lambda r: (norm(r["title"])))
    for r in recs:
        used = "".join(f'<a href="/courses/{slug_code(c)}/" title="{e(t)}">{e(c)}</a>' for c, t in r["codes"].items())
        search = " ".join([r["title"] or "", r["by"] or "", " ".join(r["codes"])]).lower()
        rows.append(f'<tr class="lib-row" data-kind="{r["kind"].lower()}" data-search="{e(search)}"><td><span class="kind">{r["kind"]}</span>{(f'<a class="t" href="{e(r["url"])}" target="_blank" rel="noopener">{e(r["title"])}</a>') if r.get("url") else f'<span class="t">{e(r["title"])}</span>'}</td>'
                    f'<td>{e(r["by"] or "")}</td><td class="num">{e(r["extent"] or "")}</td><td class="used">{used}</td></tr>')
    n_lec = sum(1 for r in LIB.values() if r["kind"] == "Lecture")
    n_read = len(LIB) - n_lec
    body = f"""<section class="page-head"><div class="wrap">
  {crumbs(("Resource Library", None))}
  <p class="eyebrow">Resources</p><h1>Resource library</h1>
  <p class="lede">Every lecture series, book, and article assigned across the curriculum, in one searchable list. Search by title, speaker, author, or course code.</p>
</div></section>
<section class="section" style="padding-top:36px"><div class="wrap" data-filter-root data-item=".lib-row" data-page="60">
  <div class="filters">
    <div class="search">{ICON['search']}<label class="sr-only" for="lq">Search resources</label><input id="lq" type="search" placeholder="Try &ldquo;Sproul&rdquo;, &ldquo;Westminster&rdquo;, or &ldquo;TH531&rdquo;" data-q></div>
    <div class="chips" role="radiogroup" aria-label="Type">
      <label class="chip"><input type="radio" name="kind" value="" checked>All <span class="n">{len(LIB):,}</span></label>
      <label class="chip"><input type="radio" name="kind" value="lecture">Lectures <span class="n">{n_lec:,}</span></label>
      <label class="chip"><input type="radio" name="kind" value="reading">Readings <span class="n">{n_read:,}</span></label>
    </div>
  </div>
  <p class="result-count" data-count aria-live="polite"></p>
  <table class="lib"><thead><tr><th>Title</th><th>Speaker / author</th><th>Length</th><th>Used in</th></tr></thead><tbody>{''.join(rows)}</tbody></table>
  <div class="more"><button class="btn btn-secondary" type="button" data-more>Show more</button></div>
  <div class="empty" data-empty hidden><p><strong>Nothing matches that search.</strong></p><p>Check the spelling, or search a speaker's last name only.</p><button class="btn btn-secondary" type="button" data-clear>Clear search</button></div>
  <p class="muted" style="margin-top:20px;font-size:.9rem">Titles link to the lecture or text named in the official program guides. Links point to third-party sites; report a broken one to <a href="mailto:info@logcollege.net">info@logcollege.net</a>.</p>
</div></section>"""
    write("library/index.html", page("Resource Library", body, active="/library/"))

def build_about():
    pdfs = "".join(f'<li><a href="{e(u)}" rel="noopener" target="_blank">{e(t)}</a></li>' for t, u in SITE["standards_pdfs"])
    body = f"""<section class="page-head"><div class="wrap">
  {crumbs(("About", None))}
  <p class="eyebrow">About LCS</p><h1>A different approach to seminary education</h1>
  <p class="lede">A decidedly Reformed seminary that educates the body of Christ completely free of charge, so graduates can follow God's call instead of paying off seminary debt.</p>
</div></section>
<div class="wrap layout"><div class="prose">
  <section id="mission"><h2>Mission and vision</h2>
    <p>The Log College &amp; Seminary desires to see theological education restored to the local church. Ministry preparation is, after all, a part of the church's discipleship task. LCS serves the local church by providing an academic platform pastors can use to train their members for ministry and to train men called to the work of the gospel ministry.</p>
    <p>The vision is to help prepare a new generation of Reformed pastors who are passionate for the glory of God, the proclamation of the gospel, and the equipping of the church for ministry, without the financial obligation of the traditional seminary.</p>
  </section>
  <section id="history"><h2>Our history</h2>
    <p>Originally established as The North American Reformed Seminary (TNARS) in 2008, the seminary was renamed to continue the mission, vision, and values of the original Log College of Neshaminy, the first free Presbyterian seminary in America.</p>
    <ol class="numbered">
      <li><h3>Historical</h3><p>As the Log College was the first free Presbyterian seminary, TNARS was the first free online Presbyterian seminary. It operates solely on the gifts of students, churches, and friends.</p></li>
      <li><h3>Methodological</h3><p>A pastoral apprenticeship model: students study theology under a qualified pastor within their own local church, as Paul instructed Timothy (2 Timothy 2:1&ndash;2).</p></li>
      <li><h3>Missional</h3><p>Producing pastor-scholars with a passion for knowledge, piety, preaching, and evangelism, with a full course on revival and church revitalization.</p></li>
      <li><h3>Doctrinal</h3><p>The Westminster Standards (1788 American Revision) are the official statement of faith. A full course studies the Standards, and students memorize the Shorter Catechism.</p></li>
      <li><h3>Attestation</h3><p>Like its predecessor, LCS rests on the caliber and fruit of its graduates.</p></li>
    </ol>
    <p style="margin-top:18px"><a href="{e(SITE['history_pdf'])}" rel="noopener" target="_blank">Read &ldquo;The Log College: Yesterday and Today&rdquo; by Dr. John McDonald (PDF)</a></p>
  </section>
  <section id="standards"><h2>Statement of faith</h2>
    <p>The Log College &amp; Seminary affirms the Westminster Standards as its official statement of faith. LCS is not affiliated with a particular denomination, and its students come from both Reformed and non-Reformed backgrounds.</p>
    <ul class="checks">{pdfs}</ul>
  </section>
  <section id="accreditation"><h2>Accreditation</h2>
    <p>LCS is an unaccredited institution, exempt from state regulation because of the religious nature of its programs.* The programs are designed to meet or exceed ATS and ARTS accreditation requirements, but the seminary does not plan to seek regional accreditation, trusting instead the biblical principle &ldquo;by their fruits you shall know them.&rdquo;</p>
    <p>LCS is an affiliate institution of the <a href="{e(SITE['arts_url'])}" rel="noopener">Association of Reformed Theological Seminaries</a>. Affiliate status does not constitute, imply, or presume ARTS accredited status.</p>
    <p class="muted" style="font-size:.88rem">* South Carolina Code of Laws, Nonpublic Postsecondary Institution License Act, Section 59-58-30(4), does not require licensure of an institution whose sole purpose is religious or theological training.</p>
  </section>
  <section id="logo"><h2>Our logo</h2>
    <p>The logo is an exact digitization of the Log College building as portrayed in the only known sketch of it. It was created by Jeremiah and Hyewon Pendleton, who donated their time and talents.</p>
  </section>
</div>
<aside><nav class="panel toc" aria-label="On this page"><h3>On this page</h3><ol>
  <li><a href="#mission">Mission and vision</a></li><li><a href="#history">Our history</a></li><li><a href="#standards">Statement of faith</a></li><li><a href="#accreditation">Accreditation</a></li><li><a href="#logo">Our logo</a></li></ol></nav></aside>
</div>"""
    write("about/index.html", page("About", body, active="/about/"))

def build_admissions():
    rows = "".join(f"<tr><td><a href=\"/programs/{p['slug']}/\">{e(p['name'])}</a></td><td>{e(p.get('admission') or '')}{'<br><span class=\"muted\">' + e(p['restricted']) + '</span>' if p.get('restricted') else ''}</td></tr>" for p in PROGRAMS)
    body = f"""<section class="page-head"><div class="wrap">
  {crumbs(("Admissions", None))}
  <p class="eyebrow">Admissions</p><h1>How to apply</h1>
  <p class="lede">Review the five requirements below, then download and complete the application form.</p>
  <div class="btn-row" style="margin-top:24px"><a class="btn btn-primary" href="{e(SITE['application_pdf'])}" rel="noopener" target="_blank">{ICON['download']}Download the application (PDF)</a><a class="btn btn-secondary" href="mailto:{e(SITE['email'])}">Email admissions</a></div>
</div></section>
<div class="wrap layout"><div class="prose">
  <section id="requirements"><h2>Admission requirements</h2>
  <ol class="numbered">
    <li><h3>Program qualifications</h3><p>Each program has its own prerequisite degree (see the table below). Th.D. applicants need a master's degree of at least 60 credit hours with 12 hours of biblical languages; if languages were not included, BS500/BS501 are completed within the doctoral program. The B.Div., M.Div., and all doctoral programs are restricted to male applicants.</p></li>
    <li><h3>Transcripts</h3><p>ATS and B.Div. applicants submit a copy of their high school diploma or GED. All other programs require official undergraduate and graduate transcripts sent directly to LCS by mail or eSCRIP-SAFE, in English. Non-English transcripts need a course-by-course credit evaluation (LCS recommends Validential).</p></li>
    <li><h3>Church membership</h3><p>Every student must be a communing member in good standing of a local church (or a member of presbytery without censure). There are no exceptions. Your pastor or a church officer sends a letter of recommendation directly to the seminary.</p></li>
    <li id="mentor-req"><h3>Mentor candidate</h3><p>You propose a mentor for approval. Mentors fully subscribe to the Westminster Confession of Faith (1788 American Revision); subscribers to the Savoy Declaration or the 1689 London Baptist Confession may also be considered. They hold a theological master's degree for ATS students, an M.Div. or higher for BTS, B.Div., MBS, MTS, and M.Div. students, and a doctorate for Th.M. and doctoral students.</p></li>
    <li><h3>English proficiency</h3><p>Applicants whose native language is not English submit one of: EFSET 50 (minimum 70, free online), TOEFL iBT (minimum 95, school code B330), or IELTS (minimum 7.0), taken within two years.</p></li>
  </ol></section>
  <section id="by-program"><h2>Requirements by program</h2>
    <div style="overflow-x:auto"><table class="table-plain"><thead><tr><th>Program</th><th>Admission requirement</th></tr></thead><tbody>{rows}</tbody></table></div>
  </section>
  <section id="mentor"><h2>Studying with your mentor</h2>
    <p>You contact your mentor every month by email or phone to report progress, even in a month without progress. Missing three consecutive monthly contacts ends the enrollment. If a mentor can no longer serve, study pauses until a new mentor is approved.</p>
    <h3>Your mentor will</h3>
    <ul class="checks"><li>Provide counsel and instruction through the program</li><li>Provide one-on-one Christian and pastoral discipleship</li><li>Give you opportunities to exercise and test your gifts</li><li>Grade all assignments and keep a record of courses and grades</li><li>Submit that record to the seminary when you complete the program</li></ul>
  </section>
</div>
<aside><div class="panel"><h3>Application</h3>
  <a class="btn btn-primary" href="{e(SITE['application_pdf'])}" rel="noopener" target="_blank">{ICON['download']}Application (PDF)</a>
  <small>Send transcripts and recommendation letters to {e(SITE['address'])}, or by email to <a href="mailto:{e(SITE['email'])}">{e(SITE['email'])}</a>.</small></div></aside>
</div>"""
    write("admissions/index.html", page("Admissions", body, active="/admissions/"))

def build_404():
    body = f"""<section class="page-head"><div class="wrap"><p class="eyebrow">Page not found</p><h1>That page is not here</h1>
<p class="lede">It may have moved. Start from the programs or search the course catalog.</p>
<div class="btn-row" style="margin-top:20px"><a class="btn btn-primary" href="/programs/">Degree programs</a><a class="btn btn-secondary" href="/courses/">Course catalog</a></div></div></section>"""
    write("404.html", page("Page not found", body))

def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(ROOT / "src" / "assets", OUT / "assets")
    build_home(); build_programs_index()
    for p in PROGRAMS:
        build_program(p)
    codes = build_catalog(); build_course_pages(codes)
    build_library(); build_about(); build_admissions(); build_404()
    (OUT / "robots.txt").write_text("User-agent: *\nDisallow: /\n" if SITE.get("concept") else "User-agent: *\nAllow: /\n")
    n = sum(1 for _ in OUT.rglob("*.html"))
    print(f"Built {n} pages for {len(PROGRAMS)} programs, {len(codes)} courses, {len(LIB)} library resources -> {OUT}")

if __name__ == "__main__":
    main()
