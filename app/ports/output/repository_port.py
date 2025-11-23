from abc import ABC, abstractmethod
from typing import Dict, Any

class RepositoryPort(ABC):
    @abstractmethod
    async def save_booking(self, booking_data: Dict[str, Any]) -> bool:
        """Guarda una reserva en la base de datos"""
        pass

    @abstractmethod
    async def log_interaction(self, user_text: str, intent: str, response: str) -> None:
        """Guarda logs de conversación para analítica"""
        pass
