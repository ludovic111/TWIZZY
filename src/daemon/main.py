#!/usr/bin/env python3
"""TWIZZY daemon entry point.

This is the main process that runs as a background service via launchd.
It initializes the agent and IPC server, then runs until stopped.
"""
import asyncio
import logging
import os
import signal
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.core.agent import create_agent, TwizzyAgent
from src.core.ipc import start_server, IPCServer
from src.core.config import TWIZZY_HOME
from src.improvement import ImprovementScheduler

# Configure logging
LOG_DIR = TWIZZY_HOME / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.DEBUG if os.environ.get("TWIZZY_DEBUG") else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "daemon.log"),
        logging.StreamHandler(),
    ]
)

logger = logging.getLogger(__name__)


class TwizzyDaemon:
    """Main daemon class that manages the agent lifecycle."""

    def __init__(self):
        self.agent: TwizzyAgent | None = None
        self.server: IPCServer | None = None
        self.improvement_scheduler: ImprovementScheduler | None = None
        self._shutdown_event = asyncio.Event()

    async def start(self):
        """Start the daemon."""
        logger.info("Starting TWIZZY daemon...")

        # Create and start agent
        try:
            self.agent = await create_agent()
        except ValueError as e:
            logger.error(f"Failed to create agent: {e}")
            logger.error("Please set KIMI_API_KEY environment variable or store it in Keychain")
            sys.exit(1)

        # Start IPC server
        self.server = await start_server(agent=self.agent)

        # Start self-improvement scheduler (AGGRESSIVE MODE)
        self.improvement_scheduler = ImprovementScheduler(
            kimi_client=self.agent.kimi_client,
            project_root=PROJECT_ROOT,
            idle_threshold_seconds=300,  # 5 minutes idle
            max_improvements_per_session=3,
        )

        def on_improvement(result):
            if result.success:
                logger.info(f"Self-improvement applied: {result.message}")
            else:
                logger.warning(f"Self-improvement failed: {result.message}")

        self.improvement_scheduler.on_improvement(on_improvement)
        await self.improvement_scheduler.start()

        logger.info("TWIZZY daemon started successfully (with aggressive self-improvement)")

    async def stop(self):
        """Stop the daemon."""
        logger.info("Stopping TWIZZY daemon...")

        if self.improvement_scheduler:
            await self.improvement_scheduler.stop()

        if self.server:
            await self.server.stop()

        if self.agent:
            await self.agent.stop()

        logger.info("TWIZZY daemon stopped")

    async def run(self):
        """Run the daemon until shutdown signal."""
        await self.start()

        # Wait for shutdown signal
        await self._shutdown_event.wait()

        await self.stop()

    def request_shutdown(self):
        """Request daemon shutdown."""
        self._shutdown_event.set()


async def main():
    """Main entry point."""
    daemon = TwizzyDaemon()

    # Setup signal handlers
    loop = asyncio.get_event_loop()

    def signal_handler():
        logger.info("Received shutdown signal")
        daemon.request_shutdown()

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, signal_handler)

    # Run daemon
    try:
        await daemon.run()
    except Exception as e:
        logger.error(f"Daemon error: {e}")
        raise
    finally:
        # Cleanup signal handlers
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.remove_signal_handler(sig)


if __name__ == "__main__":
    asyncio.run(main())
