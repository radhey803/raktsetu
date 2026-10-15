"""
Unit Tests: Landing Zone Manager & Parquet Serialization
=========================================================
Tests immutable Parquet writing, SHA-256 integrity hashing,
and rolling retention policy.
"""

from datetime import datetime, timezone

import pyarrow.parquet as pq
import pytest

from bloodgrid.ingestion.landing import (
    compute_file_sha256,
    enforce_rolling_retention,
    write_raw_landing,
)


def test_write_raw_landing_and_read_parquet(tmp_path, monkeypatch):
    monkeypatch.setattr("bloodgrid.config.settings.landing_dir", tmp_path)

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

    parquet_file, sha256_hash, row_count = write_raw_landing(sample_records, run_id, now)

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
    assert "raw_payload" in tbl.column_names

    # Overwrite guard: attempting to write same run_id must raise FileExistsError
    with pytest.raises(FileExistsError):
        write_raw_landing(sample_records, run_id, now)


def test_enforce_rolling_retention(tmp_path, monkeypatch):
    monkeypatch.setattr("bloodgrid.config.settings.landing_dir", tmp_path)

    # Create an old partition (40 days old)
    old_dir = tmp_path / "dt=2026-09-01" / "hh=00"
    old_dir.mkdir(parents=True, exist_ok=True)
    old_file = old_dir / "old_inventory.parquet"
    old_file.write_text("dummy")

    # Create recent partition
    new_dir = tmp_path / "dt=2026-10-14" / "hh=00"
    new_dir.mkdir(parents=True, exist_ok=True)
    new_file = new_dir / "new_inventory.parquet"
    new_file.write_text("dummy")

    # Retention 30 days should clean the 40-day old partition
    enforce_rolling_retention(retention_days=30)
    assert not old_file.exists()
    assert new_file.exists()
