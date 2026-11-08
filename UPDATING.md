# Refreshing the results

This page is rebuilt from the eight MLS NEXT Homegrown Division U14 conference pages on
leaguetables-soccer.pages.dev. A refresh pulls the latest results, checks them, rebuilds
`index.html`, and pushes whenever results changed and the checks pass. **Publish whatever data is available:**
the source rebuilds its pages at different times, so don't wait for every page to agree.
The live page is https://romshes.github.io/u14-results/ (GitHub Pages serves `main`).

## Steps

1. Work in the repo root and make sure it is current: `git checkout main && git pull --ff-only`.

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

   When all 8 are back (or as many as came back), run `python3 tools/assemble.py`. It merges the two team-page
   copies of every game and rewrites `data/raw_matches.txt`, `data/raw_standings.txt` and the `total` / `pending` /
   `as_of` values in `data/meta.json`. It prints NOTE lines but does not stop on them:
   - a final score shown on only one team's page (the other still says pending/scheduled) is used;
   - if two pages give different scores, the published score is kept (or the game waits until they agree);
   - a result published earlier that no page lists any more is kept;
   - a conference whose fetch file is missing, or has no standings, keeps its old data.
   It exits with an error only if no conference could be refreshed; then stop and report.
   Don't re-fetch just because of NOTE lines; mention the notable ones in the summary.

4. Run `python3 tools/validate.py`. Teams whose records differ from the source's standings table are listed
   (the standings and team pages are rebuilt at different times) but don't stop the run; the page names them.
   If it exits with an error (unreadable lines, duplicates, a team twice on one date), stop and report; do not
   build or push.

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
   and anything notable from the NOTE lines (one-sided or conflicting scores, conferences that kept old data).

If the source pages disappear or change shape so the extraction no longer works for a conference, that conference
keeps its old data; publish the rest and report it.
