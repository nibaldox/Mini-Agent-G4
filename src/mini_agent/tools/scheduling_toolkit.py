"""Scheduling and timer toolkit for Mini Agent G4"""

import time
import threading
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from agno.tools import tool

try:
    from croniter import croniter
    CRONITER_AVAILABLE = True
except ImportError:
    CRONITER_AVAILABLE = False


@dataclass
class ScheduledTask:
    """Represents a scheduled task or reminder."""
    id: str
    name: str
    description: str
    callback: Optional[Callable] = None
    interval_seconds: Optional[float] = None
    cron_expr: Optional[str] = None
    next_run: Optional[datetime] = None
    is_recurring: bool = False
    alert_message: str = ""


class Scheduler:
    """In-memory scheduler for tasks and alerts."""
    def __init__(self):
        self._tasks: Dict[str, ScheduledTask] = {}
        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def add_task(self, task: ScheduledTask) -> str:
        """Add a task to the scheduler."""
        with self._lock:
            self._tasks[task.id] = task
        return task.id

    def remove_task(self, task_id: str) -> bool:
        """Remove a task from the scheduler."""
        with self._lock:
            if task_id in self._tasks:
                del self._tasks[task_id]
                return True
        return False

    def get_task(self, task_id: str) -> Optional[ScheduledTask]:
        """Get a task by ID."""
        with self._lock:
            return self._tasks.get(task_id)

    def list_tasks(self) -> List[ScheduledTask]:
        """List all scheduled tasks."""
        with self._lock:
            return list(self._tasks.values())

    def start(self):
        """Start the scheduler background thread."""
        if not self._running:
            self._running = True
            self._thread = threading.Thread(target=self._run_loop, daemon=True)
            self._thread.start()

    def _run_loop(self):
        """Background loop to check and execute tasks."""
        while self._running:
            now = datetime.now()
            with self._lock:
                for task in list(self._tasks.values()):
                    if task.next_run and now >= task.next_run:
                        if task.callback:
                            try:
                                task.callback(task)
                            except Exception as e:
                                print(f"Task {task.id} error: {e}")

                        # Calculate next run
                        if task.cron_expr and CRONITER_AVAILABLE:
                            try:
                                cron = croniter(task.cron_expr, now)
                                task.next_run = cron.get_next(datetime)
                            except Exception:
                                self._tasks.pop(task.id, None)
                        elif task.is_recurring and task.interval_seconds:
                            task.next_run = now + timedelta(seconds=task.interval_seconds)
                        else:
                            self._tasks.pop(task.id, None)
            time.sleep(0.5)

    def stop(self):
        """Stop the scheduler."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)


_scheduler = Scheduler()
_scheduler.start()


class SchedulingToolkit:
    """Toolkit for scheduling, timers, and alerts."""

    @tool
    def set_reminder(
        self,
        name: str,
        seconds: float,
        message: str = ""
    ) -> str:
        """Set a one-time reminder that triggers after specified seconds.

        Args:
            name: Name/identifier for this reminder
            seconds: Time in seconds until the reminder triggers
            message: Optional message to display when reminder triggers

        Returns:
            Confirmation with reminder details
        """
        task_id = f"reminder_{name}_{int(time.time())}"
        next_run = datetime.now() + timedelta(seconds=seconds)

        task = ScheduledTask(
            id=task_id,
            name=name,
            description=f"Reminder: {message}" if message else name,
            next_run=next_run,
            alert_message=message or f"Reminder '{name}' triggered!"
        )

        _scheduler.add_task(task)

        return f"Reminder set: '{name}' will trigger in {seconds:.0f} seconds. ID: {task_id}"

    @tool
    def set_recurring_alert(
        self,
        name: str,
        interval_seconds: float,
        message: str = ""
    ) -> str:
        """Set a recurring alert that repeats at the specified interval.

        Args:
            name: Name/identifier for this alert
            interval_seconds: Time in seconds between repetitions
            message: Optional message to display when alert triggers

        Returns:
            Confirmation with alert details
        """
        task_id = f"alert_{name}_{int(time.time())}"

        task = ScheduledTask(
            id=task_id,
            name=name,
            description=f"Recurring alert every {interval_seconds}s: {message}" if message else name,
            next_run=datetime.now() + timedelta(seconds=interval_seconds),
            interval_seconds=interval_seconds,
            is_recurring=True,
            alert_message=message or f"Alert '{name}' triggered!"
        )

        _scheduler.add_task(task)

        return f"Recurring alert set: '{name}' every {interval_seconds:.0f} seconds. ID: {task_id}"

    @tool
    def set_cron_task(
        self,
        name: str,
        cron_expression: str,
        message: str = ""
    ) -> str:
        """Schedule a recurring task using a cron expression.

        Args:
            name: Name/identifier for this task
            cron_expression: Cron expression (e.g. '0 9 * * *' = daily at 9am,
                             '*/5 * * * *' = every 5 minutes,
                             '0 * * * *' = every hour,
                             '30 14 * * 1-5' = weekdays at 2:30pm,
                             '0 9,18 * * *' = 9am and 6pm daily)
            message: Optional message to show when the task fires

        Returns:
            Confirmation with next run time
        """
        if not CRONITER_AVAILABLE:
            return "Error: croniter package not installed. Run: uv add croniter"

        try:
            cron = croniter(cron_expression, datetime.now())
            next_run = cron.get_next(datetime)
        except Exception as e:
            return f"Error: invalid cron expression '{cron_expression}': {e}"

        task_id = f"cron_{name}_{int(time.time())}"
        task = ScheduledTask(
            id=task_id,
            name=name,
            description=f"Cron task: {cron_expression}",
            next_run=next_run,
            cron_expr=cron_expression,
            is_recurring=True,
            alert_message=message or f"Cron task '{name}' fired!"
        )

        _scheduler.add_task(task)

        next_str = next_run.strftime("%Y-%m-%d %H:%M:%S")
        return (f"Cron task set: '{name}' [{cron_expression}] — next run: {next_str}. "
                f"ID: {task_id}")

    @tool
    def list_scheduled_tasks(self) -> str:
        """List all currently scheduled tasks and their next run times.

        Returns:
            List of scheduled tasks with their details
        """
        tasks = _scheduler.list_tasks()

        if not tasks:
            return "No scheduled tasks."

        result = ["Scheduled Tasks:"]
        for i, task in enumerate(tasks, 1):
            next_time = task.next_run.strftime("%Y-%m-%d %H:%M:%S") if task.next_run else "N/A"
            recurring = "Yes" if task.is_recurring else "No"
            result.append(f"{i}. {task.name}")
            result.append(f"   ID: {task.id}")
            result.append(f"   Next run: {next_time}")
            result.append(f"   Recurring: {recurring}")
            result.append(f"   Description: {task.description}")
            result.append("")

        return "\n".join(result)

    @tool
    def cancel_scheduled_task(
        self,
        task_id: str
    ) -> str:
        """Cancel a previously scheduled task.

        Args:
            task_id: The ID of the task to cancel

        Returns:
            Confirmation of cancellation
        """
        if _scheduler.remove_task(task_id):
            return f"Task '{task_id}' cancelled successfully."
        else:
            return f"Task '{task_id}' not found."

    @tool
    def get_next_runs(
        self,
        count: int = 5
    ) -> str:
        """Get the next upcoming scheduled task runs.

        Args:
            count: Number of upcoming tasks to show (default 5)

        Returns:
            List of upcoming tasks sorted by next run time
        """
        tasks = _scheduler.list_tasks()

        if not tasks:
            return "No upcoming scheduled tasks."

        sorted_tasks = sorted(
            [t for t in tasks if t.next_run],
            key=lambda x: x.next_run
        )[:count]

        result = ["Upcoming Tasks:"]
        for i, task in enumerate(sorted_tasks, 1):
            next_time = task.next_run.strftime("%Y-%m-%d %H:%M:%S") if task.next_run else "N/A"
            result.append(f"{i}. {task.name} - {next_time}")

        return "\n".join(result)

    @tool
    def calculate_time_difference(
        self,
        datetime1: str,
        datetime2: str,
        output_unit: str = "auto"
    ) -> str:
        """Calculate the time difference between two datetime values.

        Args:
            datetime1: First datetime in format 'YYYY-MM-DD HH:MM:SS' or similar
            datetime2: Second datetime in format 'YYYY-MM-DD HH:MM:SS' or similar
            output_unit: Output unit - 'auto', 'seconds', 'minutes', 'hours', 'days'

        Returns:
            Time difference in specified units
        """
        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%d",
            "%d/%m/%Y %H:%M:%S",
            "%d/%m/%Y %H:%M",
            "%m/%d/%Y %H:%M:%S",
        ]

        dt1, dt2 = None, None

        for fmt in formats:
            try:
                dt1 = datetime.strptime(datetime1, fmt)
                dt2 = datetime.strptime(datetime2, fmt)
                break
            except ValueError:
                continue

        if dt1 is None or dt2 is None:
            return f"Error: Could not parse datetime strings. Use formats like '2024-01-15 14:30:00' or '15/01/2024 14:30'"

        delta = abs(dt2 - dt1)
        total_seconds = delta.total_seconds()

        if output_unit == "seconds":
            result = total_seconds
            unit = "seconds"
        elif output_unit == "minutes":
            result = total_seconds / 60
            unit = "minutes"
        elif output_unit == "hours":
            result = total_seconds / 3600
            unit = "hours"
        elif output_unit == "days":
            result = total_seconds / 86400
            unit = "days"
        else:
            if total_seconds < 60:
                result = total_seconds
                unit = "seconds"
            elif total_seconds < 3600:
                result = total_seconds / 60
                unit = "minutes"
            elif total_seconds < 86400:
                result = total_seconds / 3600
                unit = "hours"
            else:
                result = total_seconds / 86400
                unit = "days"

        return f"Time difference: {result:.2f} {unit}"

    @tool
    def add_to_datetime(
        self,
        datetime_str: str,
        seconds: float = 0,
        minutes: float = 0,
        hours: float = 0,
        days: float = 0
    ) -> str:
        """Add time to a datetime value.

        Args:
            datetime_str: Base datetime in format 'YYYY-MM-DD HH:MM:SS' or similar
            seconds: Seconds to add
            minutes: Minutes to add
            hours: Hours to add
            days: Days to add

        Returns:
            New datetime after adding the specified time
        """
        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%d",
        ]

        dt = None
        for fmt in formats:
            try:
                dt = datetime.strptime(datetime_str, fmt)
                break
            except ValueError:
                continue

        if dt is None:
            return f"Error: Could not parse datetime string. Use formats like '2024-01-15 14:30:00'"

        delta = timedelta(seconds=seconds, minutes=minutes, hours=hours, days=days)
        new_dt = dt + delta

        return f"Result: {new_dt.strftime('%Y-%m-%d %H:%M:%S')}"