"""
TWIZZY Skills Platform - Modular capabilities system.

Inspired by OpenClaw's skills platform for extensible capabilities.
"""

from .skill import Skill, SkillContext, SkillResult, SkillCategory
from .registry import SkillRegistry, get_skill_registry
from .loader import SkillLoader

__all__ = [
    "Skill",
    "SkillContext",
    "SkillResult",
    "SkillCategory",
    "SkillRegistry",
    "get_skill_registry",
    "SkillLoader"
]
