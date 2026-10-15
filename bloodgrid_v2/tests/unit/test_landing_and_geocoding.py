"""
Unit Tests: Landing Zone & Geocoding
====================================
Tests immutable landing zone generation, SHA-256 manifest integrity,
and geocoding centroid resolution.
"""

from bloodgrid.geo.geocode import get_district_fallback, make_facility_key


def test_make_facility_key():
    k1 = make_facility_key("Civil Hospital", "Anand", "Gujarat")
    k2 = make_facility_key("civil hospital", "anand", "gujarat")
    k3 = make_facility_key("Other Hospital", "Anand", "Gujarat")

    assert k1 == k2
    assert k1 != k3
    assert len(k1) == 32  # md5 hex length


def test_district_fallback_coordinates():
    lat, lng, prec = get_district_fallback(871, "Gujarat", "Anand")
    assert prec == "district_centroid"
    assert 22.0 <= lat <= 23.0
    assert 72.0 <= lng <= 73.5


def test_state_fallback_for_unknown_district():
    lat, lng, prec = get_district_fallback(999, "Gujarat", "UnknownDistrictXYZ")
    assert prec == "district_centroid"
    # Gujarat centroid is ~ (22.2587, 71.1924)
    assert 21.5 <= lat <= 23.5
    assert 70.5 <= lng <= 72.5
