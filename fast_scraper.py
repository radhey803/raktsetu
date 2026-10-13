import requests
import json
import pandas as pd
import time

def scrape_entire_country():
    print("🚀 Starting the High-Speed Master Scraper...")
    
    # 1. Load the metadata we found earlier
    try:
        with open('eraktkosh_all_metadata.json', 'r') as f:
            metadata = json.load(f)
    except FileNotFoundError:
        print("❌ Please ensure eraktkosh_all_metadata.json is in the same folder.")
        return

    states = metadata.get("States_and_Districts", [])
    master_data = []

    print(f"🗺️ Found {len(states)} States. Beginning extraction...")

    # 2. Loop through every State
    for state in states:
        state_id = state.get("stateCode")
        state_name = state.get("stateName")
        districts = state.get("districts", [])
        
        print(f"\n📍 Processing State: {state_name} ({len(districts)} districts)")

        # 3. Loop through every District in this State
        for district in districts:
            district_id = district.get("districtCode")
            district_name = district.get("districtName")
            
            # 4. Hit the hidden Backend API we reverse-engineered!
            # Notice we leave bloodGroup and componentId out to fetch ALL types at once.
            url = f"https://eraktkosh.mohfw.gov.in/eraktkoshPortal/eraktkosh/blood-availability?stateCode={state_id}&districtId={district_id}"
            
            try:
                response = requests.get(url, timeout=10)
                
                # If the API returned data
                if response.status_code == 200 and response.text.strip():
                    blood_banks = response.json()
                    
                    # 5. Add our State/District labels and save the records
                    for bank in blood_banks:
                        bank["State"] = state_name
                        bank["District"] = district_name
                        master_data.append(bank)
                
                # VERY IMPORTANT: Sleep for 0.5 seconds to be polite to the government server
                # Otherwise, they will block your IP for a DDoS attack.
                time.sleep(0.5)

            except Exception as e:
                print(f"⚠️ Failed to fetch {district_name}: {e}")

    # 6. Save the entire country's data to one massive CSV
    if master_data:
        df = pd.DataFrame(master_data)
        df.to_csv("INDIA_blood_inventory.csv", index=False)
        print(f"\n✅ DONE! Successfully scraped {len(df)} blood bank records across India.")
        print("💾 Saved to 'INDIA_blood_inventory.csv'")
    else:
        print("\n❌ No data was extracted.")

if __name__ == "__main__":
    scrape_entire_country()
