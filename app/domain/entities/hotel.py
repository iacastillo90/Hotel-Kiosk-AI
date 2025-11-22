from dataclasses import dataclass, field
from typing import List


@dataclass
class Hotel:
    """
    Información estática del hotel.
    Python puro, sin dependencias.
    """
    name: str
    location: str
    phone: str
    email: str
    check_in_time: str
    check_out_time: str
    amenities: List[str] = field(default_factory=list)
    
    def get_contact_info(self) -> str:
        """Retorna información de contacto formateada"""
        return f"{self.name} - Tel: {self.phone}, Email: {self.email}"
    
    def get_check_times(self) -> str:
        """Retorna horarios de check-in/out"""
        return f"Check-in: {self.check_in_time}, Check-out: {self.check_out_time}"
