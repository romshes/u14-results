"""Build data/raw_matches.txt, data/raw_standings.txt and data/meta.json from data/fetch/<slug>.txt.

Each match between two teams of a conference appears on both teams' pages. The two copies are merged;
if they disagree (score, venue, time) that is reported as a problem. A conference whose fetch file is
missing keeps its current data (so one failed fetch never wipes a conference).

Run from the repo root:  python3 tools/assemble.py [--only florida,frontier]
Exit code 1 means something is wrong: do not validate, build or publish.
"""
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
FETCH = DATA / "fetch"
# Fetches return the same apostrophe straight one time and curly the next; store them straight.
QUOTES = str.maketrans({"\u2019": "'", "\u2018": "'", "\u201c": '"', "\u201d": '"'})


def read_sections(path):
    sec, out = None, defaultdict(list)
    for line in open(path, encoding="utf-8"):
        line = line.rstrip("\n")
        if line.startswith("=== "):
            sec = line[4:].strip()
        elif line.strip() and not line.startswith("#"):
            out[sec].append(line)
    return out


def parse_fetch(path, conf, problems):
    head, standings, teams, team = {}, [], {}, None
    for n, line in enumerate(open(path, encoding="utf-8"), 1):
        line = line.rstrip("\n").strip()
        if not line:
            continue
        where = f"{path.name}:{n}"
        if line.startswith("#"):
            m = re.match(r"#\s*(\w+):\s*(.*?)\s*(\(.*)?$", line)
            if m:
                head[m.group(1)] = m.group(2)
            continue
        if line.startswith("!"):
            problems.append(f"{conf}: fetch note: {line[1:].strip()}")
            continue
        if line.startswith("== standings"):
            team = None
            continue
        if line.startswith("== team "):
            parts = [x.strip() for x in line[len("== team "):].translate(QUOTES).split("|")]
            team = parts[0]
            teams[team] = dict(slug=parts[1] if len(parts) > 1 else "", F=[], P=[])
            continue
        f = [x.strip() for x in line.translate(QUOTES).split("|")]
        if team is None:
            if len(f) != 8:
                problems.append(f"{where}: bad standings row: {line}")
            else:
                standings.append(f)
        elif f[0] == "F" and len(f) == 9:
            teams[team]["F"].append(f[1:])
        elif f[0] == "P" and len(f) in (5, 6):
            teams[team]["P"].append(f[1:5])
        else:
            problems.append(f"{where}: unreadable team line: {line}")
    return head, standings, teams


def main():
    only = None
    if "--only" in sys.argv:
        only = set(sys.argv[sys.argv.index("--only") + 1].split(","))
    meta = json.load(open(DATA / "meta.json", encoding="utf-8"))
    old_m, old_s = read_sections(DATA / "raw_matches.txt"), read_sections(DATA / "raw_standings.txt")
    problems, new_m, new_s, refreshed = [], {}, {}, []
    for conf, c in meta["conferences"].items():
        path = FETCH / f"{c['slug']}.txt"
        if not path.exists() or (only and c["slug"] not in only):
            new_m[conf], new_s[conf] = old_m.get(conf, []), old_s.get(conf, [])
            continue
        head, standings, teams = parse_fetch(path, conf, problems)
        names = [r[0] for r in standings]
        for t in names:
            if t not in teams:
                problems.append(f"{conf}: no team page section for {t}")
        for t in teams:
            if t not in names:
                problems.append(f"{conf}: team page section {t} is not in the standings")
        games, pending = {}, set()
        for t, d in teams.items():
            for r in d["F"]:
                date, time, home, hg, ag, away, venue, mtype = r
                if t not in (home, away):
                    problems.append(f"{conf}: {t}'s page lists a game without {t}: {'|'.join(r)}")
                key = (date, home, away)
                if key in games and games[key] != r:
                    problems.append(f"{conf}: team pages disagree on {date} {home} v {away}: "
                                    f"{'|'.join(games[key])}  vs  {'|'.join(r)}")
                games.setdefault(key, r)
            for r in d["P"]:
                pending.add((r[0], r[2], r[3]))
        # a game between two conference teams should be on both pages
        for (date, home, away), r in games.items():
            for t in (home, away):
                if t in teams and r not in teams[t]["F"]:
                    problems.append(f"{conf}: {date} {home} v {away} missing from {t}'s page")
        try:
            c["as_of"] = re.match(r"\d{4}-\d\d-\d\d \d\d:\d\d UTC$", head["as_of"]).group(0)
            c["total"] = int(head["total"])
        except Exception:
            problems.append(f"{conf}: missing or unreadable '# as_of:' / '# total:' header")
        c["pending"] = len(pending - set(games))
        new_m[conf] = ["|".join(r) for _, r in sorted(games.items(), key=lambda kv: (kv[0][0], kv[1][1], kv[0][1]))]
        new_s[conf] = ["|".join(r) for r in standings]
        refreshed.append(f"{conf}: {len(teams)} teams, {len(games)} results, {c['pending']} pending")
    for line in refreshed:
        print(line)
    for p in problems:
        print("PROBLEM:", p)
    if problems:
        print("Nothing written.")
        return 1
    with open(DATA / "raw_matches.txt", "w", encoding="utf-8") as f:
        for conf in meta["conferences"]:
            f.write(f"=== {conf}\n" + "".join(l + "\n" for l in new_m[conf]))
    with open(DATA / "raw_standings.txt", "w", encoding="utf-8") as f:
        f.write("# team|PTS|MP|W|T|L|GF|GA\n")
        for conf in meta["conferences"]:
            f.write(f"=== {conf}\n" + "".join(l + "\n" for l in new_s[conf]))
    w = max(len(k) for k in meta["conferences"]) + 3
    lines = [f'    {json.dumps(k) + ":":{w}} {{"slug": {json.dumps(c["slug"]) + ",":{w}} "total": {c["total"]}, '
             f'"pending": {str(c["pending"]) + ",":3} "as_of": {json.dumps(c["as_of"])}}}'
             for k, c in meta["conferences"].items()]
    top = {k: v for k, v in meta.items() if k != "conferences"}
    text = "{\n" + "".join(f"  {json.dumps(k)}: {json.dumps(v, ensure_ascii=False)},\n" for k, v in top.items())
    text += '  "conferences": {\n' + ",\n".join(lines) + "\n  }\n}\n"
    json.loads(text)
    (DATA / "meta.json").write_text(text, encoding="utf-8")
    print(f"Wrote raw_matches.txt, raw_standings.txt, meta.json ({len(refreshed)} conferences refreshed)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
