"""
Unit Tests: Landing Zone Manager & Parquet Serialization
=========================================================
Tests immutable Parquet writing, SHA-256 integrity hashing,
and overwrite prevention.
"""

from datetime import datetime, timezone

import pyarrow.parquet as pq
import pytest

from bloodlake.scraper import (
    compute_file_sha256,
    write_landing_parquet,
)


def test_write_landing_parquet_and_read(tmp_path, monkeypatch):
    monkeypatch.setattr("bloodlake.config.settings.data_landing_dir", tmp_path)

    sample_records = [
        {
            "hospitalCode": 1001,
            "hospitalname": "Anand Transfusion Centre",
            "State": "Gujarat",
            "District": "Anand",
            "hospitalType": "Government",
            "type": "Blood Bank",
            "hospitalcontact": "Phone: 02692-223344",
            "hospitaladd": "Station Road, Anand",
            "entrydate": "14-Oct-2026",
            "components": {"Packed Red Blood Cells": {"available_WithQty": "10"}},
        },
        {
            "hospitalCode": 1002,
            "hospitalname": "Civil Hospital Blood Bank",
            "State": "Gujarat",
            "District": "Anand",
            "hospitalType": "Government",
            "type": "Blood Bank",
            "hospitalcontact": "Phone: 02692-556677",
            "hospitaladd": "Court Road, Anand",
            "entrydate": "14-Oct-2026",
            "components": {"Packed Red Blood Cells": {"available_WithQty": "4"}},
        },
    ]

    now = datetime(2026, 10, 14, 12, 0, 0, tzinfo=timezone.utc)
    run_id = "test_run_001"

    parquet_file, sha256_hash, row_count = write_landing_parquet(sample_records, run_id, now)

    assert parquet_file.exists()
    assert row_count == 2
    assert len(sha256_hash) == 64

    # Verify sha256 matches independent computation
    calc_hash = compute_file_sha256(parquet_file)
    assert calc_hash == sha256_hash

    # Read back with pyarrow
    tbl = pq.read_table(parquet_file)
    assert tbl.num_rows == 2
    assert "hospital_name" in tbl.column_names
    assert "raw_payload_json" in tbl.column_names

    # Overwrite guard: attempting to write same run_id must raise FileExistsError
    with pytest.raises(FileExistsError):
        write_landing_parquet(sample_records, run_id, now)
