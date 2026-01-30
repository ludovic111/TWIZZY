"""
Base skill interface and types.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional, List


class SkillCategory(Enum):
    """Categories of skills."""
    PRODUCTIVITY = "productivity"
    COMMUNICATION = "communication"
    DEVELOPMENT = "development"
    MEDIA = "media"
    SYSTEM = "system"
    INTEGRATION = "integration"
    UTILITY = "utility"


@dataclass
class SkillContext:
    """Context passed to skill execution."""
    user_id: str
    conversation_id: str
    message: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SkillResult:
    """Result of skill execution."""
    success: bool
    message: str
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    duration_ms: int = 0


@dataclass
class SkillManifest:
    """Skill metadata and configuration."""
    name: str
    version: str
    description: str
    category: SkillCategory
    author: str
    entry_point: str
    permissions: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    config_schema: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "category": self.category.value,
            "author": self.author,
            "entry_point": self.entry_point,
            "permissions": self.permissions,
            "dependencies": self.dependencies
        }


class Skill(ABC):
    """
    Base class for all TWIZZY skills.
    
    Skills are modular capabilities that extend TWIZZY's functionality.
    Each skill is a self-contained unit with its own configuration,
    permissions, and execution logic.
    """
    
    def __init__(self):
        self._enabled = True
        self._config: Dict[str, Any] = {}
        self._manifest: Optional[SkillManifest] = None
        
    @property
    @abstractmethod
    def manifest(self) -> SkillManifest:
        """Return the skill's manifest."""
        pass
        
    @abstractmethod
    async def execute(self, context: SkillContext) -> SkillResult:
        """
        Execute the skill.
        
        Args:
            context: Execution context with user message and parameters
            
        Returns:
            SkillResult with success status and data
        """
        pass
        
    def configure(self, config: Dict[str, Any]) -> None:
        """Configure the skill with user settings."""
        self._config = config
        
    def get_config(self, key: str, default: Any = None) -> Any:
        """Get a configuration value."""
        return self._config.get(key, default)
        
    def enable(self) -> None:
        """Enable the skill."""
        self._enabled = True
        
    def disable(self) -> None:
        """Disable the skill."""
        self._enabled = False
        
    def is_enabled(self) -> bool:
        """Check if skill is enabled."""
        return self._enabled
        
    def validate_permissions(self, available_permissions: List[str]) -> bool:
        """Check if all required permissions are available."""
        if not self._manifest:
            return True
        return all(p in available_permissions for p in self._manifest.permissions)
        
    async def on_install(self) -> bool:
        """Called when skill is installed. Override for setup logic."""
        return True
        
    async def on_uninstall(self) -> bool:
        """Called when skill is uninstalled. Override for cleanup."""
        return True
        
    async def on_enable(self) -> None:
        """Called when skill is enabled."""
        pass
        
    async def on_disable(self) -> None:
        """Called when skill is disabled."""
        pass


# Example built-in skills

class EchoSkill(Skill):
    """Simple echo skill for testing."""
    
    @property
    def manifest(self) -> SkillManifest:
        return SkillManifest(
            name="echo",
            version="1.0.0",
            description="Echo back the user's message",
            category=SkillCategory.UTILITY,
            author="TWIZZY",
            entry_point="echo",
            permissions=[]
        )
        
    async def execute(self, context: SkillContext) -> SkillResult:
        return SkillResult(
            success=True,
            message=f"Echo: {context.message}",
            data={"original": context.message}
        )


class TimeSkill(Skill):
    """Get current time skill."""
    
    @property
    def manifest(self) -> SkillManifest:
        return SkillManifest(
            name="time",
            version="1.0.0",
            description="Get current date and time",
            category=SkillCategory.UTILITY,
            author="TWIZZY",
            entry_point="time",
            permissions=[]
        )
        
    async def execute(self, context: SkillContext) -> SkillResult:
        now = datetime.now()
        return SkillResult(
            success=True,
            message=f"Current time: {now.strftime('%Y-%m-%d %H:%M:%S')}",
            data={
                "datetime": now.isoformat(),
                "date": now.strftime('%Y-%m-%d'),
                "time": now.strftime('%H:%M:%S'),
                "timezone": str(now.astimezone().tzinfo)
            }
        )
