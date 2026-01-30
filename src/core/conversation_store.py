"""Conversation persistence and management for TWIZZY.

Handles saving, loading, and summarizing conversation history.
"""
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from .llm.kimi_client import Message

logger = logging.getLogger(__name__)


@dataclass
class Conversation:
    """A persisted conversation."""

    id: str
    title: str
    created_at: datetime
    updated_at: datetime
    messages: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "messages": self.messages,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Conversation":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            title=data["title"],
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            messages=data.get("messages", []),
            metadata=data.get("metadata", {}),
        )


class ConversationStore:
    """Store for persisting and retrieving conversations."""

    def __init__(self, storage_dir: Path | None = None):
        """Initialize the conversation store.

        Args:
            storage_dir: Directory to store conversations. Defaults to ~/.twizzy/conversations
        """
        self.storage_dir = storage_dir or Path.home() / ".twizzy" / "conversations"
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._cache: dict[str, Conversation] = {}

    def _get_file_path(self, conversation_id: str) -> Path:
        """Get the file path for a conversation."""
        return self.storage_dir / f"{conversation_id}.json"

    def create(self, title: str | None = None, metadata: dict[str, Any] | None = None) -> Conversation:
        """Create a new conversation.

        Args:
            title: Optional title for the conversation
            metadata: Optional metadata

        Returns:
            The new conversation
        """
        conversation_id = str(uuid.uuid4())[:8]
        now = datetime.now()

        conversation = Conversation(
            id=conversation_id,
            title=title or f"Conversation {now.strftime('%Y-%m-%d %H:%M')}",
            created_at=now,
            updated_at=now,
            metadata=metadata or {},
        )

        self._cache[conversation_id] = conversation
        self._save(conversation)

        logger.info(f"Created conversation: {conversation_id}")
        return conversation

    def get(self, conversation_id: str) -> Conversation | None:
        """Get a conversation by ID.

        Args:
            conversation_id: The conversation ID

        Returns:
            The conversation or None if not found
        """
        # Check cache first
        if conversation_id in self._cache:
            return self._cache[conversation_id]

        # Load from disk
        file_path = self._get_file_path(conversation_id)
        if not file_path.exists():
            return None

        try:
            with open(file_path) as f:
                data = json.load(f)
            conversation = Conversation.from_dict(data)
            self._cache[conversation_id] = conversation
            return conversation
        except Exception as e:
            logger.error(f"Failed to load conversation {conversation_id}: {e}")
            return None

    def save_messages(
        self,
        conversation_id: str,
        messages: list[Message],
        title: str | None = None,
    ) -> bool:
        """Save messages to a conversation.

        Args:
            conversation_id: The conversation ID
            messages: Messages to save
            title: Optional new title

        Returns:
            True if saved successfully
        """
        conversation = self.get(conversation_id)
        if conversation is None:
            logger.error(f"Conversation not found: {conversation_id}")
            return False

        # Convert messages to dicts
        conversation.messages = [
            {
                "role": msg.role,
                "content": msg.content,
                "tool_calls": msg.tool_calls,
                "tool_call_id": msg.tool_call_id,
                "reasoning_content": msg.reasoning_content,
            }
            for msg in messages
        ]

        if title:
            conversation.title = title

        conversation.updated_at = datetime.now()
        self._save(conversation)
        return True

    def _save(self, conversation: Conversation) -> None:
        """Save a conversation to disk."""
        file_path = self._get_file_path(conversation.id)
        try:
            with open(file_path, "w") as f:
                json.dump(conversation.to_dict(), f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save conversation {conversation.id}: {e}")

    def list_conversations(self, limit: int = 50) -> list[Conversation]:
        """List all conversations, sorted by most recent.

        Args:
            limit: Maximum number to return

        Returns:
            List of conversations
        """
        conversations = []

        for file_path in self.storage_dir.glob("*.json"):
            try:
                with open(file_path) as f:
                    data = json.load(f)
                conversations.append(Conversation.from_dict(data))
            except Exception as e:
                logger.warning(f"Failed to load conversation from {file_path}: {e}")

        # Sort by updated_at descending
        conversations.sort(key=lambda c: c.updated_at, reverse=True)
        return conversations[:limit]

    def delete(self, conversation_id: str) -> bool:
        """Delete a conversation.

        Args:
            conversation_id: The conversation ID

        Returns:
            True if deleted successfully
        """
        file_path = self._get_file_path(conversation_id)

        try:
            if file_path.exists():
                file_path.unlink()
            if conversation_id in self._cache:
                del self._cache[conversation_id]
            logger.info(f"Deleted conversation: {conversation_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete conversation {conversation_id}: {e}")
            return False

    def search(self, query: str) -> list[Conversation]:
        """Search conversations by content.

        Args:
            query: Search query

        Returns:
            List of matching conversations
        """
        results = []
        query_lower = query.lower()

        for conversation in self.list_conversations(limit=1000):
            # Search in title
            if query_lower in conversation.title.lower():
                results.append(conversation)
                continue

            # Search in messages
            for msg in conversation.messages:
                content = msg.get("content", "")
                if content and query_lower in content.lower():
                    results.append(conversation)
                    break

        return results


# Global store instance
_store: ConversationStore | None = None


def get_conversation_store() -> ConversationStore:
    """Get the global conversation store instance."""
    global _store
    if _store is None:
        _store = ConversationStore()
    return _store
