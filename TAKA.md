# Refreshing the U14 fullback stats (players.html)

`players.html` shows Taka highlight-clip stats for MLS NEXT U14 fullbacks, with Thomas Shestakov highlighted.
It is generated: don't edit it by hand.

- `data/taka/fullbacks.csv`: the player list (profile URL, name, position, club, category totals). It comes from
  Muse, which saves `taka_u14_fullbacks.csv` in the owner's Google Drive, folder **Taka**. Columns:
  `profile_url,name,directory_position,club,team,profile_position,on_ball,intelligence,shot,defensive,aerial,physical,game_highlight_cards,status,collected_on`
- `data/taka/scraped.json`: refreshed totals and sub-tag counts per profile, written by `tools/taka_refresh.py`.
  Only aggregates are stored (no clip-level data, no personal details).

## Nightly steps

1. In the repo root: `git pull --ff-only`.

2. **Pick up a new list from Muse.** Search Google Drive for a file titled `taka_u14_fullbacks` (CSV or Google Sheet).
   - If there is none and `data/taka/fullbacks.csv` doesn't exist either, stop: say "No Taka player list yet" and
     do nothing else.
   - If the Drive file was modified after the last commit that touched `data/taka/fullbacks.csv`
     (`git log -1 --format=%cI -- data/taka/fullbacks.csv`), download it to `/tmp/new_fullbacks.csv` and check it:
     the header must be exactly the columns above, every `profile_url` must look like
     `https://taka.io/soccer/athlete/<24 lowercase hex characters>`, and at least 50 rows must have status `OK`.
     If it passes, copy it to `data/taka/fullbacks.csv`. If it fails, keep the old file and report why.

3. **Refresh stats.** Run `python3 tools/taka_refresh.py --minutes 9 --focus-first` once, then
   `python3 tools/taka_refresh.py --minutes 9` up to 9 more times, stopping early when a run prints
   "refreshed 0 this run". Each run saves progress, so stopping early is safe.
   - Exit code 2 means Taka looks unreachable or its page changed: stop, don't publish, and report the message.
   - The scraper only reads public profiles while logged out. It records the data the page itself loads when the
     Skill categories are clicked; never call Taka's data endpoint directly.

4. **Build and check.** `python3 tools/build_players.py && python3 tools/check_players.py`.
   If the check fails, stop and report; do not push.

5. **Rebuild the results page** so its link to the stats page is present:
   `python3 tools/build.py && python3 tools/check_page.py`. If this check fails, stop and report.

6. If nothing changed (`git status --porcelain` is empty), stop. Otherwise commit and push to `main`:
   `git add -A && git commit -m "Update Taka fullback stats (<N> profiles refreshed)" && git push`
   (end the message with any attribution lines your session asks for).

7. Finish with two or three lines: profiles refreshed tonight, how many have complete data, whether a new list
   arrived from Muse, Thomas's refresh date, and anything that failed.

## Reading the numbers
Clip counts are Taka's AI-tagged highlight volume, not minutes, verified actions or ability. One clip can carry
several tags, so categories and sub-tags overlap. Per-game figures divide by games that produced highlights.
