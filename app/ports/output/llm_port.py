from abc import ABC, abstractmethod
from typing import Optional, AsyncGenerator
from dataclasses import dataclass


@dataclass
class LLMRequest:
    """Request structure para el LLM"""
    user_message: str
    conversation_history: str
    hotel_context: Optional[str] = None
    emotional_state: str = "Neutral"
    kb_confidence: float = 1.0
    system_latency_ms: int = 0
    system_prompt: Optional[str] = None
    tools: Optional[list] = None
    language: str = "es"
    max_tokens: int = 512

@dataclass
class LLMResponse:
    """Response structure from LLM"""
    text: str
    confidence: float = 1.0

class LLMPort(ABC):
    """
    Contrato para cualquier LLM (Gemini, GPT, Local).
    Define el comportamiento esperado sin acoplarse a tecnología.
    """
    
    @abstractmethod
    async def generate_stream(self, request: LLMRequest) -> AsyncGenerator[str, None]:
        """
        Genera una respuesta en streaming (chunk a chunk).
        
        Args:
            request: Solicitud con contexto y mensaje del usuario
            
        Yields:
            Chunk de texto de la respuesta
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """
        Verifica disponibilidad del LLM.
        
        Returns:
            True si el servicio está disponible
        """
        pass
