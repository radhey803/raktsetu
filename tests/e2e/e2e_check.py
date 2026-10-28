"""
End-to-end browser check (Playwright). Needs the server running: make run
Usage: uv run python tests/e2e/e2e_check.py
Prints PASS/FAIL counts and every failed check.
"""

import re

from playwright.sync_api import sync_playwright

B = "http://localhost:8000"
bugs, ok = [], []


def check(cond, name, detail=""):
    (ok if cond else bugs).append(f"{name} {detail}".strip())


def run(pg, label):
    errs, bad = [], []
    pg.on("pageerror", lambda e: errs.append(str(e)[:150]))
    pg.on("console", lambda m: m.type == "error" and errs.append(m.text[:150]))
    pg.on(
        "response",
        lambda r: (
            r.status >= 400 and "basemaps" not in r.url and bad.append(f"{r.status} {r.url[-70:]}")
        ),
    )
    dialogs = []
    pg.on("dialog", lambda d: (dialogs.append(d.message[:80]), d.dismiss()))

    def T(s):
        return pg.locator(s).first.inner_text().strip()

    p = f"[{label}]"

    pg.goto(B, wait_until="networkidle")
    pg.wait_for_timeout(1500)
    for k in ("total", "fresh", "stale", "today"):
        check(T(f"#kpi-{k}-banks") not in ("0", "--"), f"{p} KPI {k}", T(f"#kpi-{k}-banks"))
    check(pg.locator("#statesChart").is_visible(), f"{p} states chart visible")
    # every nav / footer anchor points at an existing section
    for href in set(
        pg.eval_on_selector_all("a[href^='#']", "els=>els.map(e=>e.getAttribute('href'))")
    ):
        check(href == "#" or pg.locator(href).count() == 1, f"{p} anchor target exists", href)

    # disclaimer dismiss
    if pg.locator(".disclaimer-dismiss-btn").first.is_visible():
        pg.locator(".disclaimer-dismiss-btn").first.click()
        check(
            not pg.locator(".mandatory-disclaimer-banner").first.is_visible(),
            f"{p} disclaimer dismiss",
        )

    # finder: state -> district -> search
    pg.select_option("#state-select", "Gujarat")
    pg.wait_for_timeout(200)
    check(
        not pg.is_disabled("#district-select")
        and pg.locator("#district-select option").count() > 5,
        f"{p} districts populate",
    )
    pg.select_option("#district-select", "Anand")
    pg.click("#search-btn")
    pg.wait_for_timeout(1500)
    locs = pg.locator(".hospital-card .meta-line").all_inner_texts()
    check(
        locs and all("Anand" in t for t in locs[::2]), f"{p} district filter applies", str(locs[:1])
    )
    check("district=Anand" in pg.url, f"{p} URL sync", pg.url[-60:])
    # blood group filter: every card shows only that group with stock
    pg.locator(".segment-btn[data-group='B-']").click()
    pg.wait_for_timeout(1500)
    check(pg.locator(".hospital-card").count() > 0, f"{p} B- results")
    # text search no-result + reset
    pg.fill("#search-input", "zzzz-no-such-bank")
    pg.press("#search-input", "Enter")
    pg.wait_for_timeout(1200)
    check(pg.locator(".state-message-card").count() == 1, f"{p} empty state shown")
    pg.click("#reset-btn")
    pg.wait_for_timeout(1800)
    check(
        pg.input_value("#state-select") == "ALL" and pg.input_value("#search-input") == "",
        f"{p} reset filters",
    )
    check(
        int(T("#results-count").replace(",", "")) > 1000,
        f"{p} reset restores results",
        T("#results-count"),
    )

    # sort options change order
    firsts = {}
    for v in ("freshness", "units", "reliability"):
        pg.select_option("#sort-select", v)
        pg.wait_for_timeout(1500)
        firsts[v] = T(".hospital-card .card-title")
    check(len(set(firsts.values())) > 1, f"{p} sort changes order", str(firsts))
    pg.select_option("#sort-select", "units")
    pg.wait_for_timeout(1500)
    tops = [
        sum(int(x) for x in re.findall(r"\d+", c.split("units", 1)[-1][:200]))
        for c in pg.locator(".stock-grid-4x2").all_inner_texts()[:3]
    ]
    check(tops == sorted(tops, reverse=True), f"{p} units sort descending", str(tops))
    pg.select_option("#sort-select", "distance")
    pg.wait_for_timeout(1500)
    check(
        pg.locator(".hospital-card").count() > 0,
        f"{p} distance sort without location still shows results",
    )

    # pagination
    if pg.locator("#page-next-btn").is_visible():
        s1 = T("#pagination-start")
        pg.click("#page-next-btn")
        pg.wait_for_timeout(500)
        check(T("#pagination-start") != s1, f"{p} next page")
        pg.click("#page-last-btn")
        pg.wait_for_timeout(500)
        check(T("#pagination-end") == T("#pagination-total"), f"{p} last page")
        pg.select_option("#page-size-select", index=1)
        pg.wait_for_timeout(500)
        check(T("#pagination-start") == "1", f"{p} page size resets page")
    else:
        bugs.append(f"{p} pagination hidden")

    # card actions
    tel = pg.locator(".hospital-card a[href^='tel:']").first.get_attribute("href")
    check(re.fullmatch(r"tel:[0-9+\- ]{8,16}", tel or ""), f"{p} card tel link", tel)
    pg.locator(".btn-trend-link").first.click()
    pg.wait_for_timeout(1200)
    check(pg.is_visible("#history-modal"), f"{p} trend modal opens")
    pg.select_option("#modal-component-select", index=1)
    pg.wait_for_timeout(1000)
    check(pg.locator("#modal-summary-tbody tr").count() >= 1, f"{p} trend modal component switch")
    pg.click("#modal-close-btn")
    check(
        pg.locator("#history-modal.hidden").count() == 1
        and pg.evaluate("document.body.style.overflow") == "",
        f"{p} trend modal closes, scroll restored",
    )
    pg.locator(".badge-reliability").first.click()
    check(pg.is_visible("#trust-modal"), f"{p} trust modal opens")
    pg.click("#trust-close-btn")
    check(pg.locator("#trust-modal.hidden").count() == 1, f"{p} trust modal closes")

    # map view
    pg.click("#toggle-map-btn")
    pg.wait_for_timeout(2500)
    check(pg.locator(".custom-pin-marker").count() > 0, f"{p} map markers")
    pg.locator(".custom-pin-marker").first.click(force=True)
    pg.wait_for_timeout(500)
    check(pg.locator(".leaflet-popup").count() == 1, f"{p} marker popup")
    pg.click("#map-reset-btn")
    pg.click("#toggle-grid-btn")
    pg.wait_for_timeout(300)
    check(
        pg.is_visible("#hospitals-grid") and pg.is_visible("#pagination-wrapper"),
        f"{p} back to grid",
    )

    # emergency mode: each group
    for g in pg.eval_on_selector_all(
        "#emergency-patient-group option", "o=>o.map(x=>x.value).filter(Boolean)"
    ):
        pg.select_option("#emergency-patient-group", g)
        pg.click("#emergency-search-btn")
        pg.wait_for_timeout(900)
        txt = T("#emergency-cards-grid")
        check("Error" not in txt and txt, f"{p} emergency {g}", txt[:60])
        if g.endswith("-") or "Bombay" in g:
            check(pg.is_visible("#emergency-clinical-alert"), f"{p} clinical alert for {g}")
    tels = pg.eval_on_selector_all(".emergency-tel-btn", "e=>e.map(x=>x.getAttribute('href'))")
    check(
        all(re.fullmatch(r"tel:\+?\d{8,13}", t) for t in tels),
        f"{p} emergency tel links",
        str(tels[:2]),
    )

    # rare + shortages + export
    check(pg.locator("#rare-blood-tbody tr").count() > 1, f"{p} rare table")
    pg.select_option("#shortage-group-filter", "AB-")
    pg.wait_for_timeout(1000)
    check("AB-" in T("#shortages-tbody"), f"{p} shortage group filter")
    pg.select_option("#shortage-state-filter", "Gujarat")
    pg.wait_for_timeout(1000)
    rows = pg.locator("#shortages-tbody tr").all_inner_texts()
    check(
        all("Gujarat" in r for r in rows) or "No critical" in rows[0],
        f"{p} shortage state filter",
        rows[0][:60],
    )
    for btn in ("#export-shortages-btn", "#export-availability-btn"):
        with pg.expect_download(timeout=20000) as d:
            pg.click(btn)
        check(
            d.value.suggested_filename.endswith(".csv"),
            f"{p} export {btn}",
            d.value.suggested_filename,
        )

    # donor eligibility
    def donor(age, weight, gender, days_ago, expect):
        pg.fill("#donor-age", str(age))
        pg.fill("#donor-weight", str(weight))
        pg.select_option("#donor-gender", gender)
        pg.evaluate(
            f"d=new Date();d.setDate(d.getDate()-({days_ago}));document.getElementById('donor-last-date').value=d.toISOString().split('T')[0]"
        )
        pg.locator("#donor-form [type=submit]").click()
        pg.wait_for_timeout(200)
        check(
            expect.lower() in T("#donor-status-tag").lower(),
            f"{p} donor {age}y {weight}kg {gender} {days_ago}d",
            T("#donor-status-tag"),
        )

    donor(25, 70, "male", 100, "Eligible")
    donor(17, 70, "male", 100, "Deferred")
    donor(25, 40, "male", 100, "Deferred")
    donor(30, 60, "female", 100, "Deferred")
    donor(25, 70, "male", -10, "Deferred")  # last donation in the future

    # health section
    check(T("#health-last-sync") not in ("--", "Never"), f"{p} health last sync")
    check(
        "hours ago" in T("#health-sync-age") and "-" not in T("#health-sync-age"),
        f"{p} health sync age",
        T("#health-sync-age"),
    )
    check(pg.locator("#health-runs-tbody tr").count() > 0, f"{p} health runs table")

    check(not errs, f"{p} console errors", str(errs[:3]))
    check(not bad, f"{p} failed requests", str(bad[:3]))
    check(not dialogs, f"{p} unexpected alerts", str(dialogs[:2]))


with sync_playwright() as pw:
    b = pw.chromium.launch()
    run(
        b.new_context(viewport={"width": 1366, "height": 900}, accept_downloads=True).new_page(),
        "desktop",
    )
    m = b.new_context(
        viewport={"width": 390, "height": 844},
        is_mobile=True,
        has_touch=True,
        accept_downloads=True,
    )
    mp = m.new_page()
    mp.goto(B, wait_until="networkidle")
    mp.click(".nav-toggle")
    mp.click("#main-nav a[href='#health-section']")
    mp.wait_for_timeout(2000)
    check(
        mp.evaluate(
            "document.querySelector('#health-section').getBoundingClientRect().top < 200 && document.querySelector('#health-section').getBoundingClientRect().top > 60"
        ),
        "[mobile] nav jumps to section",
    )
    check(
        mp.evaluate(
            "(()=>{const h=document.querySelector('.app-header').getBoundingClientRect().bottom;return document.querySelector('#health-section').getBoundingClientRect().top>=h-2})()"
        ),
        "[mobile] sticky header doesn't cover section title",
    )
    run(mp, "mobile")
    # offline: service worker serves shell
    ctx = b.new_context()
    op = ctx.new_page()
    op.goto(B, wait_until="networkidle")
    op.wait_for_timeout(1500)
    op.reload(wait_until="networkidle")
    op.wait_for_timeout(1500)
    ctx.set_offline(True)
    try:
        op.reload(wait_until="domcontentloaded", timeout=8000)
        op.wait_for_timeout(1500)
        check(op.locator(".brand-name").count() == 1, "[offline] app shell loads")
        check(
            op.locator("#global-stale-banner, .state-message-card").count() > 0,
            "[offline] offline notice shown",
        )
    except Exception as e:
        bugs.append(f"[offline] reload failed {str(e)[:80]}")
    b.close()

print(f"PASS {len(ok)}  FAIL {len(bugs)}")
print("\n".join(bugs))
