import asyncio
import os
import logging
import re  # <--- Necesario para split inteligente
from typing import Optional, AsyncGenerator

try:
    from elevenlabs.client import ElevenLabs
except ImportError:
    print("⚠️ elevenlabs no instalado.")
    ElevenLabs = None

from app.ports.output.tts_port import TTSPort

logger = logging.getLogger(__name__)

class ElevenLabsAdapter(TTSPort):
    def __init__(self, api_key: Optional[str] = None, voice_id: str = "21m00Tcm4TlvDq8ikWAM"):
        if ElevenLabs is None:
            raise ImportError("elevenlabs no está instalado")
        
        self.api_key = api_key or os.getenv("ELEVENLABS_API_KEY")
        if not self.api_key:
            raise ValueError("ELEVENLABS_API_KEY no configurada")
        
        self.client = ElevenLabs(api_key=self.api_key)
        self.voice_id = voice_id
        logger.info("✓ ElevenLabs: Sentence-Splitting Streaming activo")
    
    async def synthesize_stream(self, text_stream: AsyncGenerator[str, None]) -> AsyncGenerator[bytes, None]:
        """
        Acumula texto y lo procesa frase por frase de forma segura.
        """
        buffer = ""
        loop = asyncio.get_event_loop()

        async for chunk in text_stream:
            if not chunk: continue
            buffer += chunk
            
            # Bucle para procesar TODAS las frases completas en el buffer
            while True:
                # Buscar el primer delimitador de frase (. ? ! : \n)
                # Regex mejorado: Ignora puntos si están entre números (ej: "Km 7.5")
                match = re.search(r'(?<!\d)[.?!:\n](?!\d)', buffer)
                if not match:
                    break # No hay frase completa aún, seguir acumulando
                
                # Cortar justo después del delimitador
                split_idx = match.end()
                sentence = buffer[:split_idx].strip()
                buffer = buffer[split_idx:] # Guardar el resto
                
                if sentence:
                    # Sintetizar frase encontrada
                    async for audio_chunk in self._generate_audio(sentence, loop):
                        yield audio_chunk

        # FLUSH FINAL: Procesar lo que quede en el buffer (aunque no tenga punto final)
        if buffer.strip():
            async for audio_chunk in self._generate_audio(buffer.strip(), loop):
                yield audio_chunk

    async def _generate_audio(self, text: str, loop) -> AsyncGenerator[bytes, None]:
        """Helper para llamar a la API y manejar errores"""
        logger.info(f"🗣️ TTS: '{text}'")
        try:
            # Ejecutar llamada bloqueante en thread
            audio_generator = await loop.run_in_executor(
                None,
                lambda: self.client.generate(
                    text=text,
                    voice=self.voice_id,
                    model="eleven_multilingual_v2",
                    stream=True
                )
            )
            
            # Iterar el generador de ElevenLabs (que es síncrono) en el thread principal
            # Nota: Esto es rápido porque los bytes ya están bajando
            for chunk in audio_generator:
                yield chunk
                
        except Exception as e:
            logger.error(f"❌ Error TTS en frase '{text}': {e}")

    async def health_check(self) -> bool:
        return True
