import asyncio
import time
import os
import queue
import threading
from typing import Optional, AsyncGenerator, Iterator

try:
    from elevenlabs.client import ElevenLabs
except ImportError:
    print("⚠️ elevenlabs no instalado. Usa: pip install elevenlabs")
    ElevenLabs = None

from app.ports.output.tts_port import TTSPort, TTSRequest


class ElevenLabsAdapter(TTSPort):
    """
    Adaptador para ElevenLabs TTS con Streaming E2E.
    
    Conecta el stream de texto del LLM directamente al stream de audio de ElevenLabs.
    """
    
    def __init__(self, api_key: Optional[str] = None, voice_id: str = "21m00Tcm4TlvDq8ikWAM"):
        """
        Constructor.
        
        Args:
            api_key: ElevenLabs API Key
            voice_id: ID de la voz a usar
        """
        if ElevenLabs is None:
            raise ImportError("elevenlabs no está instalado")
            
        self.api_key = api_key or os.getenv("ELEVENLABS_API_KEY")
        if not self.api_key:
            raise ValueError("ELEVENLABS_API_KEY no configurada")
        
        # Inicializar cliente de ElevenLabs
        self.client = ElevenLabs(api_key=self.api_key)
        self.voice_id = voice_id
        
        print("✓ ElevenLabs Adapter inicializado (Streaming habilitado)")
    
    async def synthesize_stream(self, text_stream: AsyncGenerator[str, None]) -> AsyncGenerator[bytes, None]:
        """
        Sintetiza un stream de texto a un stream de audio.
        
        Nota: ElevenLabs requiere el texto completo, no soporta streaming de entrada.
        Acumulamos todo el texto y luego generamos audio.
        """
        # Acumular todo el texto
        full_text = ""
        async for chunk in text_stream:
            if chunk:
                full_text += chunk
        
        if not full_text:
            # No hay texto, terminar sin yield (no usar return)
            pass
        else:
            # Generar audio con el texto completo
            loop = asyncio.get_event_loop()
            
            def _generate_audio_stream():
                try:
                    return self.client.text_to_speech.convert(
                        voice_id=self.voice_id,
                        text=full_text,  # String completo, no generador
                        model_id="eleven_multilingual_v2",
                        output_format="pcm_16000",
                        voice_settings={
                            "stability": 0.5,
                            "similarity_boost": 0.75,
                        }
                    )
                except Exception as e:
                    print(f"✗ Error ElevenLabs Stream: {e}")
                    raise e
            
            # Obtener el generador de audio
            audio_generator = await loop.run_in_executor(None, _generate_audio_stream)
            
            # Consumir y yield audio chunks
            audio_iterator = iter(audio_generator)
            
            def safe_next():
                """Wrapper para evitar que StopIteration escape a asyncio"""
                try:
                    return next(audio_iterator)
                except StopIteration:
                    return None
            
            while True:
                try:
                    chunk = await loop.run_in_executor(None, safe_next)
                    
                    if chunk is None:
                        break
                        
                    yield chunk
                    
                except Exception as e:
                    print(f"⚠️ Error en chunk de audio: {e}")
                    raise e

    async def health_check(self) -> bool:
        """Verifica disponibilidad de ElevenLabs"""
        try:
            # Prueba simple no-streaming
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None, 
                lambda: self.client.text_to_speech.convert(
                    voice_id=self.voice_id,
                    text="test",
                    model_id="eleven_multilingual_v2"
                )
            )
            return True
        except:
            return False
