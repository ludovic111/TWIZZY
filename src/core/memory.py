"""Persistent memory system for TWIZZY.

Stores all conversations, facts, and context for long-term memory.
"""
import json
import logging
import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from .llm.kimi_client import Message

logger = logging.getLogger(__name__)


@dataclass
class MemoryFact:
    """A single fact/memory extracted from conversations."""
    id: str
    content: str
    source_conversation_id: str
    created_at: datetime
    fact_type: str = "general"  # user_preference, system_info, task, etc.
    confidence: float = 1.0
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "source_conversation_id": self.source_conversation_id,
            "created_at": self.created_at.isoformat(),
            "fact_type": self.fact_type,
            "confidence": self.confidence,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MemoryFact":
        return cls(
            id=data["id"],
            content=data["content"],
            source_conversation_id=data["source_conversation_id"],
            created_at=datetime.fromisoformat(data["created_at"]),
            fact_type=data.get("fact_type", "general"),
            confidence=data.get("confidence", 1.0),
        )


@dataclass
class ConversationSummary:
    """Summary of a conversation for quick reference."""
    id: str
    title: str
    summary: str
    key_points: list[str]
    created_at: datetime
    updated_at: datetime
    message_count: int = 0
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "summary": self.summary,
            "key_points": self.key_points,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "message_count": self.message_count,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ConversationSummary":
        return cls(
            id=data["id"],
            title=data["title"],
            summary=data["summary"],
            key_points=data.get("key_points", []),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            message_count=data.get("message_count", 0),
        )


class PersistentMemory:
    """Long-term memory system for TWIZZY.
    
    Stores:
    - All conversations with full history
    - Extracted facts and preferences
    - Conversation summaries for quick recall
    - User preferences and system knowledge
    """
    
    def __init__(self, storage_dir: Path | None = None):
        self.storage_dir = storage_dir or Path.home() / ".twizzy" / "memory"
        self.conversations_dir = self.storage_dir / "conversations"
        self.facts_file = self.storage_dir / "facts.json"
        self.summaries_file = self.storage_dir / "summaries.json"
        self.preferences_file = self.storage_dir / "preferences.json"
        
        # Ensure directories exist
        self.conversations_dir.mkdir(parents=True, exist_ok=True)
        
        # In-memory cache
        self._facts: dict[str, MemoryFact] = {}
        self._summaries: dict[str, ConversationSummary] = {}
        self._preferences: dict[str, Any] = {}
        
        self._load_data()
    
    def _load_data(self):
        """Load all persisted data."""
        # Load facts
        if self.facts_file.exists():
            try:
                with open(self.facts_file) as f:
                    data = json.load(f)
                self._facts = {k: MemoryFact.from_dict(v) for k, v in data.items()}
            except Exception as e:
                logger.error(f"Failed to load facts: {e}")
        
        # Load summaries
        if self.summaries_file.exists():
            try:
                with open(self.summaries_file) as f:
                    data = json.load(f)
                self._summaries = {k: ConversationSummary.from_dict(v) for k, v in data.items()}
            except Exception as e:
                logger.error(f"Failed to load summaries: {e}")
        
        # Load preferences
        if self.preferences_file.exists():
            try:
                with open(self.preferences_file) as f:
                    self._preferences = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load preferences: {e}")
    
    def _save_facts(self):
        """Save facts to disk."""
        try:
            with open(self.facts_file, "w") as f:
                json.dump({k: v.to_dict() for k, v in self._facts.items()}, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save facts: {e}")
    
    def _save_summaries(self):
        """Save summaries to disk."""
        try:
            with open(self.summaries_file, "w") as f:
                json.dump({k: v.to_dict() for k, v in self._summaries.items()}, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save summaries: {e}")
    
    def _save_preferences(self):
        """Save preferences to disk."""
        try:
            with open(self.preferences_file, "w") as f:
                json.dump(self._preferences, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save preferences: {e}")
    
    # Conversations
    
    def save_conversation(self, conversation_id: str, messages: list[Message], title: str | None = None):
        """Save a conversation with full message history."""
        file_path = self.conversations_dir / f"{conversation_id}.json"
        
        data = {
            "id": conversation_id,
            "title": title or f"Chat {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "updated_at": datetime.now().isoformat(),
            "messages": [
                {
                    "role": msg.role,
                    "content": msg.content,
                    "timestamp": datetime.now().isoformat(),
                }
                for msg in messages
            ],
        }
        
        try:
            with open(file_path, "w") as f:
                json.dump(data, f, indent=2)
            logger.debug(f"Saved conversation: {conversation_id}")
        except Exception as e:
            logger.error(f"Failed to save conversation: {e}")
    
    def get_conversation(self, conversation_id: str) -> dict | None:
        """Get a full conversation by ID."""
        file_path = self.conversations_dir / f"{conversation_id}.json"
        if not file_path.exists():
            return None
        
        try:
            with open(file_path) as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load conversation: {e}")
            return None
    
    def list_conversations(self, limit: int = 100) -> list[dict]:
        """List all conversations sorted by most recent."""
        conversations = []
        
        for file_path in self.conversations_dir.glob("*.json"):
            try:
                with open(file_path) as f:
                    data = json.load(f)
                conversations.append(data)
            except Exception as e:
                logger.warning(f"Failed to load {file_path}: {e}")
        
        conversations.sort(key=lambda c: c.get("updated_at", ""), reverse=True)
        return conversations[:limit]
    
    def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation."""
        file_path = self.conversations_dir / f"{conversation_id}.json"
        try:
            if file_path.exists():
                file_path.unlink()
            if conversation_id in self._summaries:
                del self._summaries[conversation_id]
                self._save_summaries()
            return True
        except Exception as e:
            logger.error(f"Failed to delete conversation: {e}")
            return False
    
    # Facts & Memory
    
    def add_fact(self, content: str, conversation_id: str, fact_type: str = "general") -> str:
        """Add a fact to memory."""
        fact_id = hashlib.md5(content.encode()).hexdigest()[:12]
        
        fact = MemoryFact(
            id=fact_id,
            content=content,
            source_conversation_id=conversation_id,
            created_at=datetime.now(),
            fact_type=fact_type,
        )
        
        self._facts[fact_id] = fact
        self._save_facts()
        return fact_id
    
    def get_facts(self, fact_type: str | None = None, limit: int = 50) -> list[MemoryFact]:
        """Get facts, optionally filtered by type."""
        facts = list(self._facts.values())
        
        if fact_type:
            facts = [f for f in facts if f.fact_type == fact_type]
        
        facts.sort(key=lambda f: f.created_at, reverse=True)
        return facts[:limit]
    
    def search_facts(self, query: str) -> list[MemoryFact]:
        """Search facts by content."""
        query_lower = query.lower()
        results = []
        
        for fact in self._facts.values():
            if query_lower in fact.content.lower():
                results.append(fact)
        
        return results
    
    # Preferences
    
    def set_preference(self, key: str, value: Any):
        """Set a user preference."""
        self._preferences[key] = value
        self._save_preferences()
    
    def get_preference(self, key: str, default: Any = None) -> Any:
        """Get a user preference."""
        return self._preferences.get(key, default)
    
    def get_all_preferences(self) -> dict[str, Any]:
        """Get all preferences."""
        return self._preferences.copy()
    
    # Context for LLM
    
    def get_relevant_context(self, query: str, max_facts: int = 5) -> str:
        """Get relevant facts and context for a query."""
        # Search for relevant facts
        facts = self.search_facts(query)[:max_facts]
        
        if not facts:
            return ""
        
        context = "Relevant information from previous conversations:\n"
        for fact in facts:
            context += f"- {fact.content}\n"
        
        return context
    
    def get_recent_conversations_summary(self, limit: int = 5) -> str:
        """Get a summary of recent conversations."""
        conversations = self.list_conversations(limit=limit)
        
        if not conversations:
            return ""
        
        summary = "Recent conversations:\n"
        for conv in conversations:
            title = conv.get("title", "Untitled")
            msg_count = len(conv.get("messages", []))
            summary += f"- {title} ({msg_count} messages)\n"
        
        return summary


# Global memory instance
_memory: PersistentMemory | None = None


def get_memory() -> PersistentMemory:
    """Get the global memory instance."""
    global _memory
    if _memory is None:
        _memory = PersistentMemory()
    return _memory
