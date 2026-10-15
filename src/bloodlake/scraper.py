"""
eRaktKosh Nationwide Asynchronous Scraper & Landing Zone Manager
===============================================================
Polite, high-speed asynchronous data collector for the 781 districts of India.
Adheres strictly to academic research source protection:
- Identifiable User-Agent with contact details
- Concurrency limiting via asyncio.Semaphore(10)
- Exponential backoff with random jitter on HTTP 429/5xx errors
- Circuit breaker aborts if error rate > 20%
- Minimum run interval guard (default 6 hours) to prevent repeated hammering
- Direct immutable Parquet landing serialization with SHA-256 integrity verification
"""

import asyncio
import hashlib
import json
import logging
import random
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import aiohttp
import pyarrow as pa
import pyarrow.parquet as pq

from bloodlake.config import settings

logger = logging.getLogger("bloodlake.scraper")


class CircuitBreakerError(Exception):
    """Raised when the scraper aborts due to excessive API failures."""
    pass


class RunIntervalGuardError(Exception):
    """Raised when a full crawl is attempted within the minimum interval guard window."""
    pass


async def fetch_district_data(
    session: aiohttp.ClientSession,
    semaphore: asyncio.Semaphore,
    state_name: str,
    state_id: str,
    district_name: str,
    district_id: str,
    max_retries: int = 3,
    timeout_sec: int = 20,
) -> Tuple[bool, List[Dict[str, Any]], Optional[str]]:
    """
    Fetches raw inventory for a single district with polite exponential backoff.
    Returns (success_flag, facilities_list, error_message).
    """
    url = f"{settings.eraktkosh_base_url}?stateCode={state_id}&districtId={district_id}"
    headers = {
        "User-Agent": settings.user_agent,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
    }

    for attempt in range(1, max_retries + 1):
        async with semaphore:
            try:
                timeout = aiohttp.ClientTimeout(total=timeout_sec)
                async with session.get(url, headers=headers, timeout=timeout) as response:
                    # Handle rate limiting or server overload
                    if response.status == 429 or response.status >= 500:
                        backoff = (2**attempt) + random.uniform(0.5, 1.5)
                        logger.warning(
                            "HTTP %d on district %s (%s). Backing off %.1fs (attempt %d/%d)",
                            response.status,
                            district_name,
                            state_name,
                            backoff,
                            attempt,
                            max_retries,
                        )
                        await asyncio.sleep(backoff)
                        continue

                    if response.status == 200:
                        text = await response.text()
                        if not text.strip():
                            return True, [], None

                        try:
                            blood_banks = json.loads(text)
                            if not isinstance(blood_banks, list):
                                return True, [], None

                            for bank in blood_banks:
                                bank["State"] = state_name
                                bank["District"] = district_name
                                bank["stateCode"] = str(state_id)
                                bank["districtCode"] = str(district_id)

                            return True, blood_banks, None
                        except json.JSONDecodeError as jde:
                            logger.error("JSON decode error for %s: %s", district_name, jde)
                            return False, [], f"JSON decode error: {jde}"
                    else:
                        logger.warning("Unexpected status %d for %s", response.status, district_name)
            except (aiohttp.ClientError, asyncio.TimeoutError) as err:
                if attempt == max_retries:
                    logger.error("Failed to fetch %s after %d attempts: %s", district_name, attempt, err)
                    return False, [], str(err)
                backoff = (2**attempt) + random.uniform(0.5, 1.5)
                await asyncio.sleep(backoff)

    return False, [], "Max retries exceeded"


async def scrape_nationwide(
    concurrency: Optional[int] = None,
    timeout_sec: Optional[int] = None,
    target_districts: Optional[List[Dict[str, str]]] = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Asynchronously crawls eRaktKosh across all districts in India with concurrency
    limiting and an automatic circuit breaker.
    """
    now = datetime.now(timezone.utc)
    run_id = f"run_{now.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
    scraped_at = now
    start_time = time.time()

    concurrency_limit = concurrency or settings.scraper_concurrency
    timeout = timeout_sec or settings.scraper_timeout_seconds
    semaphore = asyncio.Semaphore(concurrency_limit)

    if not settings.metadata_path.exists():
        raise FileNotFoundError(f"Metadata catalog missing at {settings.metadata_path}")

    with open(settings.metadata_path, "r", encoding="utf-8") as f:
        catalog = json.load(f)

    tasks_metadata = []
    if target_districts:
        tasks_metadata = target_districts
    else:
        for state_code, state_info in catalog.items():
            state_name = state_info.get("state_name", state_code)
            districts = state_info.get("districts", {})
            for dist_id, dist_name in districts.items():
                tasks_metadata.append({
                    "state_name": state_name,
                    "state_code": str(state_code),
                    "district_name": dist_name,
                    "district_id": str(dist_id),
                })

    total_districts = len(tasks_metadata)
    logger.info(
        "Starting polite nationwide scrape: %d districts, concurrency cap: %d, run_id: %s",
        total_districts,
        concurrency_limit,
        run_id,
    )

    all_facilities: List[Dict[str, Any]] = []
    success_count = 0
    failure_count = 0

    connector = aiohttp.TCPConnector(limit=concurrency_limit, enable_cleanup_closed=True)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [
            fetch_district_data(
                session=session,
                semaphore=semaphore,
                state_name=item["state_name"],
                state_id=item["state_code"],
                district_name=item["district_name"],
                district_id=item["district_id"],
                max_retries=settings.scraper_max_retries,
                timeout_sec=timeout,
            )
            for item in tasks_metadata
        ]

        batch_size = 50
        for i in range(0, total_districts, batch_size):
            batch = tasks[i : i + batch_size]
            results = await asyncio.gather(*batch)

            for success, facilities, _ in results:
                if success:
                    success_count += 1
                    all_facilities.extend(facilities)
                else:
                    failure_count += 1

            completed = min(i + batch_size, total_districts)
            error_rate = (failure_count / completed) if completed > 0 else 0.0

            # Circuit breaker: stop if error rate > 20% after at least 30 attempts
            if completed >= 30 and error_rate > 0.20:
                logger.critical(
                    "CIRCUIT BREAKER TRIGGERED: Error rate %.1f%% exceeds 20%% threshold (%d/%d failed). Aborting.",
                    error_rate * 100,
                    failure_count,
                    completed,
                )
                raise CircuitBreakerError(
                    f"Scraper circuit breaker triggered: {failure_count}/{completed} requests failed."
                )

    elapsed = time.time() - start_time
    error_rate = (failure_count / total_districts) if total_districts > 0 else 0.0

    summary = {
        "run_id": run_id,
        "scraped_at": scraped_at.isoformat(),
        "duration_seconds": round(elapsed, 2),
        "total_districts": total_districts,
        "success_count": success_count,
        "failure_count": failure_count,
        "error_rate": round(error_rate, 4),
        "total_facilities": len(all_facilities),
    }

    logger.info(
        "Scrape completed in %.2fs. Success: %d, Failed: %d, Error Rate: %.1f%%, Total Facilities: %d",
        elapsed,
        success_count,
        failure_count,
        error_rate * 100,
        len(all_facilities),
    )

    return all_facilities, summary


def compute_file_sha256(file_path: Path) -> str:
    """Computes SHA-256 digest of an immutable file."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            sha256.update(chunk)
    return sha256.hexdigest()


def write_landing_parquet(
    records: List[Dict[str, Any]], run_id: str, scraped_at: datetime
) -> Tuple[Path, str, int]:
    """
    Serializes raw scraped records directly to an immutable Parquet file in the landing zone:
    data/landing/dt=YYYY-MM-DD/hh=HH/inventory_<run_id>.parquet
    Never overwrites existing files. Returns (parquet_path, sha256, row_count).
    """
    partition_path = (
        settings.data_landing_dir
        / f"dt={scraped_at.strftime('%Y-%m-%d')}"
        / f"hh={scraped_at.strftime('%H')}"
    )
    partition_path.mkdir(parents=True, exist_ok=True)

    parquet_path = partition_path / f"inventory_{run_id}.parquet"
    manifest_path = partition_path / f"manifest_{run_id}.json"

    if parquet_path.exists():
        raise FileExistsError(f"Refusing to overwrite immutable landing file: {parquet_path}")

    # Build Arrow arrays directly to avoid CSV formatting collisions
    run_ids = [run_id] * len(records)
    scraped_timestamps = [scraped_at] * len(records)
    h_codes = [
        int(r.get("hospitalCode")) if str(r.get("hospitalCode", "")).isdigit() else None
        for r in records
    ]
    h_names = [str(r.get("hospitalname", "") or "") for r in records]
    states = [str(r.get("State", "") or "") for r in records]
    districts = [str(r.get("District", "") or "") for r in records]
    types = [str(r.get("hospitalType", "") or "") for r in records]
    facilities = [str(r.get("type", "") or "") for r in records]
    contacts = [str(r.get("hospitalcontact", "") or "") for r in records]
    addresses = [str(r.get("hospitaladd", "") or "") for r in records]
    entry_dates = [str(r.get("entrydate", "") or "") for r in records]
    components_raw = [
        json.dumps(r.get("components"))
        if isinstance(r.get("components"), (dict, list))
        else str(r.get("components", "") or "")
        for r in records
    ]
    raw_payloads = [json.dumps(r) for r in records]

    table = pa.Table.from_arrays(
        [
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
        ],
        names=[
            "run_id",
            "scraped_at",
            "hospital_code",
            "hospital_name",
            "state_name",
            "district_name",
            "hospital_type",
            "facility_type",
            "hospital_contact",
            "hospital_address",
            "entry_date_raw",
            "components_raw",
            "raw_payload_json",
        ],
    )

    pq.write_table(table, parquet_path, compression="zstd")
    sha256 = compute_file_sha256(parquet_path)

    manifest = {
        "run_id": run_id,
        "scraped_at": scraped_at.isoformat(),
        "parquet_file": parquet_path.name,
        "row_count": len(records),
        "sha256": sha256,
        "compression": "zstd",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    logger.info(
        "Landing zone write complete: %s (Rows: %d, SHA: %s)",
        parquet_path.name,
        len(records),
        sha256[:8],
    )
    return parquet_path, sha256, len(records)


def check_run_interval_guard(con, min_hours: float = 6.0, force: bool = False) -> None:
    """
    Enforces minimum gap between full nationwide runs to protect eRaktKosh upstream servers.
    Bypassed if force=True.
    """
    if force:
        logger.info("Run interval guard bypassed with --force flag.")
        return

    try:
        row = con.execute("""
            SELECT finished_at
            FROM gold.pipeline_runs
            WHERE status = 'SUCCESS'
            ORDER BY finished_at DESC
            LIMIT 1;
        """).fetchone()

        if row and row[0]:
            last_run_time = row[0]
            if last_run_time.tzinfo is None:
                last_run_time = last_run_time.replace(tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            elapsed_hours = (now - last_run_time).total_seconds() / 3600.0

            if elapsed_hours < min_hours:
                raise RunIntervalGuardError(
                    f"Minimum run interval guard: Last successful scrape occurred {elapsed_hours:.1f} hours ago. "
                    f"Threshold is {min_hours} hours. Use --force to override for manual testing."
                )
    except Exception as e:
        if isinstance(e, RunIntervalGuardError):
            raise
        logger.debug("Could not verify pipeline_runs for interval guard (tables may be uninitialized): %s", e)
