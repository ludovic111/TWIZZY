"""TWIZZY Web Application.

FastAPI server with WebSocket for real-time chat and REST endpoints for configuration.
Auto-reloads when the agent modifies its own code.
"""
import logging
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .websocket import ConnectionManager
from .routes import chat, config, improvement

logger = logging.getLogger(__name__)

# Paths
BASE_DIR = Path(__file__).parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

# Create FastAPI app
app = FastAPI(
    title="TWIZZY",
    description="Autonomous Self-Improving Mac Agent",
    version="0.2.0",
)

# Mount static files
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Templates
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# WebSocket connection manager
manager = ConnectionManager()

# Include routers
app.include_router(chat.router, prefix="/api", tags=["chat"])
app.include_router(config.router, prefix="/api", tags=["config"])
app.include_router(improvement.router, prefix="/api", tags=["improvement"])


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Main chat page."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/settings", response_class=HTMLResponse)
async def settings(request: Request):
    """Settings page."""
    return templates.TemplateResponse("settings.html", {"request": request})


@app.get("/improvements", response_class=HTMLResponse)
async def improvements(request: Request):
    """Self-improvement history page."""
    return templates.TemplateResponse("improvements.html", {"request": request})


@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """WebSocket endpoint for real-time chat."""
    await manager.connect(websocket)
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            message = data.get("message", "")

            if message:
                # Process message and stream response
                await manager.process_and_stream(websocket, message)

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("Client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)


@app.on_event("startup")
async def startup():
    """Initialize on startup."""
    logger.info("TWIZZY Web Server starting...")
    # Agent initialization happens in websocket manager


@app.on_event("shutdown")
async def shutdown():
    """Cleanup on shutdown."""
    logger.info("TWIZZY Web Server shutting down...")
    await manager.shutdown()
