#!/usr/bin/env python3
"""
EUREKA PRE-MARKET CRON — Standalone Scheduler Entry Point
==========================================================
Designed to run at 7:30 AM ET (11:30 UTC) Mon-Fri via GitHub Actions.
Generates pre-market intelligence signal and dispatches to Telegram.

Usage:
    python eureka_premarket_cron.py
    python eureka_premarket_cron.py --dry-run   # Print without sending
"""

import os
import sys
import argparse
import logging
from datetime import datetime

# Add parent directory to path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [PreMarket-Cron] - %(message)s'
)
logger = logging.getLogger(__name__)


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
            try:
                from core.alerts import PRIMAlerts
                alerts = PRIMAlerts()
                alerts._send_telegram(f"⚠️ EUREKA PRE-MARKET ERROR (SNDK)\n{error_msg}")
            except Exception:
                pass
    else:
        # Format and send SNDK message
        sndk_message = sndk_engine.format_premarket_message(sndk_signal)
        print(sndk_message)
        if not dry_run:
            logger.info("Sending Telegram notification for SNDK...")
            try:
                from core.alerts import PRIMAlerts
                alerts = PRIMAlerts()
                success = alerts._send_telegram(sndk_message)
                if success:
                    logger.info("[✓] SNDK Pre-market notification delivered.")
                else:
                    logger.warning("[!] SNDK Telegram delivery failed.")
            except Exception as e:
                logger.error(f"Telegram send error: {e}")
        
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
            try:
                from core.alerts import PRIMAlerts
                alerts = PRIMAlerts()
                alerts._send_telegram(f"⚠️ EUREKA PRE-MARKET ERROR (SCHD)\n{error_msg}")
            except Exception:
                pass
    else:
        # Format and send SCHD message
        schd_message = schd_engine.format_premarket_message(schd_signal)
        print(schd_message)
        if not dry_run:
            logger.info("Sending Telegram notification for SCHD...")
            try:
                from core.alerts import PRIMAlerts
                alerts = PRIMAlerts()
                success = alerts._send_telegram(schd_message)
                if success:
                    logger.info("[✓] SCHD Pre-market notification delivered.")
                else:
                    logger.warning("[!] SCHD Telegram delivery failed.")
            except Exception as e:
                logger.error(f"Telegram send error: {e}")
        
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
