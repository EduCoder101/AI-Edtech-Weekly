#!/usr/bin/env python3
"""Build script for AI in EdTech Weekly.

Reads briefings/*.md (the research source files) plus exec_summaries.json
(the executive layer) and generates a styled static site:
  - index.html
  - briefings/<date>.html

Run:  python3 build.py
"""

import json
import re
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent
BRIEFINGS = ROOT / "briefings"
SUMMARIES = json.loads((ROOT / "exec_summaries.json").read_text())

SITE_NAME = "AI in EdTech Weekly"
TAGLINE = "A weekly intelligence briefing on AI in education, for school leaders and teaching staff."

# ---------------------------------------------------------------- utilities

def esc(text):
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

REFRAMES = [
    ("For an AI Integration Lead", "For those leading AI integration"),
    ("an AI Integration Lead", "those leading AI integration"),
    ("the AI Integration Lead", "those leading AI integration"),
]

def inline(text):
    """Convert inline markdown (links, bold, italics) to HTML."""
    for old, new in REFRAMES:
        text = text.replace(old, new)
    text = esc(text.strip())
    # links
    text = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)",
                  r'<a href="\2" target="_blank" rel="noopener">\1</a>', text)
    # bold then italics
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"<em>\1</em>", text)
    # double hyphen to spaced en dash (house style: no em dashes)
    text = re.sub(r"\s+--\s+", " – ", text)
    return text

def fmt_date(iso):
    d = datetime.strptime(iso, "%Y-%m-%d")
    return f"{d.day} {d.strftime('%B %Y')}"

# ---------------------------------------------------------------- parsing

def split_sections(md):
    """Return dict of '## ' section name -> list of lines."""
    sections, current, buf = {}, None, []
    for line in md.splitlines():
        if line.startswith("## "):
            if current:
                sections[current] = buf
            current, buf = line[3:].strip(), []
        elif current:
            buf.append(line)
    if current:
        sections[current] = buf
    return sections

def parse_stories(lines):
    stories, current = [], None
    for line in lines:
        if line.startswith("### "):
            if current:
                stories.append(current)
            m = re.match(r"(\d+)\.\s*(.*)", line[4:].strip())
            current = {"num": m.group(1), "title": m.group(2),
                       "meta": "", "paras": [], "why": "", "sources": ""}
        elif current is not None:
            t = line.strip()
            if not t or t == "---":
                continue
            if not current["meta"] and re.fullmatch(r"\*\*[^*]+\*\*", t):
                current["meta"] = t.strip("*")
            elif t.startswith("**Why it matters"):
                current["why"] = re.sub(r"^\*\*Why it matters[^:]*:\*\*\s*", "", t)
            elif re.match(r"Sources?:", t):
                current["sources"] = re.sub(r"^Sources?:\s*", "", t)
            else:
                current["paras"].append(t)
    if current:
        stories.append(current)
    return stories

def parse_table(lines):
    rows = []
    for line in lines:
        t = line.strip()
        if not t.startswith("|") or re.match(r"^\|[\s\-|]+\|$", t):
            continue
        cells = [c.strip() for c in t.strip("|").split("|")]
        rows.append(cells)
    return rows[1:] if rows else []   # drop header row

def parse_watching(lines):
    items, current = [], None
    for line in lines:
        t = line.strip()
        if not t or t == "---":
            continue
        m = re.match(r"\*\*(\d+)\.\s*(.+?)\*\*$", t)
        if m:
            if current:
                items.append(current)
            current = {"title": m.group(2), "paras": [], "sources": ""}
        elif current:
            if re.match(r"Sources?:", t):
                current["sources"] = re.sub(r"^Sources?:\s*", "", t)
            else:
                current["paras"].append(t)
    if current:
        items.append(current)
    return items

def parse_source_list(lines):
    out = []
    for line in lines:
        t = line.strip()
        m = re.match(r"\d+\.\s+(.*)", t)
        if m:
            out.append(m.group(1))
    return out

def parse_briefing(path):
    md = path.read_text()
    date = path.stem
    sections = split_sections(md)
    cover = ""
    m = re.search(r"Covering (.+?)\.\*", md)
    if m:
        cover = m.group(1).replace("--", "–")
    return {
        "date": date,
        "display": fmt_date(date),
        "covering": cover,
        "stories": parse_stories(sections.get("Top Stories", [])),
        "confluence": parse_table(sections.get("Confluence Table", [])),
        "conflict": parse_table(sections.get("Conflict Table", [])),
        "watching": parse_watching(sections.get("Worth Watching", [])),
        "sourcelist": parse_source_list(sections.get("Source List", [])),
    }

# ---------------------------------------------------------------- styling

CSS = """
:root{
  --paper:#f7f5f0; --card:#ffffff; --ink:#181f30; --ink2:#3c4557;
  --muted:#6f7787; --line:#e4dfd4; --navy:#1b2a4a; --navy2:#223458;
  --accent:#0e7c66; --accent-soft:#e6f1ed; --amber:#a96f24; --amber-soft:#f7eeddd9;
}
*{box-sizing:border-box;margin:0;padding:0}
html{scroll-behavior:smooth}
body{background:var(--paper);color:var(--ink);
  font-family:'Inter',-apple-system,'Segoe UI',sans-serif;
  font-size:17px;line-height:1.65;-webkit-font-smoothing:antialiased}
a{color:var(--accent);text-decoration:none}
a:hover{text-decoration:underline}
.wrap{max-width:980px;margin:0 auto;padding:0 24px}
/* top bar */
.topbar{position:sticky;top:0;z-index:50;background:rgba(247,245,240,.92);
  backdrop-filter:blur(8px);border-bottom:1px solid var(--line)}
.topbar .wrap{display:flex;align-items:center;justify-content:space-between;height:58px}
.brand{font-family:'Fraunces',serif;font-weight:700;font-size:1.05rem;color:var(--ink);letter-spacing:.01em}
.brand:hover{text-decoration:none}
.brand span{color:var(--accent)}
.topnav{display:flex;gap:22px;font-size:.85rem;font-weight:600}
.topnav a{color:var(--ink2)}
/* issue head */
.issuehead{padding:56px 0 36px}
.kicker{font-size:.74rem;font-weight:700;letter-spacing:.14em;text-transform:uppercase;color:var(--accent);margin-bottom:14px}
h1.issue{font-family:'Fraunces',serif;font-weight:600;font-size:clamp(1.6rem,3.6vw,2.1rem);line-height:1.25;letter-spacing:-.01em}
.issuemeta{margin-top:16px;color:var(--muted);font-size:.9rem}
/* glance band */
.glance{background:var(--navy);color:#eef1f7;padding:44px 0 40px}
.glance h2{font-family:'Fraunces',serif;font-weight:600;font-size:1.35rem;color:#fff;margin-bottom:14px}
.glance .overview{font-size:1.02rem;line-height:1.7;color:#d9dfec;max-width:44em}
.glance h3{font-size:.74rem;font-weight:700;letter-spacing:.14em;text-transform:uppercase;color:#8fa8d8;margin:28px 0 12px}
.signals{list-style:none}
.signals li{position:relative;padding:10px 0 10px 26px;border-top:1px solid var(--navy2);font-size:.95rem;line-height:1.6;color:#e7ebf4}
.signals li:before{content:"";position:absolute;left:2px;top:19px;width:8px;height:8px;border-radius:50%;background:var(--accent)}
.actions{list-style:none;display:grid;gap:10px}
.actions li{background:var(--navy2);border-left:3px solid var(--accent);border-radius:0 8px 8px 0;
  padding:12px 16px;font-size:.92rem;line-height:1.55;color:#e7ebf4}
.glance a{color:#9fd4c6}
/* sections */
section.block{padding:52px 0 8px}
.sectionhead{display:flex;align-items:baseline;gap:14px;margin-bottom:8px}
.sectionhead h2{font-family:'Fraunces',serif;font-weight:600;font-size:1.5rem}
.sectionhead .sub{color:var(--muted);font-size:.88rem}
/* stories */
.story{padding:34px 0;border-bottom:1px solid var(--line)}
.story:last-child{border-bottom:none}
.storytop{display:flex;gap:16px;align-items:flex-start}
.snum{font-family:'Fraunces',serif;font-weight:600;font-size:1.5rem;color:var(--accent);line-height:1.2;min-width:1.2em}
.story h3{font-family:'Fraunces',serif;font-weight:600;font-size:1.25rem;line-height:1.3}
.smeta{margin:8px 0 14px;font-size:.78rem;font-weight:600;letter-spacing:.06em;text-transform:uppercase;color:var(--muted)}
.story p{margin-bottom:14px;color:var(--ink2);max-width:46em}
.why{background:var(--accent-soft);border-left:3px solid var(--accent);border-radius:0 10px 10px 0;
  padding:14px 18px;margin:18px 0 14px;font-size:.95rem;line-height:1.6;max-width:48em}
.why b.tag{display:block;font-size:.72rem;font-weight:700;letter-spacing:.13em;text-transform:uppercase;color:var(--accent);margin-bottom:6px}
.srcline{font-size:.82rem;color:var(--muted);line-height:1.55}
.srcline a{color:var(--muted);text-decoration:underline;text-decoration-color:var(--line);text-underline-offset:3px}
.srcline a:hover{color:var(--accent)}
/* signal cards */
.cards{display:grid;gap:16px;margin-top:20px}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:22px 24px;box-shadow:0 1px 2px rgba(24,31,48,.04)}
.card h3{font-family:'Fraunces',serif;font-weight:600;font-size:1.06rem;line-height:1.4;margin-bottom:10px}
.card p{font-size:.93rem;line-height:1.6;color:var(--ink2)}
.card .srcs{margin-top:12px;font-size:.8rem;color:var(--muted);line-height:1.6}
.card .srcs a{color:var(--muted);text-decoration:underline;text-decoration-color:var(--line);text-underline-offset:3px}
.card .srcs a:hover{color:var(--accent)}
.card.agree{border-top:3px solid var(--accent)}
.card.disagree{border-top:3px solid var(--amber)}
.pos{display:grid;gap:10px;margin:10px 0}
.pos>div{border-radius:10px;padding:12px 15px;font-size:.9rem;line-height:1.6}
.pos .a{background:var(--accent-soft)}
.pos .b{background:var(--amber-soft)}
.pos b.tag{display:block;font-size:.7rem;font-weight:700;letter-spacing:.12em;text-transform:uppercase;margin-bottom:4px}
.pos .a b.tag{color:var(--accent)}
.pos .b b.tag{color:var(--amber)}
.tension{font-size:.9rem;color:var(--ink2);line-height:1.6;padding-top:8px;border-top:1px dashed var(--line)}
.tension b.tag{font-size:.7rem;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:var(--muted);display:block;margin-bottom:4px}
/* watching */
.watch{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:22px 24px;margin-top:16px}
.watch h3{font-family:'Fraunces',serif;font-weight:600;font-size:1.06rem;margin-bottom:10px}
.watch p{font-size:.93rem;line-height:1.65;color:var(--ink2);margin-bottom:10px}
/* sources details */
details.allsources{margin:44px 0 0;border-top:1px solid var(--line);padding-top:20px}
details.allsources summary{cursor:pointer;font-weight:600;font-size:.95rem;color:var(--ink2)}
details.allsources ol{margin:16px 0 0 20px;font-size:.85rem;color:var(--muted);line-height:1.7}
details.allsources li{margin-bottom:6px}
/* pager + footer */
.pager{display:flex;justify-content:space-between;gap:16px;margin:48px 0 0;padding-top:24px;border-top:1px solid var(--line);font-size:.9rem;font-weight:600}
footer{margin-top:56px;padding:32px 0 48px;border-top:1px solid var(--line);color:var(--muted);font-size:.82rem;line-height:1.7}
/* index */
.hero{padding:72px 24px 40px}
.hero h1{font-family:'Fraunces',serif;font-weight:600;font-size:clamp(1.5rem,6.2vw,3.95rem);line-height:1.08;letter-spacing:-.015em;white-space:nowrap}
.hero p.tag{margin-top:20px;font-size:clamp(.85rem,1.85vw,1.15rem);color:var(--ink2);line-height:1.7;white-space:nowrap}
.latest{background:var(--navy);color:#eef1f7;border-radius:18px;padding:34px 36px;margin:8px 0 12px}
.latest .kicker{color:#9fd4c6}
.latest h2{font-family:'Fraunces',serif;font-weight:600;font-size:1.5rem;line-height:1.3;color:#fff;margin-bottom:12px}
.latest p{color:#d9dfec;font-size:.98rem;line-height:1.7;margin-bottom:20px}
.btn{display:inline-block;background:var(--accent);color:#fff;font-weight:600;font-size:.9rem;
  padding:11px 22px;border-radius:999px}
.btn:hover{text-decoration:none;filter:brightness(1.08)}
.archive{padding:44px 0}
.archive h2{font-family:'Fraunces',serif;font-weight:600;font-size:1.5rem;margin-bottom:6px}
.issuelist{list-style:none;margin-top:14px}
.issuelist li{border-bottom:1px solid var(--line)}
.issuelist a{display:flex;gap:24px;align-items:baseline;padding:18px 4px;color:var(--ink)}
.issuelist a:hover{background:#f1ede4;text-decoration:none}
.issuelist .d{min-width:130px;font-size:.85rem;font-weight:700;color:var(--accent);letter-spacing:.02em}
.issuelist .h{font-size:.97rem;line-height:1.5;color:var(--ink2)}
.aboutwrap{padding:20px 0 30px}
.about{max-width:44em}
.about h2{font-family:'Fraunces',serif;font-weight:600;font-size:1.5rem;margin-bottom:12px}
.about p{color:var(--ink2);margin-bottom:12px;font-size:.97rem}
@media(max-width:640px){
  .issuelist a{flex-direction:column;gap:4px}
  .latest{padding:26px 22px}
}
@media print{
  .topbar,.pager{display:none}
  body{background:#fff}
  .glance{background:#fff;color:#000;border:1px solid #ccc}
}
"""

HEAD = """<!DOCTYPE html>
<html lang="en-AU">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,600;9..144,700&family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
<style>{css}</style>
</head>
<body>
<header class="topbar"><div class="wrap">
  <a class="brand" href="{home}">AI in EdTech <span>Weekly</span></a>
  <nav class="topnav"><a href="{latest}">Latest briefing</a><a href="{home}#archive">Archive</a><a href="{home}#about">About</a></nav>
</div></header>
"""

FOOT = """
<footer><div class="wrap">
  <p><strong>AI in EdTech Weekly</strong> is compiled from primary sources each week; every claim links to its original source.
  Briefings are produced with AI-assisted research and human editorial review, and summarise third-party reporting and research
  for information purposes.</p>
</div></footer>
</body>
</html>
"""

# ---------------------------------------------------------------- rendering

def render_briefing(b, prev_b, next_b):
    s = SUMMARIES.get(b["date"], {})
    date = b["display"]
    parts = [HEAD.format(
        title=f"{SITE_NAME} · {date}",
        desc=s.get("headline", TAGLINE),
        css=CSS, home="../index.html", latest="#")]

    parts.append(f"""
<div class="wrap issuehead">
  <div class="kicker">Weekly briefing · {esc(b['covering']) or date}</div>
  <h1 class="issue">{esc(s.get('headline', 'AI in education this week'))}</h1>
  <div class="issuemeta">Issue of {date}</div>
</div>""")

    # at a glance
    signals = "".join(f"<li>{inline(x)}</li>" for x in s.get("signals", []))
    actions = "".join(f"<li>{inline(x)}</li>" for x in s.get("actions", []))
    parts.append(f"""
<section class="glance"><div class="wrap">
  <h2>At a glance</h2>
  <p class="overview">{inline(s.get('overview',''))}</p>
  <h3>Key signals</h3><ul class="signals">{signals}</ul>
  <h3>Considerations for the Executive</h3><ul class="actions">{actions}</ul>
</div></section>""")

    # stories
    story_html = ""
    for st in b["stories"]:
        paras = "".join(f"<p>{inline(p)}</p>" for p in st["paras"])
        why = (f'<div class="why"><b class="tag">Why it matters</b>{inline(st["why"])}</div>'
               if st["why"] else "")
        src = f'<p class="srcline">Sources: {inline(st["sources"])}</p>' if st["sources"] else ""
        story_html += f"""
<article class="story">
  <div class="storytop"><div class="snum">{st['num']}</div>
  <div><h3>{inline(st['title'])}</h3><div class="smeta">{esc(st['meta'])}</div></div></div>
  {paras}{why}{src}
</article>"""
    parts.append(f"""
<section class="block"><div class="wrap">
  <div class="sectionhead"><h2>The stories in depth</h2><span class="sub">Full analysis with linked sources</span></div>
  {story_html}
</div></section>""")

    # convergence
    if b["confluence"]:
        cards = ""
        for row in b["confluence"]:
            if len(row) < 3:
                continue
            theme, sources, sowhat = row[0], row[1], row[2]
            cards += f"""<div class="card agree"><h3>{inline(theme)}</h3>
<p>{inline(sowhat)}</p><div class="srcs">Sources: {inline(sources)}</div></div>"""
        parts.append(f"""
<section class="block"><div class="wrap">
  <div class="sectionhead"><h2>Where the evidence agrees</h2><span class="sub">Independent sources pointing the same way</span></div>
  <div class="cards">{cards}</div>
</div></section>""")

    # conflict
    if b["conflict"]:
        cards = ""
        for row in b["conflict"]:
            if len(row) < 4:
                continue
            theme, pa, pb, tension = row[0], row[1], row[2], row[3]
            cards += f"""<div class="card disagree"><h3>{inline(theme)}</h3>
<div class="pos"><div class="a"><b class="tag">One view</b>{inline(pa)}</div>
<div class="b"><b class="tag">The other view</b>{inline(pb)}</div></div>
<div class="tension"><b class="tag">The tension</b>{inline(tension)}</div></div>"""
        parts.append(f"""
<section class="block"><div class="wrap">
  <div class="sectionhead"><h2>Where experts disagree</h2><span class="sub">Live debates worth understanding before deciding</span></div>
  <div class="cards">{cards}</div>
</div></section>""")

    # worth watching
    if b["watching"]:
        items = ""
        for w in b["watching"]:
            paras = "".join(f"<p>{inline(p)}</p>" for p in w["paras"])
            src = f'<p class="srcline">Sources: {inline(w["sources"])}</p>' if w["sources"] else ""
            items += f'<div class="watch"><h3>{inline(w["title"])}</h3>{paras}{src}</div>'
        parts.append(f"""
<section class="block"><div class="wrap">
  <div class="sectionhead"><h2>Worth watching</h2><span class="sub">Developments to keep an eye on</span></div>
  {items}
</div></section>""")

    # full source list
    if b["sourcelist"]:
        lis = "".join(f"<li>{inline(x)}</li>" for x in b["sourcelist"])
        parts.append(f"""
<div class="wrap"><details class="allsources"><summary>Full source list for this issue ({len(b['sourcelist'])} sources)</summary>
<ol>{lis}</ol></details></div>""")

    # pager
    prev_link = (f'<a href="{prev_b["date"]}.html">← {prev_b["display"]}</a>'
                 if prev_b else "<span></span>")
    next_link = (f'<a href="{next_b["date"]}.html">{next_b["display"]} →</a>'
                 if next_b else '<a href="../index.html">All briefings →</a>')
    parts.append(f'<div class="wrap"><div class="pager">{prev_link}{next_link}</div></div>')

    parts.append(FOOT)
    return "".join(parts)

def render_index(briefings):
    latest = briefings[-1]
    s = SUMMARIES.get(latest["date"], {})
    parts = [HEAD.format(
        title=f"{SITE_NAME} · AI in education, explained weekly",
        desc=TAGLINE, css=CSS, home="index.html",
        latest=f'briefings/{latest["date"]}.html')]

    parts.append(f"""
<div class="wrap hero">
  <h1>AI in education, explained weekly.</h1>
  <p class="tag">{TAGLINE}</p>
</div>
<div class="wrap"><div class="latest">
  <div class="kicker">Latest issue · {latest['display']}</div>
  <h2>{esc(s.get('headline',''))}</h2>
  <p>{inline(s.get('overview',''))}</p>
  <a class="btn" href="briefings/{latest['date']}.html">Read the briefing</a>
</div></div>""")

    items = ""
    for b in reversed(briefings):
        h = SUMMARIES.get(b["date"], {}).get("headline", "")
        items += (f'<li><a href="briefings/{b["date"]}.html">'
                  f'<span class="d">{b["display"]}</span><span class="h">{esc(h)}</span></a></li>')
    parts.append(f"""
<section class="archive" id="archive"><div class="wrap">
  <h2>All briefings</h2>
  <ul class="issuelist">{items}</ul>
</div></section>
<section class="aboutwrap" id="about"><div class="wrap"><div class="about">
  <h2>About this briefing</h2>
  <p>AI in EdTech Weekly tracks how artificial intelligence is changing education, with a particular focus on
  Australian K-12 schools. Each issue is compiled from primary sources: government and regulator announcements,
  peer-reviewed research, sector reporting and major conference coverage.</p>
  <p>Every issue opens with an executive summary for leadership, followed by the week's stories in depth for staff
  who want the detail. Two standing sections, <em>Where the evidence agrees</em> and <em>Where experts disagree</em>,
  show where independent sources are converging and where genuine debate remains. Every claim links to its
  original source.</p>
</div></div></section>""")

    parts.append(FOOT)
    return "".join(parts)

# ---------------------------------------------------------------- main

def main():
    files = sorted(BRIEFINGS.glob("*.md"))
    briefings = [parse_briefing(f) for f in files]
    for i, b in enumerate(briefings):
        prev_b = briefings[i - 1] if i > 0 else None
        next_b = briefings[i + 1] if i < len(briefings) - 1 else None
        out = BRIEFINGS / f"{b['date']}.html"
        out.write_text(render_briefing(b, prev_b, next_b))
        print(f"built {out.relative_to(ROOT)}  ({len(b['stories'])} stories, "
              f"{len(b['confluence'])} agree, {len(b['conflict'])} disagree, "
              f"{len(b['watching'])} watching, {len(b['sourcelist'])} sources)")
    (ROOT / "index.html").write_text(render_index(briefings))
    print("built index.html")
    (ROOT / ".nojekyll").write_text("")
    print("wrote .nojekyll")

if __name__ == "__main__":
    main()
