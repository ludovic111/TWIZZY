"""
Browser automation controller using Playwright.

Provides:
- Page navigation
- Element interaction
- Screenshots
- Downloads
- Form filling
"""

import asyncio
import logging
import base64
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

try:
    from playwright.async_api import async_playwright, Page, Browser, BrowserContext
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    async_playwright = None
    Page = Browser = BrowserContext = Any

logger = logging.getLogger(__name__)


class BrowserAction(Enum):
    """Types of browser actions."""
    NAVIGATE = "navigate"
    CLICK = "click"
    TYPE = "type"
    SCREENSHOT = "screenshot"
    SCROLL = "scroll"
    EXTRACT = "extract"
    DOWNLOAD = "download"
    WAIT = "wait"


@dataclass
class BrowserConfig:
    """Configuration for browser controller."""
    headless: bool = True
    browser_type: str = "chromium"  # chromium, firefox, webkit
    user_data_dir: Optional[str] = None
    viewport_width: int = 1280
    viewport_height: int = 720
    stealth_mode: bool = True  # Hide automation indicators


@dataclass
class ActionResult:
    """Result of a browser action."""
    success: bool
    action: BrowserAction
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    screenshot: Optional[str] = None  # base64 encoded


class BrowserController:
    """
    Browser automation controller for TWIZZY.
    
    Allows the agent to:
    - Navigate to websites
    - Interact with pages
    - Take screenshots
    - Extract data
    - Download files
    """
    
    def __init__(self, config: BrowserConfig = None):
        self.config = config or BrowserConfig()
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        self._action_history: List[Dict] = []
        
    async def start(self) -> bool:
        """Start the browser."""
        if not PLAYWRIGHT_AVAILABLE:
            logger.error("playwright not installed. Run: pip install playwright && playwright install")
            return False
            
        try:
            self._playwright = await async_playwright().start()
            
            browser_launcher = getattr(self._playwright, self.config.browser_type)
            
            launch_args = {
                "headless": self.config.headless,
            }
            
            if self.config.user_data_dir:
                launch_args["user_data_dir"] = self.config.user_data_dir
                
            self._browser = await browser_launcher.launch(**launch_args)
            
            self._context = await self._browser.new_context(
                viewport={
                    "width": self.config.viewport_width,
                    "height": self.config.viewport_height
                },
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/120.0.0.0 Safari/537.36"
            )
            
            if self.config.stealth_mode:
                await self._apply_stealth()
                
            self._page = await self._context.new_page()
            
            logger.info("Browser controller started")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start browser: {e}")
            return False
            
    async def _apply_stealth(self):
        """Apply stealth mode to hide automation."""
        await self._context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            window.chrome = { runtime: {} };
        """)
        
    async def stop(self):
        """Stop the browser."""
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        logger.info("Browser controller stopped")
        
    async def navigate(self, url: str, wait_until: str = "networkidle") -> ActionResult:
        """Navigate to a URL."""
        if not self._page:
            return ActionResult(False, BrowserAction.NAVIGATE, error="Browser not started")
            
        try:
            response = await self._page.goto(url, wait_until=wait_until)
            
            self._action_history.append({
                "action": "navigate",
                "url": url,
                "status": response.status if response else None
            })
            
            return ActionResult(
                success=True,
                action=BrowserAction.NAVIGATE,
                data={
                    "url": self._page.url,
                    "title": await self._page.title(),
                    "status": response.status if response else None
                }
            )
        except Exception as e:
            return ActionResult(False, BrowserAction.NAVIGATE, error=str(e))
            
    async def click(self, selector: str) -> ActionResult:
        """Click an element."""
        if not self._page:
            return ActionResult(False, BrowserAction.CLICK, error="Browser not started")
            
        try:
            await self._page.click(selector)
            
            self._action_history.append({
                "action": "click",
                "selector": selector
            })
            
            return ActionResult(
                success=True,
                action=BrowserAction.CLICK,
                data={"selector": selector}
            )
        except Exception as e:
            return ActionResult(False, BrowserAction.CLICK, error=str(e))
            
    async def type_text(self, selector: str, text: str, submit: bool = False) -> ActionResult:
        """Type text into an input."""
        if not self._page:
            return ActionResult(False, BrowserAction.TYPE, error="Browser not started")
            
        try:
            await self._page.fill(selector, text)
            
            if submit:
                await self._page.press(selector, "Enter")
                
            self._action_history.append({
                "action": "type",
                "selector": selector,
                "text": text[:50] + "..." if len(text) > 50 else text
            })
            
            return ActionResult(
                success=True,
                action=BrowserAction.TYPE,
                data={"selector": selector, "submitted": submit}
            )
        except Exception as e:
            return ActionResult(False, BrowserAction.TYPE, error=str(e))
            
    async def screenshot(self, full_page: bool = False) -> ActionResult:
        """Take a screenshot."""
        if not self._page:
            return ActionResult(False, BrowserAction.SCREENSHOT, error="Browser not started")
            
        try:
            screenshot_bytes = await self._page.screenshot(full_page=full_page)
            screenshot_b64 = base64.b64encode(screenshot_bytes).decode()
            
            return ActionResult(
                success=True,
                action=BrowserAction.SCREENSHOT,
                data={"full_page": full_page},
                screenshot=screenshot_b64
            )
        except Exception as e:
            return ActionResult(False, BrowserAction.SCREENSHOT, error=str(e))
            
    async def scroll(self, direction: str = "down", amount: int = 500) -> ActionResult:
        """Scroll the page."""
        if not self._page:
            return ActionResult(False, BrowserAction.SCROLL, error="Browser not started")
            
        try:
            if direction == "down":
                await self._page.evaluate(f"window.scrollBy(0, {amount})")
            elif direction == "up":
                await self._page.evaluate(f"window.scrollBy(0, -{amount})")
            elif direction == "bottom":
                await self._page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                
            return ActionResult(
                success=True,
                action=BrowserAction.SCROLL,
                data={"direction": direction, "amount": amount}
            )
        except Exception as e:
            return ActionResult(False, BrowserAction.SCROLL, error=str(e))
            
    async def extract(self, selector: str, attribute: str = "textContent") -> ActionResult:
        """Extract data from elements."""
        if not self._page:
            return ActionResult(False, BrowserAction.EXTRACT, error="Browser not started")
            
        try:
            elements = await self._page.query_selector_all(selector)
            data = []
            
            for el in elements:
                if attribute == "textContent":
                    text = await el.text_content()
                    data.append(text.strip() if text else "")
                else:
                    attr_value = await el.get_attribute(attribute)
                    data.append(attr_value)
                    
            return ActionResult(
                success=True,
                action=BrowserAction.EXTRACT,
                data={
                    "selector": selector,
                    "count": len(data),
                    "values": data
                }
            )
        except Exception as e:
            return ActionResult(False, BrowserAction.EXTRACT, error=str(e))
            
    async def download(self, url: str, save_path: str) -> ActionResult:
        """Download a file."""
        if not self._page:
            return ActionResult(False, BrowserAction.DOWNLOAD, error="Browser not started")
            
        try:
            async with self._page.expect_download() as download_info:
                await self._page.evaluate(f"window.open('{url}', '_blank')")
                
            download = await download_info.value
            await download.save_as(save_path)
            
            return ActionResult(
                success=True,
                action=BrowserAction.DOWNLOAD,
                data={
                    "url": url,
                    "path": save_path,
                    "filename": download.suggested_filename
                }
            )
        except Exception as e:
            return ActionResult(False, BrowserAction.DOWNLOAD, error=str(e))
            
    async def get_page_info(self) -> Dict[str, Any]:
        """Get current page information."""
        if not self._page:
            return {"error": "Browser not started"}
            
        return {
            "url": self._page.url,
            "title": await self._page.title(),
            "viewport": {
                "width": self.config.viewport_width,
                "height": self.config.viewport_height
            }
        }
        
    def get_history(self) -> List[Dict]:
        """Get action history."""
        return self._action_history.copy()


# Global instance
_browser_controller: Optional[BrowserController] = None


async def get_browser_controller(config: BrowserConfig = None) -> BrowserController:
    """Get or create global browser controller."""
    global _browser_controller
    if _browser_controller is None:
        _browser_controller = BrowserController(config)
        await _browser_controller.start()
    return _browser_controller
