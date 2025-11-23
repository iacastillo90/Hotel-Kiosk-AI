from enum import Enum
from dataclasses import dataclass
from typing import Dict, Any, Optional

class Intent(Enum):
    GREETING = "greeting"       # Hola, buenos días -> Respuesta Script (Rápido)
    CHECK_IN = "check_in"       # Quiero hacer checkin -> Flujo Lógico
    BOOKING = "booking"         # Quiero reservar -> Flujo Lógico
    INFO = "info"               # ¿A qué hora es el desayuno? -> RAG + LLM (Lento)
    CONTACT = "contact"         # Contacto humano
    UNKNOWN = "unknown"         # ??? -> Fallback

@dataclass
class IntentResult:
    intent: Intent
    confidence: float
    entities: Dict[str, Any] # Ej: {"date": "2023-10-10"}

class IntentService:
    """
    Servicio de dominio para clasificar intenciones.
    Puede usar RegEx (ultra rápido) o Embeddings (rápido) o LLM Zero-shot (lento).
    """
    
    def detect_intent(self, text: str) -> IntentResult:
        text_lower = text.lower().strip()
        
        # 1. Heurísticas Rápidas (RegEx / Keywords) - Latencia < 1ms
        if any(w in text_lower for w in ["hola", "buenos dias", "buenas tardes", "hey", "buenas"]):
            return IntentResult(Intent.GREETING, 1.0, {})
            
        if any(w in text_lower for w in ["check-in", "check in", "llegada", "registrarme", "registro"]):
            return IntentResult(Intent.CHECK_IN, 0.9, {})
            
        if any(w in text_lower for w in ["reservar", "reserva", "habitacion", "cuarto", "alojamiento"]):
            return IntentResult(Intent.BOOKING, 0.8, {})
            
        if any(w in text_lower for w in ["contacto", "llamar", "telefono", "email", "correo", "hablar con alguien"]):
            return IntentResult(Intent.CONTACT, 0.9, {})

        if any(w in text_lower for w in ["horario", "donde", "ubicacion", "wifi", "clave", "piscina", "desayuno", "cena", "restaurante", "gym", "gimnasio"]):
            return IntentResult(Intent.INFO, 0.8, {})
            
        # 2. (Opcional Futuro) Semantic Search con ChromaDB para clasificación
        
        # Default
        return IntentResult(Intent.UNKNOWN, 0.0, {})
