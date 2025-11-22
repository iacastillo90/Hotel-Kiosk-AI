import whisper
import asyncio
import time
import tempfile
import os
from typing import Optional

from app.ports.output.stt_port import STTPort, STTResponse


class WhisperLocalAdapter(STTPort):
    """
    Adaptador para Whisper local (offline).
    
    Implementa el contrato STTPort usando OpenAI Whisper localmente.
    
    Características:
    - 100% offline (no requiere internet)
    - Modelos: tiny (~39MB, rápido) o base (~140MB, preciso)
    - Latencia: ~200-500ms en Intel N100
    - Privacidad: Audio nunca sale del dispositivo
    
    Ventajas vs Cloud STT:
    - Sin latencia de red
    - Sin costos por request
    - Sin límites de uso
    - Privacidad garantizada
    
    Trade-offs:
    - Menor precisión que modelos cloud (95% vs 98%)
    - Consume CPU localmente
    - Primera ejecución lenta (carga modelo)
    """
    
    def __init__(self, model_size: str = "base", language: str = "es"):
        """
        Constructor.
        
        Args:
            model_size: Tamaño del modelo ('tiny', 'base', 'small', 'medium', 'large')
                       - tiny: ~39MB, más rápido (~200ms), menos preciso
                       - base: ~140MB, balance (~500ms), buena precisión ✓ RECOMENDADO
                       - small: ~460MB, más lento (~1s), mejor precisión
            language: Código ISO-639-1 del idioma (ej: "es", "en")
        
        Raises:
            RuntimeError: Si el modelo no se puede cargar
        """
        self.model_size = model_size
        self.language = language
        
        print(f"📥 Cargando modelo Whisper ({model_size})...")
        
        try:
            # Cargar modelo (primera vez descarga ~140MB)
            self.model = whisper.load_model(model_size)
            print(f"✓ Whisper {model_size} cargado")
        except Exception as e:
            raise RuntimeError(f"Error cargando Whisper: {e}")
    
    async def transcribe(self, audio_bytes: bytes) -> STTResponse:
        """
        Transcribe audio a texto (offline).
        
        Args:
            audio_bytes: Audio en formato WAV (16-bit PCM, mono, 16kHz)
            
        Returns:
            Texto transcrito con metadatos
            
        Raises:
            Exception: Si la transcripción falla
        """
        start_time = time.time()
        
        try:
            # Whisper requiere un archivo WAV válido con encabezado
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp_path = tmp.name
            
            # Escribir encabezado WAV usando wave module
            import wave
            with wave.open(tmp_path, 'wb') as wav_file:
                wav_file.setnchannels(1)        # Mono
                wav_file.setsampwidth(2)        # 16-bit (2 bytes)
                wav_file.setframerate(16000)    # 16kHz
                wav_file.writeframes(audio_bytes)
            
            # Transcribir (bloqueante, pero local)
            # Ejecutamos en executor para no bloquear event loop
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self.model.transcribe(
                    tmp_path,
                    language=self.language,
                    fp16=False,  # Desactivar FP16 para compatibilidad CPU
                )
            )
            
            # Limpiar archivo temporal
            try:
                os.unlink(tmp_path)
            except:
                pass
            
            latency_ms = (time.time() - start_time) * 1000
            
            # Extraer confianza promedio de los segmentos
            confidence = 0.0
            if result.get('segments'):
                confidences = [seg.get('avg_logprob', 0.0) for seg in result['segments']]
                if confidences:
                    # avg_logprob está en escala logarítmica negativa
                    # Convertir a 0-1 (aproximado)
                    confidence = min(1.0, max(0.0, 1.0 + (sum(confidences) / len(confidences)) / 5.0))
            
            return STTResponse(
                text=result['text'].strip(),
                language=self.language,
                confidence=confidence,
                latency_ms=latency_ms
            )
            
        except Exception as e:
            print(f"✗ Error STT: {e}")
            raise
    
    def set_language(self, language: str) -> None:
        """
        Configura el idioma de transcripción.
        
        Args:
            language: Código ISO-639-1 (ej: "es", "en", "fr")
        """
        self.language = language
        print(f"✓ Idioma STT configurado a: {language}")
