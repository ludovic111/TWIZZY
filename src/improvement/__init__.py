"""Self-improvement system for TWIZZY.

This module handles autonomous code improvement:
- Analyzing usage patterns and failures
- Generating code improvements
- Testing in sandboxed environment
- Deploying with Git tracking
- Rolling back on errors
"""
from .analyzer import ImprovementAnalyzer
from .generator import ImprovementGenerator
from .scheduler import ImprovementScheduler
from .rollback import RollbackManager

__all__ = [
    "ImprovementAnalyzer",
    "ImprovementGenerator",
    "ImprovementScheduler",
    "RollbackManager",
]
