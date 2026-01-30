"""Chat API routes for TWIZZY."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..websocket import get_manager
from ...core.memory import get_memory

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


# Conversation management endpoints
@router.get("/conversations")
async def list_conversations():
    """List all conversations."""
    try:
        memory = get_memory()
        conversations = memory.list_conversations(limit=100)
        return {
            "success": True,
            "conversations": conversations
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/conversations/new")
async def new_conversation():
    """Create a new conversation."""
    manager = get_manager()
    
    try:
        agent = await manager._ensure_agent()
        agent.clear_conversation()
        return {
            "success": True,
            "conversation_id": agent.conversation.conversation_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    """Get a specific conversation."""
    try:
        memory = get_memory()
        conversation = memory.get_conversation(conversation_id)
        
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        return {
            "success": True,
            "conversation": conversation
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """Delete a conversation."""
    try:
        memory = get_memory()
        success = memory.delete_conversation(conversation_id)
        
        return {
            "success": success
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/conversations/{conversation_id}/switch")
async def switch_conversation(conversation_id: str):
    """Switch to a conversation."""
    manager = get_manager()
    
    try:
        memory = get_memory()
        conversation = memory.get_conversation(conversation_id)
        
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        agent = await manager._ensure_agent()
        await agent.load_conversation(conversation_id)
        
        return {
            "success": True,
            "conversation_id": conversation_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
