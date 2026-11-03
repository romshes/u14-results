"""Open index.html in headless Chromium (phone size) and check it works before publishing.

Checks: no script errors; result count and team count match the data; sorting changes the
order and the right-hand box; every team's record matches the source standings except the
teams listed in data/mismatches.json; no sideways scrolling on a phone.
Exit code 0 = OK, 1 = do not publish.

Run from the repo root:  python3 tools/check_page.py
"""
import json
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
rows = json.load(open(ROOT / "data" / "matches.json", encoding="utf-8"))
allowed = {x["team"] for x in json.load(open(ROOT / "data" / "mismatches.json", encoding="utf-8"))}
src = {}
for line in open(ROOT / "data" / "raw_standings.txt", encoding="utf-8"):
    line = line.strip()
    if line and line[0] not in "#=":
        t, pts, mp, w, tt, l, gf, ga = line.split("|")[:8]
        src[t.strip()] = dict(pts=int(pts), mp=int(mp), w=int(w), t=int(tt), l=int(l), gf=int(gf), ga=int(ga))

fails, errors = [], []
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
    pg.on("pageerror", lambda ex: errors.append(str(ex)))
    pg.on("console", lambda m: errors.append(m.text) if m.type == "error" and "net::" not in m.text else None)
    pg.goto((ROOT / "index.html").as_uri())
    n = int(pg.inner_text("#summary .stat b >> nth=0").replace(",", ""))
    if n != len(rows):
        fails.append(f"page shows {n} results, data has {len(rows)}")
    if pg.evaluate("document.documentElement.scrollWidth - innerWidth") > 0:
        fails.append("page scrolls sideways on a phone")
    pg.tap("#sortbtn"); pg.wait_for_timeout(250); pg.tap("#sortopts button[data-sortkey=goals]"); pg.wait_for_timeout(300)
    top_goals = pg.inner_text("#list .mcard >> nth=0 >> .rail b")
    if int(top_goals) != max(r["hg"] + r["ag"] for r in rows):
        fails.append(f"sorting by total goals puts {top_goals} first")
    teams = {r["home"] for r in rows} | {r["away"] for r in rows}
    d = b.new_page(viewport={"width": 1280, "height": 900})
    d.on("pageerror", lambda ex: errors.append(str(ex)))
    d.goto((ROOT / "index.html").as_uri())
    d.click("#tab-teams")
    heads = [h.split("\n")[0].replace("▼", "").replace("▲", "").strip() for h in d.locator("#list thead th").all_inner_texts()]
    table = d.evaluate("() => [...document.querySelectorAll('#list tbody tr')].map(tr => [...tr.children].map(td => td.innerText.trim()))")
    ix = {h: i for i, h in enumerate(heads)}
    if len(table) != len(teams):
        fails.append(f"teams tab shows {len(table)} teams, data has {len(teams)}")
    for r in table:
        team = r[0].lstrip("☆★ ").strip()
        got = dict(pts=int(r[ix["Pts"]]), mp=int(r[ix["MP"]]), w=int(r[ix["W"]]), t=int(r[ix["T"]]), l=int(r[ix["L"]]),
                   gf=int(r[ix["GF"]]), ga=int(r[ix["GA"]]))
        if src.get(team) != got and team not in allowed:
            fails.append(f"{team}: page {got} vs source standings {src.get(team)}")
    b.close()
fails += [f"script error: {x}" for x in errors]
print("OK: page checks passed" if not fails else "\n".join("FAIL: " + f for f in fails))
sys.exit(1 if fails else 0)
