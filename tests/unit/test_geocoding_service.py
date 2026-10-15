"""
Unit Tests: Geographic Coordinate Resolution & Approximation Honesty
===================================================================
Tests that coordinates are resolved accurately for Indian districts,
that an honest approximate flag is returned, and that deterministic
jitter prevents overlapping map markers.
"""

from bloodlake.geo import resolve_facility_lat_lng


def test_resolve_anand_district_coordinates():
    lat, lng, is_approx = resolve_facility_lat_lng(1001, "Gujarat", "Anand")
    # Anand is approximately 22.56N, 72.92E
    assert 22.4 <= lat <= 22.7
    assert 72.8 <= lng <= 73.1
    assert is_approx is True


def test_deterministic_offset_avoids_pin_collision():
    lat1, lng1, _ = resolve_facility_lat_lng(1001, "Gujarat", "Anand")
    lat2, lng2, _ = resolve_facility_lat_lng(1002, "Gujarat", "Anand")

    # Both within Anand, but slightly offset so markers do not stack exactly on top of each other
    assert (lat1, lng1) != (lat2, lng2)
    assert abs(lat1 - lat2) < 0.05
    assert abs(lng1 - lng2) < 0.05


def test_unknown_location_fallback():
    lat, lng, is_approx = resolve_facility_lat_lng(9999, "UnknownState", "UnknownDistrict")
    assert isinstance(lat, float)
    assert isinstance(lng, float)
    assert is_approx is True
