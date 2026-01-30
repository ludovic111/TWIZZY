"""
TWIZZY Canvas - Visual workspace for agent outputs.

Inspired by OpenClaw's A2UI Canvas for visual interactions.
"""

from .canvas import Canvas, CanvasElement, CanvasType, get_canvas
from .renderer import CanvasRenderer

__all__ = ["Canvas", "CanvasElement", "CanvasType", "get_canvas", "CanvasRenderer"]
