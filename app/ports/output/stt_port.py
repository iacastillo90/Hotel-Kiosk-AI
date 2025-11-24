from abc import ABC, abstractmethod
from typing import AsyncGenerator
from dataclasses import dataclass


@dataclass
class STTResponse:
    """Response del Speech-to-Text"""
    text: str
    language: str
    confidence: float  # 0.0 - 1.0
    latency_ms: float


class STTPort(ABC):
    """
    Contrato para Speech-to-Text (Whisper, Azure, Google).
    Define comportamiento sin acoplar tecnología.
    """
    
    @abstractmethod
    async def transcribe(self, audio_bytes: bytes) -> STTResponse:
        """
        Transcribe audio a texto.
        
        Args:
            audio_bytes: Audio en formato raw bytes (WAV)
            
        Returns:
            Texto transcrito con metadatos
        """
        pass
    
    @abstractmethod
    def set_language(self, language: str) -> None:
        """
        Configura el idioma de transcripción.
        
        Args:
            language: Código ISO-639-1 (ej: "es", "en")
        """
        pass

    @abstractmethod
    async def transcribe_stream(self, audio_stream: AsyncGenerator[bytes, None]) -> AsyncGenerator[str, None]:
        """
        Transcribe audio en tiempo real y devuelve la transcripción incremental.
        
        Args:
            audio_stream: Generador asíncrono de chunks de audio.
            
        Yields:
            Chunk de texto o transcripción parcial actualizada.
        """
        pass
