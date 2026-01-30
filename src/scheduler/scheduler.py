"""
Task scheduler for automated agent actions.

Allows scheduling recurring or one-time tasks that the agent will execute.
"""

import asyncio
import logging
import uuid
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from croniter import croniter

try:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.cron import CronTrigger as APCronTrigger
    from apscheduler.triggers.interval import IntervalTrigger as APIntervalTrigger
    from apscheduler.triggers.date import DateTrigger as APDateTrigger
    APSCHEDULER_AVAILABLE = True
except ImportError:
    APSCHEDULER_AVAILABLE = False
    AsyncIOScheduler = None

logger = logging.getLogger(__name__)


class TaskType(Enum):
    """Types of scheduled tasks."""
    CRON = "cron"           # Cron expression
    INTERVAL = "interval"   # Fixed interval
    ONCE = "once"           # One-time execution
    WAKEUP = "wakeup"       # System wakeup task


@dataclass
class ScheduledTask:
    """A scheduled task."""
    id: str
    name: str
    task_type: TaskType
    trigger: Any  # Cron string, timedelta, or datetime
    action: str   # What to do (message/command)
    enabled: bool = True
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    run_count: int = 0
    max_runs: Optional[int] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)


class TaskScheduler:
    """
    Task scheduler for TWIZZY.
    
    Supports:
    - Cron expressions (e.g., "0 9 * * *" for 9am daily)
    - Fixed intervals (e.g., every 30 minutes)
    - One-time scheduled tasks
    - System wakeups
    """
    
    def __init__(self):
        self._scheduler: Optional[AsyncIOScheduler] = None
        self._tasks: Dict[str, ScheduledTask] = {}
        self._callbacks: List[Callable[[ScheduledTask], Any]] = []
        self._running = False
        
        if APSCHEDULER_AVAILABLE:
            self._scheduler = AsyncIOScheduler()
        else:
            logger.warning("apscheduler not installed. Run: pip install apscheduler")
            
    async def start(self):
        """Start the scheduler."""
        if not self._scheduler:
            logger.error("Scheduler not available")
            return False
            
        self._scheduler.start()
        self._running = True
        logger.info("Task scheduler started")
        return True
        
    async def stop(self):
        """Stop the scheduler."""
        if self._scheduler:
            self._scheduler.shutdown()
        self._running = False
        logger.info("Task scheduler stopped")
        
    def add_callback(self, callback: Callable[[ScheduledTask], Any]):
        """Add a callback to run when tasks execute."""
        self._callbacks.append(callback)
        
    def schedule_cron(self, name: str, cron_expression: str, action: str, 
                      max_runs: Optional[int] = None) -> str:
        """
        Schedule a task using cron expression.
        
        Args:
            name: Task name
            cron_expression: Cron string (e.g., "0 9 * * 1-5" for 9am weekdays)
            action: What to execute
            max_runs: Maximum number of executions
            
        Returns:
            Task ID
        """
        task_id = str(uuid.uuid4())[:8]
        
        task = ScheduledTask(
            id=task_id,
            name=name,
            task_type=TaskType.CRON,
            trigger=cron_expression,
            action=action,
            max_runs=max_runs
        )
        
        if self._scheduler:
            # Parse cron and create APScheduler job
            try:
                job = self._scheduler.add_job(
                    func=self._execute_task,
                    trigger=APCronTrigger.from_crontab(cron_expression),
                    args=[task_id],
                    id=task_id,
                    replace_existing=True
                )
                task.next_run = job.next_run_time
            except Exception as e:
                logger.error(f"Failed to schedule cron task: {e}")
                return ""
                
        self._tasks[task_id] = task
        logger.info(f"Scheduled cron task '{name}': {cron_expression}")
        return task_id
        
    def schedule_interval(self, name: str, minutes: int, action: str,
                          max_runs: Optional[int] = None) -> str:
        """
        Schedule a task to run at fixed intervals.
        
        Args:
            name: Task name
            minutes: Interval in minutes
            action: What to execute
            max_runs: Maximum number of executions
            
        Returns:
            Task ID
        """
        task_id = str(uuid.uuid4())[:8]
        
        task = ScheduledTask(
            id=task_id,
            name=name,
            task_type=TaskType.INTERVAL,
            trigger=timedelta(minutes=minutes),
            action=action,
            max_runs=max_runs
        )
        
        if self._scheduler:
            try:
                job = self._scheduler.add_job(
                    func=self._execute_task,
                    trigger=APIntervalTrigger(minutes=minutes),
                    args=[task_id],
                    id=task_id,
                    replace_existing=True
                )
                task.next_run = job.next_run_time
            except Exception as e:
                logger.error(f"Failed to schedule interval task: {e}")
                return ""
                
        self._tasks[task_id] = task
        logger.info(f"Scheduled interval task '{name}': every {minutes} minutes")
        return task_id
        
    def schedule_once(self, name: str, run_at: datetime, action: str) -> str:
        """
        Schedule a one-time task.
        
        Args:
            name: Task name
            run_at: When to run
            action: What to execute
            
        Returns:
            Task ID
        """
        task_id = str(uuid.uuid4())[:8]
        
        task = ScheduledTask(
            id=task_id,
            name=name,
            task_type=TaskType.ONCE,
            trigger=run_at,
            action=action
        )
        
        if self._scheduler:
            try:
                job = self._scheduler.add_job(
                    func=self._execute_task,
                    trigger=APDateTrigger(run_date=run_at),
                    args=[task_id],
                    id=task_id,
                    replace_existing=True
                )
                task.next_run = job.next_run_time
            except Exception as e:
                logger.error(f"Failed to schedule one-time task: {e}")
                return ""
                
        self._tasks[task_id] = task
        logger.info(f"Scheduled one-time task '{name}' at {run_at}")
        return task_id
        
    async def _execute_task(self, task_id: str):
        """Execute a scheduled task."""
        task = self._tasks.get(task_id)
        if not task or not task.enabled:
            return
            
        logger.info(f"Executing scheduled task: {task.name}")
        
        task.last_run = datetime.now()
        task.run_count += 1
        
        # Check max runs
        if task.max_runs and task.run_count >= task.max_runs:
            task.enabled = False
            if self._scheduler:
                self._scheduler.remove_job(task_id)
                
        # Notify callbacks
        for callback in self._callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    asyncio.create_task(callback(task))
                else:
                    callback(task)
            except Exception as e:
                logger.error(f"Task callback error: {e}")
                
    def cancel_task(self, task_id: str) -> bool:
        """Cancel a scheduled task."""
        if task_id not in self._tasks:
            return False
            
        if self._scheduler:
            try:
                self._scheduler.remove_job(task_id)
            except:
                pass
                
        del self._tasks[task_id]
        logger.info(f"Cancelled task: {task_id}")
        return True
        
    def pause_task(self, task_id: str) -> bool:
        """Pause a task temporarily."""
        if task_id not in self._tasks:
            return False
            
        self._tasks[task_id].enabled = False
        
        if self._scheduler:
            self._scheduler.pause_job(task_id)
            
        return True
        
    def resume_task(self, task_id: str) -> bool:
        """Resume a paused task."""
        if task_id not in self._tasks:
            return False
            
        self._tasks[task_id].enabled = True
        
        if self._scheduler:
            self._scheduler.resume_job(task_id)
            
        return True
        
    def get_task(self, task_id: str) -> Optional[ScheduledTask]:
        """Get a task by ID."""
        return self._tasks.get(task_id)
        
    def list_tasks(self) -> List[ScheduledTask]:
        """List all tasks."""
        return list(self._tasks.values())
        
    def get_upcoming(self, count: int = 10) -> List[ScheduledTask]:
        """Get upcoming scheduled tasks."""
        enabled_tasks = [t for t in self._tasks.values() if t.enabled]
        enabled_tasks.sort(key=lambda t: t.next_run or datetime.max)
        return enabled_tasks[:count]
        
    def get_stats(self) -> Dict[str, Any]:
        """Get scheduler statistics."""
        total = len(self._tasks)
        enabled = sum(1 for t in self._tasks.values() if t.enabled)
        completed = sum(1 for t in self._tasks.values() if t.max_runs and t.run_count >= t.max_runs)
        
        return {
            "total_tasks": total,
            "enabled": enabled,
            "paused": total - enabled,
            "completed": completed,
            "running": self._running
        }


# Global instance
_scheduler: Optional[TaskScheduler] = None


def get_scheduler() -> TaskScheduler:
    """Get or create global scheduler."""
    global _scheduler
    if _scheduler is None:
        _scheduler = TaskScheduler()
    return _scheduler
