"""
Skill registry for managing installed skills.
"""

import logging
from typing import Dict, List, Optional, Type
from dataclasses import dataclass

from .skill import Skill, SkillManifest, SkillCategory

logger = logging.getLogger(__name__)


@dataclass
class RegisteredSkill:
    """A skill in the registry."""
    name: str
    skill_class: Type[Skill]
    instance: Optional[Skill] = None
    installed_at: Optional[str] = None


class SkillRegistry:
    """
    Registry for managing TWIZZY skills.
    
    Handles skill discovery, registration, and lifecycle management.
    """
    
    def __init__(self):
        self._skills: Dict[str, RegisteredSkill] = {}
        self._categories: Dict[SkillCategory, List[str]] = {
            cat: [] for cat in SkillCategory
        }
        
    def register(self, skill_class: Type[Skill]) -> bool:
        """
        Register a skill class.
        
        Args:
            skill_class: The Skill subclass to register
            
        Returns:
            True if registered successfully
        """
        try:
            # Create temporary instance to get manifest
            temp_instance = skill_class()
            manifest = temp_instance.manifest
            
            name = manifest.name.lower()
            
            if name in self._skills:
                logger.warning(f"Skill '{name}' already registered, replacing")
                
            self._skills[name] = RegisteredSkill(
                name=name,
                skill_class=skill_class,
                installed_at=None
            )
            
            self._categories[manifest.category].append(name)
            
            logger.info(f"Registered skill: {name} ({manifest.category.value})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register skill: {e}")
            return False
            
    def unregister(self, name: str) -> bool:
        """Unregister a skill."""
        name = name.lower()
        
        if name not in self._skills:
            return False
            
        skill = self._skills[name]
        
        # Uninstall if installed
        if skill.instance:
            self.uninstall(name)
            
        # Remove from categories
        temp_instance = skill.skill_class()
        category = temp_instance.manifest.category
        if name in self._categories[category]:
            self._categories[category].remove(name)
            
        del self._skills[name]
        logger.info(f"Unregistered skill: {name}")
        return True
        
    async def install(self, name: str, config: Dict = None) -> bool:
        """
        Install and instantiate a skill.
        
        Args:
            name: Skill name
            config: Optional configuration
            
        Returns:
            True if installed successfully
        """
        name = name.lower()
        
        if name not in self._skills:
            logger.error(f"Skill '{name}' not registered")
            return False
            
        registered = self._skills[name]
        
        if registered.instance:
            logger.warning(f"Skill '{name}' already installed")
            return True
            
        try:
            instance = registered.skill_class()
            
            if config:
                instance.configure(config)
                
            success = await instance.on_install()
            if not success:
                logger.error(f"Skill '{name}' on_install failed")
                return False
                
            registered.instance = instance
            registered.installed_at = __import__('datetime').datetime.now().isoformat()
            
            logger.info(f"Installed skill: {name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to install skill '{name}': {e}")
            return False
            
    async def uninstall(self, name: str) -> bool:
        """Uninstall a skill."""
        name = name.lower()
        
        if name not in self._skills:
            return False
            
        registered = self._skills[name]
        
        if not registered.instance:
            return True
            
        try:
            await registered.instance.on_uninstall()
            registered.instance = None
            registered.installed_at = None
            
            logger.info(f"Uninstalled skill: {name}")
            return True
            
        except Exception as e:
            logger.error(f"Error uninstalling skill '{name}': {e}")
            return False
            
    async def enable(self, name: str) -> bool:
        """Enable a skill."""
        instance = self.get_instance(name)
        if not instance:
            return False
            
        instance.enable()
        await instance.on_enable()
        logger.info(f"Enabled skill: {name}")
        return True
        
    async def disable(self, name: str) -> bool:
        """Disable a skill."""
        instance = self.get_instance(name)
        if not instance:
            return False
            
        instance.disable()
        await instance.on_disable()
        logger.info(f"Disabled skill: {name}")
        return True
        
    def get_instance(self, name: str) -> Optional[Skill]:
        """Get an installed skill instance."""
        name = name.lower()
        
        if name not in self._skills:
            return None
            
        return self._skills[name].instance
        
    def get_manifest(self, name: str) -> Optional[SkillManifest]:
        """Get a skill's manifest."""
        name = name.lower()
        
        if name not in self._skills:
            return None
            
        temp_instance = self._skills[name].skill_class()
        return temp_instance.manifest
        
    def list_skills(self, category: SkillCategory = None) -> List[str]:
        """List all registered skills."""
        if category:
            return self._categories[category].copy()
        return list(self._skills.keys())
        
    def list_installed(self) -> List[str]:
        """List installed skills."""
        return [
            name for name, reg in self._skills.items()
            if reg.instance is not None
        ]
        
    def list_enabled(self) -> List[str]:
        """List enabled skills."""
        return [
            name for name, reg in self._skills.items()
            if reg.instance and reg.instance.is_enabled()
        ]
        
    def get_stats(self) -> Dict:
        """Get registry statistics."""
        total = len(self._skills)
        installed = sum(1 for s in self._skills.values() if s.instance)
        enabled = sum(1 for s in self._skills.values() if s.instance and s.instance.is_enabled())
        
        by_category = {
            cat.value: len(skills)
            for cat, skills in self._categories.items()
        }
        
        return {
            "total": total,
            "installed": installed,
            "enabled": enabled,
            "by_category": by_category
        }


# Global registry
_registry: Optional[SkillRegistry] = None


def get_skill_registry() -> SkillRegistry:
    """Get or create global skill registry."""
    global _registry
    if _registry is None:
        _registry = SkillRegistry()
    return _registry
