"""
Speech-to-Text for TWIZZY using Whisper or system recognition.

macOS: Uses `dictate` or Speech Recognition framework
Linux: Uses whisper.cpp or Vosk
"""

import asyncio
import logging
import platform
import subprocess
import tempfile
import wave
from typing import Optional, Callable
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class STTConfig:
    """Configuration for STT."""
    engine: str = "whisper"  # "whisper", "system", "vosk"
    model_size: str = "base"  # tiny, base, small, medium, large
    language: str = "en"
    sample_rate: int = 16000
    openai_api_key: Optional[str] = None  # For Whisper API


class SpeechToText:
    """
    Speech-to-Text engine for TWIZZY.
    
    Supports:
    - OpenAI Whisper (local or API)
    - macOS dictation
    - Vosk (offline, lightweight)
    """
    
    def __init__(self, config: STTConfig = None):
        self.config = config or STTConfig()
        self._whisper_model = None
        self._vosk_model = None
        self._recording = False
        
        if self.config.engine == "whisper":
            self._init_whisper()
        elif self.config.engine == "vosk":
            self._init_vosk()
            
    def _init_whisper(self):
        """Initialize Whisper model."""
        try:
            import whisper
            logger.info(f"Loading Whisper model: {self.config.model_size}")
            self._whisper_model = whisper.load_model(self.config.model_size)
            logger.info("Whisper model loaded")
        except ImportError:
            logger.warning("openai-whisper not installed. Run: pip install openai-whisper")
        except Exception as e:
            logger.error(f"Failed to load Whisper: {e}")
            
    def _init_vosk(self):
        """Initialize Vosk model."""
        try:
            from vosk import Model, KaldiRecognizer
            model_path = f"models/vosk-model-small-{self.config.language}"
            if Path(model_path).exists():
                self._vosk_model = Model(model_path)
                logger.info("Vosk model loaded")
            else:
                logger.warning(f"Vosk model not found at {model_path}")
        except ImportError:
            logger.warning("vosk not installed. Run: pip install vosk")
            
    async def transcribe(self, audio_path: str) -> str:
        """
        Transcribe audio file to text.
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            Transcribed text
        """
        if not Path(audio_path).exists():
            logger.error(f"Audio file not found: {audio_path}")
            return ""
            
        if self.config.engine == "whisper":
            return await self._transcribe_whisper(audio_path)
        elif self.config.engine == "vosk":
            return await self._transcribe_vosk(audio_path)
        else:
            return await self._transcribe_system(audio_path)
            
    async def _transcribe_whisper(self, audio_path: str) -> str:
        """Transcribe using Whisper."""
        if self._whisper_model:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self._whisper_model.transcribe(
                    audio_path,
                    language=self.config.language,
                    fp16=False
                )
            )
            return result.get("text", "").strip()
        else:
            # Fallback to API
            return await self._transcribe_whisper_api(audio_path)
            
    async def _transcribe_whisper_api(self, audio_path: str) -> str:
        """Transcribe using OpenAI Whisper API."""
        try:
            import httpx
            
            api_key = self.config.openai_api_key
            if not api_key:
                logger.error("OpenAI API key not configured")
                return ""
                
            async with httpx.AsyncClient() as client:
                with open(audio_path, "rb") as f:
                    response = await client.post(
                        "https://api.openai.com/v1/audio/transcriptions",
                        headers={"Authorization": f"Bearer {api_key}"},
                        files={"file": f},
                        data={
                            "model": "whisper-1",
                            "language": self.config.language
                        },
                        timeout=60
                    )
                    
                if response.status_code == 200:
                    return response.json().get("text", "").strip()
                else:
                    logger.error(f"Whisper API error: {response.status_code}")
                    return ""
                    
        except Exception as e:
            logger.error(f"Whisper API failed: {e}")
            return ""
            
    async def _transcribe_vosk(self, audio_path: str) -> str:
        """Transcribe using Vosk."""
        if not self._vosk_model:
            return ""
            
        try:
            from vosk import KaldiRecognizer
            
            wf = wave.open(audio_path, "rb")
            if wf.getnchannels() != 1 or wf.getsampwidth() != 2 or wf.getcomptype() != "NONE":
                logger.error("Audio file must be WAV format mono PCM")
                return ""
                
            recognizer = KaldiRecognizer(self._vosk_model, wf.getframerate())
            
            results = []
            while True:
                data = wf.readframes(4000)
                if len(data) == 0:
                    break
                if recognizer.AcceptWaveform(data):
                    result = recognizer.Result()
                    results.append(result)
                    
            final_result = recognizer.FinalResult()
            results.append(final_result)
            
            # Parse results
            import json
            text_parts = []
            for r in results:
                data = json.loads(r)
                if "text" in data and data["text"]:
                    text_parts.append(data["text"])
                    
            return " ".join(text_parts)
            
        except Exception as e:
            logger.error(f"Vosk transcription failed: {e}")
            return ""
            
    async def _transcribe_system(self, audio_path: str) -> str:
        """Transcribe using system recognition (macOS)."""
        system = platform.system()
        
        if system == "Darwin":
            # macOS doesn't have a CLI STT, would need custom implementation
            logger.warning("macOS system STT not implemented, use Whisper")
            return ""
        else:
            logger.warning(f"System STT not available on {system}")
            return ""
            
    async def record_and_transcribe(self, duration: int = 5) -> str:
        """
        Record audio for a duration and transcribe.
        
        Args:
            duration: Recording duration in seconds
            
        Returns:
            Transcribed text
        """
        audio_path = await self._record_audio(duration)
        if audio_path:
            return await self.transcribe(audio_path)
        return ""
        
    async def _record_audio(self, duration: int) -> Optional[str]:
        """Record audio to temp file."""
        system = platform.system()
        temp_path = tempfile.mktemp(suffix=".wav")
        
        try:
            if system == "Darwin":
                # Use sox or ffmpeg
                cmd = [
                    "sox", "-d",  # default input device
                    "-r", str(self.config.sample_rate),
                    "-c", "1",  # mono
                    temp_path,
                    "trim", "0", str(duration)
                ]
            elif system == "Linux":
                cmd = [
                    "arecord",
                    "-D", "plughw:1,0",  # default mic
                    "-f", "S16_LE",
                    "-r", str(self.config.sample_rate),
                    "-c", "1",
                    "-d", str(duration),
                    temp_path
                ]
            else:
                return None
                
            proc = await asyncio.create_subprocess_exec(*cmd)
            await proc.wait()
            
            return temp_path if proc.returncode == 0 else None
            
        except Exception as e:
            logger.error(f"Recording failed: {e}")
            return None
            
    def start_continuous(self, callback: Callable[[str], None]) -> None:
        """Start continuous listening (for wake word)."""
        # This would integrate with wake word detector
        pass


# Global instance
_stt: Optional[SpeechToText] = None


def get_stt_engine(config: STTConfig = None) -> SpeechToText:
    """Get or create global STT engine."""
    global _stt
    if _stt is None:
        _stt = SpeechToText(config)
    return _stt
