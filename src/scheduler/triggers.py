"""
Custom trigger types for the scheduler.
"""

from datetime import datetime, timedelta
from typing import Optional
from abc import ABC, abstractmethod


class Trigger(ABC):
    """Base class for triggers."""
    
    @abstractmethod
    def get_next_run_time(self, after: datetime) -> Optional[datetime]:
        """Get the next run time after the given datetime."""
        pass


class CronTrigger(Trigger):
    """Cron-based trigger."""
    
    def __init__(self, expression: str):
        self.expression = expression
        
        try:
            from croniter import croniter
            self._cron = croniter(expression)
        except ImportError:
            self._cron = None
            
    def get_next_run_time(self, after: datetime) -> Optional[datetime]:
        if self._cron:
            self._cron.set_current(after)
            return self._cron.get_next(datetime)
        return None


class IntervalTrigger(Trigger):
    """Fixed interval trigger."""
    
    def __init__(self, seconds: int = 0, minutes: int = 0, hours: int = 0, days: int = 0):
        self.interval = timedelta(
            seconds=seconds,
            minutes=minutes,
            hours=hours,
            days=days
        )
        
    def get_next_run_time(self, after: datetime) -> Optional[datetime]:
        return after + self.interval


class DateTrigger(Trigger):
    """One-time date trigger."""
    
    def __init__(self, run_date: datetime):
        self.run_date = run_date
        self._triggered = False
        
    def get_next_run_time(self, after: datetime) -> Optional[datetime]:
        if self._triggered or after > self.run_date:
            return None
        self._triggered = True
        return self.run_date
