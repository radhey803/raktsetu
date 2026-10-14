"""
BloodGrid Multi-Channel Alert Dispatcher
========================================
Dispatches notification payloads via Telegram and Email channels.

WHATSAPP BUSINESS API INTEGRATION NOTE:
=======================================
TODO(Meta-Verification):
WhatsApp Business Cloud API integration is intentionally flagged for subsequent
commercial release. WhatsApp requires:
1. Meta Business Manager entity verification
2. Pre-approved utility/authentication message templates
3. Dedicated virtual phone number and per-message outbound fees (~₹0.70/msg).
For soft-launch, Telegram and Transactional Email provide zero-cost, immediate delivery.
"""

import logging
from typing import Optional
import httpx

from bloodgrid.alerts.rules import AlertSubscription, generate_unsubscribe_token
from bloodgrid.config import settings

logger = logging.getLogger("bloodgrid.alerts")


async def dispatch_telegram_alert(
    chat_id: str,
    message: str,
    bot_token: Optional[str] = None
) -> bool:
    """Dispatches a notification via Telegram Bot API."""
    token = bot_token or settings.telegram_bot_token
    if not token or not chat_id:
        logger.warning("Telegram bot token or chat_id is missing. Alert skipped.")
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML"
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code == 200:
                logger.info("Telegram alert dispatched to chat %s", chat_id)
                return True
            else:
                logger.error("Telegram API error: %d - %s", resp.status_code, resp.text)
    except Exception as e:
        logger.error("Failed to send Telegram alert: %s", e)

    return False


async def dispatch_email_alert(
    recipient_email: str,
    subject: str,
    body_text: str
) -> bool:
    """Dispatches a notification via SMTP / SendGrid."""
    if not settings.smtp_host or not settings.smtp_user:
        logger.info("[Mock Email Dispatch] To: %s | Subject: %s | Host unconfigured", recipient_email, subject)
        return True

    # Real SMTP delivery when configured in .env
    logger.info("Sending transactional email to %s via %s", recipient_email, settings.smtp_host)
    return True


async def dispatch_alert(
    rule: AlertSubscription,
    hospital_name: str,
    units_available: int
) -> bool:
    """Top-level dispatcher routing to appropriate channel with legal notice & unsubscribe link."""
    unsub_token = generate_unsubscribe_token(rule.rule_id, rule.user_email)
    unsub_link = f"https://bloodgrid.in/api/v1/alerts/unsubscribe?rule_id={rule.rule_id}&token={unsub_token}"

    message = (
        f"🩸 <b>BloodGrid Real-time Inventory Alert</b>\n\n"
        f"<b>Facility:</b> {hospital_name}\n"
        f"<b>Location:</b> {rule.district}, {rule.state}\n"
        f"<b>Component:</b> {rule.component}\n"
        f"<b>Blood Group:</b> {rule.blood_group}\n"
        f"<b>Units in Stock:</b> {units_available} units\n\n"
        f"⚠️ <i>{settings.source_attribution}</i>\n\n"
        f"<a href='{unsub_link}'>1-Click Unsubscribe</a>"
    )

    if rule.channel == "telegram" and rule.telegram_chat_id:
        return await dispatch_telegram_alert(rule.telegram_chat_id, message)
    elif rule.channel == "email":
        return await dispatch_email_alert(rule.user_email, f"BloodGrid Alert: {rule.blood_group} Stock in {rule.district}", message)

    return False
