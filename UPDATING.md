# Refreshing the results

The page is rebuilt from the official MLS NEXT schedule only. The schedule table on
https://www.mlssoccer.com/mlsnext/schedule/all/ is an embedded tool
(https://mls-assist.theintelligenceplatform.com/#/schedule/mls-next-league-26-27) that loads one JSON file with every
game, score, venue and group of the season. `tools/fetch_official.py` downloads that file and keeps the U14 League
games of the 8 conferences in `data/meta.json`. No other site is used.
The live page is https://romshes.github.io/u14-results/ (GitHub Pages serves `main`).

The session needs network access to `mls-assist.theintelligenceplatform.com`.

## Steps

1. Work in the repo root and make sure it is current: `git checkout main && git pull --ff-only`.

2. Run `python3 tools/fetch_official.py`. It rewrites `data/raw_matches.txt`, `data/raw_standings.txt` and the
   `total` / `pending` / `as_of` values in `data/meta.json`. It prints one line per conference and NOTE lines for
   results dated in the future. If it exits with an error (download failed, a conference group missing), stop and
   report; nothing was written.

3. Run `python3 tools/validate.py`. If it exits with an error (unreadable lines, duplicates, a team twice on one date),
   stop and report; do not build or push.

4. If `git diff --quiet data/raw_matches.txt` says the results are unchanged, discard everything
   (`git checkout -- .`) and stop: there is nothing new to publish.

5. Run `python3 tools/build.py`, then `python3 tools/check_page.py`. If the check fails, stop and report; do not push.

6. Commit and push to `main`:
   `git add -A && git commit -m "Update results: <N> matches (scores as of <date>)" && git push`
   (end the commit message with any attribution lines your session asks for).
   GitHub Pages updates the live page within a minute or two.

7. Also update the private Claude copy of the page (artifact `da631913-6dde-45c1-9ca6-53c37362c0de`,
   https://claude.ai/code/artifact/da631913-6dde-45c1-9ca6-53c37362c0de): republish `index.html` to it.
   If this fails, say so; GitHub is the main copy.

8. Finish with two or three lines: how many results were added (and from which dates), the new total, and anything
   notable (NOTE lines, results that changed or disappeared compared with the previous version: check with
   `git diff data/raw_matches.txt`).

If the official data changes shape (different JSON keys, a renamed group or season key), fix `tools/fetch_official.py`
and report it. When a new season starts, the season key in `tools/fetch_official.py` (`SEASON_KEY`) must be updated;
the key is the last part of the schedule tool's address.
