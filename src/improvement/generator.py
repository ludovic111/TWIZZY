"""Improvement generator - Generates code improvements using Kimi.

This module takes improvement opportunities and generates actual code changes:
- Creates new plugins
- Fixes bugs in existing code
- Optimizes slow operations
- Adds new capabilities
"""
import ast
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class CodeChange:
    """A proposed code change."""

    file_path: Path
    change_type: str  # "create", "modify", "delete"
    description: str
    old_content: str | None
    new_content: str
    line_start: int | None = None
    line_end: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "file_path": str(self.file_path),
            "change_type": self.change_type,
            "description": self.description,
            "old_content": self.old_content,
            "new_content": self.new_content,
            "line_start": self.line_start,
            "line_end": self.line_end,
        }


@dataclass
class Improvement:
    """A complete improvement with code changes."""

    id: str
    title: str
    description: str
    changes: list[CodeChange]
    test_code: str | None = None


IMPROVEMENT_PROMPT = """You are an expert Python developer improving an AI agent called TWIZZY.

TWIZZY is an autonomous Mac agent with these components:
- Agent core: src/core/agent.py (orchestrator)
- LLM client: src/core/llm/kimi_client.py (Kimi K2.5 API)
- Plugins: src/plugins/ (terminal, filesystem, applications)
- Self-improvement: src/improvement/

Current improvement opportunity:
{opportunity}

Context:
{context}

Your task: Generate code changes to address this improvement opportunity.

Requirements:
1. Keep changes minimal and focused
2. Follow existing code patterns
3. Include docstrings and type hints
4. Make sure imports are correct
5. Generate test code if applicable

Output format - respond with a JSON object:
{{
    "title": "Short title",
    "description": "What this improvement does",
    "changes": [
        {{
            "file_path": "relative/path/to/file.py",
            "change_type": "create|modify",
            "description": "What this change does",
            "content": "The complete new content for the file or modified section"
        }}
    ],
    "test_code": "Optional pytest code to test the changes"
}}

Only output valid JSON, nothing else.
"""


class ImprovementGenerator:
    """Generates code improvements using Kimi."""

    def __init__(self, kimi_client, project_root: Path):
        """Initialize the generator.

        Args:
            kimi_client: KimiClient instance
            project_root: Root directory of the TWIZZY project
        """
        self.kimi_client = kimi_client
        self.project_root = project_root

    async def generate(self, opportunity: dict[str, Any]) -> Improvement | None:
        """Generate an improvement for an opportunity.

        Args:
            opportunity: The improvement opportunity dict

        Returns:
            Improvement object with code changes, or None if generation failed
        """
        from ..core.llm.kimi_client import Message

        # Build context from project files
        context = await self._build_context(opportunity)

        prompt = IMPROVEMENT_PROMPT.format(
            opportunity=opportunity,
            context=context,
        )

        messages = [
            Message(role="system", content="You are a code generation assistant. Output only valid JSON."),
            Message(role="user", content=prompt),
        ]

        try:
            response = await self.kimi_client.chat(messages, thinking=True)

            if not response.content:
                logger.error("Empty response from Kimi")
                return None

            # Parse JSON response
            result = self._parse_response(response.content)
            if not result:
                return None

            # Build Improvement object
            changes = []
            for change_data in result.get("changes", []):
                file_path = self.project_root / change_data["file_path"]
                old_content = None
                if file_path.exists() and change_data["change_type"] == "modify":
                    old_content = file_path.read_text()

                changes.append(CodeChange(
                    file_path=file_path,
                    change_type=change_data["change_type"],
                    description=change_data.get("description", ""),
                    old_content=old_content,
                    new_content=change_data["content"],
                ))

            return Improvement(
                id=opportunity.get("id", "unknown"),
                title=result.get("title", "Untitled improvement"),
                description=result.get("description", ""),
                changes=changes,
                test_code=result.get("test_code"),
            )

        except Exception as e:
            logger.error(f"Failed to generate improvement: {e}")
            return None

    def _parse_response(self, content: str) -> dict | None:
        """Parse JSON from model response."""
        import json

        # Try to extract JSON from the response
        # Handle markdown code blocks
        if "```json" in content:
            match = re.search(r"```json\s*(.*?)\s*```", content, re.DOTALL)
            if match:
                content = match.group(1)
        elif "```" in content:
            match = re.search(r"```\s*(.*?)\s*```", content, re.DOTALL)
            if match:
                content = match.group(1)

        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            return None

    async def _build_context(self, opportunity: dict) -> str:
        """Build context from relevant project files."""
        context_parts = []

        # Include relevant files based on opportunity type
        opp_type = opportunity.get("type", "")
        tools = opportunity.get("context", {}).get("tools_involved", [])

        # Always include base plugin interface
        base_plugin = self.project_root / "src/plugins/base.py"
        if base_plugin.exists():
            context_parts.append(f"# {base_plugin}\n{base_plugin.read_text()[:2000]}")

        # Include relevant plugin files
        for tool in tools[:3]:  # Limit to 3 tools
            # Find plugin file
            for plugin_dir in (self.project_root / "src/plugins").iterdir():
                if plugin_dir.is_dir() and plugin_dir.name in tool.lower():
                    plugin_file = plugin_dir / "plugin.py"
                    if plugin_file.exists():
                        content = plugin_file.read_text()
                        context_parts.append(f"# {plugin_file}\n{content[:2000]}")
                        break

        return "\n\n---\n\n".join(context_parts)

    def validate_code(self, code: str) -> tuple[bool, str]:
        """Validate Python code syntax.

        Args:
            code: Python code to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            ast.parse(code)
            return True, ""
        except SyntaxError as e:
            return False, f"Syntax error at line {e.lineno}: {e.msg}"

    def validate_improvement(self, improvement: Improvement) -> tuple[bool, list[str]]:
        """Validate all code changes in an improvement.

        Args:
            improvement: The improvement to validate

        Returns:
            Tuple of (all_valid, list of error messages)
        """
        errors = []

        for change in improvement.changes:
            if change.file_path.suffix == ".py":
                valid, error = self.validate_code(change.new_content)
                if not valid:
                    errors.append(f"{change.file_path}: {error}")

        return len(errors) == 0, errors
