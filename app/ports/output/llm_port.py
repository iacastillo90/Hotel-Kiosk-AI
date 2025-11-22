from abc import ABC, abstractmethod
from typing import Optional
from dataclasses import dataclass


@dataclass
class LLMRequest:
    """Request structure para el LLM"""
    user_message: str
    conversation_history: str
    hotel_context: Optional[str] = None
    language: str = "es"
    max_tokens: int = 512


@dataclass
class LLMResponse:
    """Response structure del LLM"""
    text: str
    model: str
    tokens_used: int
    latency_ms: float


class LLMPort(ABC):
    """
    Contrato para cualquier LLM (Gemini, GPT, Local).
    Define el comportamiento esperado sin acoplarse a tecnología.
    """
    
    @abstractmethod
    async def generate(self, request: LLMRequest) -> LLMResponse:
        """
        Genera una respuesta basada en el prompt.
        
        Args:
            request: Solicitud con contexto y mensaje del usuario
            
        Returns:
            Respuesta del LLM con texto y metadatos
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
