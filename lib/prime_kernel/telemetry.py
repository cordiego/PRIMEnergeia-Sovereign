"""
PRIME-Kernel — Unified Telemetry & Notifications
====================================================
Shared logging, metrics collection, and Telegram notification
helper used across all PRIMEnergeia SBUs.

Author: Diego Córdoba Urrutia — PRIMEnergeia S.A.S.
"""

import os
import json
import time
import logging
import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field


# ─────────────────────────────────────────────────────────────
# PRIMELogger — Branded Logging
# ─────────────────────────────────────────────────────────────
class PRIMELogger:
    """
    Consistent logging across all SBUs with branded formatting.

    Usage:
        logger = PRIMELogger("PRIME Grid")
        logger.info("VZA-400 frequency stabilized")
        logger.metric("capital_rescued_usd", 231243)
    """

    _FORMAT = "%(asctime)s — [%(name)s] — %(levelname)s — %(message)s"

    def __init__(self, sbu_name: str, level: int = logging.INFO):
        self.sbu_name = sbu_name
        self._logger = logging.getLogger(f"PRIMEnergeia.{sbu_name}")
        self._logger.setLevel(level)

        if not self._logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter(self._FORMAT))
            self._logger.addHandler(handler)

        self._metrics: List[Dict[str, Any]] = []

    def info(self, msg: str):
        self._logger.info(msg)

    def warning(self, msg: str):
        self._logger.warning(msg)

    def error(self, msg: str):
        self._logger.error(msg)

    def metric(self, name: str, value: Any, unit: str = ""):
        """Log a named metric with timestamp."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "sbu": self.sbu_name,
            "metric": name,
            "value": value,
            "unit": unit,
        }
        self._metrics.append(entry)
        self._logger.info(f"📊 {name}: {value} {unit}")

    def get_metrics(self) -> List[Dict]:
        return self._metrics.copy()

    def export_metrics(self, filepath: str):
        """Export collected metrics to JSON file."""
        with open(filepath, "w") as f:
            json.dump(self._metrics, f, indent=2, default=str)
        self._logger.info(f"Metrics exported → {filepath}")


# ─────────────────────────────────────────────────────────────
# PRIMETelemetry — Telegram + Webhook Notifications
# ─────────────────────────────────────────────────────────────
@dataclass
class NotificationResult:
    """Result of a notification attempt."""
    success: bool
    channel: str
    timestamp: str
    error: Optional[str] = None
    retry_count: int = 0


class PRIMETelemetry:
    """
    Unified notification system with retry logic.

    Supports:
      - Telegram Bot API
      - Generic webhooks
      - Local file logging (fallback)

    Usage:
        telemetry = PRIMETelemetry()
        telemetry.send_telegram("🔌 VZA-400: $57,811 USD rescued")
    """

    MAX_RETRIES = 3
    BASE_DELAY_S = 1.0  # Exponential backoff base

    def __init__(
        self,
        telegram_token: Optional[str] = None,
        telegram_chat_id: Optional[str] = None,
        webhook_url: Optional[str] = None,
    ):
        self.telegram_token = telegram_token or os.environ.get("TELEGRAM_BOT_TOKEN", "")
        self.telegram_chat_id = telegram_chat_id or os.environ.get("TELEGRAM_CHAT_ID", "")
        self.webhook_url = webhook_url or os.environ.get("PRIME_WEBHOOK_URL", "")
        self._log_dir = os.path.expanduser("~/.prime_telemetry")
        os.makedirs(self._log_dir, exist_ok=True)

    def send_telegram(self, message: str, disable_preview: bool = True) -> NotificationResult:
        """
        Send a Telegram message with exponential backoff retry.
        IMPORTANT: Does NOT use parse_mode to avoid silent failures
        with special characters.
        """
        if not self.telegram_token or not self.telegram_chat_id:
            return self._fallback_log(message, "telegram")

        import urllib.request
        import urllib.error

        url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
        payload = json.dumps({
            "chat_id": self.telegram_chat_id,
            "text": message,
            "disable_web_page_preview": disable_preview,
        }).encode("utf-8")

        for attempt in range(self.MAX_RETRIES):
            try:
                req = urllib.request.Request(
                    url, data=payload,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=10) as resp:
                    if resp.status == 200:
                        return NotificationResult(
                            success=True,
                            channel="telegram",
                            timestamp=datetime.now(timezone.utc).isoformat(),
                            retry_count=attempt,
                        )
            except (urllib.error.URLError, TimeoutError) as e:
                delay = self.BASE_DELAY_S * (2 ** attempt)
                time.sleep(delay)

        return self._fallback_log(message, "telegram", error="Max retries exceeded")

    def send_webhook(self, payload: Dict) -> NotificationResult:
        """Send payload to configured webhook URL with retry."""
        if not self.webhook_url:
            return self._fallback_log(json.dumps(payload), "webhook")

        import urllib.request
        import urllib.error

        data = json.dumps(payload).encode("utf-8")

        for attempt in range(self.MAX_RETRIES):
            try:
                req = urllib.request.Request(
                    self.webhook_url, data=data,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=10) as resp:
                    if resp.status < 300:
                        return NotificationResult(
                            success=True,
                            channel="webhook",
                            timestamp=datetime.now(timezone.utc).isoformat(),
                            retry_count=attempt,
                        )
            except (urllib.error.URLError, TimeoutError):
                delay = self.BASE_DELAY_S * (2 ** attempt)
                time.sleep(delay)

        return self._fallback_log(json.dumps(payload), "webhook", error="Max retries exceeded")

    def _fallback_log(self, message: str, channel: str,
                      error: Optional[str] = None) -> NotificationResult:
        """Fallback: write notification to local file."""
        ts = datetime.now(timezone.utc).isoformat()
        log_file = os.path.join(self._log_dir, f"notifications_{datetime.now().strftime('%Y%m%d')}.jsonl")

        entry = {
            "timestamp": ts,
            "channel": channel,
            "message": message,
            "error": error or "no_credentials",
        }

        with open(log_file, "a") as f:
            f.write(json.dumps(entry) + "\n")

        return NotificationResult(
            success=False,
            channel=f"{channel}_fallback",
            timestamp=ts,
            error=error or "Credentials not configured — logged to file",
        )

    # ─── Convenience: SBU-branded notifications ───

    def notify_grid_rescue(self, node: str, capital_usd: float, freq_stability: float):
        """Branded notification for Grid SBU capital rescue events."""
        msg = (
            f"🔌 PRIME Grid — Capital Rescue\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Node: {node}\n"
            f"Capital Rescued: ${capital_usd:,.0f} USD\n"
            f"Frequency Stability: {freq_stability:.2%}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"PRIMEnergeia S.A.S."
        )
        return self.send_telegram(msg)

    def notify_trade_signal(self, portfolio_value: float, signals: List[Dict]):
        """Branded notification for Quant SBU trade signals."""
        lines = [
            f"📈 PRIME Quant — Eureka Signal",
            f"━━━━━━━━━━━━━━━━━━━━━━━━",
            f"Portfolio: ${portfolio_value:,.0f} USD",
        ]
        for s in signals[:5]:
            action = s.get("action", "HOLD")
            ticker = s.get("ticker", "?")
            pct = s.get("trade_pct", 0)
            emoji = "🟢" if action == "BUY" else "🔴"
            lines.append(f"{emoji} {action} {ticker}: {pct:+.1f}%")
        lines.extend([
            f"━━━━━━━━━━━━━━━━━━━━━━━━",
            f"PRIMEnergeia S.A.S.",
        ])
        return self.send_telegram("\n".join(lines))

    def notify_engine_status(self, engine_id: str, power_kw: float, health_pct: float):
        """Branded notification for Power SBU engine status."""
        msg = (
            f"⚡ PRIME Power — Engine Status\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Engine: {engine_id}\n"
            f"Output: {power_kw:.0f} kW\n"
            f"Health: {health_pct:.1f}%\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"PRIMEnergeia S.A.S."
        )
        return self.send_telegram(msg)
