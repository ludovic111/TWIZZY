"""Improvement scheduler - Runs improvements during idle time.

This module schedules and runs the self-improvement process:
- Detects when the agent is idle
- Analyzes for improvement opportunities
- Generates and tests improvements
- Deploys improvements with Git tracking
"""
import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable

from .analyzer import ImprovementAnalyzer, ImprovementOpportunity
from .generator import ImprovementGenerator, Improvement
from .rollback import RollbackManager

logger = logging.getLogger(__name__)


@dataclass
class ImprovementResult:
    """Result of an improvement attempt."""

    improvement_id: str
    success: bool
    message: str
    changes_applied: int
    timestamp: datetime


class ImprovementScheduler:
    """Schedules and runs self-improvement during idle time."""

    def __init__(
        self,
        kimi_client,
        project_root: Path,
        idle_threshold_seconds: int = 300,  # 5 minutes
        max_improvements_per_session: int = 3,
    ):
        """Initialize the scheduler.

        Args:
            kimi_client: KimiClient for generating improvements
            project_root: Root directory of the project
            idle_threshold_seconds: How long before considering agent idle
            max_improvements_per_session: Max improvements to apply in one session
        """
        self.kimi_client = kimi_client
        self.project_root = project_root
        self.idle_threshold = timedelta(seconds=idle_threshold_seconds)
        self.max_improvements = max_improvements_per_session

        self.analyzer = ImprovementAnalyzer()
        self.generator = ImprovementGenerator(kimi_client, project_root)
        self.rollback = RollbackManager(project_root)

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

        try:
            # Generate improvement
            improvement = await self.generator.generate(opportunity.to_dict())
            if not improvement:
                return ImprovementResult(
                    improvement_id=opportunity.id,
                    success=False,
                    message="Failed to generate improvement",
                    changes_applied=0,
                    timestamp=datetime.now(),
                )

            # Validate improvement
            valid, errors = self.generator.validate_improvement(improvement)
            if not valid:
                return ImprovementResult(
                    improvement_id=opportunity.id,
                    success=False,
                    message=f"Validation failed: {'; '.join(errors)}",
                    changes_applied=0,
                    timestamp=datetime.now(),
                )

            # Create snapshot before applying
            snapshot_id = await self.rollback.create_snapshot(
                f"Before improvement: {improvement.title}"
            )

            # Apply changes
            applied = 0
            for change in improvement.changes:
                try:
                    if change.change_type == "create":
                        change.file_path.parent.mkdir(parents=True, exist_ok=True)
                        change.file_path.write_text(change.new_content)
                    elif change.change_type == "modify":
                        change.file_path.write_text(change.new_content)
                    applied += 1
                except Exception as e:
                    logger.error(f"Failed to apply change to {change.file_path}: {e}")
                    # Rollback on error
                    await self.rollback.rollback_to(snapshot_id)
                    return ImprovementResult(
                        improvement_id=opportunity.id,
                        success=False,
                        message=f"Failed to apply changes: {e}",
                        changes_applied=0,
                        timestamp=datetime.now(),
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
                        timestamp=datetime.now(),
                    )

            # Commit the improvement
            await self.rollback.commit_improvement(improvement)

            return ImprovementResult(
                improvement_id=opportunity.id,
                success=True,
                message=f"Applied: {improvement.title}",
                changes_applied=applied,
                timestamp=datetime.now(),
            )

        except Exception as e:
            logger.error(f"Error processing improvement: {e}")
            return ImprovementResult(
                improvement_id=opportunity.id,
                success=False,
                message=str(e),
                changes_applied=0,
                timestamp=datetime.now(),
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
