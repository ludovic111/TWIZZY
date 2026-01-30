"""
Wake word detection for hands-free TWIZZY activation.

Uses:
- pvporcupine (Picovoice) for on-device wake word
- Or Vosk for keyword spotting
"""

import asyncio
import logging
import struct
from typing import Optional, Callable
from dataclasses import dataclass
from pathlib import Path

try:
    import pvporcupine
    PORCUPINE_AVAILABLE = True
except ImportError:
    PORCUPINE_AVAILABLE = False
    pvporcupine = None

try:
    import pyaudio
    PYAUDIO_AVAILABLE = True
except ImportError:
    PYAUDIO_AVAILABLE = False
    pyaudio = None

logger = logging.getLogger(__name__)


@dataclass
class WakeWordConfig:
    """Configuration for wake word detection."""
    keyword: str = "hey twizzy"  # or "computer", "jarvis", etc.
    sensitivity: float = 0.5
    access_key: Optional[str] = None  # Picovoice access key
    custom_model_path: Optional[str] = None


class WakeWordDetector:
    """
    Wake word detector for hands-free activation.
    
    Supports:
    - Picovince Porcupine (on-device, fast)
    - Custom keyword models
    """
    
    # Built-in keywords from Porcupine
    BUILT_IN_KEYWORDS = [
        "alexa", "americano", "blueberry", "bumblebee", "computer",
        "grapefruit", "grasshopper", "hey google", "hey siri",
        "jarvis", "ok google", "picovoice", "porcupine", "terminator"
    ]
    
    def __init__(self, config: WakeWordConfig = None):
        self.config = config or WakeWordConfig()
        self._porcupine: Optional["pvporcupine.Porcupine"] = None
        self._pa: Optional["pyaudio.PyAudio"] = None
        self._stream = None
        self._running = False
        self._callbacks: list[Callable] = []
        
        if PORCUPINE_AVAILABLE and PYAUDIO_AVAILABLE:
            self._init_porcupine()
            
    def _init_porcupine(self):
        """Initialize Porcupine wake word engine.""""
        try:
            keyword = self.config.keyword.lower().replace(" ", "_")
            
            # Map custom keywords to built-ins
            keyword_map = {
                "hey twizzy": "computer",
                "twizzy": "computer",
                "ok twizzy": "ok_google",
            }
            
            if keyword in keyword_map:
                keyword = keyword_map[keyword]
                
            if keyword not in self.BUILT_IN_KEYWORDS:
                logger.warning(f"Keyword '{keyword}' not in built-in list, using 'computer'")
                keyword = "computer"
                
            self._porcupine = pvporcupine.create(
                access_key=self.config.access_key or "",
                keywords=[keyword],
                sensitivities=[self.config.sensitivity]
            )
            
            self._pa = pyaudio.PyAudio()
            logger.info(f"Wake word detector initialized for '{self.config.keyword}'")
            
        except Exception as e:
            logger.error(f"Failed to initialize Porcupine: {e}")
            self._porcupine = None
            
    def add_callback(self, callback: Callable) -> None:
        """Add callback to run when wake word detected."""
        self._callbacks.append(callback)
        
    def remove_callback(self, callback: Callable) -> None:
        """Remove callback."""
        if callback in self._callbacks:
            self._callbacks.remove(callback)
            
    def start(self) -> bool:
        """Start listening for wake word."""
        if not self._porcupine or not self._pa:
            logger.error("Wake word engine not initialized")
            return False
            
        try:
            self._stream = self._pa.open(
                rate=self._porcupine.sample_rate,
                channels=1,
                format=pyaudio.paInt16,
                input=True,
                frames_per_buffer=self._porcupine.frame_length
            )
            
            self._running = True
            asyncio.create_task(self._listen_loop())
            logger.info("Wake word detector started")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start wake word detector: {e}")
            return False
            
    async def _listen_loop(self):
        """Main listening loop."""
        while self._running:
            try:
                # Read audio frame
                pcm = self._stream.read(self._porcupine.frame_length, exception_on_overflow=False)
                pcm = struct.unpack_from("h" * self._porcupine.frame_length, pcm)
                
                # Process
                keyword_index = self._porcupine.process(pcm)
                
                if keyword_index >= 0:
                    logger.info(f"Wake word '{self.config.keyword}' detected!")
                    
                    # Run callbacks
                    for callback in self._callbacks:
                        try:
                            if asyncio.iscoroutinefunction(callback):
                                asyncio.create_task(callback())
                            else:
                                callback()
                        except Exception as e:
                            logger.error(f"Wake word callback error: {e}")
                            
            except Exception as e:
                logger.error(f"Listen loop error: {e}")
                await asyncio.sleep(0.1)
                
    def stop(self):
        """Stop listening."""
        self._running = False
        
        if self._stream:
            self._stream.stop_stream()
            self._stream.close()
            
        if self._porcupine:
            self._porcupine.delete()
            
        if self._pa:
            self._pa.terminate()
            
        logger.info("Wake word detector stopped")
        
    def is_running(self) -> bool:
        """Check if detector is running."""
        return self._running


# Global instance
_wake_detector: Optional[WakeWordDetector] = None


def get_wake_detector(config: WakeWordConfig = None) -> WakeWordDetector:
    """Get or create global wake word detector."""
    global _wake_detector
    if _wake_detector is None:
        _wake_detector = WakeWordDetector(config)
    return _wake_detector
