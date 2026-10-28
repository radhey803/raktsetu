"""Build data/district_coords.json: one OpenStreetMap (Nominatim) centroid per state/district.

Run once (about 1 request/second, ~12 minutes); re-run only when new districts appear.
Usage: uv run python scripts/data/geocode_districts.py
"""

import json
import time
import urllib.parse
import urllib.request

import duckdb

from bloodlake.config import settings
from bloodlake.geo import STATE_COORDS, haversine_distance_km

OUT = settings.base_dir / "data" / "district_coords.json"


def nominatim(query: str):
    params = urllib.parse.urlencode(
        {"q": query, "format": "json", "limit": 1, "countrycodes": "in"}
    )
    req = urllib.request.Request(
        f"https://nominatim.openstreetmap.org/search?{params}",
        headers={"User-Agent": settings.user_agent},
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read())
    return (float(data[0]["lat"]), float(data[0]["lon"])) if data else None


def main() -> None:
    coords = json.loads(OUT.read_text()) if OUT.exists() else {}
    con = duckdb.connect(str(settings.serving_path), read_only=True)
    pairs = con.execute(
        "SELECT DISTINCT state_name, district_name FROM main_gold.dim_blood_banks "
        "WHERE state_name IS NOT NULL AND district_name IS NOT NULL ORDER BY 1, 2"
    ).fetchall()
    for state, district in pairs:
        key = f"{state.strip().lower()}|{district.strip().lower()}"
        if key in coords:
            continue
        state_centre = STATE_COORDS.get(state.strip().lower())
        hit = None
        for query in (f"{district} district, {state}, India", f"{district}, {state}, India"):
            time.sleep(1.1)  # Nominatim usage policy: max 1 request/second
            try:
                hit = nominatim(query)
            except Exception as exc:
                print("error", key, exc)
            # reject matches that landed in the wrong state
            if hit and (not state_centre or haversine_distance_km(*hit, *state_centre) < 900):
                break
            hit = None
        coords[key] = list(hit) if hit else None
        print(key, coords[key], flush=True)
        OUT.write_text(json.dumps(coords, indent=1, sort_keys=True))
    print("done", sum(v is not None for v in coords.values()), "/", len(coords))


if __name__ == "__main__":
    main()
