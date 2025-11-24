from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, AsyncGenerator


@dataclass
class TTSRequest:
    """Request para Text-to-Speech (Legacy)"""
    text: str
    language: str = "es"
    voice_id: Optional[str] = None
    speed: float = 1.0


@dataclass
class TTSResponse:
    """Response del TTS (Legacy)"""
    audio_bytes: bytes
    duration_ms: float
    latency_ms: float


class TTSPort(ABC):
    """
    Contrato para Text-to-Speech (ElevenLabs, pyttsx3, Azure).
    Define comportamiento sin acoplar tecnología.
    """
    
    @abstractmethod
    async def synthesize_stream(self, text_stream: AsyncGenerator[str, None]) -> AsyncGenerator[bytes, None]:
        """
        Sintetiza un stream de texto a un stream de audio.
        
        Args:
            text_stream: Generador asíncrono de chunks de texto desde el LLM
            
        Yields:
            Chunk de bytes de audio (para reproducción inmediata)
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """
        Verifica disponibilidad del servicio TTS.
        
        Returns:
            True si el servicio está disponible
        """
        pass
