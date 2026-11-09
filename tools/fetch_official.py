"""Fetch the official MLS NEXT data and write data/raw_matches.txt, data/raw_standings.txt and data/meta.json.

Source: the schedule tool embedded on https://www.mlssoccer.com/mlsnext/schedule/all/
(https://mls-assist.theintelligenceplatform.com/#/schedule/mls-next-league-26-27). That tool loads one JSON
file with every game, score, venue, group and standings table of the season:
    https://mls-assist.theintelligenceplatform.com/data/standings/<season-key>.json
(The tool's /data/schedule/<key>.json file is an older, rarely synced copy; don't use it.)

Kept: competition "League", age group U14, one group (bracket) per conference in data/meta.json.
A game is a result when it is marked completed and has both scores. A game that started more than
3 hours ago without a result counts as pending.

Run from the repo root:  python3 tools/fetch_official.py [--file saved.json]
Exit code 1 if the data can't be read or a conference is missing; nothing is written then.
"""
import datetime as dt
import json
import ssl
import sys
import time
import urllib.request
from collections import defaultdict
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
BASE = "https://mls-assist.theintelligenceplatform.com"
SEASON_KEY = "mls-next-league-26-27"
AGE = "U14"
QUOTES = str.maketrans({"\u2019": "'", "\u2018": "'", "\u201c": '"', "\u201d": '"'})
COMPETITION = "League"


def download(url):
    ctx = ssl.create_default_context()
    ca = Path("/root/.ccr/ca-bundle.crt")
    if ca.exists():
        ctx.load_verify_locations(str(ca))
    req = urllib.request.Request(url, headers={"User-Agent": "u14-results refresh"})
    with urllib.request.urlopen(req, context=ctx, timeout=120) as r:
        return json.load(r)


def local_time(start, tzname):
    t = dt.datetime.fromisoformat(start.replace("Z", "+00:00")).astimezone(ZoneInfo(tzname))
    return t.date().isoformat(), f"{t.strftime('%I:%M %p').lstrip('0')} {t.tzname()}"


def main():
    if "--file" in sys.argv:
        raw = json.load(open(sys.argv[sys.argv.index("--file") + 1], encoding="utf-8"))
    else:
        raw = download(f"{BASE}/data/standings/{SEASON_KEY}.json?_t={int(time.time() * 1000)}")
    cs = raw["competition_season"]
    synced = dt.datetime.fromisoformat(raw["synced_at"].replace("Z", "+00:00")).astimezone(dt.timezone.utc)
    as_of = synced.strftime("%Y-%m-%d %H:%M UTC")

    ages = {a["id"]: a["name"] for a in cs["age_groups"]}
    comp = next(c["id"] for c in cs["competitions"] if c["name"] == COMPETITION)
    orgs = {o["id"]: " ".join(o["name"].translate(QUOTES).split()) for o in cs["organisations"]}
    venues = {v["id"]: " ".join(v["name"].translate(QUOTES).split()) for v in cs["event_locations"]}
    stage = next(s for s in cs["competition_season_stages"] if s["name"] == COMPETITION)
    brackets = {b["name"].strip(): b for b in stage["competition_brackets"] if ages.get(b["age_group_id"]) == AGE}

    meta = json.load(open(DATA / "meta.json", encoding="utf-8"))
    missing = [c for c in meta["conferences"] if c not in brackets]
    if missing:
        print(f"ERROR: no {AGE} {COMPETITION} group for {', '.join(missing)} (groups found: {', '.join(sorted(brackets))})")
        return 1

    by_bracket = defaultdict(list)
    for ev in cs["events"]:
        if ev.get("competition_id") == comp:
            by_bracket[ev.get("competition_bracket_id")].append(ev)

    now = dt.datetime.now(dt.timezone.utc)
    out_m, out_s, notes = {}, {}, []
    for conf, c in meta["conferences"].items():
        b = brackets[conf]
        evs = by_bracket.get(b["id"], [])
        results, pending = [], 0
        for ev in evs:
            home, away = orgs.get(ev["home_organisation_id"]), orgs.get(ev["away_organisation_id"])
            date, clock = local_time(ev["start_time"], ev["local_timezone"])
            start = dt.datetime.fromisoformat(ev["start_time"].replace("Z", "+00:00"))
            done = ev.get("completed") and ev.get("home_score") is not None and ev.get("away_score") is not None
            if not done:
                if start < now - dt.timedelta(hours=3):
                    pending += 1
                continue
            if start > now:
                notes.append(f"{conf}: game {ev['game_key']} {date} {home} v {away} has a result but is dated in the future")
            venue = venues.get(ev.get("event_location_id"), "").replace("|", "/")
            results.append([date, clock, home, str(ev["home_score"]), str(ev["away_score"]), away, venue, COMPETITION])
        results.sort(key=lambda r: (r[0], r[2]))
        out_m[conf] = ["|".join(r) for r in results]
        # The official U14 groups list their teams but publish no points table, so the table is
        # computed from the official results (validate.py then checks the two stay consistent).
        tab = {orgs.get(s["organisation_id"], s["name"].strip()): dict(PTS=0, MP=0, W=0, T=0, L=0, GF=0, GA=0) for s in b["standings"]}
        for r in results:
            for team, gf, ga in ((r[2], int(r[3]), int(r[4])), (r[5], int(r[4]), int(r[3]))):
                t = tab.setdefault(team, dict(PTS=0, MP=0, W=0, T=0, L=0, GF=0, GA=0))
                k = "W" if gf > ga else "T" if gf == ga else "L"
                t["MP"] += 1; t[k] += 1; t["GF"] += gf; t["GA"] += ga; t["PTS"] += {"W": 3, "T": 1, "L": 0}[k]
        out_s[conf] = ["|".join([n] + [str(t[k]) for k in ("PTS", "MP", "W", "T", "L", "GF", "GA")]) for n, t in tab.items()]
        c["total"], c["pending"], c["as_of"] = len(evs), pending, as_of
        print(f"{conf}: {len(tab)} teams, {len(evs)} games, {len(results)} results, {pending} pending")

    for n in notes:
        print("NOTE:", n)
    with open(DATA / "raw_matches.txt", "w", encoding="utf-8") as f:
        for conf in meta["conferences"]:
            f.write(f"=== {conf}\n" + "".join(l + "\n" for l in out_m[conf]))
    with open(DATA / "raw_standings.txt", "w", encoding="utf-8") as f:
        f.write("# team|PTS|MP|W|T|L|GF|GA\n")
        for conf in meta["conferences"]:
            f.write(f"=== {conf}\n" + "".join(l + "\n" for l in out_s[conf]))
    meta["source"] = "https://www.mlssoccer.com/mlsnext/schedule/all/"
    w = max(len(k) for k in meta["conferences"]) + 3
    lines = [f'    {json.dumps(k) + ":":{w}} {{"slug": {json.dumps(c["slug"]) + ",":{w}} "total": {c["total"]}, '
             f'"pending": {str(c["pending"]) + ",":3} "as_of": {json.dumps(c["as_of"])}}}'
             for k, c in meta["conferences"].items()]
    top = {k: v for k, v in meta.items() if k != "conferences"}
    text = "{\n" + "".join(f"  {json.dumps(k)}: {json.dumps(v, ensure_ascii=False)},\n" for k, v in top.items())
    text += '  "conferences": {\n' + ",\n".join(lines) + "\n  }\n}\n"
    json.loads(text)
    (DATA / "meta.json").write_text(text, encoding="utf-8")
    print(f"Wrote raw_matches.txt, raw_standings.txt, meta.json (official data synced {as_of})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
