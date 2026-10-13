import asyncio
import aiohttp
import json
import pandas as pd
import time

# A Semaphore is a rate-limiter. It ensures only 10 requests happen at the exact same time.
# This prevents us from crashing the government server (DDoS) while still being incredibly fast.
CONCURRENT_REQUESTS = 10
semaphore = asyncio.Semaphore(CONCURRENT_REQUESTS)

async def fetch_district_data(session, state_name, state_id, district_name, district_id):
    url = f"https://eraktkosh.mohfw.gov.in/eraktkoshPortal/eraktkosh/blood-availability?stateCode={state_id}&districtId={district_id}"
    
    # The semaphore ensures we wait our turn if there are already 10 requests running
    async with semaphore:
        try:
            # We don't need time.sleep() anymore because the semaphore controls the flow!
            async with session.get(url, timeout=15) as response:
                if response.status == 200:
                    text = await response.text()
                    if text.strip():
                        blood_banks = json.loads(text)
                        
                        # Add state and district labels
                        for bank in blood_banks:
                            bank["State"] = state_name
                            bank["District"] = district_name
                        return blood_banks
        except Exception as e:
            print(f"⚠️ Failed to fetch {district_name}: {e}")
    return []

async def scrape_entire_country_async():
    print("🚀 Starting the ASYNC High-Speed Scraper...")
    start_time = time.time()
    
    with open('eraktkosh_all_metadata.json', 'r') as f:
        metadata = json.load(f)

    states = metadata.get("States_and_Districts", [])
    
    # 1. We prepare a massive list of tasks (one for every single district)
    tasks = []
    
    # We use a single ClientSession to reuse network connections (super fast)
    async with aiohttp.ClientSession() as session:
        for state in states:
            state_id = state.get("stateCode")
            state_name = state.get("stateName")
            
            for district in state.get("districts", []):
                district_id = district.get("districtCode")
                district_name = district.get("districtName")
                
                # We don't run them yet, we just add them to the queue
                task = asyncio.create_task(
                    fetch_district_data(session, state_name, state_id, district_name, district_id)
                )
                tasks.append(task)
        
        print(f"📦 Created {len(tasks)} parallel district tasks. Firing them now...")
        
        # 2. FIRE ALL TASKS AT ONCE! (The semaphore keeps it safe)
        results = await asyncio.gather(*tasks)
    
    # 3. Combine all the results
    master_data = []
    for district_result in results:
        master_data.extend(district_result)
        
    end_time = time.time()

    # 4. Save the data
    if master_data:
        df = pd.DataFrame(master_data)
        df.to_csv("INDIA_blood_inventory_async.csv", index=False)
        print(f"\n✅ DONE! Successfully scraped {len(df)} blood bank records across India.")
        print(f"⏱️  Total time taken: {round(end_time - start_time, 2)} seconds!")
        print("💾 Saved to 'INDIA_blood_inventory_async.csv'")
    else:
        print("\n❌ No data was extracted.")

if __name__ == "__main__":
    # Windows fix for asyncio, not strictly needed for Linux but good practice
    import sys
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
    asyncio.run(scrape_entire_country_async())
