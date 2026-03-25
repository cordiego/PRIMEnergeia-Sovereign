"""
PRIMEngine — Alert System
============================
Telegram + logging-based alerting for dispatch events,
anomalies, and system health notifications.

Reuses the pattern from Eureka-Sovereign's notification system.

PRIMEnergeia S.A.S.
"""

import os
import json
import logging
import time
from datetime import datetime
from typing import Optional

import urllib.request
import urllib.error

logger = logging.getLogger("primengine.alerts")

TELEGRAM_BOT_TOKEN = os.environ.get("PRIME_TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("PRIME_TELEGRAM_CHAT_ID", "")
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds


class PRIMAlerts:
    """Multi-channel alert system for PRIMEngine operations."""

    def __init__(self, bot_token: str = "", chat_id: str = ""):
        self.bot_token = bot_token or TELEGRAM_BOT_TOKEN
        self.chat_id = chat_id or TELEGRAM_CHAT_ID
        self.telegram_enabled = bool(self.bot_token and self.chat_id)

        if not self.telegram_enabled:
            logger.warning("Telegram alerts disabled — set PRIME_TELEGRAM_BOT_TOKEN and PRIME_TELEGRAM_CHAT_ID")

    def _send_telegram(self, text: str) -> bool:
        """Send message via Telegram Bot API with retry logic."""
        if not self.telegram_enabled:
            return False

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = json.dumps({
            "chat_id": self.chat_id,
            "text": text,
        }).encode("utf-8")

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                req = urllib.request.Request(
                    url, data=payload,
                    headers={"Content-Type": "application/json"}
                )
                with urllib.request.urlopen(req, timeout=10) as response:
                    if response.status == 200:
                        return True
            except (urllib.error.URLError, urllib.error.HTTPError, OSError) as e:
                logger.warning(f"Telegram send attempt {attempt}/{MAX_RETRIES} failed: {e}")
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_DELAY * attempt)

        logger.error("Telegram alert failed after all retries")
        return False

    # ─── Alert Types ───

    def dispatch_complete(self, market: str, fleet_mw: float,
                          savings_pct: float, savings_usd: float,
                          solver_ms: float):
        """Alert: dispatch optimization completed."""
        msg = (
            f"⚡ PRIMEngine Dispatch Complete\n"
            f"Market: {market.upper()}\n"
            f"Fleet: {fleet_mw:.0f} MW\n"
            f"Savings: {savings_pct:.1f}% (${savings_usd:,.0f})\n"
            f"Solver: {solver_ms:.0f}ms\n"
            f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        )
        logger.info(msg.replace("\n", " | "))
        self._send_telegram(msg)

    def price_anomaly(self, market: str, node: str,
                      expected_price: float, actual_price: float):
        """Alert: market price exceeds forecast by >20%."""
        deviation = abs(actual_price - expected_price) / expected_price * 100
        msg = (
            f"🚨 Price Anomaly Detected\n"
            f"Market: {market.upper()} | Node: {node}\n"
            f"Expected: ${expected_price:.2f}/MWh\n"
            f"Actual: ${actual_price:.2f}/MWh\n"
            f"Deviation: {deviation:.1f}%\n"
            f"Action: Re-optimizing dispatch"
        )
        logger.warning(msg.replace("\n", " | "))
        self._send_telegram(msg)

    def frequency_violation(self, market: str, frequency: float,
                             threshold: float, penalty_usd: float):
        """Alert: grid frequency dropped below penalty threshold."""
        msg = (
            f"⚠️ Frequency Violation\n"
            f"Market: {market.upper()}\n"
            f"Frequency: {frequency:.4f} Hz (threshold: {threshold:.2f} Hz)\n"
            f"Estimated Penalty: ${penalty_usd:,.0f}\n"
            f"Synthetic inertia injected"
        )
        logger.warning(msg.replace("\n", " | "))
        self._send_telegram(msg)

    def system_health(self, status: str, details: str = ""):
        """Alert: system health notification."""
        emoji = "✅" if status == "healthy" else "🔴"
        msg = (
            f"{emoji} PRIMEngine Health: {status.upper()}\n"
            f"{details}\n"
            f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        )
        logger.info(msg.replace("\n", " | "))
        self._send_telegram(msg)

    def daily_summary(self, total_dispatches: int, total_savings_usd: float,
                      markets_active: list):
        """Daily operations summary."""
        msg = (
            f"📊 PRIMEngine Daily Summary\n"
            f"Dispatches: {total_dispatches}\n"
            f"Total Savings: ${total_savings_usd:,.0f}\n"
            f"Markets: {', '.join(m.upper() for m in markets_active)}\n"
            f"Date: {datetime.now().strftime('%Y-%m-%d')}"
        )
        logger.info(msg.replace("\n", " | "))
        self._send_telegram(msg)


# Default instance
alerts = PRIMAlerts()
