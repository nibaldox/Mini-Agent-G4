"""Proactive memory loop — periodic nudges and context summarization."""

import asyncio
import threading
import time
from datetime import datetime, timedelta
from typing import Optional, Callable

try:
    from croniter import croniter
    CRONITER_AVAILABLE = True
except ImportError:
    CRONITER_AVAILABLE = False


class ProactiveMemoryLoop:
    """
    Background loop that periodically:
    1. Summarizes recent conversation context → memory
    2. Sends proactive nudges to the user via callback
    3. Prunes old/stale memories
    """

    def __init__(
        self,
        memory_summarizer: Optional[Callable] = None,
        nudge_callback: Optional[Callable[[str], None]] = None,
    ):
        """
        Args:
            memory_summarizer: async fn(session_id) -> summary string
            nudge_callback: fn(message) -> sends nudge to user
        """
        self._summarizer = memory_summarizer
        self._nudge = nudge_callback
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._last_summary_time: Optional[datetime] = None
        self._summary_interval_hours = 2  # summarize every 2h of conversation
        self._nudge_schedule: list[tuple[str, str]] = []  # (cron_expr, message)

    def add_nudge(self, cron_expr: str, message: str) -> bool:
        """Add a scheduled nudge (e.g. '0 9 * * *' -> 'Good morning stand-up reminder')."""
        if not CRONITER_AVAILABLE:
            return False
        try:
            croniter(cron_expr, datetime.now())
            self._nudge_schedule.append((cron_expr, message))
            return True
        except Exception:
            return False

    def start(self) -> None:
        """Start the background loop."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop the loop."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)

    def _run_loop(self) -> None:
        """Main loop — checks nudges every minute."""
        while self._running:
            now = datetime.now()

            # Check scheduled nudges
            if CRONITER_AVAILABLE:
                for cron_expr, message in self._nudge_schedule:
                    try:
                        cron = croniter(cron_expr, now)
                        prev = cron.get_prev(datetime)
                        # If previous run is within the last 2 minutes, fire the nudge
                        if (now - prev).total_seconds() < 120 and self._nudge:
                            self._nudge(message)
                    except Exception:
                        pass

            # Memory summarization (best-effort every interval)
            if (
                self._summarizer
                and self._last_summary_time
                and (now - self._last_summary_time).total_seconds()
                >= self._summary_interval_hours * 3600
            ):
                asyncio.run(self._do_summarize())
                self._last_summary_time = now
            elif not self._last_summary_time:
                self._last_summary_time = now

            time.sleep(60)  # check every minute

    async def _do_summarize(self) -> None:
        """Run memory summarization."""
        if not self._summarizer:
            return
        try:
            summary = await self._summarizer()
            if summary and self._nudge:
                self._nudge(f"[Memory update] {summary}")
        except Exception as e:
            print(f"[ProactiveMemory] summarization error: {e}")

    def set_interval(self, hours: int) -> None:
        """Set how often to summarize (in hours)."""
        self._summary_interval_hours = hours


# ─── Module-level singleton ────────────────────────────────────────────────────

_proactive_loop: Optional[ProactiveMemoryLoop] = None


def get_proactive_loop() -> ProactiveMemoryLoop:
    global _proactive_loop
    if _proactive_loop is None:
        _proactive_loop = ProactiveMemoryLoop()
    return _proactive_loop
