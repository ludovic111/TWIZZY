"""Docker sandbox for testing improvements.

This module provides a safe environment to test generated code
before deploying it to the main agent.
"""
import asyncio
import logging
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class SandboxResult:
    """Result from running code in sandbox."""

    success: bool
    output: str
    error: str | None
    exit_code: int
    duration_ms: int


class DockerSandbox:
    """Docker-based sandbox for testing improvements."""

    DOCKERFILE = '''FROM python:3.11-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir pytest httpx pydantic

# Copy test code
COPY . /app/

# Run tests
CMD ["python", "-m", "pytest", "-v", "--tb=short"]
'''

    def __init__(self, project_root: Path):
        """Initialize the sandbox.

        Args:
            project_root: Root directory of the project
        """
        self.project_root = project_root
        self._container_name = "twizzy-sandbox"

    async def is_docker_available(self) -> bool:
        """Check if Docker is available."""
        try:
            process = await asyncio.create_subprocess_exec(
                "docker", "version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await process.communicate()
            return process.returncode == 0
        except FileNotFoundError:
            return False

    async def run_tests(
        self,
        test_files: dict[str, str],
        source_files: dict[str, str] | None = None,
        timeout: int = 60,
    ) -> SandboxResult:
        """Run tests in a Docker sandbox.

        Args:
            test_files: Dict of filename -> content for test files
            source_files: Optional dict of filename -> content for source files
            timeout: Test timeout in seconds

        Returns:
            SandboxResult with test output
        """
        import time
        start_time = time.time()

        if not await self.is_docker_available():
            logger.warning("Docker not available, falling back to local execution")
            return await self._run_local(test_files, source_files, timeout)

        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Write Dockerfile
            (tmppath / "Dockerfile").write_text(self.DOCKERFILE)

            # Write source files
            if source_files:
                for filename, content in source_files.items():
                    filepath = tmppath / filename
                    filepath.parent.mkdir(parents=True, exist_ok=True)
                    filepath.write_text(content)

            # Write test files
            tests_dir = tmppath / "tests"
            tests_dir.mkdir(exist_ok=True)
            for filename, content in test_files.items():
                (tests_dir / filename).write_text(content)

            # Build Docker image
            build_process = await asyncio.create_subprocess_exec(
                "docker", "build", "-t", self._container_name, ".",
                cwd=str(tmppath),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            build_stdout, build_stderr = await build_process.communicate()

            if build_process.returncode != 0:
                return SandboxResult(
                    success=False,
                    output=build_stdout.decode(),
                    error=f"Build failed: {build_stderr.decode()}",
                    exit_code=build_process.returncode,
                    duration_ms=int((time.time() - start_time) * 1000),
                )

            # Run tests in container
            try:
                run_process = await asyncio.create_subprocess_exec(
                    "docker", "run", "--rm",
                    "--memory=256m",
                    "--cpus=0.5",
                    "--network=none",  # No network access
                    self._container_name,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await asyncio.wait_for(
                    run_process.communicate(),
                    timeout=timeout
                )

                return SandboxResult(
                    success=run_process.returncode == 0,
                    output=stdout.decode(),
                    error=stderr.decode() if stderr else None,
                    exit_code=run_process.returncode,
                    duration_ms=int((time.time() - start_time) * 1000),
                )

            except asyncio.TimeoutError:
                # Kill container on timeout
                await asyncio.create_subprocess_exec(
                    "docker", "kill", self._container_name
                )
                return SandboxResult(
                    success=False,
                    output="",
                    error=f"Test timed out after {timeout} seconds",
                    exit_code=-1,
                    duration_ms=timeout * 1000,
                )

    async def _run_local(
        self,
        test_files: dict[str, str],
        source_files: dict[str, str] | None,
        timeout: int,
    ) -> SandboxResult:
        """Fallback: run tests locally without Docker."""
        import time
        start_time = time.time()

        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Write source files
            if source_files:
                for filename, content in source_files.items():
                    filepath = tmppath / filename
                    filepath.parent.mkdir(parents=True, exist_ok=True)
                    filepath.write_text(content)

            # Write test files
            for filename, content in test_files.items():
                filepath = tmppath / filename
                filepath.parent.mkdir(parents=True, exist_ok=True)
                filepath.write_text(content)

            try:
                process = await asyncio.create_subprocess_exec(
                    "python", "-m", "pytest", "-v", "--tb=short",
                    cwd=str(tmppath),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )

                return SandboxResult(
                    success=process.returncode == 0,
                    output=stdout.decode(),
                    error=stderr.decode() if stderr else None,
                    exit_code=process.returncode,
                    duration_ms=int((time.time() - start_time) * 1000),
                )

            except asyncio.TimeoutError:
                return SandboxResult(
                    success=False,
                    output="",
                    error=f"Test timed out after {timeout} seconds",
                    exit_code=-1,
                    duration_ms=timeout * 1000,
                )

    async def cleanup(self):
        """Clean up Docker resources."""
        # Remove sandbox image
        await asyncio.create_subprocess_exec(
            "docker", "rmi", "-f", self._container_name,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
