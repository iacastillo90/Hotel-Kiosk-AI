from typing import Dict, Any
from app.ports.output.repository_port import RepositoryPort

class MockRepositoryAdapter(RepositoryPort):
    """
    Simula una base de datos para desarrollo local.
    No requiere MySQL instalado.
    """
    async def save_booking(self, booking_data: Dict[str, Any]) -> bool:
        print(f"📝 [MOCK DB] Guardando reserva simulada: {booking_data}")
        return True

    async def log_interaction(self, user_text: str, intent: str, response: str) -> None:
        # No hacemos print aquí para no ensuciar la consola, o solo debug
        pass
