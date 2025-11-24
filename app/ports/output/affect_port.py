from abc import ABC, abstractmethod
from typing import AsyncGenerator

class AffectPort(ABC):
    """
    Puerto para análisis afectivo/emocional del audio.
    """
    
    @abstractmethod
    async def analyze_stream(self, audio_stream: AsyncGenerator[bytes, None]) -> str:
        """
        Analiza un stream de audio y determina el estado emocional predominante.
        
        Args:
            audio_stream: Generador de chunks de audio.
            
        Returns:
            String describiendo el estado emocional (ej: "Neutral", "Frustrado", "Apurado").
        """
        pass
