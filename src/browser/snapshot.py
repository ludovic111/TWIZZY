"""
Page snapshot for LLM consumption.

Converts a webpage into a structured format that the LLM can understand.
"""

from dataclasses import dataclass
from typing import List, Dict, Optional
from enum import Enum


class ElementType(Enum):
    """Types of page elements."""
    HEADING = "heading"
    PARAGRAPH = "paragraph"
    LINK = "link"
    BUTTON = "button"
    INPUT = "input"
    IMAGE = "image"
    LIST = "list"
    TABLE = "table"
    NAVIGATION = "navigation"
    OTHER = "other"


@dataclass
class PageElement:
    """A single element on the page."""
    type: ElementType
    text: str
    selector: Optional[str] = None
    attributes: Dict = None
    children: List["PageElement"] = None
    
    def __post_init__(self):
        if self.attributes is None:
            self.attributes = {}
        if self.children is None:
            self.children = []


@dataclass
class PageSnapshot:
    """
    A simplified representation of a webpage for LLM consumption.
    
    Extracts key elements and structure without overwhelming the context.
    """
    url: str
    title: str
    elements: List[PageElement]
    interactive_elements: List[PageElement]  # buttons, links, inputs
    text_content: str  # Plain text for LLM reading
    
    def to_llm_format(self, max_length: int = 4000) -> str:
        """
        Convert snapshot to a format suitable for LLM consumption.
        
        Args:
            max_length: Maximum length of output
            
        Returns:
            Formatted string representation
        """
        lines = [
            f"Page: {self.title}",
            f"URL: {self.url}",
            "",
            "=== Interactive Elements ===",
        ]
        
        # Add interactive elements with selectors
        for i, elem in enumerate(self.interactive_elements[:20], 1):
            elem_text = elem.text[:50] if elem.text else "[No text]"
            lines.append(f"{i}. [{elem.type.value}] {elem_text}")
            if elem.selector:
                lines.append(f"   Selector: {elem.selector}")
            lines.append("")
            
        lines.append("=== Page Content ===")
        lines.append(self.text_content[:max_length - 500])
        
        result = "\n".join(lines)
        
        if len(result) > max_length:
            result = result[:max_length - 3] + "..."
            
        return result
        
    @classmethod
    def from_playwright_page(cls, page) -> "PageSnapshot":
        """
        Create a snapshot from a Playwright page.
        
        This is a simplified version - in production would use
        more sophisticated extraction.
        """
        import asyncio
        
        async def _extract():
            url = page.url
            title = await page.title()
            
            # Extract all elements
            elements = []
            interactive = []
            
            # Get headings
            headings = await page.query_selector_all("h1, h2, h3, h4, h5, h6")
            for i, h in enumerate(headings):
                text = await h.text_content()
                if text:
                    elem = PageElement(
                        type=ElementType.HEADING,
                        text=text.strip(),
                        selector=f"h{i+1}:nth-of-type({i+1})"
                    )
                    elements.append(elem)
                    
            # Get links
            links = await page.query_selector_all("a")
            for i, link in enumerate(links):
                text = await link.text_content()
                href = await link.get_attribute("href")
                if text and text.strip():
                    elem = PageElement(
                        type=ElementType.LINK,
                        text=text.strip()[:100],
                        selector=f"a[href='{href}']" if href else f"a:nth-of-type({i+1})",
                        attributes={"href": href}
                    )
                    elements.append(elem)
                    interactive.append(elem)
                    
            # Get buttons
            buttons = await page.query_selector_all("button, input[type='submit']")
            for i, btn in enumerate(buttons):
                text = await btn.text_content() or await btn.get_attribute("value")
                elem = PageElement(
                    type=ElementType.BUTTON,
                    text=text.strip() if text else "[Button]",
                    selector=f"button:nth-of-type({i+1})"
                )
                elements.append(elem)
                interactive.append(elem)
                
            # Get inputs
            inputs = await page.query_selector_all("input, textarea, select")
            for i, inp in enumerate(inputs):
                placeholder = await inp.get_attribute("placeholder")
                name = await inp.get_attribute("name")
                input_type = await inp.get_attribute("type") or "text"
                
                label = placeholder or name or f"Input {i+1}"
                elem = PageElement(
                    type=ElementType.INPUT,
                    text=f"[{input_type}] {label}",
                    selector=f"input[name='{name}']" if name else f"input:nth-of-type({i+1})",
                    attributes={"type": input_type, "name": name, "placeholder": placeholder}
                )
                elements.append(elem)
                interactive.append(elem)
                
            # Get main text content
            paragraphs = await page.query_selector_all("p")
            text_parts = []
            for p in paragraphs[:10]:  # Limit paragraphs
                text = await p.text_content()
                if text and len(text.strip()) > 20:
                    text_parts.append(text.strip())
                    
            text_content = "\n\n".join(text_parts)
            
            return cls(
                url=url,
                title=title,
                elements=elements,
                interactive_elements=interactive,
                text_content=text_content
            )
            
        return asyncio.get_event_loop().run_until_complete(_extract())
