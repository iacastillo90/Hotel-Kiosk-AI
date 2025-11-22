from enum import Enum
from dataclasses import dataclass
import re


class Intent(Enum):
    """Intents soportados por el sistema"""
    CHECK_IN = "check_in"
    BOOKING = "booking"
    CONTACT = "contact"
    INFO = "info"  # Pregunta general
    GREETING = "greeting"
    UNKNOWN = "unknown"


@dataclass
class IntentResult:
    """Resultado de detección de intent"""
    intent: Intent
    confidence: float  # 0.0 - 1.0
    entities: dict  # {entity_type: value}


class IntentService:
    """
    Detecta intenciones del usuario usando patterns y/o ML.
    Python puro, sin dependencias externas.
    """
    
    def __init__(self):
        # Patterns simples (regex) para cada intent
        self.patterns = {
            Intent.CHECK_IN: [
                r"check.?in", r"hacer.*entrada", r"registra.*llegada"
            ],
            Intent.BOOKING: [
                r"reserv", r"book", r"mesa", r"restaurante"
            ],
            Intent.CONTACT: [
                r"teléfono", r"email", r"contacto", r"llamar"
            ],
            Intent.GREETING: [
                r"hola", r"buenos", r"hi", r"hello", r"saludos"
            ],
        }
    
    def detect_intent(self, text: str) -> IntentResult:
        """
        Detecta intent de un texto.
        
        Args:
            text: Mensaje del usuario
            
        Returns:
            IntentResult con intent detectado y confianza
        """
        text_lower = text.lower()
        scores = {}
        
        # Scoring basado en patterns
        for intent, patterns in self.patterns.items():
            score = 0
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    score += 1
            scores[intent] = score
        
        # Encontrar intent con máximo score
        if max(scores.values()) > 0:
            best_intent = max(scores, key=scores.get)
            confidence = min(scores[best_intent] / 2, 1.0)  # Normalizar
        else:
            best_intent = Intent.UNKNOWN
            confidence = 0.0
        
        # Extraer entidades según el intent
        entities = self._extract_entities(text_lower, best_intent)
        
        return IntentResult(
            intent=best_intent,
            confidence=confidence,
            entities=entities
        )
    
    def _extract_entities(self, text: str, intent: Intent) -> dict:
        """
        Extrae entidades según el intent.
        
        Args:
            text: Texto en lowercase
            intent: Intent detectado
            
        Returns:
            Diccionario con entidades extraídas
        """
        entities = {}
        
        if intent == Intent.BOOKING:
            # Buscar fechas (formato DD/MM)
            date_match = re.search(r'(\d{1,2})[/-](\d{1,2})', text)
            if date_match:
                entities["date"] = f"{date_match.group(1)}/{date_match.group(2)}"
            
            # Buscar hora
            time_match = re.search(r'(\d{1,2}):?(\d{2})?', text)
            if time_match:
                hour = time_match.group(1)
                minute = time_match.group(2) or "00"
                entities["time"] = f"{hour}:{minute}"
            
            # Buscar número de personas
            party_match = re.search(r'(\d+)\s*(?:person|gente|comensales)', text)
            if party_match:
                entities["party_size"] = int(party_match.group(1))
        
        return entities
