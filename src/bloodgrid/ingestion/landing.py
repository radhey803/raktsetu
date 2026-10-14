"""
BloodGrid Landing Zone Manager
==============================
Writes immutable raw Parquet (zstd) files into data/landing/dt=YYYY-MM-DD/hh=HH/
with run-level metadata, SHA-256 integrity verification, and rolling retention.
Never overwrites existing files.
"""

import hashlib
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Tuple
import pyarrow as pa
import pyarrow.parquet as pq

from bloodgrid.config import settings

logger = logging.getLogger("bloodgrid.landing")


def get_landing_dir(dt: datetime) -> Path:
    """Returns partitioned landing directory path: data/landing/dt=YYYY-MM-DD/hh=HH/"""
    partition_path = settings.landing_dir / f"dt={dt.strftime('%Y-%m-%d')}" / f"hh={dt.strftime('%H')}"
    partition_path.mkdir(parents=True, exist_ok=True)
    return partition_path


def write_raw_landing(
    records: List[Dict[str, Any]],
    run_id: str,
    scraped_at: datetime
) -> Tuple[Path, str, int]:
    """
    Serializes raw scraped records directly to an immutable Parquet file.
    Preserves raw JSON payload and metadata columns (run_id, scraped_at).
    Returns (file_path, sha256_checksum, row_count).
    """
    landing_dir = get_landing_dir(scraped_at)
    parquet_path = landing_dir / f"inventory_{run_id}.parquet"
    manifest_path = landing_dir / f"manifest_{run_id}.json"

    if parquet_path.exists():
        raise FileExistsError(f"Refusing to overwrite immutable landing file: {parquet_path}")

    # Build Arrow arrays preserving raw dictionaries/strings
    run_ids = [run_id] * len(records)
    scraped_timestamps = [scraped_at] * len(records)
    h_codes = [int(r.get("hospitalCode")) if str(r.get("hospitalCode", "")).isdigit() else None for r in records]
    h_names = [str(r.get("hospitalname", "") or "") for r in records]
    states = [str(r.get("State", "") or "") for r in records]
    districts = [str(r.get("District", "") or "") for r in records]
    types = [str(r.get("hospitalType", "") or "") for r in records]
    facilities = [str(r.get("type", "") or "") for r in records]
    contacts = [str(r.get("hospitalcontact", "") or "") for r in records]
    addresses = [str(r.get("hospitaladd", "") or "") for r in records]
    entry_dates = [str(r.get("entrydate", "") or "") for r in records]
    components_raw = [json.dumps(r.get("components")) if isinstance(r.get("components"), (dict, list)) else str(r.get("components", "") or "") for r in records]
    raw_payloads = [json.dumps(r) for r in records]

    table = pa.Table.from_arrays([
        pa.array(run_ids, type=pa.string()),
        pa.array(scraped_timestamps, type=pa.timestamp("us")),
        pa.array(h_codes, type=pa.int64()),
        pa.array(h_names, type=pa.string()),
        pa.array(states, type=pa.string()),
        pa.array(districts, type=pa.string()),
        pa.array(types, type=pa.string()),
        pa.array(facilities, type=pa.string()),
        pa.array(contacts, type=pa.string()),
        pa.array(addresses, type=pa.string()),
        pa.array(entry_dates, type=pa.string()),
        pa.array(components_raw, type=pa.string()),
        pa.array(raw_payloads, type=pa.string()),
    ], names=[
        "run_id", "scraped_at", "hospital_code", "hospital_name", "state_name",
        "district_name", "hospital_type", "facility_type", "hospital_contact",
        "hospital_address", "entry_date_raw", "components_raw", "raw_payload"
    ])

    pq.write_table(table, parquet_path, compression="zstd")

    # Compute SHA-256 checksum of the written Parquet file
    sha256 = hashlib.sha256()
    with open(parquet_path, "rb") as f:
        while chunk := f.read(65536):
            sha256.update(chunk)
    file_sha256 = sha256.hexdigest()

    parquet_path_resolved = parquet_path.resolve()
    base_dir_resolved = settings.base_dir.resolve()
    try:
        rel_path = str(parquet_path_resolved.relative_to(base_dir_resolved))
    except ValueError:
        rel_path = str(parquet_path)

    manifest = {
        "run_id": run_id,
        "scraped_at": scraped_at.isoformat(),
        "parquet_file": rel_path,
        "row_count": len(records),
        "sha256": file_sha256,
        "source": "https://eraktkosh.mohfw.gov.in"
    }

    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    logger.info("Landing zone write complete: %s (Rows: %d, SHA: %s)", parquet_path.name, len(records), file_sha256[:8])
    return parquet_path, file_sha256, len(records)


def apply_retention_policy(retention_days: int = 30) -> int:
    """
    Removes landing partitions older than retention_days.
    Returns count of removed partition folders.
    """
    cutoff = datetime.now() - timedelta(days=retention_days)
    removed_count = 0
    if not settings.landing_dir.exists():
        return 0

    for dt_dir in settings.landing_dir.glob("dt=*"):
        date_str = dt_dir.name.split("=")[-1]
        try:
            folder_date = datetime.strptime(date_str, "%Y-%m-%d")
            if folder_date < cutoff:
                for file in dt_dir.glob("**/*"):
                    file.unlink(missing_ok=True)
                dt_dir.rmdir()
                removed_count += 1
                logger.info("Evicted expired landing partition: %s", dt_dir)
        except ValueError:
            continue

    return removed_count
