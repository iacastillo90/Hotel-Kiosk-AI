from abc import ABC, abstractmethod
from typing import Callable, Optional


class AudioInputPort(ABC):
    """
    Contrato para captura de audio.
    Define comportamiento sin acoplar tecnología (PyAudio, etc).
    """
    
    @abstractmethod
    def start_listening(self,
                       on_audio_chunk: Callable[[bytes], None],
                       on_silence_detected: Callable[[], None]) -> None:
        """
        Inicia la escucha de audio con callbacks.
        
        Args:
            on_audio_chunk: Callback cuando se captura audio (streaming)
            on_silence_detected: Callback cuando se detecta silencio (fin de discurso)
        """
        pass
    
    @abstractmethod
    def stop_listening(self) -> None:
        """Detiene la escucha de audio"""
        pass
    
    @abstractmethod
    def get_last_audio_chunk(self) -> Optional[bytes]:
        """
        Retorna el último chunk de audio capturado.
        
        Returns:
            Audio bytes o None si no hay audio
        """
        pass
