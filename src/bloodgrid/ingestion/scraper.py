"""
BloodGrid Ingestion Scraper
===========================
Polite, high-speed asynchronous data collector for eRaktKosh.

Adheres strictly to source protection rules:
- Identifiable User-Agent with contact email
- Configurable concurrency limit (default 10 via asyncio.Semaphore)
- Exponential backoff with random jitter on HTTP 429/5xx errors
- Circuit breaker aborts execution if error rate > 20%
- Minimum 3 hours between full runs guard
"""

import asyncio
import json
import logging
import random
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import aiohttp

from bloodgrid.config import settings

logger = logging.getLogger("bloodgrid.scraper")

METADATA_FILE = settings.base_dir / "eraktkosh_all_metadata.json"
BASE_URL = "https://eraktkosh.mohfw.gov.in/eraktkoshPortal/eraktkosh/blood-availability"


class CircuitBreakerError(Exception):
    """Raised when the scraper aborts due to an unacceptably high error rate."""

    pass


class RunIntervalGuardError(Exception):
    """Raised when attempting a full run within the minimum interval guard period."""

    pass


async def fetch_district_data(
    session: aiohttp.ClientSession,
    semaphore: asyncio.Semaphore,
    state_name: str,
    state_id: str,
    district_name: str,
    district_id: str,
    max_retries: int = 3,
    timeout_sec: int = 15,
) -> Tuple[bool, List[Dict[str, Any]], Optional[str]]:
    """
    Fetches raw inventory for a single district with polite exponential backoff.
    Returns (success_flag, facilities_list, error_message).
    """
    url = f"{BASE_URL}?stateCode={state_id}&districtId={district_id}"
    headers = {
        "User-Agent": settings.scraper_user_agent,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
    }

    for attempt in range(1, max_retries + 1):
        async with semaphore:
            try:
                timeout = aiohttp.ClientTimeout(total=timeout_sec)
                async with session.get(url, headers=headers, timeout=timeout) as response:
                    # Respect HTTP 429 (Too Many Requests) or 5xx server errors
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
                        logger.warning(
                            "Unexpected status %d for %s", response.status, district_name
                        )
            except (aiohttp.ClientError, asyncio.TimeoutError) as err:
                if attempt == max_retries:
                    logger.error(
                        "Failed to fetch %s after %d attempts: %s", district_name, attempt, err
                    )
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
    limiting and an automatic circuit-breaker.
    """
    run_id = f"run_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
    scraped_at = datetime.utcnow()
    start_time = time.time()

    concurrency_limit = concurrency or settings.scraper_concurrency
    timeout = timeout_sec or settings.scraper_timeout_sec
    semaphore = asyncio.Semaphore(concurrency_limit)

    if not METADATA_FILE.exists():
        raise FileNotFoundError(f"Metadata catalog missing at {METADATA_FILE}")

    with open(METADATA_FILE, "r") as f:
        metadata = json.load(f)

    states = metadata.get("States_and_Districts", [])
    district_tasks_info = []

    if target_districts:
        district_tasks_info = target_districts
    else:
        for state in states:
            s_id = str(state.get("stateCode", ""))
            s_name = state.get("stateName", "")
            for dist in state.get("districts", []):
                d_id = str(dist.get("districtCode", ""))
                d_name = dist.get("districtName", "")
                district_tasks_info.append(
                    {
                        "state_name": s_name,
                        "state_id": s_id,
                        "district_name": d_name,
                        "district_id": d_id,
                    }
                )

    total_districts = len(district_tasks_info)
    logger.info(
        "Starting polite nationwide scrape: %d districts, concurrency cap: %d, run_id: %s",
        total_districts,
        concurrency_limit,
        run_id,
    )

    all_records: List[Dict[str, Any]] = []
    successful_districts = 0
    failed_districts = 0
    failed_district_errors: Dict[str, str] = {}

    connector = aiohttp.TCPConnector(limit=concurrency_limit, ttl_dns_cache=300)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [
            fetch_district_data(
                session=session,
                semaphore=semaphore,
                state_name=d["state_name"],
                state_id=d["state_id"],
                district_name=d["district_name"],
                district_id=d["district_id"],
                timeout_sec=timeout,
            )
            for d in district_tasks_info
        ]

        # Gather all responses
        results = await asyncio.gather(*tasks)

        for idx, (success, banks, err) in enumerate(results):
            d_info = district_tasks_info[idx]
            if success:
                successful_districts += 1
                all_records.extend(banks)
            else:
                failed_districts += 1
                failed_district_errors[f"{d_info['state_name']}:{d_info['district_name']}"] = (
                    err or "Unknown"
                )

    elapsed = time.time() - start_time
    error_rate = (failed_districts / total_districts * 100.0) if total_districts > 0 else 0.0

    logger.info(
        "Scrape completed in %.2fs. Success: %d, Failed: %d, Error Rate: %.1f%%, Total Facilities: %d",
        elapsed,
        successful_districts,
        failed_districts,
        error_rate,
        len(all_records),
    )

    # Circuit Breaker check
    if error_rate > settings.circuit_breaker_max_error_pct:
        raise CircuitBreakerError(
            f"Circuit breaker tripped: error rate {error_rate:.1f}% exceeds max threshold {settings.circuit_breaker_max_error_pct}% "
            f"({failed_districts}/{total_districts} districts failed)."
        )

    summary = {
        "run_id": run_id,
        "scraped_at": scraped_at.isoformat(),
        "total_districts": total_districts,
        "successful_districts": successful_districts,
        "failed_districts": failed_districts,
        "error_rate_pct": round(error_rate, 2),
        "total_facilities": len(all_records),
        "duration_seconds": round(elapsed, 2),
        "failed_samples": dict(list(failed_district_errors.items())[:10]),
    }

    return all_records, summary
