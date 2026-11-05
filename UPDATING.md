# Refreshing the results

This page is rebuilt from the eight MLS NEXT Homegrown Division U14 conference pages on
leaguetables-soccer.pages.dev. A refresh pulls the latest results, checks them, rebuilds
`index.html`, and pushes **only when results changed and every check passes**.
The live page is https://romshes.github.io/u14-results/ (GitHub Pages serves `main`).

## Steps

1. Work in the repo root and make sure it is current: `git pull --ff-only`.

2. Clear old fetch files: `rm -rf data/fetch && mkdir -p data/fetch`.

3. Fetch the 8 conferences (in `data/meta.json`). WebFetch returns only the first ~39,000 characters of a page
   word for word and summarizes the rest unreliably; a conference page is ~80,000 characters, so its match list
   is cut off. Results are therefore read from the **team pages** (~20,000 characters each, returned in full).
   Start 8 general-purpose agents at once, one per conference, each with this brief (fill in name and slug):

   ```
   Read tools/FETCH_CONFERENCE.md in the repo and follow it exactly for Conference "<Conference>",
   slug "<slug>". Use WebFetch for every page. Write the output to data/fetch/<slug>.txt with the Write tool.
   Do not edit any other file and do not run git. Reply with the one-line summary the brief asks for.
   ```

   When all 8 are back, run `python3 tools/assemble.py`. It merges the two team-page copies of every game,
   reports any disagreement between them, and rewrites `data/raw_matches.txt`, `data/raw_standings.txt` and the
   `total` / `pending` / `as_of` values in `data/meta.json`. A conference whose fetch file is missing keeps its old
   data. If it prints a PROBLEM, re-run that conference's agent once (for a team-page disagreement, ask it to
   re-fetch the two teams involved) and assemble again; if it still fails, stop and report.

4. Run `python3 tools/validate.py`.
   - If teams in a conference differ from the standings, re-fetch those teams' pages (step 3 brief, only
     those teams, updating their sections in `data/fetch/<slug>.txt`), run `tools/assemble.py` and validate again. A game the source counts in its standings but never lists cannot be
     fixed; leave it (validate allows up to 4 such teams, each within one game).
   - If it still exits with an error, stop. Do not build or push; report the problems.

5. If `git diff --quiet data/raw_matches.txt` says the results are unchanged, discard everything
   (`git checkout -- . && rm -rf data/fetch`) and stop: there is nothing new to publish.

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
