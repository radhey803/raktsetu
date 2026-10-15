"""
Unit Tests: Multi-Channel Alert Dispatcher
==========================================
Tests Telegram bot dispatch, transactional email dispatch,
and top-level dispatcher routing with legal notices.
"""

from unittest.mock import AsyncMock, patch

import pytest

from bloodgrid.alerts.dispatcher import (
    dispatch_alert,
    dispatch_email_alert,
    dispatch_telegram_alert,
)
from bloodgrid.alerts.rules import AlertSubscription


@pytest.mark.asyncio
async def test_dispatch_telegram_alert_missing_token_or_chat():
    # When token or chat_id is missing, gracefully returns False without crashing
    res = await dispatch_telegram_alert(chat_id="", message="Test Alert", bot_token=None)
    assert res is False


@pytest.mark.asyncio
async def test_dispatch_telegram_alert_success():
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value.status_code = 200

        res = await dispatch_telegram_alert(
            chat_id="123456", message="<b>Test Blood Alert</b>", bot_token="test_bot_token"
        )
        assert res is True
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert "123456" == kwargs["json"]["chat_id"]


@pytest.mark.asyncio
async def test_dispatch_email_alert_unconfigured_host():
    # In dev without SMTP configured, returns True as mock delivery
    res = await dispatch_email_alert(
        recipient_email="coordinator@hospital.org",
        subject="Emergency Alert",
        body_text="O- Blood Available",
    )
    assert res is True


@pytest.mark.asyncio
async def test_top_level_dispatch_alert_telegram():
    rule = AlertSubscription(
        user_email="doctor@test.com",
        channel="telegram",
        telegram_chat_id="chat_7788",
        state="Gujarat",
        district="Anand",
        component="Packed Red Blood Cells",
        blood_group="O-",
        is_emergency=True,
    )

    with patch(
        "bloodgrid.alerts.dispatcher.dispatch_telegram_alert", new_callable=AsyncMock
    ) as mock_tg:
        mock_tg.return_value = True
        success = await dispatch_alert(
            rule, hospital_name="Anand Civil Hospital", units_available=4
        )
        assert success is True
        mock_tg.assert_called_once()
        args = mock_tg.call_args[0]
        assert args[0] == "chat_7788"
        assert "Anand Civil Hospital" in args[1]
        assert "Data sourced from eRaktKosh" in args[1]
        assert "1-Click Unsubscribe" in args[1]


@pytest.mark.asyncio
async def test_top_level_dispatch_alert_email():
    rule = AlertSubscription(
        user_email="coordinator@test.com",
        channel="email",
        state="Gujarat",
        district="Anand",
        is_emergency=True,
    )

    with patch(
        "bloodgrid.alerts.dispatcher.dispatch_email_alert", new_callable=AsyncMock
    ) as mock_email:
        mock_email.return_value = True
        success = await dispatch_alert(rule, hospital_name="Red Cross Centre", units_available=8)
        assert success is True
        mock_email.assert_called_once()
        args = mock_email.call_args[0]
        assert args[0] == "coordinator@test.com"
        assert "Red Cross Centre" in args[2]
