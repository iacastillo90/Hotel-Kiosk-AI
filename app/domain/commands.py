from dataclasses import dataclass, field
from typing import Any, Optional, List, Dict

@dataclass
class GenerateLLMStreamCommand:
    """Comando para generar un stream de respuesta del LLM."""
    user_message: str
    conversation_history: str = "" # Deprecated/Optional if using conversation object
    hotel_context: str = ""
    emotional_state: str = "Neutral"
    kb_confidence: float = 1.0
    system_latency_ms: int = 0
    tools: Optional[List[Dict[str, Any]]] = None
    language: str = "es"
    # Campos para PromptFactory
    conversation: Any = None 
    context: Any = None

@dataclass
class SearchKnowledgeQuery:
    """Query para buscar contexto RAG."""
    query_text: str
    top_k: int = 3
    min_score: float = 0.5

@dataclass
class SynthesizeTTSCommand:
    """Comando para sintetizar voz."""
    text_stream: Any # AsyncGenerator[str, None]

@dataclass
class SaveBookingCommand:
    """Comando para guardar una reserva."""
    booking_data: Dict[str, Any]

@dataclass
class LogInteractionCommand:
    """Comando para loguear una interacción."""
    user_text: str
    intent: str
    response_text: str
