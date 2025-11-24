import pyttsx3
import asyncio
import time
import tempfile
import os
from typing import AsyncGenerator

from app.ports.output.tts_port import TTSPort, TTSRequest, TTSResponse


class Pyttsx3FallbackAdapter(TTSPort):
    """
    Fallback local para TTS (sin red, baja calidad).
    
    Usado cuando ElevenLabs no está disponible.
    
    Características:
    - 100% offline
    - Gratis
    - Latencia: ~1-2s
    - Calidad: Voz robótica (pero comprensible)
    """
    
    def __init__(self):
        """Constructor"""
        try:
            self.engine = pyttsx3.init()
            self.engine.setProperty('rate', 150)  # Velocidad
            self.engine.setProperty('volume', 0.9)
            print("✓ pyttsx3 Fallback Adapter inicializado")
        except Exception as e:
            print(f"⚠️ Error inicializando pyttsx3: {e}")
            self.engine = None
    
    async def synthesize(self, request: TTSRequest) -> TTSResponse:
        """
        Sintetiza con pyttsx3 (bloqueante pero local).
        
        Args:
            request: Solicitud con texto
            
        Returns:
            Audio sintetizado
        """
        start_time = time.time()
        
        try:
            loop = asyncio.get_event_loop()
            audio_bytes = await loop.run_in_executor(
                None,
                lambda: self._synthesize_blocking(request.text)
            )
            
            latency_ms = (time.time() - start_time) * 1000
            
            # Estimar duración
            word_count = len(request.text.split())
            estimated_duration_ms = word_count * 50
            
            return TTSResponse(
                audio_bytes=audio_bytes,
                duration_ms=estimated_duration_ms,
                latency_ms=latency_ms
            )
            
        except Exception as e:
            print(f"✗ Error pyttsx3: {e}")
            raise
    
    def _synthesize_blocking(self, text: str) -> bytes:
        """
        Sintetiza bloqueante.
        
        Args:
            text: Texto a sintetizar
            
        Returns:
            Audio bytes
        """
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name
        
        self.engine.save_to_file(text, tmp_path)
        self.engine.runAndWait()
        
        with open(tmp_path, "rb") as f:
            audio_bytes = f.read()
        
        try:
            os.unlink(tmp_path)
        except:
            pass
        
        return audio_bytes

    async def synthesize_stream(self, text_stream: AsyncGenerator[str, None]) -> AsyncGenerator[bytes, None]:
        """
        Implementación dummy de streaming para pyttsx3.
        Acumula todo el texto y sintetiza al final (no es verdadero streaming).
        """
        full_text = ""
        async for chunk in text_stream:
            full_text += chunk
            
        if full_text:
            # Reutilizamos la lógica de synthesize
            request = TTSRequest(text=full_text)
            response = await self.synthesize(request)
            yield response.audio_bytes

    async def health_check(self) -> bool:
        """Siempre disponible (local)"""
        return self.engine is not None
