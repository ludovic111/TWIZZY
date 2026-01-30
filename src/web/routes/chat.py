"""Chat API routes for TWIZZY."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..websocket import get_manager

router = APIRouter()


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    response: str
    conversation_id: str | None = None


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Send a chat message (non-streaming, for simple requests)."""
    manager = get_manager()

    try:
        agent = await manager._ensure_agent()
        response = await agent.process_message(request.message)
        return ChatResponse(
            response=response,
            conversation_id=agent.conversation.conversation_id
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/clear")
async def clear_conversation():
    """Clear the current conversation."""
    manager = get_manager()

    try:
        agent = await manager._ensure_agent()
        agent.clear_conversation()
        return {"success": True, "message": "Conversation cleared"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_status():
    """Get agent status."""
    manager = get_manager()

    try:
        agent = await manager._ensure_agent()
        return agent.get_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_history():
    """Get conversation history."""
    manager = get_manager()

    try:
        agent = await manager._ensure_agent()
        return await agent.get_conversation_history()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
