"""
Geographic Coordinate Resolver (District Centroid Level)
========================================================
Resolves latitude and longitude for Indian blood bank facilities using verified
State and District centroids. Applies deterministic pseudo-random offsets so multiple
blood banks in the same district don't overlap into a single pin.

NOTE: All locations returned are marked with is_approximate_location = True
("approximate location, district level") to maintain academic integrity and honesty.
"""

import hashlib
from typing import Dict, Tuple

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
    "morbi": (22.8120, 70.8377),
    "surendranagar": (22.7275, 71.6370),
    "amreli": (21.6032, 71.2221),
    "gir somnath": (20.9042, 70.3667),
    "botad": (22.1700, 71.6600),
    "porbandar": (21.6417, 69.6293),
    "devbhumi dwarka": (22.2442, 68.9685),
    "kachchh": (23.7337, 69.8597),
    "tapi": (21.2333, 73.4333),
    "narmada": (21.8700, 73.5000),
    "dang": (20.8500, 73.7000),
    "chhotaudepur": (22.3000, 74.0000),
    "mahisagar": (23.1600, 73.5500),
    # Key Metros and National Centers
    "mumbai": (19.0760, 72.8777),
    "mumbai suburban": (19.1136, 72.8697),
    "pune": (18.5204, 73.8567),
    "nagpur": (21.1458, 79.0882),
    "bengaluru urban": (12.9716, 77.5946),
    "chennai": (13.0827, 80.2707),
    "hyderabad": (17.3850, 78.4867),
    "kolkata": (22.5726, 88.3639),
    "lucknow": (26.8467, 80.9462),
    "jaipur": (26.9124, 75.7873),
    "bhopal": (23.2599, 77.4126),
    "patna": (25.5941, 85.1376),
    "chandigarh": (30.7333, 76.7794),
    "new delhi": (28.6139, 77.2090),
    "central delhi": (28.6500, 77.2200),
    "south delhi": (28.5000, 77.2000),
}


def resolve_facility_lat_lng(
    hospital_code: int, state: str, district: str
) -> Tuple[float, float, bool]:
    """
    Returns (latitude, longitude, is_approximate_location).
    Applies small deterministic offset based on hospital_code hash to separate map pins.
    """
    s_clean = (state or "").strip().lower()
    d_clean = (district or "").strip().lower()

    base_lat, base_lng = 22.5645, 72.9289  # Default to Gujarat/Anand center
    found = False

    if d_clean in DISTRICT_COORDS:
        base_lat, base_lng = DISTRICT_COORDS[d_clean]
        found = True
    elif s_clean in STATE_COORDS:
        base_lat, base_lng = STATE_COORDS[s_clean]
        found = True
    else:
        # Fallback partial matching
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

    # Apply small deterministic offset (+- 0.015 deg ~ 1.5 km) to prevent overlapping pins
    h_bytes = hashlib.md5(f"{hospital_code}:{d_clean}".encode()).digest()
    offset_lat = ((h_bytes[0] % 100) / 100.0 - 0.5) * 0.03
    offset_lng = ((h_bytes[1] % 100) / 100.0 - 0.5) * 0.03

    return round(base_lat + offset_lat, 5), round(base_lng + offset_lng, 5), True
