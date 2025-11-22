import asyncio
import time
import os
from typing import Optional

try:
    from elevenlabs.client import ElevenLabs
except ImportError:
    print("⚠️ elevenlabs no instalado. Usa: pip install elevenlabs")
    ElevenLabs = None

from app.ports.output.tts_port import TTSPort, TTSRequest, TTSResponse
from adapters.utils.resilience import CircuitBreaker, retry_async


class ElevenLabsAdapter(TTSPort):
    """
    Adaptador para ElevenLabs TTS (Cloud, alta calidad).
    
    Características:
    - Voz natural de alta calidad
    - Latencia: ~300-500ms
    - Streaming: Puede empezar a reproducir antes de terminar
    - Costo: ~$0.30 por 1000 caracteres
    
    Ventajas vs TTS Local:
    - Calidad superior (suena humano)
    - Rápido (más que pyttsx3)
    - Soporte para múltiples voces/idiomas
    
    Trade-offs:
    - Requiere internet
    - Costos por uso
    - Dependencia de servicio externo
    """
    
    def __init__(self, api_key: Optional[str] = None, voice_id: str = "21m00Tcm4TlvDq8ikWAM"):
        """
        Constructor.
        
        Args:
            api_key: ElevenLabs API Key
            voice_id: ID de la voz a usar (default: Rachel - femenina, natural)
            
        Raises:
            ValueError: Si no se encuentra API key
        """
        if ElevenLabs is None:
            raise ImportError("elevenlabs no está instalado")
            
        self.api_key = api_key or os.getenv("ELEVENLABS_API_KEY")
        if not self.api_key:
            raise ValueError("ELEVENLABS_API_KEY no configurada")
        
        # Inicializar cliente de ElevenLabs (nueva API)
        self.client = ElevenLabs(api_key=self.api_key)
        self.voice_id = voice_id
        
        # Circuit Breaker
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=3,
            recovery_timeout_s=30
        )
        
        print("✓ ElevenLabs Adapter inicializado")
    
    @retry_async(max_retries=2, initial_delay_s=0.2)
    async def synthesize(self, request: TTSRequest) -> TTSResponse:
        """
        Sintetiza texto a audio con ElevenLabs.
        
        Args:
            request: Solicitud con texto y configuración
            
        Returns:
            Audio sintetizado
        """
        if self.circuit_breaker.is_open():
            raise RuntimeError("Circuit breaker abierto para ElevenLabs")
        
        start_time = time.time()
        
        try:
            # Limitar largo (ElevenLabs cobra por caracteres)
            text = request.text[:1000] if len(request.text) > 1000 else request.text
            
            # Llamada con timeout de 5s (TTS puede tardar)
            response = await asyncio.wait_for(
                self._call_elevenlabs(text, request.speed),
                timeout=5.0
            )
            
            latency_ms = (time.time() - start_time) * 1000
            
            self.circuit_breaker.record_success()
            
            # Estimar duración (aproximado: ~50ms por palabra)
            word_count = len(request.text.split())
            estimated_duration_ms = word_count * 50
            
            return TTSResponse(
                audio_bytes=response,
                duration_ms=estimated_duration_ms,
                latency_ms=latency_ms
            )
            
        except asyncio.TimeoutError:
            print(f"✗ Timeout ElevenLabs (>5s)")
            self.circuit_breaker.record_failure()
            raise
            
        except Exception as e:
            print(f"✗ Error ElevenLabs: {e}")
            self.circuit_breaker.record_failure()
            raise
    
    async def _call_elevenlabs(self, text: str, speed: float) -> bytes:
        """
        Llamada a ElevenLabs (ejecutada en executor).
        
        Args:
            text: Texto a sintetizar
            speed: Velocidad (1.0 = normal)
            
        Returns:
            Audio bytes
        """
        loop = asyncio.get_event_loop()
        
        def _generate():
            # Usar la API v2.x de ElevenLabs
            audio_generator = self.client.text_to_speech.convert(
                voice_id=self.voice_id,
                text=text,
                model_id="eleven_multilingual_v2",
                voice_settings={
                    "stability": 0.5,
                    "similarity_boost": 0.75,
                    "speed": speed
                }
            )
            
            # Convertir el generador a bytes
            audio_bytes = b"".join(audio_generator)
            return audio_bytes
        
        return await loop.run_in_executor(None, _generate)
    
    async def health_check(self) -> bool:
        """Verifica disponibilidad de ElevenLabs"""
        try:
            await asyncio.wait_for(
                self.synthesize(TTSRequest(text="test")),
                timeout=3.0
            )
            return True
        except:
            return False
