# BloodGrid: One-Page Commercial Pitch & 2-Minute Demo Script

---

## 1. Executive Pitch (One-Page)

### The Problem
In medical emergencies across India—trauma accidents, emergency surgeries, thalassemia transfusions, postpartum hemorrhages—finding compatible blood components is a panicked, fragmented ordeal. Families and doctors scramble across WhatsApp groups, make dozens of futile phone calls, or physically drive to blood banks only to find units depleted or reserved.

While the Government of India operates the eRaktKosh portal, it suffers from three critical bottlenecks:
1. **Raw, Unindexed UI**: Citizens must manually cycle through dropdowns across 781 districts without cross-district radius search, reliability ratings, or mobile-first navigation.
2. **Zero Automated Shortage Intelligence**: NGOs, blood donation organizers, and hospital networks have no way to subscribe to alerts (e.g. *"Alert our foundation when Anand drops below 5 units of O- PRBC"*).
3. **No Commercial-Grade Developer API**: Health-tech startups, hospital management software (HMS), and ambulance dispatchers lack a low-latency, SLA-backed REST API to query real-time national blood inventory.

### The Solution: BloodGrid
BloodGrid transforms national blood metrics into an enterprise-grade intelligence platform:
- **Zero-Latency Emergency Finder**: Sub-5ms search with strict group normalization (`B+` never confuses `AB+`; `O+` never confuses `Oh+`), verified contact buttons, and precision geolocation.
- **Reliability Scoring Engine (0-100)**: Proprietary algorithm penalizing stale reporting (>24h), invalid phone numbers, or incomplete component reporting, guiding doctors to facilities that actually respond.
- **Automated Shortage Radar & Multi-Channel Alerts**: Proactive notifications via Telegram and Email when critical blood supplies drop below safety thresholds.
- **NGO Donation Camp Suggester**: Highlights districts experiencing persistent deficits across consecutive snapshots, optimizing voluntary donation drive scheduling.

### Target Customers & Commercial Tiers (Prices in INR)
1. **Citizens & Public (Free)**: Search, map, SOS card, and district availability.
2. **Pro (₹499 / month)**: Individual emergency alerts, SMS/Telegram triggers, up to 10 watchlist districts.
3. **API Developer (₹2,499 / month)**: Programmatic REST API access, 500 requests/minute, webhook subscriptions.
4. **Organization / Hospital Network (₹7,999 / month)**: Multi-seat dashboard, daily shortage CSV exports, blood camp location recommendations, dedicated support.

---

## 2. Two-Minute Live Product Demo Script

**Speaker Setup**: Have `https://bloodgrid.in` (or local `http://localhost:8000`) open on a clean browser tab.

```text
[0:00 - 0:25] THE PAIN & THE HOOK
"Imagine a doctor in Anand needs 3 units of O-negative Packed Red Blood Cells for an emergency surgery in 45 minutes. Right now, families make desperate calls or post frantic WhatsApp messages. 

eRaktKosh has the data, but it's trapped in a slow portal without real-time filtering or reliability indicators.

Enter BloodGrid."

[0:25 - 0:55] EMERGENCY FINDER & RELIABILITY SCORE
[Action: Select 'Gujarat' -> 'Anand' -> 'Packed Red Blood Cells' -> 'O-']
"With one tap on BloodGrid, our sub-5-millisecond engine queries over 4,680 blood banks nationwide. 

Notice what you see: Not just a count, but a Reliability Score. Indian Red Cross Anand has a 92 out of 100 because it updated within the last 12 hours, has an active, verified phone number, and reports full component breakdowns. 

One tap opens the dialer directly. Another tap shares an emergency SOS card on WhatsApp with exact address and inventory count."

[0:55 - 1:25] RARE BLOOD RADAR & DISTRICT DEFICITS
[Action: Click 'Rare Blood Radar' tab or toggle Bombay Blood Group]
"What if the patient has Bombay Blood Group—one in ten thousand in India? 
Our Rare Blood Radar indexes Oh+ and Oh- inventory across the entire state instantly. 

For NGOs and CSR foundations, our Shortage Radar flags districts in red where inventory has hit zero, and our Donation Camp Suggester mathematically pinpoints where donation drives will save the most lives this weekend."

[1:25 - 1:55] AUTOMATION & COMMERCIAL MOAT
[Action: Switch to /dashboard to show API Keys & Alerts]
"Behind this is a modern data lakehouse: DuckDB analytical engine, immutable Parquet landing zone, and automated 4-hour crawls with circuit breakers.

Hospital networks and health-tech platforms subscribe to our Developer API at ₹2,499/month for programmatic access. 

BloodGrid costs just ₹440 a month to run on a lightweight VPS, meaning we break even with just two paid subscribers."

[1:55 - 2:00] CLOSING
"BloodGrid: Real-time national blood intelligence that turns panic into precise action. Thank you."
```
