"""Conversation summarization for managing long contexts.

Automatically summarizes old conversation messages to stay within
context window limits while preserving important information.
"""
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .llm.kimi_client import KimiClient, Message

logger = logging.getLogger(__name__)


@dataclass
class Summary:
    """A conversation summary."""
    content: str
    message_count: int
    original_messages: list["Message"]


class ConversationSummarizer:
    """Summarizes conversation history to manage context window.
    
    When conversations get too long, this class:
    1. Identifies older messages to summarize
    2. Generates a concise summary using the LLM
    3. Replaces old messages with the summary
    4. Keeps recent messages intact
    """
    
    def __init__(
        self,
        kimi_client: "KimiClient",
        max_messages_before_summary: int = 30,
        messages_to_summarize: int = 20,
        keep_recent: int = 10,
    ):
        """Initialize the summarizer.
        
        Args:
            kimi_client: Client for calling the summarization LLM
            max_messages_before_summary: Trigger summary when exceeding this
            messages_to_summarize: How many old messages to summarize each time
            keep_recent: Always keep this many recent messages unsummarized
        """
        self.kimi_client = kimi_client
        self.max_messages = max_messages_before_summary
        self.messages_to_summarize = messages_to_summarize
        self.keep_recent = keep_recent
    
    async def maybe_summarize(self, messages: list["Message"]) -> list["Message"]:
        """Check if summarization is needed and perform it.
        
        Args:
            messages: Current conversation messages (excluding system)
            
        Returns:
            Messages with old content summarized if needed
        """
        # Don't summarize if under the limit
        if len(messages) <= self.max_messages:
            return messages
        
        # Calculate how many messages to summarize
        # Keep system message + summary + recent messages
        to_summarize_count = len(messages) - self.keep_recent
        
        if to_summarize_count < 5:  # Need at least 5 messages to summarize
            return messages
        
        logger.info(f"Summarizing {to_summarize_count} messages, keeping {self.keep_recent} recent")
        
        # Split messages
        to_summarize = messages[:to_summarize_count]
        to_keep = messages[to_summarize_count:]
        
        # Generate summary
        summary = await self._generate_summary(to_summarize)
        
        # Create summary message
        from .llm.kimi_client import Message
        summary_message = Message(
            role="system",
            content=f"[Conversation Summary]\n{summary}\n\n[Recent messages follow]"
        )
        
        # Combine: summary + recent messages
        result = [summary_message] + to_keep
        
        logger.info(f"Reduced {len(messages)} messages to {len(result)} (summary + {len(to_keep)} recent)")
        return result
    
    async def _generate_summary(self, messages: list["Message"]) -> str:
        """Generate a summary of conversation messages.
        
        Args:
            messages: Messages to summarize
            
        Returns:
            Summary text
        """
        # Build conversation text
        conversation_text = ""
        for msg in messages:
            role = msg.role
            content = msg.content or ""
            
            if role == "user":
                conversation_text += f"User: {content}\n\n"
            elif role == "assistant":
                conversation_text += f"Assistant: {content[:500]}...\n\n" if len(content) > 500 else f"Assistant: {content}\n\n"
            elif role == "tool":
                conversation_text += f"[Tool result: {content[:200]}...]\n\n" if len(content) > 200 else f"[Tool result: {content}]\n\n"
        
        # Create summarization prompt
        summarization_prompt = f"""Summarize the following conversation concisely. 
Focus on:
- Key topics discussed
- Important facts or decisions
- User preferences mentioned
- Tasks completed or in progress

Keep the summary under 300 words.

Conversation:
{conversation_text}

Summary:"""

        from .llm.kimi_client import Message
        summary_messages = [
            Message(role="system", content="You are a helpful assistant that summarizes conversations accurately and concisely."),
            Message(role="user", content=summarization_prompt)
        ]
        
        try:
            response = await self.kimi_client.chat(summary_messages, thinking=False)
            summary = response.content or "Previous conversation about various topics."
            return summary.strip()
        except Exception as e:
            logger.error(f"Failed to generate summary: {e}")
            return "Previous conversation (summary unavailable)."
    
    def get_context_window_info(self, messages: list["Message"]) -> dict:
        """Get information about current context window usage.
        
        Args:
            messages: Current messages
            
        Returns:
            Dict with context window statistics
        """
        total_chars = sum(len(m.content or "") for m in messages)
        estimated_tokens = total_chars // 4  # Rough estimate: ~4 chars per token
        
        # Kimi K2.5 has 256k context window
        context_limit = 256000
        usage_percent = (estimated_tokens / context_limit) * 100
        
        return {
            "message_count": len(messages),
            "total_characters": total_chars,
            "estimated_tokens": estimated_tokens,
            "context_limit": context_limit,
            "usage_percent": round(usage_percent, 2),
            "needs_summarization": len(messages) > self.max_messages,
        }
