"""Refresh Taka clip stats for the fullbacks in data/taka/fullbacks.csv, stalest profiles first.

Logged out, read-only. For each public profile: confirm the shown name matches the list, open the
Skill tab, click each of the six categories once (fresh page load per category), and keep the clip
data the page itself loads. Stores only per-player totals and sub-tag counts in data/taka/scraped.json.
Progress is saved after every profile, so it can be stopped and re-run at any time.

Run from the repo root:  python3 tools/taka_refresh.py --minutes 9 [--focus-first]
Prints a summary line and exits 0. Exit code 2 = Taka unreachable or page layout changed (stop and report).
"""
import argparse, csv, datetime as dt, json, os, random, re, sys, time, unicodedata
from collections import Counter
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
D = ROOT / "data" / "taka"
OUT = D / "scraped.json"
CATS = ["On Ball", "Intelligence", "Shot", "Defensive", "Aerial", "Physical"]
URL_RE = re.compile(r"^https://taka\.io/soccer/athlete/[0-9a-f]{24}$")
FOCUS = "thomas shestakov"


def norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", s).strip().lower()


def scrape(page, url, expected):
    caps = []

    def on_resp(r):
        if "us-api.taka.io/proscore" in r.url and r.request.method == "POST":
            try:
                body = json.loads(r.request.post_data or "{}")
                if body.get("operationName") == "getPlayerHighlightsByCategory":
                    caps.append((body["variables"], r.json()))
            except Exception:
                pass

    page.on("response", on_resp)
    rec = {"scraped_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}
    try:
        for i, cat in enumerate(CATS):
            page.goto(url, wait_until="domcontentloaded", timeout=45000)
            page.wait_for_selector("main", timeout=30000)
            if i == 0:
                page.wait_for_timeout(2000)
                title = page.title()
                name = title[7:].strip() if title.startswith("Taka - ") else None
                rec["shown_name"] = name
                if not name:
                    rec["status"] = "PRIVATE_OR_MISSING"
                    return rec
                if norm(name) != norm(expected):
                    rec["status"] = "MISMATCH"
                    return rec
            n_before = len(caps)
            sk = page.locator('text="Skill"')
            for _ in range(40):
                if sk.count():
                    break
                page.wait_for_timeout(250)
            if sk.count():
                sk.first.click(force=True, timeout=10000)
            btn = page.locator('[data-test="button-label"]').filter(has_text=re.compile(rf"^{cat}$"))
            for _ in range(40):
                if btn.count():
                    break
                page.wait_for_timeout(250)
            if not btn.count():
                continue  # category not shown on this profile -> N/A
            btn.first.click(force=True, timeout=10000)
            for _ in range(60):
                page.wait_for_timeout(250)
                if len(caps) > n_before:
                    break
        totals, loaded, subtags, fixtures, seen = {}, {}, Counter(), set(), set()
        for vars_, j in caps:
            d = (((j or {}).get("data") or {}).get("getDataBySport") or {}).get("getPlayerHighlightsByCategory")
            if not d:
                continue
            cat = vars_.get("category")
            nodes = d.get("nodes") or []
            totals[cat], loaded[cat] = d.get("total"), len(nodes)
            for n in nodes:
                fixtures.add((n.get("fixture") or {}).get("id"))
                for tag in (n.get("categorisations") or "").split(","):
                    tag = tag.strip()
                    key = (n.get("clipId"), tag)
                    if tag and key not in seen:  # a clip counts once per sub-tag across categories
                        seen.add(key)
                        subtags[tag] += 1
        rec.update(status="DONE" if totals else "NO_CATEGORIES", totals=totals,
                   complete=bool(totals) and all(totals[c] == loaded[c] for c in totals),
                   games_with_clips=len(fixtures - {None}), subtags=dict(subtags))
        return rec
    except Exception as e:
        rec.update(status="ERROR", error=str(e)[:200])
        return rec
    finally:
        page.remove_listener("response", on_resp)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--minutes", type=float, default=9)
    ap.add_argument("--focus-first", action="store_true", help="refresh Thomas first, even if recently done")
    a = ap.parse_args()
    deadline = time.time() + a.minutes * 60
    rows = [r for r in csv.DictReader(open(D / "fullbacks.csv", encoding="utf-8-sig"))
            if (r.get("status") or "OK").strip().upper() == "OK"]
    rows = [r for r in rows if URL_RE.match(r["profile_url"].strip().rstrip("/"))]
    store = json.load(open(OUT, encoding="utf-8")) if OUT.exists() else {}
    started_today = dt.datetime.now(dt.timezone.utc).date().isoformat()

    def age(r):
        rec = store.get(r["profile_url"].strip().rstrip("/"))
        return rec["scraped_at"] if rec else ""
    rows.sort(key=age)  # never-done first, then oldest
    if a.focus_first:
        rows.sort(key=lambda r: norm(r["name"]) != FOCUS)
    proxy = os.environ.get("HTTPS_PROXY")
    done, statuses, fails_in_row = 0, Counter(), 0
    with sync_playwright() as pw:
        br = pw.chromium.launch(proxy={"server": proxy} if proxy else None)
        ctx = br.new_context(viewport={"width": 1400, "height": 1000})
        ctx.route(re.compile(r".*\.(png|jpe?g|webp|gif|mp4|m3u8|ts|woff2?)(\?.*)?$"), lambda r: r.abort())
        ctx.route(re.compile(r".*(vsapi\.proscore|posthog|cookieyes|sentry|googletag|google-analytics|maze).*"), lambda r: r.abort())
        page = ctx.new_page()
        for r in rows:
            url = r["profile_url"].strip().rstrip("/")
            prev = store.get(url)
            is_focus = a.focus_first and norm(r["name"]) == FOCUS
            if prev and prev["scraped_at"][:10] == started_today and not is_focus:
                break  # everything left was refreshed today
            if time.time() > deadline - 45:
                break
            rec = scrape(page, url, r["name"].strip())
            statuses[rec["status"]] += 1
            if rec["status"] == "DONE":
                store[url] = rec
                fails_in_row = 0
            else:
                if rec["status"] in ("PRIVATE_OR_MISSING", "MISMATCH"):
                    store[url] = {**(prev or {}), "scraped_at": rec["scraped_at"], "last_status": rec["status"]}
                fails_in_row += 1
            done += 1
            tmp = OUT.with_suffix(".tmp")
            json.dump(store, open(tmp, "w", encoding="utf-8"), ensure_ascii=False, sort_keys=True)
            tmp.replace(OUT)
            if fails_in_row >= 8:
                print(f"STOP: {fails_in_row} profiles in a row failed ({dict(statuses)}); Taka may be down or its page changed.")
                sys.exit(2)
            time.sleep(random.uniform(1.5, 3.5))
        br.close()
    fresh = sum(1 for r in rows if (store.get(r["profile_url"].strip().rstrip("/")) or {}).get("scraped_at", "")[:10] == started_today)
    complete = sum(1 for v in store.values() if v.get("complete"))
    print(f"refreshed {done} this run {dict(statuses)}; {fresh}/{len(rows)} done today; {complete} profiles with complete data stored")


if __name__ == "__main__":
    main()
