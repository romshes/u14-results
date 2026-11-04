"""Build players.html: Taka clip stats for MLS NEXT U14 fullbacks, with Thomas Shestakov highlighted.

Inputs (in data/taka/):
  fullbacks.csv   player list + category totals (Muse's taka_u14_fullbacks.csv, columns per the brief)
  scraped.json    optional, from tools/taka_refresh.py: refreshed totals and sub-tag counts per profile

Run from the repo root:  python3 tools/build_players.py
Only player-performance fields are published (no height, weight, nationality or commitment status).
"""
import csv
import datetime as dt
import html
import json
from collections import Counter, defaultdict
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
D = ROOT / "data" / "taka"
FOCUS = "thomas shestakov"
CATS = [("on_ball", "On Ball", "On_Ball"), ("intelligence", "Intelligence", "Intelligence"),
        ("shot", "Shot", "Shot"), ("defensive", "Defensive", "Defensive"),
        ("aerial", "Aerial", "Aerial"), ("physical", "Physical", "Physical")]
# Sub-tags that matter most for fullbacks; shown as per-game rates when clip data exists.
SUBTAGS = ["Challenge", "Def 1v1", "Clearance/Block", "Intercept", "Short Pass", "Long Pass",
           "Cross", "Dribble / Att 1v1", "Off Ball Intelligence", "Pressure"]


def num(v):
    v = (v or "").strip()
    return int(v) if v.isdigit() else None


def side(p):
    p = (p or "").lower()
    if "right" in p and "left" in p:
        return "RB/LB"
    return "RB" if "right" in p else "LB" if "left" in p else ""


players = {}
for r in csv.DictReader(open(D / "fullbacks.csv", encoding="utf-8-sig")):
    url = r["profile_url"].strip().rstrip("/")
    players[url] = dict(
        u=url, n=r["name"].strip(), c=r.get("club", "").strip(), t=r.get("team", "").strip(),
        p=side(r.get("directory_position")) or r.get("profile_position", "").strip(),
        s=r.get("status", "OK").strip().upper() or "OK",
        g=num(r.get("game_highlight_cards")), d=r.get("collected_on", "").strip(),
        **{k: num(r.get(k)) for k, _, _ in CATS})

# Scraper refresh (data/taka/scraped.json, written by tools/taka_refresh.py): newer complete
# records override the list's totals and add sub-tag counts.
scraped = json.load(open(D / "scraped.json", encoding="utf-8")) if (D / "scraped.json").exists() else {}
sub = {}
for url, rec in scraped.items():
    if url not in players or not rec.get("complete"):
        continue
    pl = players[url]
    for k, _, api in CATS:
        if isinstance(rec["totals"].get(api), int):
            pl[k] = rec["totals"][api]
    pl["g"] = rec.get("games_with_clips") or pl["g"]
    pl["d"] = rec["scraped_at"][:10]
    sub[url] = rec.get("subtags", {})
has_sub = bool(sub)

rows = []
for pl in players.values():
    if pl["s"] != "OK" or scraped.get(pl["u"], {}).get("last_status") in ("MISMATCH", "PRIVATE_OR_MISSING"):
        pl["s"] = pl["s"] if pl["s"] != "OK" else "HIDDEN"
        continue
    vals = [pl[k] for k, _, _ in CATS if pl[k] is not None]
    pl["tot"] = sum(vals) if vals else None
    if has_sub and pl["u"] in sub:
        pl["sub"] = {t: sub[pl["u"]].get(t, 0) for t in SUBTAGS}
    pl["f"] = pl["n"].lower() == FOCUS
    rows.append(pl)

# Percentile of the focus player among fullbacks with games, per game, for each measure.
def per_game(pl, k):
    v = pl["sub"].get(k) if k in SUBTAGS else pl.get(k)
    return v / pl["g"] if v is not None and pl.get("g") else None

focus = next((pl for pl in rows if pl["f"]), None)
measures = [(k, lbl) for k, lbl, _ in CATS] + ([(t, t) for t in SUBTAGS] if has_sub else [])
pct = []
if focus:
    for k, lbl in measures:
        if k in SUBTAGS and "sub" not in focus:
            continue
        mine = per_game(focus, k)
        pool = [x for x in (per_game(pl, k) for pl in rows if not pl["f"] and (k not in SUBTAGS or "sub" in pl)) if x is not None]
        if mine is None or not pool:
            continue
        below = sum(x < mine for x in pool) + 0.5 * sum(x == mine for x in pool)
        pct.append(dict(k=lbl, v=round(mine, 2), p=round(100 * below / len(pool)), avg=round(sum(pool) / len(pool), 2), n=len(pool)))

n_rb = sum(pl["p"] in ("RB", "RB/LB") for pl in rows)
n_lb = sum(pl["p"] in ("LB", "RB/LB") for pl in rows)
n_hidden = sum(pl["s"] != "OK" for pl in players.values())
dates = sorted(pl["d"] for pl in rows if pl["d"])
as_of = dates[-1] if dates else ""
today = dt.datetime.now(ZoneInfo("America/New_York")).date().isoformat()


def js(o):
    return json.dumps(o, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")


data = [dict(u=p["u"], n=p["n"], c=p["c"], t=p["t"], p=p["p"], g=p["g"], tot=p["tot"], f=p["f"],
             **{k: p[k] for k, _, _ in CATS}, **({"sub": p["sub"]} if "sub" in p else {})) for p in rows]
cols = [dict(k=k, l=lbl) for k, lbl, _ in CATS]
page = (ROOT / "tools" / "players_template.html").read_text(encoding="utf-8")
subs = {
    "__DATA__": js(data), "__COLS__": js(cols), "__SUBTAGS__": js(SUBTAGS if has_sub else []),
    "__PCT__": js(pct), "__FOCUS__": js(focus["n"] if focus else None),
    "__COUNT__": f"{len(rows):,}", "__NRB__": f"{n_rb:,}", "__NLB__": f"{n_lb:,}",
    "__ASOF__": html.escape(as_of or today), "__HIDDEN__": f"{n_hidden:,}",
}
for k, v in subs.items():
    assert page.count(k) >= 1, f"placeholder {k} missing in players_template.html"
    page = page.replace(k, v)
(ROOT / "players.html").write_text(page, encoding="utf-8")
print(f"players.html: {len(rows)} fullbacks ({n_rb} RB, {n_lb} LB), {n_hidden} private/missing, "
      f"sub-tags {'yes' if has_sub else 'no'}, focus {'found' if focus else 'NOT FOUND'}, {len(page)/1024:.0f} KB")
