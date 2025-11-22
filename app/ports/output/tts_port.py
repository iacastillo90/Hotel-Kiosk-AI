from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class TTSRequest:
    """Request para Text-to-Speech"""
    text: str
    language: str = "es"
    voice_id: Optional[str] = None
    speed: float = 1.0


@dataclass
class TTSResponse:
    """Response del TTS"""
    audio_bytes: bytes
    duration_ms: float
    latency_ms: float


class TTSPort(ABC):
    """
    Contrato para Text-to-Speech (ElevenLabs, pyttsx3, Azure).
    Define comportamiento sin acoplar tecnología.
    """
    
    @abstractmethod
    async def synthesize(self, request: TTSRequest) -> TTSResponse:
        """
        Sintetiza texto a audio.
        
        Args:
            request: Solicitud con texto y configuración
            
        Returns:
            Audio sintetizado con metadatos
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
