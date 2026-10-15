import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bloodlake.scraper import (
    CircuitBreakerError,
    fetch_district_data,
    scrape_nationwide,
)


@pytest.mark.asyncio
async def test_fetch_district_data_success():
    mock_session = MagicMock()
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.text.return_value = (
        '[{"hospital_name": "Test Hospital", "available_stock": "10"}]'
    )
    mock_session.get.return_value.__aenter__.return_value = mock_response

    semaphore = asyncio.Semaphore(5)
    success, facilities, err = await fetch_district_data(
        session=mock_session,
        semaphore=semaphore,
        state_name="Gujarat",
        state_id="12",
        district_name="Anand",
        district_id="123",
        max_retries=1,
        timeout_sec=5,
    )

    assert success is True
    assert len(facilities) == 1
    assert facilities[0]["hospital_name"] == "Test Hospital"
    assert facilities[0]["State"] == "Gujarat"
    assert facilities[0]["District"] == "Anand"
    assert err is None


@pytest.mark.asyncio
async def test_fetch_district_data_empty():
    mock_session = MagicMock()
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.text.return_value = "   "
    mock_session.get.return_value.__aenter__.return_value = mock_response

    semaphore = asyncio.Semaphore(5)
    success, facilities, err = await fetch_district_data(
        session=mock_session,
        semaphore=semaphore,
        state_name="Gujarat",
        state_id="12",
        district_name="Anand",
        district_id="123",
        max_retries=1,
    )

    assert success is True
    assert len(facilities) == 0
    assert err is None


@pytest.mark.asyncio
async def test_fetch_district_data_json_decode_error():
    mock_session = MagicMock()
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.text.return_value = "<html>Not JSON</html>"
    mock_session.get.return_value.__aenter__.return_value = mock_response

    semaphore = asyncio.Semaphore(5)
    success, facilities, err = await fetch_district_data(
        session=mock_session,
        semaphore=semaphore,
        state_name="Gujarat",
        state_id="12",
        district_name="Anand",
        district_id="123",
        max_retries=1,
    )

    assert success is False
    assert len(facilities) == 0
    assert "JSON decode error" in err


@pytest.mark.asyncio
async def test_fetch_district_data_retry_on_429_then_success():
    mock_session = MagicMock()

    resp_429 = AsyncMock()
    resp_429.status = 429

    resp_200 = AsyncMock()
    resp_200.status = 200
    resp_200.text.return_value = '[{"name": "Anand Bank"}]'

    cm_429 = MagicMock()
    cm_429.__aenter__.return_value = resp_429
    cm_429.__aexit__.return_value = None

    cm_200 = MagicMock()
    cm_200.__aenter__.return_value = resp_200
    cm_200.__aexit__.return_value = None

    mock_session.get.side_effect = [cm_429, cm_200]

    with patch("asyncio.sleep", new_callable=AsyncMock):
        semaphore = asyncio.Semaphore(5)
        success, facilities, err = await fetch_district_data(
            session=mock_session,
            semaphore=semaphore,
            state_name="Gujarat",
            state_id="12",
            district_name="Anand",
            district_id="123",
            max_retries=2,
        )

        assert success is True
        assert len(facilities) == 1


@pytest.mark.asyncio
async def test_scrape_nationwide_with_targets():
    target_districts = [
        {"state_name": "Gujarat", "state_code": "12", "district_name": "Anand", "district_id": "101"}
    ]

    with patch(
        "bloodlake.scraper.fetch_district_data", new_callable=AsyncMock
    ) as mock_fetch:
        mock_fetch.return_value = (True, [{"hospital_name": "Anand Red Cross"}], None)

        records, meta = await scrape_nationwide(
            concurrency=2, timeout_sec=5, target_districts=target_districts
        )

        assert len(records) == 1
        assert meta["total_districts"] == 1
        assert meta["success_count"] == 1
        assert meta["failure_count"] == 0
        assert meta["error_rate"] == 0.0


@pytest.mark.asyncio
async def test_scrape_nationwide_circuit_breaker():
    target_districts = [
        {"state_name": "State A", "state_code": "1", "district_name": f"Dist {i}", "district_id": str(i)}
        for i in range(1, 35)
    ]

    with patch(
        "bloodlake.scraper.fetch_district_data", new_callable=AsyncMock
    ) as mock_fetch:
        # All fail -> error rate = 100% > 20% threshold after 30
        mock_fetch.return_value = (False, [], "Connection timed out")

        with pytest.raises(CircuitBreakerError):
            await scrape_nationwide(concurrency=2, timeout_sec=5, target_districts=target_districts)
