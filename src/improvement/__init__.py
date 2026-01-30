"""Self-improvement system for TWIZZY.

This module handles autonomous code improvement:
- Analyzing usage patterns and failures
- Generating code improvements
- Testing in sandboxed environment
- Deploying with Git tracking
- Automatically committing and pushing to GitHub
"""
from .analyzer import ImprovementAnalyzer
from .generator import ImprovementGenerator
from .scheduler import ImprovementScheduler, ImprovementResult
from .rollback import RollbackManager
from .git_auto_commit import GitAutoCommit, GitCommitResult, auto_commit_improvement

__all__ = [
    "ImprovementAnalyzer",
    "ImprovementGenerator",
    "ImprovementScheduler",
    "RollbackManager",
    "GitAutoCommit",
    "GitCommitResult",
    "auto_commit_improvement",
    "ImprovementResult",
]
