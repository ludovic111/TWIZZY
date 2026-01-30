#!/usr/bin/env python3
"""TWIZZY daemon entry point.

This is the main process that runs as a background service via launchd.
It starts the FastAPI web server with uvicorn (auto-reload enabled).
"""
import logging
import os
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.core.config import TWIZZY_HOME

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


def main():
    """Main entry point - start uvicorn web server."""
    import uvicorn

    logger.info("Starting TWIZZY web server...")

    # Configuration
    host = os.environ.get("TWIZZY_HOST", "127.0.0.1")
    port = int(os.environ.get("TWIZZY_PORT", "7777"))
    reload = os.environ.get("TWIZZY_RELOAD", "true").lower() == "true"

    logger.info(f"Server: http://{host}:{port}")
    logger.info(f"Auto-reload: {reload}")

    # Start uvicorn
    uvicorn.run(
        "src.web.app:app",
        host=host,
        port=port,
        reload=reload,
        reload_dirs=[str(PROJECT_ROOT / "src")] if reload else None,
        log_level="info",
    )


if __name__ == "__main__":
    main()
