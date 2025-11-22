from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from typing import Optional


class MessageRole(Enum):
    """Roles posibles en una conversación"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


@dataclass
class Message:
    """
    Representa un mensaje en la conversación.
    Python puro, sin dependencias externas.
    """
    content: str
    role: MessageRole
    timestamp: datetime = field(default_factory=datetime.now)
    audio_duration_ms: Optional[float] = None  # Para métricas


@dataclass
class HotelContext:
    """
    Contexto relevante del hotel obtenido de RAG.
    Representa información extraída del vector store.
    """
    hotel_name: str
    information: str  # Texto extraído
    relevance_score: float  # 0.0 - 1.0
    
    def __post_init__(self):
        """Validación"""
        if not 0.0 <= self.relevance_score <= 1.0:
            raise ValueError(f"relevance_score debe estar entre 0 y 1, recibido: {self.relevance_score}")


@dataclass
class AssistantResponse:
    """
    Respuesta estructurada del asistente.
    Contiene la respuesta + metadatos.
    """
    text: str
    context: Optional[HotelContext]
    confidence: float  # 0.0 - 1.0 (Para futuro AI feedback)
    processing_time_ms: float
    
    def __post_init__(self):
        """Validación"""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence debe estar entre 0 y 1, recibido: {self.confidence}")
