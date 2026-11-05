# Fetching one conference (brief for a fetch agent)

WebFetch returns only the first ~39,000 characters of a page word for word; the rest comes back as a
model-written summary that is not reliable. A conference page is ~80,000 characters, so its match list is
cut off. Each **team page** is ~20,000 characters and comes back complete, so results are read from the team
pages, and only the top of the conference page (standings, totals, timestamp, team links) is used.

Replace `<Conference>` and `<slug>` below (names and slugs as in `data/meta.json`). Write the output file
with the Write tool; do not edit any other file.

## 1. Conference page

WebFetch `https://leaguetables-soccer.pages.dev/mls-next-homegrown-division/u14/<slug>` with this prompt:

```
Use only text that appears word for word on the page. From the TOP of the page:
A) the "Schedule data as of ..." timestamp, exactly as written;
B) the total number of matches stated in the Results heading ("N matches");
C) the standings table: the header labels in column order, then every row in that order, | separated,
   including for each team the href of its team-page link.
```

## 2. Every team page

For **every** team in the standings, WebFetch its team page
(`https://leaguetables-soccer.pages.dev/mls-next-homegrown-division/u14/<slug>/<team-slug>`, the href from the
standings) with this prompt:

```
Return verbatim, no commentary, every match block on this page in page order, one per line:
date(YYYY-MM-DD)|time with AM/PM and time zone|first-listed (home) team|home goals|away goals|second-listed (away) team|venue|match type (write the label shown, e.g. League)|status
Use status FINAL when a score is shown, PENDING when the block says "Score pending", SCHEDULED otherwise
(leave goals empty unless FINAL). Also give the page's sentence "N matches on <team>'s ... schedule".
Do not skip any block. Confirm whether the page text you received was complete or truncated.
```

If a team page comes back truncated or summarized, fetch it once more; if it still is, record that in the file
(`! truncated <team>`) rather than guessing.

## 3. Output file: `data/fetch/<slug>.txt`

```
# conference: <Conference>
# as_of: YYYY-MM-DD HH:MM UTC          (the "data as of" time, converted to 24-hour UTC)
# total: N                             (matches stated in the Results heading)
== standings                           (one row per team, columns reordered to team|PTS|MP|W|T|L|GF|GA)
Team Name|PTS|MP|W|T|L|GF|GA
...
== team Team Name|team-slug|N          (N = matches on the team's schedule, from its page)
F|2026-09-05|1:00 PM EDT|Home|5|1|Away|Venue|League        (FINAL)
P|2026-10-31|2:00 PM EDT|Home|Away|Venue                    (PENDING: "Score pending")
...                                                         (skip SCHEDULED blocks)
```

Rules: copy team names and venues exactly as the page shows them (same spelling as the standings);
keep the time exactly as shown (`h:mm AM TZ`); one `== team` section for every team in the standings, even if
it has no completed games. Then reply with one line: teams fetched, F lines, P lines, and any truncation.
