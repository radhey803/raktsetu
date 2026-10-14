from unittest.mock import MagicMock, patch

import duckdb

from bloodgrid.geo.geocode import (
    get_cached_coordinates,
    get_district_fallback,
    make_facility_key,
    query_nominatim,
    resolve_facility_lat_lng,
    store_cached_coordinates,
)


def test_make_facility_key():
    import hashlib

    key = make_facility_key("Anand Civil Hospital", "Anand", "Gujarat")
    expected = hashlib.md5("anand civil hospital|anand|gujarat".encode("utf-8")).hexdigest()
    assert key == expected
    assert len(key) == 32


def test_cache_storage_and_retrieval():
    con = duckdb.connect(":memory:")
    con.execute("CREATE SCHEMA gold;")
    con.execute("""
        CREATE TABLE gold.geocode_cache (
            facility_key VARCHAR PRIMARY KEY,
            hospital_name VARCHAR,
            state_name VARCHAR,
            district_name VARCHAR,
            address VARCHAR,
            latitude DOUBLE,
            longitude DOUBLE,
            precision VARCHAR,
            geocoded_at TIMESTAMP
        );
    """)

    store_cached_coordinates(
        con=con,
        facility_key="anand civil::anand::gujarat",
        hospital_name="Anand Civil",
        state="Gujarat",
        district="Anand",
        address="Station Road",
        lat=22.5645,
        lng=72.9289,
        precision="exact",
    )

    cached = get_cached_coordinates(con, "anand civil::anand::gujarat")
    assert cached is not None
    lat, lng, prec = cached
    assert lat == 22.5645
    assert lng == 72.9289
    assert prec == "exact"


def test_district_fallback_with_jitter():
    lat1, lng1, prec1 = get_district_fallback(1001, "Gujarat", "Anand")
    lat2, lng2, prec2 = get_district_fallback(1002, "Gujarat", "Anand")

    assert prec1 == "district_centroid"
    assert prec2 == "district_centroid"
    # Lat/lng should be close to Anand (22.56, 72.92) but slightly different due to deterministic hash
    assert abs(lat1 - 22.5645) < 0.1
    assert (lat1, lng1) != (lat2, lng2)


def test_query_nominatim_mock_success():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = [{"lat": "22.55", "lon": "72.95", "type": "hospital"}]

    with patch("httpx.Client.get", return_value=mock_resp):
        res = query_nominatim("Anand Civil Hospital, Anand, Gujarat, India")
        assert res is not None
        lat, lon, prec = res
        assert lat == 22.55
        assert lon == 72.95
        assert prec == "exact"


def test_resolve_facility_lat_lng_flow():
    con = duckdb.connect(":memory:")
    con.execute("CREATE SCHEMA gold;")
    con.execute("""
        CREATE TABLE gold.geocode_cache (
            facility_key VARCHAR PRIMARY KEY,
            hospital_name VARCHAR,
            state_name VARCHAR,
            district_name VARCHAR,
            address VARCHAR,
            latitude DOUBLE,
            longitude DOUBLE,
            precision VARCHAR,
            geocoded_at TIMESTAMP
        );
    """)

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = [{"lat": "22.55", "lon": "72.95", "type": "amenity"}]

    with patch("httpx.Client.get", return_value=mock_resp):
        lat, lon, prec = resolve_facility_lat_lng(
            hospital_code=1001,
            hospital_name="Anand Red Cross",
            hospital_address="Station Road",
            state="Gujarat",
            district="Anand",
            con=con,
            allow_network_lookup=True,
        )
        assert prec == "exact"
        assert lat == 22.55

        # Check that it cached in DuckDB
        cached = get_cached_coordinates(
            con, make_facility_key("Anand Red Cross", "Anand", "Gujarat")
        )
        assert cached is not None
        assert cached[0] == 22.55
