import asyncio
import pandas as pd
from playwright.async_api import async_playwright

async def scrape_eraktkosh():
    async with async_playwright() as p:
        print("🚀 Launching browser...")
        browser = await p.chromium.launch(headless=False, slow_mo=500)
        context = await browser.new_context()
        page = await context.new_page()

        print("🌐 Navigating to eRaktKosh...")
        await page.goto("https://eraktkosh.mohfw.gov.in/eraktkoshPortal/#/publicPages/bloodAvailabilitySearch")
        await page.wait_for_load_state("networkidle")

        try:
            print("⏳ Selecting State (Gujarat)...")
            await page.locator("#rc_select_1").click()
            await page.locator("#rc_select_1").fill("gu")
            await page.get_by_text("Gujarat", exact=True).click()

            print("⏳ Waiting for districts to load from the server...")
            await page.wait_for_timeout(2000)

            print("⏳ Selecting District (Ahmedabad)...")
            # In Ant Design, the second dropdown input is usually rc_select_2
            # Wait for it to become interactive
            await page.locator("#rc_select_2").click(timeout=5000)
            await page.locator("#rc_select_2").fill("ahm")
            await page.get_by_text("Ahmedabad", exact=True).click()

            # Optional: Selecting Component
            # await page.get_by_text("Packed Red Blood Cells", exact=True).click()

            print("🔎 Clicking Search...")
            await page.get_by_role("button", name="Search").click()

            print("⏳ Waiting for the results table to load...")
            # Ant Design uses 'ant-table-row' for actual visible data rows. 
            # The first generic 'tr' is hidden, which causes timeouts.
            await page.wait_for_selector("tr.ant-table-row", timeout=15000)

            print("📊 Extracting data...")
            # Extract all actual data rows from the table
            rows = await page.locator("tr.ant-table-row").all()
            
            scraped_data = []
            for row in rows:
                cells = await row.locator("td").all_inner_texts()
                
                if len(cells) >= 4:
                    raw_blood_bank = cells[1].strip()
                    category = cells[2].strip()
                    raw_availability = cells[3].strip()
                    last_updated = cells[4].strip() if len(cells) > 4 else "N/A"
                    
                    # 1. Parse Blood Bank details
                    parts = raw_blood_bank.split('\n\n')
                    hospital_name = parts[0].strip()
                    details = parts[1] if len(parts) > 1 else ""
                    
                    phone = email = ""
                    import re
                    phone_match = re.search(r"Phone:\s*([0-9\-\,\s]+)", details)
                    if phone_match: phone = phone_match.group(1).strip().strip(',')
                    
                    email_match = re.search(r"Email:\s*([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)", details)
                    if email_match: email = email_match.group(1).strip()
                    
                    address = details.split("Phone:")[0].strip().strip(',') if "Phone:" in details else details.strip()
                    
                    # 2. Setup a base dictionary for this row
                    row_data = {
                        "Hospital_Name": hospital_name,
                        "Address": address,
                        "Phone": phone,
                        "Email": email,
                        "Category": category,
                        "Last_Updated": last_updated
                    }
                    
                    # 3. Parse Availability (e.g., "O+Ve : 56, A+Ve : 31")
                    if raw_availability != "Not Available":
                        items = raw_availability.split(",")
                        for item in items:
                            if ":" in item:
                                bg, qty = item.split(":")
                                clean_bg = bg.strip().replace("Ve", "") # Converts O+Ve to O+
                                row_data[f"Blood_{clean_bg}"] = int(qty.strip())
                    
                    scraped_data.append(row_data)

            # Convert to Pandas DataFrame
            df = pd.DataFrame(scraped_data)
            
            # Reorder columns slightly so Blood Groups are neatly at the end
            # Fill NaN values in Blood Group columns with 0
            df = df.fillna(0)
            
            print("\n✅ Scraped & Cleaned Successfully! Here is the proper data:")
            print(df.head())
            print(f"\nTotal Records Found: {len(df)}")
            
            df.to_csv("ahmedabad_blood_inventory.csv", index=False)
            print("💾 Saved CLEAN data to 'ahmedabad_blood_inventory.csv'")

        except Exception as e:
            print(f"\n❌ Error during interaction: {e}")

        # Keep browser open for 3 seconds so you can see it finished, then close
        await asyncio.sleep(3)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(scrape_eraktkosh())
