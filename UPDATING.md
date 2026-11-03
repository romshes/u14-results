# Refreshing the results

This page is rebuilt from the eight MLS NEXT Homegrown Division U14 conference pages on
leaguetables-soccer.pages.dev. A refresh pulls the latest results, checks them, rebuilds
`index.html`, and pushes **only when results changed and every check passes**.
The live page is https://romshes.github.io/u14-results/ (GitHub Pages serves `main`).

## Steps

1. Work in the repo root and make sure it is current: `git pull --ff-only`.

2. For each conference in `data/meta.json` (8 of them), fetch
   `https://leaguetables-soccer.pages.dev/mls-next-homegrown-division/u14/<slug>` with WebFetch.
   Send all 8 fetches at once, each with exactly this prompt:

   ```
   Extract data verbatim, no commentary, no summarizing, do not skip any rows.
   PART 1 — every COMPLETED match (has a final score) as lines, one per match: date(YYYY-MM-DD)|time|home team|home goals|away goals|away team|venue|match type. List ALL completed matches on the page.
   PART 2 — the standings table: first the header labels exactly in the page's column order, then every row in that same order, | separated.
   PART 3 — total matches the page states, the 'data as of' timestamp, and how many matches are marked 'Score pending'.
   ```

3. Write what came back, replacing the old contents:
   - `data/raw_matches.txt`: a `=== <Conference>` line for each conference (names as in meta.json), then one
     line per completed match: `YYYY-MM-DD|h:mm AM|PM TZ|Home|home goals|away goals|Away|Venue|Type`
     (for example `2026-10-25|3:00 PM EDT|New York City FC|14|2|The Island FC East|Da Silva Memorial Field|League`).
     Copy team names and venues exactly. Only matches with a final score; skip "Score pending" and scheduled ones.
   - `data/raw_standings.txt`: keep the `# team|PTS|MP|W|T|L|GF|GA` line, then a `=== <Conference>` line and one row
     per team as `team|PTS|MP|W|T|L|GF|GA`. The source lists W, T, L in that order, but check the header labels
     WebFetch returns and reorder to match; a row's points must equal 3×W + T.
   - `data/meta.json`: for each conference update `total` (matches the page says it has), `pending`
     (matches marked "Score pending") and `as_of` (the page's "data as of" time, as `YYYY-MM-DD HH:MM UTC`).

4. Run `python3 tools/validate.py`.
   - If teams in a conference differ from the standings, re-fetch that conference asking for every match
     involving those teams (date, time, home, score, away, venue, any status label), fix copying mistakes in
     `raw_matches.txt`, and run it again. A game the source counts in its standings but never lists cannot be
     fixed; leave it (validate allows up to 4 such teams, each within one game).
   - If it still exits with an error, stop. Do not build or push; report the problems.

5. If `git diff --quiet data/raw_matches.txt` says the results are unchanged, discard everything
   (`git checkout -- .`) and stop: there is nothing new to publish.

6. Run `python3 tools/build.py`, then `python3 tools/check_page.py`. If the check fails, stop and report; do not push.

7. Commit and push to `main`:
   `git add -A && git commit -m "Update results: <N> matches (scores as of <date>)" && git push`
   (end the commit message with any attribution lines your session asks for).
   GitHub Pages updates the live page within a minute or two.

8. Also update the private Claude copy of the page (artifact slug `da631913-6dde-45c1-9ca6-53c37362c0de`):
   get its live version with get_artifact, then publish_files with `index.html` served as `index.html`,
   that slug and that version as base_version. If this fails, say so; GitHub is the main copy.

9. Finish with two or three lines: how many results were added (and from which dates), the new total,
   and anything that needed fixing or still doesn't match the source standings.

If the source pages disappear or change shape so the extraction no longer works, stop and report it rather than
publishing partial data.
