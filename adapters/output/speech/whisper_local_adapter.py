import asyncio
import time
import numpy as np
import io
import logging
from typing import Optional

# Usamos faster_whisper en lugar de whisper estándar
try:
    from faster_whisper import WhisperModel
except ImportError:
    raise ImportError("Instala faster-whisper: pip install faster-whisper")

from app.ports.output.stt_port import STTPort, STTResponse

# Configuración de Logging
logger = logging.getLogger(__name__)

class WhisperLocalAdapter(STTPort):
    """
    Adaptador optimizado usando Faster-Whisper (CTranslate2).
    
    Mejoras vs versión anterior:
    1. IN-MEMORY: No escribe archivos temporales (WAV) en disco.
    2. VELOCIDAD: Usa CTranslate2 (hasta 4x más rápido en CPU).
    3. QUANTIZATION: Usa int8 para inferencia veloz sin perder mucha precisión.
    """
    
    def __init__(self, model_size: str = "base", language: str = "es"):
        """
        Inicializa el modelo optimizado.
        Args:
            model_size: 'tiny', 'base', 'small' (Recomendado 'base' o 'small' para CPU)
            language: 'es'
        """
        self.model_size = model_size
        self.language = language
        self._model: Optional[WhisperModel] = None
        
        # Warm-up en inicialización (bloqueante intencional al inicio para no sufrir después)
        logger.info(f"🚀 Cargando Faster-Whisper ({model_size}) en CPU con int8...")
        start = time.time()
        
        # device="cpu", compute_type="int8" es la clave para velocidad en laptops/kioscos
        self._model = WhisperModel(model_size, device="cpu", compute_type="int8")
        
        logger.info(f"✓ Modelo cargado en {time.time() - start:.2f}s")

    async def transcribe(self, audio_bytes: bytes) -> STTResponse:
        """
        Transcribe audio directamente desde memoria sin tocar el disco.
        """
        if not audio_bytes:
            raise ValueError("Audio bytes vacíos")

        start_time = time.time()
        
        loop = asyncio.get_event_loop()
        
        try:
            # 1. Pre-procesamiento de audio (CPU Bound) -> Ejecutar en thread
            # Convertir bytes raw (PCM 16-bit) a float32 numpy array normalizado
            audio_array = await loop.run_in_executor(None, self._bytes_to_float_array, audio_bytes)
            
            # 2. Inferencia (CPU Bound intenso) -> Ejecutar en thread
            result_text, confidence = await loop.run_in_executor(
                None, 
                self._run_inference, 
                audio_array
            )
            
            latency_ms = (time.time() - start_time) * 1000
            
            logger.info(f"🎙️ STT: '{result_text}' | Conf: {confidence:.2f} | ⏱️ {latency_ms:.0f}ms")
            
            return STTResponse(
                text=result_text,
                language=self.language,
                confidence=confidence,
                latency_ms=latency_ms
            )
            
        except Exception as e:
            logger.error(f"✗ Error STT Crítico: {e}")
            # Fallback silencioso o re-raise según política
            return STTResponse(text="", language=self.language, confidence=0.0, latency_ms=0.0)

    def _bytes_to_float_array(self, audio_bytes: bytes) -> np.ndarray:
        """Convierte bytes PCM 16-bit a array Float32 normalizado (-1.0 a 1.0)"""
        # Asumimos que audio_bytes viene directo de pyaudio (int16)
        # frombuffer es CERO-COPY (muy rápido)
        int16_array = np.frombuffer(audio_bytes, dtype=np.int16)
        
        # Normalización vectorizada
        return int16_array.astype(np.float32) / 32768.0

    def _run_inference(self, audio_array: np.ndarray) -> tuple[str, float]:
        """Ejecuta la inferencia bloqueante de Faster-Whisper"""
        segments, info = self._model.transcribe(
            audio_array,
            language=self.language,
            beam_size=5,
            vad_filter=True,  # VAD interno ayuda a filtrar ruido extra
            vad_parameters=dict(min_silence_duration_ms=500)
        )
        
        # Faster-whisper devuelve un generador, hay que consumirlo
        text_segments = []
        scores = []
        
        for segment in segments:
            text_segments.append(segment.text)
            scores.append(np.exp(segment.avg_logprob)) # logprob a probabilidad
            
        final_text = " ".join(text_segments).strip()
        
        # Calcular confianza promedio
        avg_confidence = sum(scores) / len(scores) if scores else 0.0
        
        return final_text, avg_confidence

    def set_language(self, language: str) -> None:
        self.language = language
