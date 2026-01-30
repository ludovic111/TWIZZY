"""
Canvas system for visual agent outputs.

The Canvas is a shared visual workspace where the agent can:
- Display images and charts
- Show interactive forms
- Render structured data
- Create visual workflows
"""

import json
import uuid
import logging
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class CanvasType(Enum):
    """Types of canvas elements."""
    TEXT = "text"
    MARKDOWN = "markdown"
    CODE = "code"
    IMAGE = "image"
    CHART = "chart"
    TABLE = "table"
    FORM = "form"
    CARD = "card"
    LIST = "list"
    TIMELINE = "timeline"
    MAP = "map"
    IFRAME = "iframe"


@dataclass
class CanvasElement:
    """A single element on the canvas."""
    id: str
    type: CanvasType
    content: Any
    title: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    position: Dict[str, int] = field(default_factory=lambda: {"x": 0, "y": 0})
    size: Dict[str, int] = field(default_factory=lambda: {"width": 100, "height": 100})
    style: Dict[str, str] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    @classmethod
    def create(cls, element_type: CanvasType, content: Any, **kwargs) -> "CanvasElement":
        """Create a new canvas element with auto-generated ID."""
        return cls(
            id=str(uuid.uuid4())[:8],
            type=element_type,
            content=content,
            **kwargs
        )


class Canvas:
    """
    Visual workspace for agent outputs.
    
    The Canvas allows the agent to create rich visual representations
    that go beyond simple text responses.
    """
    
    def __init__(self, canvas_id: Optional[str] = None):
        self.id = canvas_id or str(uuid.uuid4())[:8]
        self.elements: Dict[str, CanvasElement] = {}
        self._listeners: List[Callable] = []
        self._history: List[Dict] = []
        self.created_at = datetime.now().isoformat()
        
    def add_element(self, element: CanvasElement) -> str:
        """Add an element to the canvas."""
        self.elements[element.id] = element
        self._history.append({
            "action": "add",
            "element_id": element.id,
            "timestamp": datetime.now().isoformat()
        })
        self._notify_listeners("add", element)
        logger.debug(f"Added element {element.id} to canvas {self.id}")
        return element.id
        
    def update_element(self, element_id: str, content: Any = None, **kwargs) -> bool:
        """Update an existing element."""
        if element_id not in self.elements:
            return False
            
        element = self.elements[element_id]
        
        if content is not None:
            element.content = content
            
        for key, value in kwargs.items():
            if hasattr(element, key):
                setattr(element, key, value)
                
        element.updated_at = datetime.now().isoformat()
        
        self._history.append({
            "action": "update",
            "element_id": element_id,
            "timestamp": datetime.now().isoformat()
        })
        
        self._notify_listeners("update", element)
        return True
        
    def remove_element(self, element_id: str) -> bool:
        """Remove an element from the canvas."""
        if element_id not in self.elements:
            return False
            
        element = self.elements.pop(element_id)
        
        self._history.append({
            "action": "remove",
            "element_id": element_id,
            "timestamp": datetime.now().isoformat()
        })
        
        self._notify_listeners("remove", element)
        return True
        
    def clear(self):
        """Clear all elements from the canvas."""
        self.elements.clear()
        self._history.append({
            "action": "clear",
            "timestamp": datetime.now().isoformat()
        })
        self._notify_listeners("clear", None)
        
    def get_element(self, element_id: str) -> Optional[CanvasElement]:
        """Get an element by ID."""
        return self.elements.get(element_id)
        
    def get_elements_by_type(self, element_type: CanvasType) -> List[CanvasElement]:
        """Get all elements of a specific type."""
        return [e for e in self.elements.values() if e.type == element_type]
        
    def add_listener(self, callback: Callable):
        """Add a change listener."""
        self._listeners.append(callback)
        
    def remove_listener(self, callback: Callable):
        """Remove a change listener."""
        if callback in self._listeners:
            self._listeners.remove(callback)
            
    def _notify_listeners(self, action: str, element: Optional[CanvasElement]):
        """Notify all listeners of a change."""
        for listener in self._listeners:
            try:
                listener(self.id, action, element)
            except Exception as e:
                logger.error(f"Canvas listener error: {e}")
                
    def to_dict(self) -> Dict[str, Any]:
        """Convert canvas to dictionary."""
        return {
            "id": self.id,
            "created_at": self.created_at,
            "elements": {
                k: {
                    "id": v.id,
                    "type": v.type.value,
                    "content": v.content,
                    "title": v.title,
                    "metadata": v.metadata,
                    "position": v.position,
                    "size": v.size,
                    "style": v.style,
                    "created_at": v.created_at,
                    "updated_at": v.updated_at
                }
                for k, v in self.elements.items()
            },
            "element_count": len(self.elements)
        }
        
    def to_json(self) -> str:
        """Convert canvas to JSON string."""
        return json.dumps(self.to_dict(), indent=2)
        
    # Convenience methods for common element types
    
    def add_text(self, text: str, title: Optional[str] = None) -> str:
        """Add a text element."""
        element = CanvasElement.create(
            CanvasType.TEXT,
            content=text,
            title=title
        )
        return self.add_element(element)
        
    def add_markdown(self, markdown: str, title: Optional[str] = None) -> str:
        """Add a markdown element."""
        element = CanvasElement.create(
            CanvasType.MARKDOWN,
            content=markdown,
            title=title
        )
        return self.add_element(element)
        
    def add_code(self, code: str, language: str = "python", title: Optional[str] = None) -> str:
        """Add a code element."""
        element = CanvasElement.create(
            CanvasType.CODE,
            content={"code": code, "language": language},
            title=title or f"Code ({language})"
        )
        return self.add_element(element)
        
    def add_image(self, image_url: str, alt_text: str = "", title: Optional[str] = None) -> str:
        """Add an image element."""
        element = CanvasElement.create(
            CanvasType.IMAGE,
            content={"url": image_url, "alt": alt_text},
            title=title
        )
        return self.add_element(element)
        
    def add_table(self, headers: List[str], rows: List[List[Any]], title: Optional[str] = None) -> str:
        """Add a table element."""
        element = CanvasElement.create(
            CanvasType.TABLE,
            content={"headers": headers, "rows": rows},
            title=title or "Table"
        )
        return self.add_element(element)
        
    def add_chart(self, chart_type: str, data: Dict, title: Optional[str] = None) -> str:
        """
        Add a chart element.
        
        Args:
            chart_type: "bar", "line", "pie", "scatter"
            data: Chart.js compatible data structure
        """
        element = CanvasElement.create(
            CanvasType.CHART,
            content={"type": chart_type, "data": data},
            title=title or f"Chart ({chart_type})"
        )
        return self.add_element(element)
        
    def add_card(self, title: str, content: str, metadata: Optional[Dict] = None) -> str:
        """Add a card element."""
        element = CanvasElement.create(
            CanvasType.CARD,
            content={"title": title, "body": content},
            title=title,
            metadata=metadata or {}
        )
        return self.add_element(element)
        
    def add_list(self, items: List[str], ordered: bool = False, title: Optional[str] = None) -> str:
        """Add a list element."""
        element = CanvasElement.create(
            CanvasType.LIST,
            content={"items": items, "ordered": ordered},
            title=title
        )
        return self.add_element(element)
        
    def add_form(self, fields: List[Dict], submit_label: str = "Submit", title: Optional[str] = None) -> str:
        """
        Add a form element.
        
        Args:
            fields: List of field definitions with name, type, label, required
            submit_label: Label for submit button
        """
        element = CanvasElement.create(
            CanvasType.FORM,
            content={"fields": fields, "submit_label": submit_label},
            title=title or "Form"
        )
        return self.add_element(element)


# Global canvas registry
_canvases: Dict[str, Canvas] = {}


def get_canvas(canvas_id: Optional[str] = None) -> Canvas:
    """Get or create a canvas."""
    if canvas_id and canvas_id in _canvases:
        return _canvases[canvas_id]
        
    canvas = Canvas(canvas_id)
    _canvases[canvas.id] = canvas
    return canvas


def list_canvases() -> List[str]:
    """List all canvas IDs."""
    return list(_canvases.keys())


def delete_canvas(canvas_id: str) -> bool:
    """Delete a canvas."""
    if canvas_id in _canvases:
        del _canvases[canvas_id]
        return True
    return False
