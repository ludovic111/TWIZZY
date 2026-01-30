"""
TWIZZY Browser Automation - Control Chrome/Chromium for web tasks.

Inspired by OpenClaw's browser control capabilities.
"""

from .controller import BrowserController, BrowserAction, get_browser_controller
from .snapshot import PageSnapshot

__all__ = ["BrowserController", "BrowserAction", "get_browser_controller", "PageSnapshot"]
