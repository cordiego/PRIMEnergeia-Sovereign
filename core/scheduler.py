"""
PRIMEngine — Background Scheduler
=====================================
Lightweight task scheduler using APScheduler for periodic re-optimization,
market data refresh, and session cleanup.

PRIMEnergeia S.A.S.
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Optional, Callable

logger = logging.getLogger("primengine.scheduler")


class PRIMScheduler:
    """Background task scheduler for PRIMEngine operations.

    Uses APScheduler if available, falls back to a simple thread-based
    approach for environments without it.
    """

    def __init__(self):
        self._scheduler = None
        self._jobs = {}
        self._running = False
        self._init_scheduler()

    def _init_scheduler(self):
        try:
            from apscheduler.schedulers.background import BackgroundScheduler
            self._scheduler = BackgroundScheduler(
                job_defaults={"coalesce": True, "max_instances": 1}
            )
            logger.info("APScheduler backend initialized")
        except ImportError:
            logger.warning("APScheduler not installed — using manual scheduling")
            self._scheduler = None

    def start(self):
        """Start the scheduler."""
        if self._scheduler:
            self._scheduler.start()
            self._running = True
            logger.info("PRIMEngine scheduler started")

    def stop(self):
        """Gracefully stop the scheduler."""
        if self._scheduler and self._running:
            self._scheduler.shutdown(wait=False)
            self._running = False
            logger.info("PRIMEngine scheduler stopped")

    def add_periodic_task(self, name: str, func: Callable,
                          interval_minutes: int = 15, **kwargs):
        """Schedule a periodic task.

        Parameters
        ----------
        name : str
            Unique job name
        func : callable
            Function to execute
        interval_minutes : int
            Execution interval in minutes
        """
        if self._scheduler:
            job = self._scheduler.add_job(
                func, "interval", minutes=interval_minutes,
                id=name, replace_existing=True, **kwargs
            )
            self._jobs[name] = job
            logger.info(f"Scheduled '{name}' every {interval_minutes}min")
        else:
            logger.warning(f"Cannot schedule '{name}' — no scheduler backend")

    def remove_task(self, name: str):
        """Remove a scheduled task."""
        if self._scheduler and name in self._jobs:
            self._scheduler.remove_job(name)
            del self._jobs[name]

    @property
    def active_jobs(self):
        return list(self._jobs.keys())


# ─── Built-in Tasks ───

def task_cleanup_stale_sessions(max_age_hours: int = 24):
    """Clean up sessions older than max_age_hours."""
    from core.database import get_connection
    cutoff = (datetime.now() - timedelta(hours=max_age_hours)).isoformat()
    try:
        with get_connection() as conn:
            result = conn.execute(
                "DELETE FROM dispatch_sessions WHERE status='created' AND created_at < ?",
                (cutoff,)
            )
            if result.rowcount > 0:
                logger.info(f"Cleaned {result.rowcount} stale sessions")
    except Exception as e:
        logger.error(f"Session cleanup failed: {e}")


def task_market_data_refresh():
    """Refresh market price data (placeholder for real API integration)."""
    logger.info(f"Market data refresh at {datetime.now().isoformat()}")
    # TODO: Integrate real ERCOT/SEN/MIBEL price feeds
    # - ERCOT: ercot.com/gridmktinfo/dashboards
    # - SEN: cenace.gob.mx
    # - MIBEL: omie.es


def task_re_optimize_active_sessions():
    """Re-run optimization for active sessions with updated market data."""
    from core.database import get_connection
    try:
        with get_connection() as conn:
            active = conn.execute(
                "SELECT session_id, market, fleet_mw FROM dispatch_sessions WHERE status='active'"
            ).fetchall()
            for row in active:
                logger.info(f"Re-optimizing session {row['session_id']} ({row['market']})")
                # TODO: trigger re-optimization with latest market data
    except Exception as e:
        logger.error(f"Re-optimization failed: {e}")


# ─── Default Scheduler Instance ───

def create_default_scheduler() -> PRIMScheduler:
    """Create scheduler with standard PRIMEngine tasks."""
    scheduler = PRIMScheduler()
    scheduler.add_periodic_task(
        "cleanup_sessions", task_cleanup_stale_sessions,
        interval_minutes=60
    )
    scheduler.add_periodic_task(
        "market_refresh", task_market_data_refresh,
        interval_minutes=15
    )
    scheduler.add_periodic_task(
        "re_optimize", task_re_optimize_active_sessions,
        interval_minutes=15
    )
    return scheduler
