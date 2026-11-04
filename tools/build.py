"""Build index.html from tools/template.html and the validated data in data/.

Run from the repo root after tools/validate.py:  python3 tools/build.py
"""
import datetime as dt
import html
import json
from collections import Counter
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
e = html.escape

rows = json.load(open(DATA / "matches.json", encoding="utf-8"))
mismatches = json.load(open(DATA / "mismatches.json", encoding="utf-8"))
meta = json.load(open(DATA / "meta.json", encoding="utf-8"))
confs = meta["conferences"]
today = dt.datetime.now(ZoneInfo("America/New_York")).date()


def stamp(s):  # "2026-11-03 14:23 UTC" -> datetime
    return dt.datetime.strptime(s.replace(" UTC", ""), "%Y-%m-%d %H:%M")


def nice_day(d):
    return f"{d.strftime('%b')} {d.day}, {d.year}"


def nice_stamp(s):
    t = stamp(s)
    return f"{nice_day(t)}, {t.strftime('%I:%M %p').lstrip('0')} UTC"


stamps = Counter(c["as_of"] for c in confs.values())
main_stamp = stamps.most_common(1)[0][0]
newest = max(stamp(c["as_of"]) for c in confs.values())
odd = [f"the {name} page as of {nice_stamp(c['as_of'])}" for name, c in confs.items() if c["as_of"] != main_stamp]
scheduled = sum(c["total"] for c in confs.values())
pending = sum(c["pending"] for c in confs.values())

FLAG_TEXT = ("Listed with a final score but dated after the last update. "
             "Possibly a forfeit or a data-entry error; check the official schedule.")
data, flagged = [], []
for r in rows:
    clock, ampm, tz = r["time"].split()
    hh, mm = map(int, clock.split(":"))
    rec = dict(c=r["conf"], d=r["date"], k=f"{clock} {ampm}", z=tz,
               n=(hh % 12 + (12 if ampm.upper() == "PM" else 0)) * 60 + mm,
               h=r["home"], a=r["away"], hg=r["hg"], ag=r["ag"], v=r["venue"])
    if dt.date.fromisoformat(r["date"]) > today:
        rec["f"] = FLAG_TEXT
        flagged.append(r)
    data.append(rec)

# ---- notes ----
src = (f'League results for the MLS NEXT Homegrown Division U14 age group, {meta["season"]}, as listed on '
       f'<a href="{meta["source"]}">leaguetables-soccer.pages.dev</a> (data as of {nice_stamp(main_stamp)}'
       + (f'; {"; ".join(odd)}' if odd else "") + "). "
       "Every conference's results are checked against that site's standings table"
       + (", and they agree except as noted below. " if mismatches else " and agree. ")
       + f'Official schedule and standings: <a href="{meta["official"]}">mlssoccer.com/mlsnext/schedule/u14</a>.')
gap = f'{pending} played games still show "score pending" at the source.'
if mismatches:
    names = ", ".join(f'{e(x["team"])} ({x["conf"]})' for x in mismatches)
    gap += (f" The source's standings and its own match list disagree for {names}: the standings count a game "
            "that isn't in the list (or the other way round), so these records may differ slightly from the official table.")
flag_note = ""
if flagged:
    ex = flagged[0]
    flag_note = (f'<p id="flagnote">† Results marked † have a final score but are dated after the last update '
                 f'(for example {e(ex["home"])} {ex["hg"]}–{ex["ag"]} {e(ex["away"])}, dated {nice_day(dt.date.fromisoformat(ex["date"]))}). '
                 "They may be forfeits or data-entry errors. The source counts them in its standings, so they are counted here too.</p>")
NOTES = f"""    <p><strong>Source.</strong> {src}</p>
    <p><strong>Not here yet.</strong> {gap}</p>
    {flag_note}
    <p><strong>Sorting.</strong> Tap Sort and pick what to sort by. The box on the right of every card shows the value being sorted, and in table view that column is shaded. Tap the arrow button to reverse the order. The previous sort stays on as the tie-breaker, up to three levels.</p>
    <p><strong>Terms.</strong> Records read W-L-T, and H and A mark the home and away team. PPG is points per game (3 for a win, 1 for a tie). Rank is within the conference by PPG, then goal difference, then goals for; the official table may order teams tied on PPG differently. Adjusted GD per game is goal difference per game adjusted for the strength of the opponents played, centred on 0 within each conference. Opponents' PPG is the average PPG of the teams a team has faced. Upset gap is the loser's season PPG minus the winner's, shown only when the lower team won. Kickoff times are local. All games here are within-conference league games, so comparisons across conferences are rough. Pinning a team with ☆ highlights it everywhere and is remembered in this browser only.</p>"""
META = dict(season=meta["season"], scheduled=scheduled, pending=pending, asOf=nice_day(newest))


def js(obj):
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")


page = open(ROOT / "tools" / "template.html", encoding="utf-8").read()
subs = {"__DATA__": js(data), "__META__": js(META), "__NOTES__": NOTES,
        "__STATIC__": '<p class="noscript static">Sorting and filters need JavaScript. Open this page in a web browser.</p>',
        "__STATIC_CSS__": "", "__SEASON__": meta["season"], "__PLAYED__": f"{len(rows):,}",
        "__SCHEDULED__": f"{scheduled:,}", "__ASOF__": nice_day(newest),
        "__PLAYERS_LINK__": ('\n    <p class="lede"><a href="players.html" style="color:var(--ink);font-weight:600">'
                             'U14 fullback stats from Taka →</a></p>') if (ROOT / "players.html").exists() else ""}
for k, v in subs.items():
    assert page.count(k) == 1, f"placeholder {k} missing or repeated in template"
    page = page.replace(k, v)
open(ROOT / "index.html", "w", encoding="utf-8").write(page)
print(f"index.html: {len(data)} results, {scheduled} scheduled, {pending} pending, flagged {len(flagged)}, "
      f"differing teams {len(mismatches)}, {len(page) / 1024:.0f} KB")
