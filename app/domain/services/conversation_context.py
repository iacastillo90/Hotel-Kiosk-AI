from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from app.domain.services.intent_service import Intent


class ConversationContext:
    """
    Maneja el contexto y estado de la conversación.
    Python puro, sin dependencias.
    """
    
    def __init__(self, session_id: str):
        """
        Constructor.
        
        Args:
            session_id: ID único de la sesión
        """
        self.session_id = session_id
        self.state: Dict[str, Any] = {}
        self.created_at = datetime.now()
        self.last_activity = datetime.now()
        self.intent_history: List[Intent] = []
    
    def set_state(self, key: str, value: Any) -> None:
        """
        Guarda estado en el contexto.
        
        Args:
            key: Clave del estado
            value: Valor a guardar
        """
        self.state[key] = value
        self.last_activity = datetime.now()
    
    def get_state(self, key: str, default: Any = None) -> Any:
        """
        Obtiene estado del contexto.
        
        Args:
            key: Clave del estado
            default: Valor por defecto si no existe
            
        Returns:
            Valor guardado o default
        """
        return self.state.get(key, default)
    
    def is_expired(self, ttl_minutes: int = 30) -> bool:
        """
        Verifica si la sesión ha expirado.
        
        Args:
            ttl_minutes: Tiempo de vida en minutos
            
        Returns:
            True si la sesión expiró
        """
        return (datetime.now() - self.last_activity) > timedelta(minutes=ttl_minutes)
    
    def record_intent(self, intent: Intent) -> None:
        """
        Registra un intent para tracking.
        
        Args:
            intent: Intent detectado
        """
        self.intent_history.append(intent)
    
    def get_session_summary(self) -> str:
        """
        Genera resumen de la sesión para logging.
        
        Returns:
            String con resumen de la sesión
        """
        return (
            f"Session {self.session_id}: "
            f"{len(self.intent_history)} intents, "
            f"state={self.state}"
        )
