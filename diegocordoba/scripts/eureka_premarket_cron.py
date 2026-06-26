#!/usr/bin/env python3
"""
EUREKA PRE-MARKET CRON — Standalone Scheduler Entry Point
==========================================================
Designed to run at 7:30 AM ET (11:30 UTC) Mon-Fri via GitHub Actions.
Generates pre-market intelligence signal and dispatches to Telegram
via BOTH DoctorPRIME and Eureka bots.

Usage:
    python eureka_premarket_cron.py
    python eureka_premarket_cron.py --dry-run   # Print without sending
"""

import os
import sys
import json
import argparse
import logging
import time
import urllib.request
import urllib.error
from datetime import datetime

# Add parent directory to path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [PreMarket-Cron] - %(message)s'
)
logger = logging.getLogger(__name__)

# ─── Telegram Configuration ───────────────────────────────────────
# Both bots send to the same chat_id
CHAT_ID = os.environ.get("PRIME_TELEGRAM_CHAT_ID", "")

BOTS = {
    "DoctorPRIME": os.environ.get("PRIME_TELEGRAM_BOT_TOKEN", ""),
    "Eureka":      os.environ.get("EUREKA_TELEGRAM_BOT_TOKEN", ""),
}

MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds


def send_telegram(text: str, bot_name: str = None) -> bool:
    """Send message via Telegram Bot API with retry logic.
    
    If bot_name is specified, sends from that bot only.
    If bot_name is None, sends from ALL configured bots.
    """
    if not CHAT_ID:
        logger.error("PRIME_TELEGRAM_CHAT_ID not set — cannot send Telegram messages")
        return False

    bots_to_use = {}
    if bot_name and bot_name in BOTS:
        bots_to_use = {bot_name: BOTS[bot_name]}
    else:
        bots_to_use = BOTS

    any_success = False
    for name, token in bots_to_use.items():
        if not token:
            logger.warning(f"[{name}] Bot token not set — skipping")
            continue

        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = json.dumps({
            "chat_id": CHAT_ID,
            "text": text,
        }).encode("utf-8")

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                req = urllib.request.Request(
                    url, data=payload,
                    headers={"Content-Type": "application/json"}
                )
                with urllib.request.urlopen(req, timeout=15) as response:
                    if response.status == 200:
                        logger.info(f"[✓] [{name}] Telegram message delivered")
                        any_success = True
                        break
            except (urllib.error.URLError, urllib.error.HTTPError, OSError) as e:
                logger.warning(f"[{name}] Send attempt {attempt}/{MAX_RETRIES} failed: {e}")
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_DELAY * attempt)

        else:
            logger.error(f"[{name}] Telegram delivery FAILED after {MAX_RETRIES} retries")

    return any_success


def is_market_day() -> bool:
    """Check if today is a US equity trading day."""
    try:
        import pandas_market_calendars as mcal
        nyse = mcal.get_calendar('NYSE')
        today = datetime.now().strftime('%Y-%m-%d')
        schedule = nyse.schedule(start_date=today, end_date=today)
        return len(schedule) > 0
    except ImportError:
        # Fallback: weekday check only (Mon=0, Fri=4)
        return datetime.now().weekday() < 5
    except Exception as e:
        logger.warning(f"Market calendar check failed: {e}. Defaulting to weekday check.")
        return datetime.now().weekday() < 5


def run_premarket_cron(dry_run: bool = False):
    """Execute the pre-market intelligence pipeline."""
    logger.info("=" * 55)
    logger.info("EUREKA PRE-MARKET CRON — Starting")
    logger.info("=" * 55)

    # Check if today is a trading day
    if not is_market_day():
        logger.info("Today is not a trading day. Exiting gracefully.")
        return

    # Import the pre-market engines
    try:
        import eureka_premarket as sndk_engine
        import eureka_schd_premarket as schd_engine
    except ImportError as e:
        logger.error(f"Failed to import engines: {e}")
        send_telegram(f"⚠️ EUREKA PRE-MARKET IMPORT ERROR\n{e}")
        sys.exit(1)

    # ---------------------------------------------------------
    # 1. RUN SNDK ENGINE
    # ---------------------------------------------------------
    logger.info("Generating pre-market signal for SNDK...")
    sndk_signal = sndk_engine.generate_premarket_signal()

    if sndk_signal is None or "error" in sndk_signal:
        error_msg = sndk_signal.get("error", "Unknown error") if sndk_signal else "Signal generation returned None"
        logger.error(f"SNDK Pre-market signal failed: {error_msg}")
        if not dry_run:
            send_telegram(f"⚠️ EUREKA PRE-MARKET ERROR (SNDK)\n{error_msg}")
    else:
        # Format and send SNDK message
        sndk_message = sndk_engine.format_premarket_message(sndk_signal)
        print(sndk_message)
        if not dry_run:
            logger.info("Sending Telegram notification for SNDK...")
            send_telegram(sndk_message)

        try:
            sndk_engine.save_premarket_history(sndk_signal)
            logger.info("[✓] SNDK Pre-market history saved.")
        except Exception as e:
            logger.warning(f"Failed to save SNDK history: {e}")

    # ---------------------------------------------------------
    # 2. RUN SCHD ENGINE
    # ---------------------------------------------------------
    logger.info("Generating pre-market signal for SCHD...")
    schd_signal = schd_engine.generate_premarket_signal()

    if schd_signal is None or "error" in schd_signal:
        error_msg = schd_signal.get("error", "Unknown error") if schd_signal else "Signal generation returned None"
        logger.error(f"SCHD Pre-market signal failed: {error_msg}")
        if not dry_run:
            send_telegram(f"⚠️ EUREKA PRE-MARKET ERROR (SCHD)\n{error_msg}")
    else:
        # Format and send SCHD message
        schd_message = schd_engine.format_premarket_message(schd_signal)
        print(schd_message)
        if not dry_run:
            logger.info("Sending Telegram notification for SCHD...")
            send_telegram(schd_message)

        try:
            schd_engine.save_premarket_history(schd_signal)
            logger.info("[✓] SCHD Pre-market history saved.")
        except Exception as e:
            logger.warning(f"Failed to save SCHD history: {e}")

    logger.info("EUREKA PRE-MARKET CRON — Complete")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Eureka Pre-Market Cron Runner")
    parser.add_argument("--dry-run", action="store_true",
                        help="Run without sending Telegram notification")
    args = parser.parse_args()

    run_premarket_cron(dry_run=args.dry_run)
