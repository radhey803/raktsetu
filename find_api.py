import asyncio
from playwright.async_api import async_playwright
import json

async def intercept_search_api():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # Listen to all API requests and print the ones triggered by the Search button
        page.on("request", lambda request: asyncio.create_task(log_request(request)))
        page.on("response", lambda response: asyncio.create_task(log_response(response)))

        print("🌐 Navigating to eRaktKosh...")
        await page.goto("https://eraktkosh.mohfw.gov.in/eraktkoshPortal/#/publicPages/bloodAvailabilitySearch")
        await page.wait_for_load_state("networkidle")

        print("⏳ Selecting Gujarat...")
        await page.locator("#rc_select_1").click()
        await page.locator("#rc_select_1").fill("gu")
        await page.get_by_text("Gujarat", exact=True).click()

        await page.wait_for_timeout(2000)

        print("⏳ Selecting Ahmedabad...")
        await page.locator("#rc_select_2").click(timeout=5000)
        await page.locator("#rc_select_2").fill("ahm")
        await page.get_by_text("Ahmedabad", exact=True).click()

        print("🔎 Clicking Search (Watch the logs!)...")
        await page.get_by_role("button", name="Search").click()

        print("⏳ Waiting for table to load...")
        # Wait for the table to guarantee the API call finished
        await page.wait_for_selector("tr.ant-table-row", timeout=15000)
        
        await asyncio.sleep(2) # Give it 2 seconds to finish printing logs
        await browser.close()

async def log_request(request):
    url = request.url.lower()
    # We only care about backend API calls, ignoring images/css
    if "api" in url or "search" in url or "blood" in url or "cnt" in url:
        print(f"\n[🚀 OUTGOING REQUEST] {request.method} {request.url}")
        if request.post_data:
            print(f"[📦 PAYLOAD] {request.post_data}")

async def log_response(response):
    url = response.url.lower()
    if "api" in url or "search" in url or "blood" in url or "cnt" in url:
        try:
            if "application/json" in response.headers.get("content-type", ""):
                text = await response.text()
                print(f"[✅ INCOMING RESPONSE from {response.url}] (First 200 chars):")
                print(text[:200] + "...\n")
        except Exception:
            pass

if __name__ == "__main__":
    asyncio.run(intercept_search_api())
