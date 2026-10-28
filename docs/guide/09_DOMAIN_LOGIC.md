# 09 · Domain Logic

**What you will learn**
- The blood compatibility rules the app uses, and where they come from
- How the trust score, emergency rank and shortage severity are calculated, with worked examples
- The donor eligibility rules
- How locations and distances are found

> ⚠️ **Disclaimer:** this logic is for **search guidance only**. It is not medical advice. A doctor and
> the blood bank always do cross-matching before any transfusion.

---

## 1. Blood group compatibility

### The basics, simply
- Your **ABO** group (A, B, AB, O) depends on which **antigens** (markers) are on your red cells.
  A has "A", B has "B", AB has both, and O has neither.
- Your **Rh** (+/−) depends on whether the "D" antigen is there.
- A patient's body **attacks red cells that carry markers it does not have**. So:
  - O- red cells have no markers, so **anyone** can receive them. O- is the **universal red-cell donor**.
  - AB+ patients have every marker, so they can receive **any** red cells. AB+ is the **universal recipient**.
- **Plasma is the reverse.** Plasma carries *antibodies*, not markers. AB plasma has no anti-A or anti-B
  antibodies, so **AB is the universal plasma donor**, and Rh does not matter for plasma.
- **Bombay (Oh)** is a very rare group with no "H" marker. These patients can **only** receive Bombay
  blood. Even O blood can kill them.

### The red-cell table (from `data/medical_rules.json`)

| Patient | Can receive red cells from |
|---------|----------------------------|
| O- | O- |
| O+ | O+, O- |
| A- | A-, O- |
| A+ | A+, A-, O+, O- |
| B- | B-, O- |
| B+ | B+, B-, O+, O- |
| AB- | AB-, A-, B-, O- |
| AB+ | **all 8** |
| Bombay (Oh+) | Bombay (Oh+), Bombay (Oh-) |
| Bombay (Oh-) | Bombay (Oh-) |

Each rule in the JSON file has a `source` and a `source_url` (NBTC India / WHO). The API returns these
as `source_attribution`.

### Plasma (in code: `PLASMA_ABO_DONORS` in `medical.py`)
```python
PLASMA_ABO_DONORS = {"O": ["O", "A", "B", "AB"], "A": ["A", "AB"], "B": ["B", "AB"], "AB": ["AB"]}
```
If the component name contains "plasma", the ABO list is used and **both** Rh signs are allowed.
For example, an A- patient's plasma can come from A+, A-, AB+ or AB-.

> Other components, such as platelets and whole blood, use the red-cell table. This is the safe
> (strictest) choice.

### `get_compatible_donor_groups(patient_group, component)`
1. Normalises the input: `"o-"` → `O-`, `"oh+"` / `"bombay"` → `Bombay (Oh+)`.
2. Looks the group up in the table. If it is unknown, it returns `"TODO_VERIFY"` and the API answers **422**.
3. If the component is plasma, it returns the reversed ABO list.
4. It adds a **warning** for Bombay (critical) and for Rh-negative groups (anti-D risk).

### How to change a rule
Edit `data/medical_rules.json`, keep the `source` fields, and run `uv run pytest tests/unit/test_emergency_mode.py`.
You don't need to restart anything else: the rules are read from the file.

---

## 2. Trust (reliability) score

The same formula is written twice:
- in SQL, in [`mart_reliability_score.sql`](../../dbt/models/gold/mart_reliability_score.sql) (used by the app);
- in Python, in [`scoring.py`](../../src/bloodlake/scoring.py) (used by the tests).

| Part | Rule | Points |
|------|------|--------|
| Freshness | updated ≤1 day / ≤3 / ≤6 / ≤13 / older | 50 / 35 / 20 / 8 / 0 |
| Contact | contact has 8 or more digits in a row (`[0-9]{8,}`) | 25 / 0 |
| Completeness | distinct components reported: ≥3 / 1–2 / 0 | 25 / 15 / 0 |

**Label:** High ≥ 75 · Medium 40–74 · Low < 40.

**Worked example.** Civil Hospital X:
- updated 2 days ago → **35**
- contact "Phone: 02692 261234" has 11 digits → **25**
- reports PRBC, Platelets, FFP and Whole Blood (4 components) → **25**
- **total 85 → High**

**Same bank, 10 days later with no update:** 8 + 25 + 25 = **58 → Medium**.

Why these weights? **Freshness counts most**, because old stock numbers are the biggest risk in an
emergency. A working phone number matters because the user must call. Reporting more components is a
sign the bank actually uses the system.

---

## 3. Emergency rank score

This is in `routes.py`, in `get_emergency_recommendations`. All the factors are explained in
[08 §3](08_BACKEND_API.md#get-apiv1emergency-emergency-mode).

**Worked example** (with location):

| | Bank A | Bank B |
|---|---|---|
| Updated | today → 100 | 5 days → 40 |
| Trust | 85 | 100 |
| Units | 4 → 40 | 15 → 100 |
| Distance | 8 km → 92 | 60 km → 40 |
| **Score** | 0.35·100 + 0.30·85 + 0.25·40 + 0.10·92 = **79.7** | 0.35·40 + 0.30·100 + 0.25·100 + 0.10·40 = **73.0** |

Bank A ranks first. Its numbers are fresh and it is close, even though Bank B has more units.

---

## 4. Shortage severity (district)

From `mart_district_status.sql`, using the total units of that group and component in the district:

| Total units | Status | Severity |
|-------------|--------|----------|
| 0 | CRITICAL_DEPLETION | 100 |
| 1–5 | HIGH_SHORTAGE | 75 |
| 6–15 | MODERATE_SHORTAGE | 40 |
| > 15 | ADEQUATE | 10 |

---

## 5. Donor eligibility

These rules are in `data/medical_rules.json` → `donor_eligibility`. The website checks them in the
browser (`evaluateDonorEligibility()` in `app.js`), so nothing is sent to the server.

| Rule | Value | Source |
|------|-------|--------|
| Age | 18–65 years | Drugs & Cosmetics Act, NBTC |
| Weight | ≥ 45 kg (350 ml bag) | NBTC |
| Haemoglobin | ≥ 12.5 g/dL | NBTC / WHO |
| Gap since the last donation | men 90 days, women 120 days | NBTC |
| Tattoo / piercing / surgery | wait 6 months | NBTC |
| Fever / infection / antibiotics | wait until fully recovered | NBTC |
| Last donation date in the future | rejected as invalid input | (input check) |

If deferred, the page calculates the **next eligible date** = last donation + 90 or 120 days.

---

## 6. Location and distance

### Where a bank's coordinates come from: `resolve_facility_lat_lng()` in `geo.py`
It tries these sources in order:
1. **`data/district_coords.json`**: 706 state|district centres from OpenStreetMap. The key looks like
   `"gujarat|anand"`. The file is loaded once (`@lru_cache`).
2. The built-in `DISTRICT_COORDS` dictionary (big cities).
3. The built-in `STATE_COORDS` dictionary (state capitals).
4. A partial name match.
5. A default (Anand).

Then it adds a **fixed small offset** (±0.012°, about 1.2 km) based on an MD5 hash of the hospital
code. Banks in the same district then do not sit on top of each other on the map, and each bank always
gets the same position. Every result is marked `is_approximate_location = true`.

### Building `district_coords.json`: `scripts/data/geocode_districts.py`
- It calls **Nominatim** (`nominatim.openstreetmap.org/search?q=<district>, <state>&countrycodes=in`).
- It waits about 1 second between calls (Nominatim's usage policy) and sends our User-Agent.
- It keeps the coordinates it already has. Run it again only when eRaktKosh adds new districts.
- About 10 districts that Nominatim could not find were added by hand (district headquarters).

```bash
uv run python scripts/data/geocode_districts.py
```

### Distance: `haversine_distance_km(lat1, lon1, lat2, lon2)`
```python
R = 6371.0
a = sin²(Δφ/2) + cos φ1 · cos φ2 · sin²(Δλ/2)
c = 2 · atan2(√a, √(1−a))
distance = R · c            # rounded to 2 decimals
```
This is the straight-line distance. Road distance is usually 20–40 % longer.

---

Next: [10 · Frontend →](10_FRONTEND.md)
