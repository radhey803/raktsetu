"""
BloodGrid Geocoding Engine
==========================
Resolves real geographical coordinates for blood centres using Nominatim (OpenStreetMap),
with permanent database caching, strict 1 req/sec rate-limiting, and graceful centroid fallback.

Records precision tags:
- 'exact': Facility name matched directly in OpenStreetMap
- 'street': Road / street level resolution
- 'district_centroid': Approximate location based on district center
"""

import hashlib
import logging
import re
import time
from typing import Dict, Optional, Tuple
import duckdb
import httpx

from bloodgrid.config import settings

logger = logging.getLogger("bloodgrid.geo")

# Last request timestamp to enforce 1 second rate limit for Nominatim
_LAST_NOMINATIM_REQUEST_TS = 0.0

# District Centroids fallback dictionary
STATE_CENTROIDS: Dict[str, Tuple[float, float]] = {
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

DISTRICT_CENTROIDS: Dict[str, Tuple[float, float]] = {
    # Gujarat
    "anand": (22.5645, 72.9289),
    "ahmedabad": (23.0225, 72.5714),
    "vadodara": (22.3072, 73.1812),
    "surat": (21.1702, 72.8311),
    "rajkot": (22.3039, 70.8022),
    "gandhinagar": (23.2156, 72.6369),
    "bhavnagar": (21.7645, 72.1519),
    "jamnagar": (22.4707, 70.0577),
    "junagadh": (21.5222, 70.4579),
    "kutch": (23.2420, 69.6669),
    "mehsana": (23.5880, 72.3693),
    "bharuch": (21.7051, 72.9959),
    "valsad": (20.5992, 72.9342),
    "navsari": (20.9467, 72.9520),
    "porbandar": (21.6417, 69.6293),
    "amreli": (21.6032, 71.2221),
    "surendranagar": (22.7278, 71.6370),
    "morbi": (22.8120, 70.8385),
    "patan": (23.8493, 72.1266),
    "banaskantha": (24.1724, 72.4346),
    "sabarkantha": (23.6841, 73.0483),
    "arvalli": (23.5414, 73.2384),
    "panchmahal": (22.7567, 73.6149),
    "dahod": (22.8373, 74.2562),
    "kheda": (22.7513, 72.6847),
    "mahisagar": (23.1678, 73.5583),
    "chhota udepur": (22.3108, 74.0118),
    "narmada": (21.8741, 73.5594),
    "tapi": (21.1684, 73.3986),
    "dang": (20.8560, 73.7088),
    "gir somnath": (20.9042, 70.3653),
    "devbhumi dwarka": (22.2442, 68.9685),
    "botad": (22.1706, 71.6667),

    # Maharashtra
    "mumbai": (19.0760, 72.8777),
    "mumbai suburban": (19.1136, 72.8697),
    "pune": (18.5204, 73.8567),
    "nagpur": (21.1458, 79.0882),
    "thane": (19.2183, 72.9781),
    "nashik": (19.9975, 73.7898),
    "aurangabad": (19.8762, 75.3433),
    "solapur": (17.6599, 75.9064),
    "kolhapur": (16.7050, 74.2433),

    # Delhi NCR
    "central delhi": (28.6448, 77.2167),
    "east delhi": (28.6276, 77.2950),
    "new delhi": (28.6139, 77.2090),
    "north delhi": (28.7041, 77.1025),
    "south delhi": (28.5355, 77.2410),
    "west delhi": (28.6562, 77.0722),
    "noida": (28.5355, 77.3910),
    "gautam buddha nagar": (28.5355, 77.3910),
    "gurugram": (28.4595, 77.0266),
    "faridabad": (28.4089, 77.3178),

    # Karnataka
    "bangalore urban": (12.9716, 77.5946),
    "bengaluru urban": (12.9716, 77.5946),
    "mysore": (12.2958, 76.6394),
    "mysuru": (12.2958, 76.6394),
    "belgaum": (15.8497, 74.4977),
    "dharwad": (15.4589, 75.0078),
    "mangalore": (12.9141, 74.8560),

    # Tamil Nadu
    "chennai": (13.0827, 80.2707),
    "coimbatore": (11.0168, 76.9558),
    "madurai": (9.9252, 78.1198),
    "tiruchirappalli": (10.7905, 78.7047),
    "salem": (11.6643, 78.1460),

    # West Bengal
    "kolkata": (22.5726, 88.3639),
    "howrah": (22.5958, 88.2636),
    "north 24 parganas": (22.7212, 88.4839),
    "south 24 parganas": (22.1583, 88.5422),
    "darjeeling": (27.0410, 88.2663),

    # Telangana
    "hyderabad": (17.3850, 78.4867),
    "rangareddy": (17.2403, 78.4294),
    "warangal": (17.9689, 79.5941),

    # Rajasthan
    "jaipur": (26.9124, 75.7873),
    "jodhpur": (26.2389, 73.0243),
    "udaipur": (24.5854, 73.7125),
    "kota": (25.2138, 75.8648),

    # Uttar Pradesh
    "lucknow": (26.8467, 80.9462),
    "kanpur nagar": (26.4499, 80.3319),
    "varanasi": (25.3176, 82.9739),
    "agra": (27.1767, 78.0081),
    "prayagraj": (25.4358, 81.8463),

    # Kerala
    "thiruvananthapuram": (8.5241, 76.9366),
    "ernakulam": (9.9816, 76.2999),
    "kozhikode": (11.2588, 75.7804),

    # Madhya Pradesh
    "bhopal": (23.2599, 77.4126),
    "indore": (22.7196, 75.8577),
    "gwalior": (26.2183, 78.1828),
    "jabalpur": (23.1815, 79.9864),
}


def make_facility_key(hospital_name: str, district: str, state: str) -> str:
    """Generates a stable unique lookup hash for a facility."""
    raw = f"{hospital_name.strip().lower()}|{district.strip().lower()}|{state.strip().lower()}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def get_cached_coordinates(con: duckdb.DuckDBPyConnection, facility_key: str) -> Optional[Tuple[float, float, str]]:
    """Checks DuckDB geocode_cache table."""
    try:
        row = con.execute("""
            SELECT latitude, longitude, precision
            FROM gold.geocode_cache
            WHERE facility_key = ?;
        """, [facility_key]).fetchone()
        if row and row[0] is not None and row[1] is not None:
            return float(row[0]), float(row[1]), str(row[2])
    except Exception:
        pass
    return None


def store_cached_coordinates(
    con: duckdb.DuckDBPyConnection,
    facility_key: str,
    hospital_name: str,
    state: str,
    district: str,
    address: str,
    lat: float,
    lng: float,
    precision: str
) -> None:
    """Persists geocoded coordinate into DuckDB geocode_cache table."""
    try:
        con.execute("""
            INSERT OR REPLACE INTO gold.geocode_cache 
            (facility_key, hospital_name, state_name, district_name, address, latitude, longitude, precision, geocoded_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP);
        """, [facility_key, hospital_name, state, district, address, lat, lng, precision])
    except Exception as e:
        logger.warning("Failed to cache geocode result: %s", e)


def get_district_fallback(hospital_code: Optional[int], state: str, district: str) -> Tuple[float, float, str]:
    """
    Computes deterministic centroid with slight spatial jitter to keep individual
    hospital markers distinguishable on high-zoom maps.
    """
    s_norm = state.strip().lower()
    d_norm = district.strip().lower()

    if d_norm in DISTRICT_CENTROIDS:
        base_lat, base_lng = DISTRICT_CENTROIDS[d_norm]
    elif s_norm in STATE_CENTROIDS:
        base_lat, base_lng = STATE_CENTROIDS[s_norm]
    else:
        base_lat, base_lng = (20.5937, 78.9629)  # India center fallback

    # Apply deterministic tiny jitter (hash of hospital code)
    if hospital_code:
        h_hash = int(hashlib.md5(str(hospital_code).encode()).hexdigest(), 16)
        angle = (h_hash % 360) * (3.14159265 / 180.0)
        radius = ((h_hash % 100) / 100.0) * 0.015  # ~1.5 km maximum offset
        import math
        lat = base_lat + (radius * math.sin(angle))
        lng = base_lng + (radius * math.cos(angle))
        return round(lat, 5), round(lng, 5), "district_centroid"

    return round(base_lat, 5), round(base_lng, 5), "district_centroid"


def query_nominatim(query: str) -> Optional[Tuple[float, float, str]]:
    """
    Queries OpenStreetMap Nominatim with strict 1 req/sec rate limit.
    """
    global _LAST_NOMINATIM_REQUEST_TS
    now = time.time()
    elapsed = now - _LAST_NOMINATIM_REQUEST_TS
    if elapsed < 1.1:
        time.sleep(1.1 - elapsed)

    headers = {
        "User-Agent": settings.nominatim_user_agent,
        "Accept-Language": "en"
    }
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": query,
        "format": "json",
        "limit": 1,
        "countrycodes": "in"
    }

    try:
        _LAST_NOMINATIM_REQUEST_TS = time.time()
        with httpx.Client(timeout=8.0) as client:
            resp = client.get(url, params=params, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                if data and len(data) > 0:
                    lat = float(data[0]["lat"])
                    lon = float(data[0]["lon"])
                    osm_type = data[0].get("type", "")
                    precision = "exact" if osm_type in ("hospital", "clinic", "amenity") else "street"
                    return lat, lon, precision
    except Exception as e:
        logger.debug("Nominatim lookup failed for %s: %s", query, e)

    return None


def resolve_facility_lat_lng(
    hospital_code: Optional[int],
    hospital_name: str,
    hospital_address: str,
    state: str,
    district: str,
    con: Optional[duckdb.DuckDBPyConnection] = None,
    allow_network_lookup: bool = False
) -> Tuple[float, float, str]:
    """
    Main resolution entry point:
    1. Checks DuckDB geocode_cache table
    2. Optional Nominatim network lookup (rate limited, cached permanently)
    3. District/State centroid fallback (with precision 'district_centroid')
    """
    facility_key = make_facility_key(hospital_name, district, state)

    # 1. Check permanent database cache
    if con:
        cached = get_cached_coordinates(con, facility_key)
        if cached:
            return cached

    # 2. Network Geocoding (if permitted, e.g. during batch ingestion)
    if allow_network_lookup and hospital_name:
        clean_name = re.sub(r"[\(\[].*?[\)\]]", "", hospital_name).strip()
        search_query = f"{clean_name}, {district}, {state}, India"
        result = query_nominatim(search_query)
        if result:
            lat, lon, precision = result
            if con:
                store_cached_coordinates(
                    con, facility_key, hospital_name, state, district, hospital_address, lat, lon, precision
                )
            return lat, lon, precision

    # 3. Deterministic District Centroid Fallback
    lat, lng, prec = get_district_fallback(hospital_code, state, district)
    return lat, lng, prec
