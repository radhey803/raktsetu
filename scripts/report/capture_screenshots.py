"""
Captures the report screenshots from the running website (make run first).

Desktop shots use a 760 px wide browser so that, placed at full page width (6.2 in),
text prints at about 8 pt and stays readable without zooming. Tall shots are cropped
to at most 1.2x their width so they fit a page at full width.

Usage: uv run python scripts/report/capture_screenshots.py
"""

from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

BASE = "http://localhost:8000"
OUT = Path(__file__).resolve().parents[2] / "docs" / "screenshots"
MAX_RATIO = 1.2


def crop(path):
    im = Image.open(path)
    if im.height > im.width * MAX_RATIO:
        im.crop((0, 0, im.width, int(im.width * MAX_RATIO))).save(path)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("*.png"):
        old.unlink()
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 760, "height": 1000}, device_scale_factor=2)
        pg = ctx.new_page()
        pg.goto(BASE, wait_until="networkidle")
        pg.wait_for_timeout(2000)
        if pg.locator(".disclaimer-dismiss-btn").first.is_visible():
            pg.locator(".disclaimer-dismiss-btn").first.click()
        # the sticky header would otherwise cover the top of element screenshots
        pg.add_style_tag(content=".app-header { position: static !important; }")

        def shot(selector, name):
            el = pg.locator(selector).first
            el.scroll_into_view_if_needed()
            pg.wait_for_timeout(400)
            el.screenshot(path=OUT / f"{name}.png")
            crop(OUT / f"{name}.png")

        pg.evaluate("scrollTo(0, 0)")
        pg.wait_for_timeout(300)
        pg.screenshot(path=OUT / "01_home.png")
        pg.select_option("#emergency-patient-group", "O-")
        pg.click("#emergency-search-btn")
        pg.wait_for_timeout(1500)
        shot("#emergency-section", "02_emergency")
        pg.select_option("#state-select", "Gujarat")
        pg.select_option("#district-select", "Anand")
        pg.click("#search-btn")
        pg.wait_for_timeout(2000)
        shot("#finder-section", "03_finder")
        shot("#hospitals-grid", "03b_cards")
        pg.locator(".btn-trend-link").nth(1).click()
        pg.wait_for_timeout(2000)
        pg.locator("#history-modal .modal-container").screenshot(path=OUT / "05_trend_modal.png")
        crop(OUT / "05_trend_modal.png")
        pg.keyboard.press("Escape")
        pg.locator(".badge-reliability").first.click()
        pg.wait_for_timeout(500)
        pg.locator("#trust-modal .modal-container").screenshot(path=OUT / "06_trust_modal.png")
        crop(OUT / "06_trust_modal.png")
        pg.keyboard.press("Escape")
        pg.click("#toggle-map-btn")
        pg.wait_for_timeout(4000)
        shot("#map-view-container", "04_map")
        pg.click("#toggle-grid-btn")
        shot("#chart-section", "07_network_chart")
        shot("#radar-section", "08_rare_blood")
        shot("#shortages-section", "09_shortages")
        pg.fill("#donor-age", "24")
        pg.fill("#donor-weight", "68")
        pg.locator("#donor-form [type=submit]").click()
        pg.wait_for_timeout(400)
        shot("#donor-section", "10_donor")
        shot("#health-section", "11_data_health")

        m = browser.new_context(
            viewport={"width": 390, "height": 780},
            device_scale_factor=2,
            is_mobile=True,
            has_touch=True,
        )
        mp = m.new_page()
        mp.goto(BASE, wait_until="networkidle")
        mp.wait_for_timeout(1500)
        mp.screenshot(path=OUT / "12_mobile_home.png")
        mp.click(".nav-toggle")
        mp.wait_for_timeout(400)
        mp.screenshot(path=OUT / "13_mobile_menu.png")
        mp.click(".nav-toggle")
        mp.locator(".hospital-card").first.scroll_into_view_if_needed()
        mp.wait_for_timeout(800)
        mp.screenshot(path=OUT / "14_mobile_cards.png")
        mp.select_option("#emergency-patient-group", "O-")
        mp.click("#emergency-search-btn")
        mp.wait_for_timeout(1500)
        mp.locator(".emergency-card").first.scroll_into_view_if_needed()
        mp.wait_for_timeout(500)
        mp.screenshot(path=OUT / "15_mobile_emergency.png")
        browser.close()
    print(f"Saved {len(list(OUT.glob('*.png')))} screenshots to {OUT}")


if __name__ == "__main__":
    main()
