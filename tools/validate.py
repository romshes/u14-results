"""Parse data/raw_matches.txt and data/raw_standings.txt, cross-check them, and write data/matches.json.

Every conference's results are rebuilt into a standings table and compared with the
table shown on the source page (data/raw_standings.txt, columns team|PTS|MP|W|T|L|GF|GA).

The source's standings table is rebuilt less often than its team pages, so teams whose records differ
from it are reported (and listed on the page via data/mismatches.json) but do not stop a refresh.

Exit code 0: data is usable.
Exit code 1: something is wrong (bad lines, duplicates, a team twice on one date, missing sections) -> do not publish.

Run from the repo root:  python3 tools/validate.py
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"


def sections(path):
    sec, out = None, defaultdict(list)
    for line in open(path, encoding="utf-8"):
        line = line.rstrip("\n")
        if not line.strip() or line.startswith("#"):
            continue
        if line.startswith("=== "):
            sec = line[4:].strip()
            continue
        out[sec].append(line.split("|"))
    return out


def main():
    matches, standings = sections(DATA / "raw_matches.txt"), sections(DATA / "raw_standings.txt")
    meta = json.load(open(DATA / "meta.json", encoding="utf-8"))
    problems, mismatches, rows = [], [], []
    for conf in meta["conferences"]:
        if conf not in matches:
            problems.append(f"{conf}: no results section")
            continue
        calc = defaultdict(lambda: dict(MP=0, W=0, T=0, L=0, GF=0, GA=0, PTS=0))
        seen, played_on = set(), defaultdict(set)
        for r in matches[conf]:
            if len(r) != 8:
                problems.append(f"{conf}: bad line ({len(r)} fields): {'|'.join(r)}")
                continue
            date, time, home, hg, ag, away, venue, mtype = (x.strip() for x in r)
            try:
                hg, ag = int(hg), int(ag)
                clock, ampm, tz = time.split()
                h, m = map(int, clock.split(":"))
                assert ampm in ("AM", "PM") and 1 <= h <= 12 and 0 <= m < 60 and len(date) == 10
            except Exception:
                problems.append(f"{conf}: unreadable line: {'|'.join(r)}")
                continue
            if (date, home, away) in seen:
                problems.append(f"{conf}: duplicate {date} {home} v {away}")
            seen.add((date, home, away))
            for t in (home, away):
                if date in played_on[t]:
                    problems.append(f"{conf}: {t} has two games on {date}")
                played_on[t].add(date)
            for team, gf, ga in ((home, hg, ag), (away, ag, hg)):
                c = calc[team]
                c["MP"] += 1; c["GF"] += gf; c["GA"] += ga
                k = "W" if gf > ga else "T" if gf == ga else "L"
                c[k] += 1; c["PTS"] += {"W": 3, "T": 1, "L": 0}[k]
            rows.append(dict(conf=conf, date=date, time=time, home=home, hg=hg, ag=ag, away=away, venue=venue, type=mtype))
        page = {s[0].strip(): dict(zip(["PTS", "MP", "W", "T", "L", "GF", "GA"], map(int, s[1:8]))) for s in standings.get(conf, [])}
        if not page:
            problems.append(f"{conf}: no standings section")
        for t in sorted(set(calc) | set(page)):
            a, b = calc.get(t), page.get(t)
            if a is None or b is None:
                problems.append(f"{conf}: {t} only in {'standings' if a is None else 'results'}")
                continue
            diff = {k: [a[k], b[k]] for k in b if a[k] != b[k]}
            if diff:
                mismatches.append(dict(conf=conf, team=t, results=a, standings=b))
        n = len(matches[conf])
        print(f"{conf:13s} results={n:3d} teams={len(calc):2d} standings_teams={len(page):2d} mismatched_teams="
              f"{sum(1 for x in mismatches if x['conf'] == conf)}")

    for x in mismatches:
        print(f"  differs: {x['conf']} / {x['team']}: results {x['results']} vs standings {x['standings']}")
    json.dump(rows, open(DATA / "matches.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    json.dump(mismatches, open(DATA / "mismatches.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(f"TOTAL results={len(rows)}  differing teams={len(mismatches)}  problems={len(problems)}")
    for p in problems:
        print("PROBLEM:", p)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
