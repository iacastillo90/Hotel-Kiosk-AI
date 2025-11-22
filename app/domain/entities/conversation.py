from dataclasses import dataclass, field
from typing import List
from datetime import datetime
from app.domain.entities.message import Message


@dataclass
class Conversation:
    """
    Gestiona el historial de conversación.
    Python puro, sin dependencias.
    """
    session_id: str
    messages: List[Message] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.now)
    language: str = "es"
    
    def add_message(self, message: Message) -> None:
        """Añade un mensaje al historial"""
        self.messages.append(message)
    
    def get_recent_context(self, n: int = 5) -> str:
        """
        Retorna los últimos N mensajes como contexto para el LLM.
        
        Args:
            n: Número de mensajes recientes a incluir
            
        Returns:
            String con el historial formateado
        """
        recent = self.messages[-n:] if len(self.messages) > n else self.messages
        
        context = "\n".join([
            f"{msg.role.value}: {msg.content}"
            for msg in recent
        ])
        
        return context
    
    def clear_history(self) -> None:
        """Limpia el historial (para nueva conversación)"""
        self.messages.clear()
    
    def get_message_count(self) -> int:
        """Retorna el número total de mensajes"""
        return len(self.messages)
    
    def get_duration_minutes(self) -> float:
        """Calcula la duración de la conversación en minutos"""
        if not self.messages:
            return 0.0
        
        duration = datetime.now() - self.started_at
        return duration.total_seconds() / 60.0
