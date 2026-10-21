"""
Unit Tests: Geographic Coordinate Resolution, Haversine Distance & Precision
============================================================================
Tests:
1. Haversine Great Circle distance formula against verified city pairs:
   - Anand to Ahmedabad (~65 km)
   - Mumbai to Pune (~120 km)
   - Delhi to Jaipur (~240 km)
2. Location precision labels ('exact', 'street', 'district_centroid', 'failed')
3. Approximate location integrity flag
4. Deterministic jitter to prevent map pin stacking
"""

import pytest

from bloodlake.geo import (
    haversine_distance_km,
    resolve_facility_coordinates_detailed,
    resolve_facility_lat_lng,
)


@pytest.mark.parametrize(
    "city1, coords1, city2, coords2, expected_min_km, expected_max_km",
    [
        # Anand to Ahmedabad (~65 km)
        ("Anand", (22.5645, 72.9289), "Ahmedabad", (23.0225, 72.5714), 60.0, 72.0),
        # Mumbai to Pune (~120 km)
        ("Mumbai", (19.0760, 72.8777), "Pune", (18.5204, 73.8567), 115.0, 130.0),
        # Delhi to Jaipur (~240 km)
        ("Delhi", (28.6139, 77.2090), "Jaipur", (26.9124, 75.7873), 230.0, 250.0),
    ],
)
def test_haversine_known_city_pairs(
    city1, coords1, city2, coords2, expected_min_km, expected_max_km
):
    dist = haversine_distance_km(coords1[0], coords1[1], coords2[0], coords2[1])
    assert expected_min_km <= dist <= expected_max_km, f"Distance {dist} km out of expected range for {city1}-{city2}"


def test_haversine_same_point():
    assert haversine_distance_km(22.5645, 72.9289, 22.5645, 72.9289) == 0.0


def test_resolve_anand_district_coordinates():
    lat, lng, is_approx = resolve_facility_lat_lng(1001, "Gujarat", "Anand")
    assert 22.4 <= lat <= 22.7
    assert 72.8 <= lng <= 73.1
    assert is_approx is True


def test_deterministic_offset_avoids_pin_collision():
    lat1, lng1, _ = resolve_facility_lat_lng(1001, "Gujarat", "Anand")
    lat2, lng2, _ = resolve_facility_lat_lng(1002, "Gujarat", "Anand")
    assert (lat1, lng1) != (lat2, lng2)
    assert abs(lat1 - lat2) < 0.05
    assert abs(lng1 - lng2) < 0.05


def test_unknown_location_fallback():
    lat, lng, is_approx = resolve_facility_lat_lng(9999, "UnknownState", "UnknownDistrict")
    assert isinstance(lat, float)
    assert isinstance(lng, float)
    assert is_approx is True


def test_precision_labels():
    # Centroid fallback precision
    lat, lng, prec = resolve_facility_coordinates_detailed(1001, "Gujarat", "Anand")
    assert prec in ("exact", "street", "district_centroid", "failed")
    assert prec == "district_centroid"
