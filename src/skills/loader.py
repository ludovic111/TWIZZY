"""
Skill loader for dynamic skill discovery and loading.
"""

import importlib
import importlib.util
import logging
import os
from pathlib import Path
from typing import List, Type, Optional

from .skill import Skill
from .registry import get_skill_registry

logger = logging.getLogger(__name__)


class SkillLoader:
    """
    Loads skills from various sources.
    
    Supports:
    - Built-in skills (in src/skills/built_in/)
    - Workspace skills (in workspace/skills/)
    - External packages
    """
    
    BUILT_IN_PATH = Path(__file__).parent / "built_in"
    WORKSPACE_PATH = Path("workspace/skills")
    
    def __init__(self):
        self._loaded_modules: set = set()
        
    def load_builtin_skills(self) -> int:
        """Load all built-in skills."""
        count = 0
        
        # Create built_in directory if not exists
        self.BUILT_IN_PATH.mkdir(parents=True, exist_ok=True)
        
        # Add __init__.py
        init_file = self.BUILT_IN_PATH / "__init__.py"
        if not init_file.exists():
            init_file.write_text("# Built-in skills package\n")
            
        # Load skills
        for py_file in self.BUILT_IN_PATH.glob("*.py"):
            if py_file.name.startswith("_"):
                continue
                
            skill_class = self._load_skill_file(py_file)
            if skill_class:
                registry = get_skill_registry()
                if registry.register(skill_class):
                    count += 1
                    
        logger.info(f"Loaded {count} built-in skills")
        return count
        
    def load_workspace_skills(self) -> int:
        """Load skills from workspace directory."""
        count = 0
        
        if not self.WORKSPACE_PATH.exists():
            return 0
            
        for py_file in self.WORKSPACE_PATH.glob("*.py"):
            if py_file.name.startswith("_"):
                continue
                
            skill_class = self._load_skill_file(py_file)
            if skill_class:
                registry = get_skill_registry()
                if registry.register(skill_class):
                    count += 1
                    
        logger.info(f"Loaded {count} workspace skills")
        return count
        
    def load_skill_package(self, package_path: str) -> bool:
        """Load a skill from a package directory."""
        path = Path(package_path)
        
        if not path.exists():
            logger.error(f"Skill package not found: {path}")
            return False
            
        skill_file = path / "skill.py"
        if not skill_file.exists():
            skill_file = path / f"{path.name}.py"
            
        if not skill_file.exists():
            logger.error(f"No skill file found in {path}")
            return False
            
        skill_class = self._load_skill_file(skill_file)
        if skill_class:
            registry = get_skill_registry()
            return registry.register(skill_class)
            
        return False
        
    def _load_skill_file(self, file_path: Path) -> Optional[Type[Skill]]:
        """Load a skill class from a Python file."""
        module_name = f"twizzy_skill_{file_path.stem}"
        
        if module_name in self._loaded_modules:
            return None
            
        try:
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            module = importlib.util.module_from_spec(spec)
            
            # Add to sys.modules temporarily
            import sys
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            
            self._loaded_modules.add(module_name)
            
            # Find Skill subclass
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type) and 
                    issubclass(attr, Skill) and 
                    attr is not Skill):
                    logger.debug(f"Found skill class: {attr_name}")
                    return attr
                    
            logger.warning(f"No Skill subclass found in {file_path}")
            return None
            
        except Exception as e:
            logger.error(f"Failed to load skill file {file_path}: {e}")
            return None
            
    def discover_skills(self, directory: str) -> List[str]:
        """Discover available skills in a directory."""
        path = Path(directory)
        
        if not path.exists():
            return []
            
        skills = []
        for py_file in path.glob("*.py"):
            if py_file.name.startswith("_"):
                continue
                
            # Quick check for Skill subclass
            content = py_file.read_text()
            if "class" in content and "Skill" in content:
                skills.append(py_file.stem)
                
        return skills
