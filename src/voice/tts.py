"""
Text-to-Speech for TWIZZY using system voices or ElevenLabs.

macOS: Uses `say` command (built-in)
Linux: Uses espeak or pyttsx3
Optional: ElevenLabs for high-quality voices
"""

import asyncio
import logging
import platform
import subprocess
import tempfile
import os
from typing import Optional
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class TTSConfig:
    """Configuration for TTS."""
    engine: str = "system"  # "system", "elevenlabs", "pyttsx3"
    voice: Optional[str] = None
    speed: float = 1.0
    elevenlabs_api_key: Optional[str] = None
    elevenlabs_voice_id: Optional[str] = None


class TextToSpeech:
    """
    Text-to-Speech engine for TWIZZY.
    
    Supports:
    - macOS `say` command (best latency)
    - pyttsx3 (cross-platform)
    - ElevenLabs (high quality, requires API key)
    """
    
    def __init__(self, config: TTSConfig = None):
        self.config = config or TTSConfig()
        self._engine = None
        self._elevenlabs = None
        
        if self.config.engine == "elevenlabs":
            self._init_elevenlabs()
        elif self.config.engine == "pyttsx3":
            self._init_pyttsx3()
            
    def _init_elevenlabs(self):
        """Initialize ElevenLabs client."""
        try:
            from elevenlabs import ElevenLabs
            if self.config.elevenlabs_api_key:
                self._elevenlabs = ElevenLabs(api_key=self.config.elevenlabs_api_key)
                logger.info("ElevenLabs TTS initialized")
        except ImportError:
            logger.warning("elevenlabs not installed. Run: pip install elevenlabs")
            
    def _init_pyttsx3(self):
        """Initialize pyttsx3 engine."""
        try:
            import pyttsx3
            self._engine = pyttsx3.init()
            if self.config.voice:
                self._engine.setProperty('voice', self.config.voice)
            self._engine.setProperty('rate', int(200 * self.config.speed))
            logger.info("pyttsx3 TTS initialized")
        except ImportError:
            logger.warning("pyttsx3 not installed. Run: pip install pyttsx3")
            
    async def speak(self, text: str, block: bool = False) -> None:
        """
        Speak the given text.
        
        Args:
            text: Text to speak
            block: If True, wait for speech to complete
        """
        if not text:
            return
            
        # Truncate very long text
        if len(text) > 500:
            text = text[:497] + "..."
            
        logger.debug(f"TTS: {text[:100]}...")
        
        if self.config.engine == "elevenlabs" and self._elevenlabs:
            await self._speak_elevenlabs(text, block)
        elif self.config.engine == "pyttsx3" and self._engine:
            await self._speak_pyttsx3(text, block)
        else:
            await self._speak_system(text, block)
            
    async def _speak_system(self, text: str, block: bool) -> None:
        """Use system TTS (macOS say, Linux espeak)."""
        system = platform.system()
        
        try:
            if system == "Darwin":  # macOS
                cmd = ["say"]
                if self.config.voice:
                    cmd.extend(["-v", self.config.voice])
                if self.config.speed != 1.0:
                    cmd.extend(["-r", str(int(200 * self.config.speed))])
                cmd.append(text)
                
            elif system == "Linux":
                cmd = ["espeak", text]
                if self.config.voice:
                    cmd.extend(["-v", self.config.voice])
                    
            else:  # Windows or fallback
                cmd = ["powershell", "-c", f"Add-Type -AssemblyName System.Speech; "
                       f"$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
                       f"$synth.Speak('{text.replace(\"'\", \"'\"'\")}');"]
            
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL
            )
            
            if block:
                await proc.wait()
            else:
                # Don't wait, but prevent zombie processes
                asyncio.create_task(proc.wait())
                
        except Exception as e:
            logger.error(f"System TTS failed: {e}")
            
    async def _speak_elevenlabs(self, text: str, block: bool) -> None:
        """Use ElevenLabs API for high-quality TTS."""
        try:
            import httpx
            
            voice_id = self.config.elevenlabs_voice_id or "21m00Tcm4TlvDq8ikWAM"
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
                    headers={
                        "xi-api-key": self.config.elevenlabs_api_key,
                        "Content-Type": "application/json"
                    },
                    json={
                        "text": text,
                        "model_id": "eleven_monolingual_v1",
                        "voice_settings": {
                            "stability": 0.5,
                            "similarity_boost": 0.5
                        }
                    },
                    timeout=60
                )
                
                if response.status_code == 200:
                    # Save to temp file and play
                    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                        f.write(response.content)
                        temp_path = f.name
                    
                    # Play audio
                    await self._play_audio(temp_path, block)
                    
                    # Cleanup
                    if block:
                        os.unlink(temp_path)
                    else:
                        asyncio.create_task(self._cleanup_file(temp_path))
                else:
                    logger.error(f"ElevenLabs API error: {response.status_code}")
                    
        except Exception as e:
            logger.error(f"ElevenLabs TTS failed: {e}")
            # Fallback to system
            await self._speak_system(text, block)
            
    async def _speak_pyttsx3(self, text: str, block: bool) -> None:
        """Use pyttsx3 for cross-platform TTS."""
        def _speak():
            self._engine.say(text)
            self._engine.runAndWait()
            
        loop = asyncio.get_event_loop()
        if block:
            await loop.run_in_executor(None, _speak)
        else:
            loop.run_in_executor(None, _speak)
            
    async def _play_audio(self, path: str, block: bool) -> None:
        """Play audio file using system player."""
        system = platform.system()
        
        if system == "Darwin":
            cmd = ["afplay", path]
        elif system == "Linux":
            cmd = ["mpg123", "-q", path]
        else:
            return
            
        proc = await asyncio.create_subprocess_exec(*cmd)
        
        if block:
            await proc.wait()
        else:
            asyncio.create_task(proc.wait())
            
    async def _cleanup_file(self, path: str, delay: float = 5.0) -> None:
        """Clean up temp file after delay."""
        await asyncio.sleep(delay)
        try:
            os.unlink(path)
        except:
            pass
            
    def get_voices(self) -> list:
        """Get available voices for current engine."""
        if self.config.engine == "pyttsx3" and self._engine:
            return [v.name for v in self._engine.getProperty('voices')]
        elif platform.system() == "Darwin":
            # Get macOS voices
            result = subprocess.run(["say", "-v", "?"], capture_output=True, text=True)
            voices = []
            for line in result.stdout.split('\n')[:20]:  # Limit output
                if line.strip():
                    voices.append(line.split()[0])
            return voices
        return []


# Global instance
_tts: Optional[TextToSpeech] = None


def get_tts_engine(config: TTSConfig = None) -> TextToSpeech:
    """Get or create global TTS engine."""
    global _tts
    if _tts is None:
        _tts = TextToSpeech(config)
    return _tts
