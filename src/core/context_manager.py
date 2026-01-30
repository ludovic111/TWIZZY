"""Conversation context management for TWIZZY.

Handles compression and summarization of long conversations
to stay within token limits while preserving important context.
"""
import json
import logging
from dataclasses import dataclass
from typing import Any

from .llm.kimi_client import Message, KimiClient

logger = logging.getLogger(__name__)


@dataclass
class ContextStats:
    """Statistics about context management."""
    total_messages: int
    compressed_messages: int
    original_tokens: int
    compressed_tokens: int
    compression_ratio: float


class ContextManager:
    """Manages conversation context to optimize token usage.
    
    Strategies:
    1. Sliding window - Keep only recent N messages
    2. Summarization - Compress old messages into summary
    3. Selective retention - Keep important messages, compress others
    """
    
    def __init__(
        self,
        max_messages: int = 50,
        compress_threshold: int = 30,
        summary_threshold: int = 20,
    ):
        self.max_messages = max_messages
        self.compress_threshold = compress_threshold
        self.summary_threshold = summary_threshold
        self._conversation_summary: str | None = None
        self._important_message_indices: set[int] = set()
    
    def manage_context(
        self,
        messages: list[Message],
        kimi_client: KimiClient | None = None,
    ) -> list[Message]:
        """Manage conversation context to fit within limits.
        
        Args:
            messages: Full conversation history
            kimi_client: Optional client for summarization
            
        Returns:
            Optimized message list
        """
        if len(messages) <= self.max_messages:
            return messages
        
        # Always keep system message and recent messages
        system_messages = [m for m in messages if m.role == "system"]
        non_system = [m for m in messages if m.role != "system"]
        
        if len(non_system) <= self.max_messages:
            return messages
        
        # Strategy: Keep first few, summarize middle, keep recent
        keep_first = 3
        keep_recent = self.max_messages - keep_first - 1  # -1 for potential summary
        
        first_messages = non_system[:keep_first]
        recent_messages = non_system[-keep_recent:]
        middle_messages = non_system[keep_first:-keep_recent]
        
        # Create summary of middle section if we have a client
        if middle_messages and kimi_client:
            summary = self._create_summary(middle_messages, kimi_client)
            if summary:
                summary_msg = Message(
                    role="system",
                    content=f"[Earlier conversation summary: {summary}]"
                )
                return system_messages + first_messages + [summary_msg] + recent_messages
        
        # Without summarization, just truncate
        return system_messages + first_messages + recent_messages
    
    def _create_summary(
        self,
        messages: list[Message],
        kimi_client: KimiClient,
    ) -> str | None:
        """Create a summary of messages using Kimi.
        
        Args:
            messages: Messages to summarize
            kimi_client: Kimi client for API call
            
        Returns:
            Summary text or None
        """
        try:
            # Build conversation text
            conversation_text = "\n".join([
                f"{m.role}: {m.content[:200]}..." if len(m.content) > 200 else f"{m.role}: {m.content}"
                for m in messages
            ])
            
            summary_prompt = f"""Summarize the following conversation concisely. 
Focus on key facts, decisions, and context needed to continue the conversation.
Keep it under 200 words.

Conversation:
{conversation_text}

Summary:"""
            
            summary_messages = [
                Message(role="system", content="You are a helpful assistant that summarizes conversations."),
                Message(role="user", content=summary_prompt),
            ]
            
            # Run synchronously for simplicity (in practice, this should be async)
            import asyncio
            response = asyncio.get_event_loop().run_until_complete(
                kimi_client.chat(summary_messages, thinking=False)
            )
            
            if response.content:
                return response.content.strip()
            
        except Exception as e:
            logger.error(f"Failed to create summary: {e}")
        
        return None
    
    def mark_important(self, message_index: int):
        """Mark a message as important (should not be compressed)."""
        self._important_message_indices.add(message_index)
    
    def get_stats(self, original: list[Message], compressed: list[Message]) -> ContextStats:
        """Calculate compression statistics."""
        orig_tokens = sum(len(m.content.split()) for m in original)
        comp_tokens = sum(len(m.content.split()) for m in compressed)
        
        return ContextStats(
            total_messages=len(original),
            compressed_messages=len(compressed),
            original_tokens=orig_tokens,
            compressed_tokens=comp_tokens,
            compression_ratio=comp_tokens / max(orig_tokens, 1),
        )


class TokenEstimator:
    """Estimate token counts for messages.
    
    Rough estimation: ~1.3 tokens per word for English text.
    """
    
    TOKENS_PER_WORD = 1.3
    OVERHEAD_TOKENS = 4  # Per message overhead
    
    @classmethod
    def estimate(cls, text: str) -> int:
        """Estimate token count for text."""
        word_count = len(text.split())
        return int(word_count * cls.TOKENS_PER_WORD) + cls.OVERHEAD_TOKENS
    
    @classmethod
    def estimate_messages(cls, messages: list[Message]) -> int:
        """Estimate token count for message list."""
        total = 0
        for msg in messages:
            total += cls.estimate(msg.content)
            if msg.tool_calls:
                total += cls.estimate(json.dumps(msg.tool_calls))
        return total


class SmartContextManager(ContextManager):
    """Advanced context manager with semantic understanding.
    
    Identifies and preserves:
    - User preferences stated in conversation
    - Important decisions or conclusions
    - Action items or tasks
    - Key facts about files/projects
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._extracted_facts: list[str] = []
    
    def extract_facts(self, messages: list[Message]) -> list[str]:
        """Extract important facts from messages.
        
        Simple heuristic-based extraction:
        - Messages with "prefer", "like", "want" indicate preferences
        - Messages with "decided", "conclusion", "agreed" indicate decisions
        - Messages with "todo", "task", "need to" indicate action items
        """
        facts = []
        
        preference_keywords = ["prefer", "like", "want", "don't want", "hate"]
        decision_keywords = ["decided", "conclusion", "agreed", "chosen", "selected"]
        action_keywords = ["todo", "task", "need to", "should", "must", "will"]
        
        for msg in messages:
            if msg.role != "user":
                continue
            
            content_lower = msg.content.lower()
            
            # Check for preferences
            if any(kw in content_lower for kw in preference_keywords):
                facts.append(f"User preference: {msg.content[:100]}")
            
            # Check for decisions
            if any(kw in content_lower for kw in decision_keywords):
                facts.append(f"Decision: {msg.content[:100]}")
            
            # Check for action items
            if any(kw in content_lower for kw in action_keywords):
                facts.append(f"Action item: {msg.content[:100]}")
        
        self._extracted_facts = facts
        return facts
    
    def manage_context(
        self,
        messages: list[Message],
        kimi_client: KimiClient | None = None,
    ) -> list[Message]:
        """Manage context with fact preservation."""
        # Extract facts before compression
        facts = self.extract_facts(messages)
        
        # Get base context
        managed = super().manage_context(messages, kimi_client)
        
        # If we have important facts and they're not in recent messages, add them
        if facts and len(messages) > self.max_messages:
            facts_text = "Important context:\n" + "\n".join(f"- {f}" for f in facts[:5])
            facts_msg = Message(role="system", content=facts_text)
            
            # Insert after system messages
            system_count = sum(1 for m in managed if m.role == "system")
            managed.insert(system_count, facts_msg)
        
        return managed
