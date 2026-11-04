"""Open players.html in headless Chromium (phone and desktop) and check it before publishing.

Checks: no script errors; row count matches the data; Thomas's row and comparison panel are present;
sorting changes the order; no sideways scrolling on a phone. Exit 0 = OK, 1 = do not publish.
Run from the repo root:  python3 tools/check_players.py
"""
import json
import re
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
html = (ROOT / "players.html").read_text(encoding="utf-8")
data = json.loads(re.search(r"const DATA=(\[.*?\]), COLS=", html, re.S).group(1))
fails, errors = [], []
if len(data) < 50:
    fails.append(f"only {len(data)} players in the data")
with sync_playwright() as p:
    b = p.chromium.launch()
    for name, vp, mob in [("phone", {"width": 390, "height": 844}, True), ("desktop", {"width": 1300, "height": 900}, False)]:
        pg = b.new_page(viewport=vp, is_mobile=mob)
        pg.on("pageerror", lambda ex: errors.append(str(ex)))
        pg.goto((ROOT / "players.html").as_uri())
        pg.wait_for_timeout(600)
        rows = pg.locator("#tbl tbody tr").count()
        if rows != len(data):
            fails.append(f"{name}: table shows {rows} rows, data has {len(data)}")
        if not pg.locator("tr.me").count():
            fails.append(f"{name}: Thomas's row is missing")
        if pg.locator("#focus").is_hidden():
            fails.append(f"{name}: Thomas's comparison panel is hidden")
        first = pg.inner_text("#tbl tbody tr td")
        pg.click("th[data-k='defensive']")
        pg.click("th[data-k='defensive']")
        if pg.inner_text("#tbl tbody tr td") == first and len(data) > 2:
            fails.append(f"{name}: sorting did not change the order")
        if mob and pg.evaluate("document.documentElement.scrollWidth - innerWidth") > 1:
            fails.append("phone: page scrolls sideways")
    b.close()
for x in errors:
    fails.append("script error: " + x)
print("OK" if not fails else "FAIL\n  " + "\n  ".join(fails))
sys.exit(1 if fails else 0)
