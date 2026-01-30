"""Improvement scheduler - Runs improvements during idle time.

This module schedules and runs the self-improvement process:
- Detects when the agent is idle
- Analyzes for improvement opportunities
- Generates and tests improvements
- Deploys improvements with Git tracking
- Automatically commits and pushes to GitHub
"""
import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable

from .analyzer import ImprovementAnalyzer, ImprovementOpportunity
from .generator import ImprovementGenerator, Improvement
from .rollback import RollbackManager
from .git_auto_commit import GitAutoCommit, GitCommitResult

logger = logging.getLogger(__name__)


@dataclass
class ImprovementResult:
    """Result of an improvement attempt."""

    improvement_id: str
    success: bool
    message: str
    changes_applied: int
    timestamp: datetime
    git_result: GitCommitResult | None = field(default=None)
    commit_hash: str | None = field(default=None)
    pushed_to_github: bool = field(default=False)


class ImprovementScheduler:
    """Schedules and runs self-improvement during idle time."""

    def __init__(
        self,
        kimi_client,
        project_root: Path,
        idle_threshold_seconds: int = 300,  # 5 minutes
        max_improvements_per_session: int = 3,
        auto_push_to_github: bool = True,
    ):
        """Initialize the scheduler.

        Args:
            kimi_client: KimiClient for generating improvements
            project_root: Root directory of the project
            idle_threshold_seconds: How long before considering agent idle
            max_improvements_per_session: Max improvements to apply in one session
            auto_push_to_github: Whether to automatically push to GitHub
        """
        self.kimi_client = kimi_client
        self.project_root = project_root
        self.idle_threshold = timedelta(seconds=idle_threshold_seconds)
        self.max_improvements = max_improvements_per_session
        self.auto_push_to_github = auto_push_to_github

        self.analyzer = ImprovementAnalyzer()
        self.generator = ImprovementGenerator(kimi_client, project_root)
        self.rollback = RollbackManager(project_root)
        self.git_committer = GitAutoCommit(project_root)

        self._last_activity = datetime.now()
        self._running = False
        self._task: asyncio.Task | None = None
        self._improvement_history: list[ImprovementResult] = []
        self._on_improvement_callback: Callable[[ImprovementResult], None] | None = None

    def record_activity(self):
        """Record user activity to reset idle timer."""
        self._last_activity = datetime.now()

    def is_idle(self) -> bool:
        """Check if the agent is considered idle."""
        return datetime.now() - self._last_activity > self.idle_threshold

    def on_improvement(self, callback: Callable[[ImprovementResult], None]):
        """Register a callback for when improvements are made."""
        self._on_improvement_callback = callback

    def set_auto_push(self, enabled: bool):
        """Enable or disable automatic GitHub push."""
        self.auto_push_to_github = enabled
        self.git_committer.set_enabled(enabled)
        logger.info(f"Auto-push to GitHub {'enabled' if enabled else 'disabled'}")

    async def start(self):
        """Start the improvement scheduler."""
        if self._running:
            return

        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("Improvement scheduler started")

    async def stop(self):
        """Stop the improvement scheduler."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Improvement scheduler stopped")

    async def _run_loop(self):
        """Main improvement loop."""
        while self._running:
            try:
                # Check every minute
                await asyncio.sleep(60)

                if not self.is_idle():
                    continue

                logger.info("Agent is idle, checking for improvement opportunities...")

                # Analyze for opportunities
                opportunities = self.analyzer.analyze()
                if not opportunities:
                    logger.debug("No improvement opportunities found")
                    continue

                # Process top opportunities
                applied = 0
                for opp in opportunities[:self.max_improvements]:
                    if not self.is_idle():  # Stop if user becomes active
                        break

                    result = await self._process_opportunity(opp)
                    self._improvement_history.append(result)

                    if self._on_improvement_callback:
                        self._on_improvement_callback(result)

                    if result.success:
                        applied += 1

                if applied > 0:
                    logger.info(f"Applied {applied} improvements during idle time")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in improvement loop: {e}")

    async def _process_opportunity(self, opportunity: ImprovementOpportunity) -> ImprovementResult:
        """Process a single improvement opportunity.

        Args:
            opportunity: The opportunity to process

        Returns:
            ImprovementResult with success status
        """
        logger.info(f"Processing improvement: {opportunity.description}")
        timestamp = datetime.now()

        try:
            # Generate improvement
            improvement = await self.generator.generate(opportunity.to_dict())
            if not improvement:
                return ImprovementResult(
                    improvement_id=opportunity.id,
                    success=False,
                    message="Failed to generate improvement",
                    changes_applied=0,
                    timestamp=timestamp,
                )

            # Validate improvement
            valid, errors = self.generator.validate_improvement(improvement)
            if not valid:
                return ImprovementResult(
                    improvement_id=opportunity.id,
                    success=False,
                    message=f"Validation failed: {'; '.join(errors)}",
                    changes_applied=0,
                    timestamp=timestamp,
                )

            # Create snapshot before applying
            snapshot_id = await self.rollback.create_snapshot(
                f"Before improvement: {improvement.title}"
            )

            # Apply changes
            applied = 0
            files_changed = []
            for change in improvement.changes:
                try:
                    if change.change_type == "create":
                        change.file_path.parent.mkdir(parents=True, exist_ok=True)
                        change.file_path.write_text(change.new_content)
                    elif change.change_type == "modify":
                        change.file_path.write_text(change.new_content)
                    applied += 1
                    files_changed.append(str(change.file_path.relative_to(self.project_root)))
                except Exception as e:
                    logger.error(f"Failed to apply change to {change.file_path}: {e}")
                    # Rollback on error
                    await self.rollback.rollback_to(snapshot_id)
                    return ImprovementResult(
                        improvement_id=opportunity.id,
                        success=False,
                        message=f"Failed to apply changes: {e}",
                        changes_applied=0,
                        timestamp=timestamp,
                    )

            # Run tests if provided
            if improvement.test_code:
                test_passed = await self._run_tests(improvement.test_code)
                if not test_passed:
                    logger.warning("Tests failed, rolling back improvement")
                    await self.rollback.rollback_to(snapshot_id)
                    return ImprovementResult(
                        improvement_id=opportunity.id,
                        success=False,
                        message="Tests failed after applying changes",
                        changes_applied=0,
                        timestamp=timestamp,
                    )

            # Commit the improvement locally
            await self.rollback.commit_improvement(improvement)

            # Auto-commit and push to GitHub
            git_result = None
            commit_hash = None
            pushed = False
            
            if self.auto_push_to_github:
                logger.info("Auto-committing and pushing to GitHub...")
                git_result = await self.git_committer.commit_and_push_improvement(
                    title=improvement.title,
                    description=improvement.description,
                    improvement_id=improvement.id,
                    files_changed=files_changed,
                )
                commit_hash = git_result.commit_hash
                pushed = git_result.pushed
                
                if git_result.success:
                    logger.info(f"🚀 Improvement committed and pushed: {git_result.message}")
                else:
                    logger.warning(f"Git operation issue: {git_result.message}")

            return ImprovementResult(
                improvement_id=opportunity.id,
                success=True,
                message=f"Applied: {improvement.title}",
                changes_applied=applied,
                timestamp=timestamp,
                git_result=git_result,
                commit_hash=commit_hash,
                pushed_to_github=pushed,
            )

        except Exception as e:
            logger.error(f"Error processing improvement: {e}")
            return ImprovementResult(
                improvement_id=opportunity.id,
                success=False,
                message=str(e),
                changes_applied=0,
                timestamp=timestamp,
            )

    async def _run_tests(self, test_code: str) -> bool:
        """Run test code in a sandbox.

        Args:
            test_code: pytest code to run

        Returns:
            True if tests passed
        """
        # Write test file
        test_file = self.project_root / "tests" / "_auto_test.py"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text(test_code)

        try:
            # Run pytest
            process = await asyncio.create_subprocess_exec(
                "python", "-m", "pytest", str(test_file), "-v",
                cwd=str(self.project_root),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()

            success = process.returncode == 0
            if not success:
                logger.warning(f"Test output: {stdout.decode()}")
                logger.warning(f"Test errors: {stderr.decode()}")

            return success

        finally:
            # Cleanup test file
            if test_file.exists():
                test_file.unlink()

    def get_history(self) -> list[ImprovementResult]:
        """Get improvement history."""
        return self._improvement_history.copy()

    async def force_improvement(self) -> ImprovementResult | None:
        """Force an improvement run regardless of idle status.

        Returns:
            ImprovementResult if an improvement was made, None otherwise
        """
        opportunities = self.analyzer.analyze()
        if not opportunities:
            return None

        return await self._process_opportunity(opportunities[0])

    async def improve_now(self, focus: str | None = None) -> dict:
        """Trigger improvement immediately (for web API).

        Args:
            focus: Optional area to focus improvement on

        Returns:
            Dict with success status and details
        """
        # Rate limiting - prevent too frequent improvements
        if self._improvement_history:
            last = self._improvement_history[-1]
            cooldown = timedelta(minutes=5)
            if datetime.now() - last.timestamp < cooldown:
                remaining = cooldown - (datetime.now() - last.timestamp)
                return {
                    "success": False,
                    "error": f"Rate limited. Try again in {int(remaining.total_seconds())} seconds."
                }

        # Find opportunities (with optional focus)
        opportunities = self.analyzer.analyze()
        if focus:
            # Filter by focus area if provided
            opportunities = [
                o for o in opportunities
                if focus.lower() in o.description.lower()
                   or focus.lower() in o.type.value.lower()
            ]

        if not opportunities:
            return {
                "success": False,
                "error": "No improvement opportunities found" + (f" for '{focus}'" if focus else "")
            }

        # Process the top opportunity
        result = await self._process_opportunity(opportunities[0])
        self._improvement_history.append(result)

        if self._on_improvement_callback:
            self._on_improvement_callback(result)

        if result.success:
            response = {
                "success": True,
                "improvement": result.message,
                "improvement_id": result.improvement_id,
                "files_changed": result.changes_applied,
                "commit_hash": result.commit_hash,
                "pushed_to_github": result.pushed_to_github,
            }
            
            if result.git_result:
                response["git_message"] = result.git_result.message
                
            return response
        else:
            return {
                "success": False,
                "error": result.message
            }

    async def commit_manual_changes(self, message: str, description: str = "") -> dict:
        """Commit and push manual changes to GitHub.
        
        Args:
            message: Commit message
            description: Extended description
            
        Returns:
            Dict with success status
        """
        result = await self.git_committer.commit_and_push_manual_changes(message, description)
        
        return {
            "success": result.success,
            "message": result.message,
            "commit_hash": result.commit_hash,
            "pushed": result.pushed,
            "files_changed": result.files_changed,
            "error": result.error,
        }

    async def get_git_status(self) -> dict:
        """Get current git status."""
        is_repo = await self.git_committer.is_git_repo()
        has_remote = await self.git_committer.has_remote() if is_repo else False
        remote_url = await self.git_committer.get_remote_url() if has_remote else None
        has_changes = await self.git_committer.has_changes_to_commit() if is_repo else False
        changed_files = await self.git_committer.get_changed_files() if has_changes else []
        history = await self.git_committer.get_commit_history(5) if is_repo else []
        
        return {
            "is_git_repo": is_repo,
            "has_remote": has_remote,
            "remote_url": remote_url,
            "has_uncommitted_changes": has_changes,
            "changed_files": changed_files,
            "auto_push_enabled": self.auto_push_to_github,
            "recent_commits": history,
        }


# Global scheduler instance
_scheduler: ImprovementScheduler | None = None


def get_scheduler(agent=None) -> ImprovementScheduler:
    """Get the global scheduler instance.

    Args:
        agent: Optional agent to initialize scheduler with

    Returns:
        ImprovementScheduler instance
    """
    global _scheduler
    if _scheduler is None and agent is not None:
        from pathlib import Path
        project_root = Path(__file__).parent.parent.parent
        _scheduler = ImprovementScheduler(
            kimi_client=agent.kimi_client,
            project_root=project_root,
            idle_threshold_seconds=300,
            max_improvements_per_session=3,
            auto_push_to_github=True,
        )
    return _scheduler
