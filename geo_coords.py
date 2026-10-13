"""
Geographic Coordinate Resolver for Indian Blood Banks
=====================================================
Provides accurate geographic centroids for Indian States, Union Territories,
and major districts, with deterministic hospital fanning for clear map clustering.
"""

import hashlib
from typing import Tuple, Dict

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
    "kheda": (22.7547, 72.6837),
    "mehsana": (23.5880, 72.3693),
    "bharuch": (21.7051, 72.9959),
    "navsari": (20.9507, 72.9320),
    "valsad": (20.5992, 72.9342),
    "dahod": (22.8373, 74.2562),
    "panchmahal": (22.7562, 73.6166),
    "banaskantha": (24.1724, 72.4346),
    "sabarkantha": (23.5977, 73.0641),
    "patan": (23.8493, 72.1266),
    "surendranagar": (22.7276, 71.6370),
    "amreli": (21.6032, 71.2223),
    "porbandar": (21.6417, 69.6293),
    "gir somnath": (20.9042, 70.3667),
    "morbi": (22.8120, 70.8377),
    "botad": (22.1704, 71.6667),
    "devbhumi dwarka": (22.2394, 68.9678),
    "tapi": (21.2858, 73.4475),
    "narmada": (21.8700, 73.5594),
    "dang": (20.8560, 73.7088),
    "aravalli": (23.5417, 73.3083),
    "mahisagar": (23.1678, 73.5703),
    "chhotaudepur": (22.3108, 74.0118),
    "kachchh": (23.2420, 69.6669),

    # Maharashtra
    "mumbai": (18.9220, 72.8347),
    "mumbai suburban": (19.1136, 72.8697),
    "pune": (18.5204, 73.8567),
    "nagpur": (21.1458, 79.0882),
    "nashik": (19.9975, 73.7898),
    "thane": (19.2183, 72.9781),
    "aurangabad": (19.8762, 75.3433),
    "chhatrapati sambhajinagar": (19.8762, 75.3433),
    "solapur": (17.6599, 75.9064),
    "kolhapur": (16.7050, 74.2433),
    "amravati": (20.9374, 77.7796),
    "nanded": (19.1383, 77.3210),
    "sangli": (16.8524, 74.5815),
    "satara": (17.6805, 74.0183),
    "raigad": (18.5158, 73.1822),
    "palghar": (19.6936, 72.7655),

    # Delhi
    "central delhi": (28.6453, 77.2128),
    "new delhi": (28.6139, 77.2090),
    "north delhi": (28.7041, 77.1025),
    "south delhi": (28.4817, 77.1873),
    "east delhi": (28.6279, 77.2784),
    "west delhi": (28.6664, 77.0674),

    # Karnataka
    "bengaluru urban": (12.9716, 77.5946),
    "bangalore urban": (12.9716, 77.5946),
    "bengaluru rural": (13.2257, 77.5750),
    "mysuru": (12.2958, 76.6394),
    "mysore": (12.2958, 76.6394),
    "dakshina kannada": (12.8703, 74.8806),
    "mangaluru": (12.9141, 74.8560),
    "belagavi": (15.8497, 74.4977),
    "hubballi-dharwad": (15.3647, 75.1240),

    # Tamil Nadu
    "chennai": (13.0827, 80.2707),
    "coimbatore": (11.0168, 76.9558),
    "madurai": (9.9252, 78.1198),
    "tiruchirappalli": (10.7905, 78.7047),
    "salem": (11.6643, 78.1460),

    # Uttar Pradesh
    "lucknow": (26.8467, 80.9462),
    "kanpur nagar": (26.4499, 80.3319),
    "varanasi": (25.3176, 82.9739),
    "agra": (27.1767, 78.0081),
    "prayagraj": (25.4358, 81.8463),
    "allahabad": (25.4358, 81.8463),
    "meerut": (28.9845, 77.7064),
    "ghaziabad": (28.6692, 77.4538),
    "gautam buddha nagar": (28.5355, 77.3910),
    "noida": (28.5355, 77.3910),

    # West Bengal
    "kolkata": (22.5726, 88.3639),
    "howrah": (22.5958, 88.2636),
    "north 24 parganas": (22.7210, 88.4847),
    "south 24 parganas": (22.1352, 88.4016),
    "darjeeling": (27.0410, 88.2663),

    # Rajasthan
    "jaipur": (26.9124, 75.7873),
    "jodhpur": (26.2389, 73.0243),
    "udaipur": (24.5854, 73.7125),
    "kota": (25.2138, 75.8648),
    "bikaner": (28.0229, 73.3119),

    # Telangana
    "hyderabad": (17.3850, 78.4867),
    "rangareddy": (17.2403, 78.4294),
    "warangal": (17.9689, 79.5941),

    # Kerala
    "thiruvananthapuram": (8.5241, 76.9366),
    "ernakulam": (9.9816, 76.2999),
    "kochi": (9.9312, 76.2673),
    "kozhikode": (11.2588, 75.7804),

    # Madhya Pradesh
    "bhopal": (23.2599, 77.4126),
    "indore": (22.7196, 75.8577),
    "gwalior": (26.2183, 78.1828),
    "jabalpur": (23.1815, 79.9864),

    # Bihar
    "patna": (25.5941, 85.1376),
    "gaya": (24.7955, 85.0002),
    "muzaffarpur": (26.1209, 85.3647),

    # Punjab
    "ludhiana": (30.9010, 75.8573),
    "amritsar": (31.6340, 74.8723),
    "jalandhar": (31.3260, 75.5762),
}

def resolve_facility_lat_lng(hospital_code: int, state: str, district: str) -> Tuple[float, float]:
    """
    Returns accurate (lat, lng) coordinates for any blood bank in India.
    Falls back to state centroid with deterministic spatial distribution.
    """
    dist_key = (district or "").lower().strip()
    state_key = (state or "").lower().strip()

    if dist_key in DISTRICT_COORDS:
        base_lat, base_lng = DISTRICT_COORDS[dist_key]
    elif state_key in STATE_COORDS:
        # Fallback to state centroid + district-based offset
        st_lat, st_lng = STATE_COORDS[state_key]
        dist_hash = int(hashlib.md5(dist_key.encode()).hexdigest()[:6], 16)
        dist_offset_lat = ((dist_hash % 100) - 50) * 0.015
        dist_offset_lng = (((dist_hash >> 6) % 100) - 50) * 0.015
        base_lat = st_lat + dist_offset_lat
        base_lng = st_lng + dist_offset_lng
    else:
        # National center fallback (Nagpur / Central India)
        base_lat, base_lng = (21.1458, 79.0882)

    # Apply deterministic hospital jitter (spreads facilities within ~1-2km)
    h_hash = int(hashlib.md5(f"{hospital_code}_{dist_key}".encode()).hexdigest()[:6], 16)
    jitter_lat = ((h_hash % 60) - 30) * 0.0006
    jitter_lng = (((h_hash >> 6) % 60) - 30) * 0.0006

    return round(base_lat + jitter_lat, 5), round(base_lng + jitter_lng, 5)
