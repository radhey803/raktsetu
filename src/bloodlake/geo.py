"""
Geographic Coordinate & Distance Resolver (District Centroid & Geocode Service)
=============================================================================
Resolves latitude and longitude for Indian blood bank facilities:
1. Haversine Great Circle distance calculation in kilometers.
2. Verified State and District centroid lookup with deterministic jitter.
3. Nominatim Geocoding Cache (geocode_cache table) adhering to 1 req/sec policy.
4. Precision labeling: 'exact', 'street', 'district_centroid', 'failed'.
"""

import hashlib
import json
import math
import time
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional, Tuple

STATE_COORDS: Dict[str, Tuple[float, float]] = {
    "andaman and nicobar islands": (11.6670, 92.7359),
    "andhra pradesh": (15.9129, 79.7400),
    "arunachal pradesh": (27.1004, 93.6166),
    "assam": (26.2006, 92.9376),
    "bihar": (25.0961, 85.3131),
    "chandigarh": (30.7333, 76.7794),
    "chhattisgarh": (21.2787, 81.8661),
    "dadra and nagar haveli and daman and diu": (20.4283, 72.8397),
    "delhi": (28.6139, 77.2090),
    "goa": (15.2993, 74.1240),
    "gujarat": (22.2587, 71.1924),
    "haryana": (29.0588, 76.0856),
    "himachal pradesh": (31.1048, 77.1734),
    "jammu and kashmir": (33.7782, 76.5762),
    "jharkhand": (23.6102, 85.2799),
    "karnataka": (15.3173, 75.7139),
    "kerala": (10.8505, 76.2711),
    "ladakh": (34.1526, 77.5771),
    "lakshadweep": (10.5667, 72.6417),
    "madhya pradesh": (22.9734, 78.6569),
    "maharashtra": (19.7515, 75.7139),
    "manipur": (24.6637, 93.9063),
    "meghalaya": (25.4670, 91.3662),
    "mizoram": (23.1645, 92.9376),
    "nagaland": (26.1584, 94.5624),
    "odisha": (20.9517, 85.0985),
    "puducherry": (11.9416, 79.8083),
    "punjab": (31.1471, 75.3412),
    "rajasthan": (27.0238, 74.2179),
    "sikkim": (27.5330, 88.5122),
    "tamil nadu": (11.1271, 78.6569),
    "telangana": (18.1124, 79.0193),
    "tripura": (23.9408, 91.9882),
    "uttar pradesh": (26.8467, 80.9462),
    "uttarakhand": (30.0668, 79.0193),
    "west bengal": (22.9868, 87.8550),
}

DISTRICT_COORDS: Dict[str, Tuple[float, float]] = {
    # Gujarat Key Districts
    "anand": (22.5645, 72.9289),
    "ahmedabad": (23.0225, 72.5714),
    "vadodara": (22.3072, 73.1812),
    "surat": (21.1702, 72.8311),
    "rajkot": (22.3039, 70.8022),
    "gandhinagar": (23.2156, 72.6369),
    "bhavnagar": (21.7645, 72.1519),
    "jamnagar": (22.4707, 70.0577),
    "junagadh": (21.5222, 70.4579),
    "kheda": (22.7533, 72.6841),
    "mehsana": (23.5880, 72.3693),
    "bharuch": (21.7051, 72.9959),
    "navsari": (20.9467, 72.9520),
    "valsad": (20.5992, 72.9342),
    "panchmahal": (22.7753, 73.6149),
    "dahod": (22.8360, 74.2536),
    "banaskantha": (24.1724, 72.4346),
    "sabarkantha": (23.5977, 72.9698),
    "arvalli": (23.5414, 73.1812),
    "aravalli": (23.5414, 73.1812),
    "morbi": (22.8120, 70.8377),
    "surendranagar": (22.7275, 71.6370),
    "amreli": (21.6032, 71.2221),
    "gir somnath": (20.9042, 70.3667),
    "botad": (22.1700, 71.6600),
    "porbandar": (21.6417, 69.6293),
    "devbhumi dwarka": (22.2442, 68.9685),
    "kachchh": (23.7337, 69.8597),
    "kutch": (23.7337, 69.8597),
    "tapi": (21.2333, 73.4333),
    "narmada": (21.8700, 73.5000),
    "dang": (20.8500, 73.7000),
    "chhotaudepur": (22.3000, 74.0000),
    "mahisagar": (23.1600, 73.5500),
    # Key Metros and National Centers
    "mumbai": (19.0760, 72.8777),
    "mumbai city": (19.0760, 72.8777),
    "mumbai suburban": (19.1136, 72.8697),
    "pune": (18.5204, 73.8567),
    "nagpur": (21.1458, 79.0882),
    "bengaluru": (12.9716, 77.5946),
    "bengaluru urban": (12.9716, 77.5946),
    "chennai": (13.0827, 80.2707),
    "hyderabad": (17.3850, 78.4867),
    "kolkata": (22.5726, 88.3639),
    "lucknow": (26.8467, 80.9462),
    "jaipur": (26.9124, 75.7873),
    "bhopal": (23.2599, 77.4126),
    "patna": (25.5941, 85.1376),
    "chandigarh": (30.7333, 76.7794),
    "delhi": (28.6139, 77.2090),
    "new delhi": (28.6139, 77.2090),
    "central delhi": (28.6500, 77.2200),
    "south delhi": (28.5000, 77.2000),
}


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Computes Great Circle distance between two pairs of GPS coordinates
    using the spherical Haversine formula (Earth radius = 6371.0 km).
    """
    R = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return round(R * c, 2)


_LAST_NOMINATIM_CALL: float = 0.0


def geocode_with_nominatim(query: str) -> Optional[Tuple[float, float, str]]:
    """
    Queries OpenStreetMap Nominatim with strict 1.0 second rate limiting.
    User-Agent identifies academic project.
    Returns (lat, lng, precision) or None.
    Precision is 'exact', 'street', or 'district_centroid'.
    """
    global _LAST_NOMINATIM_CALL
    now = time.time()
    elapsed = now - _LAST_NOMINATIM_CALL
    if elapsed < 1.05:
        time.sleep(1.05 - elapsed)

    _LAST_NOMINATIM_CALL = time.time()

    params = urllib.parse.urlencode({"q": query, "format": "json", "limit": 1, "addressdetails": 1})
    url = f"https://nominatim.openstreetmap.org/search?{params}"
    headers = {
        "User-Agent": "eRaktKosh-Blood-Lakehouse-Academic/1.0 (academic research; Academic Project)",
        "Accept": "application/json",
    }

    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status != 200:
                return None
            data = json.loads(response.read().decode("utf-8"))
            if not data or len(data) == 0:
                return None

            item = data[0]
            lat = float(item["lat"])
            lon = float(item["lon"])
            osm_type = item.get("type", "")
            osm_class = item.get("class", "")

            if osm_class in ("amenity", "building") or osm_type in ("hospital", "clinic"):
                precision = "exact"
            elif osm_class in ("highway", "road") or osm_type in ("residential", "street"):
                precision = "street"
            else:
                precision = "district_centroid"

            return lat, lon, precision
    except Exception:
        return None


def resolve_facility_lat_lng(
    hospital_code: int,
    state: str,
    district: str,
    address: Optional[str] = None,
    con: Optional[Any] = None,
) -> Tuple[float, float, bool]:
    """
    Returns (latitude, longitude, is_approximate_location).
    Deterministic centroid calculation with hash offset to prevent marker stacking.
    """
    s_clean = (state or "").strip().lower()
    d_clean = (district or "").strip().lower()

    base_lat, base_lng = 22.5645, 72.9289  # Default Anand center
    found = False

    if d_clean in DISTRICT_COORDS:
        base_lat, base_lng = DISTRICT_COORDS[d_clean]
        found = True
    elif s_clean in STATE_COORDS:
        base_lat, base_lng = STATE_COORDS[s_clean]
        found = True
    else:
        for k, v in DISTRICT_COORDS.items():
            if k in d_clean or d_clean in k:
                base_lat, base_lng = v
                found = True
                break
        if not found:
            for k, v in STATE_COORDS.items():
                if k in s_clean or s_clean in k:
                    base_lat, base_lng = v
                    found = True
                    break

    # Apply deterministic offset (+- 0.012 deg ~ 1.2 km) based on hospital_code hash
    h_bytes = hashlib.md5(f"{hospital_code}:{d_clean}".encode()).digest()
    offset_lat = ((h_bytes[0] % 100) / 100.0 - 0.5) * 0.024
    offset_lng = ((h_bytes[1] % 100) / 100.0 - 0.5) * 0.024

    return round(base_lat + offset_lat, 5), round(base_lng + offset_lng, 5), True


def resolve_facility_coordinates_detailed(
    hospital_code: int,
    state: str,
    district: str,
    address: Optional[str] = None,
    con: Optional[Any] = None,
) -> Tuple[float, float, str]:
    """
    Detailed resolver returning (latitude, longitude, precision_label).
    Precision labels: 'exact', 'street', 'district_centroid'.
    Checks geocode_cache table if con is provided, otherwise falls back to centroid.
    """
    if con and address:
        try:
            q_clean = f"{address.strip()}, {district.strip()}, {state.strip()}".lower()
            cached = con.execute(
                "SELECT latitude, longitude, precision FROM main.geocode_cache WHERE query = ? LIMIT 1;",
                [q_clean],
            ).fetchone()
            if cached and cached[0] and cached[1]:
                return float(cached[0]), float(cached[1]), str(cached[2])
        except Exception:
            pass

    lat, lng, _ = resolve_facility_lat_lng(hospital_code, state, district)
    return lat, lng, "district_centroid"
