"""
TWIZZY Doctor - Diagnostic and repair tool.

Inspired by OpenClaw's `openclaw doctor` for system health checks.
"""

from .doctor import Doctor, CheckResult, CheckSeverity, get_doctor
from .checks import Check, register_check

__all__ = ["Doctor", "CheckResult", "CheckSeverity", "get_doctor", "Check", "register_check"]
