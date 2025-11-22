import webrtcvad
import numpy as np
from collections import deque


class VADFilter:
    """
    Voice Activity Detection usando WebRTC VAD.
    
    WebRTC VAD es un detector de voz robusto desarrollado por Google
    para WebRTC (comunicaciones en tiempo real). Es superior a filtros
    de energía simples porque:
    
    - Detecta características espectrales de voz humana
    - Robusto ante ruido ambiente (música, ventiladores, etc)
    - Múltiples modos de agresividad
    - Optimizado para tiempo real
    
    Modos:
    - 0: Menos agresivo (detecta más, puede incluir ruido)
    - 1: Normal
    - 2: Agresivo
    - 3: Muy agresivo (solo voz clara) ✓ RECOMENDADO para Expo
    """
    
    def __init__(self,
                 sample_rate: int = 16000,
                 frame_duration_ms: int = 30,
                 mode: int = 3,
                 min_speech_frames: int = 5):
        """
        Constructor.
        
        Args:
            sample_rate: Hz (debe ser 8000, 16000, 32000 o 48000)
            frame_duration_ms: Duración del frame (10, 20 o 30 ms)
            mode: Agresividad (0-3, donde 3 es más estricto)
            min_speech_frames: Mínimo de frames de voz para activar detección
        """
        if sample_rate not in [8000, 16000, 32000, 48000]:
            raise ValueError(f"sample_rate debe ser 8000, 16000, 32000 o 48000, recibido: {sample_rate}")
        
        if frame_duration_ms not in [10, 20, 30]:
            raise ValueError(f"frame_duration_ms debe ser 10, 20 o 30, recibido: {frame_duration_ms}")
        
        self.sample_rate = sample_rate
        self.frame_duration_ms = frame_duration_ms
        self.frame_size = int(sample_rate * frame_duration_ms / 1000)
        
        # Inicializar WebRTC VAD
        self.vad = webrtcvad.Vad()
        self.vad.set_mode(mode)
        
        # Estado
        self.min_speech_frames = min_speech_frames
        self.speech_frames = deque(maxlen=min_speech_frames)
        self.silence_frames = 0
        self.speech_detected = False
        
        print(f"✓ VAD inicializado (modo {mode}, frame {frame_duration_ms}ms)")
    
    def is_speech(self, audio_chunk: bytes) -> bool:
        """
        Determina si el chunk contiene voz humana.
        
        Args:
            audio_chunk: Audio en formato raw bytes (16-bit PCM)
            
        Returns:
            True si hay voz, False si es silencio/ruido
        """
        try:
            # WebRTC VAD requiere frames de tamaño específico
            # Si el chunk es más grande, procesamos por frames
            is_speech_detected = False
            
            # Procesar en frames del tamaño correcto
            frame_bytes = self.frame_size * 2  # 2 bytes por sample (16-bit)
            
            for i in range(0, len(audio_chunk), frame_bytes):
                frame = audio_chunk[i:i + frame_bytes]
                
                # Si el frame es muy corto, rellenar con ceros
                if len(frame) < frame_bytes:
                    frame = frame + b'\x00' * (frame_bytes - len(frame))
                
                # Detectar voz en este frame
                try:
                    is_speech_frame = self.vad.is_speech(frame, self.sample_rate)
                    if is_speech_frame:
                        is_speech_detected = True
                        break
                except:
                    # Si hay error, asumir que no es voz
                    continue
            
            # Actualizar estado
            if is_speech_detected:
                self.speech_frames.append(True)
                self.silence_frames = 0
                
                # Activar detección si tenemos suficientes frames de voz
                if len(self.speech_frames) == self.min_speech_frames:
                    self.speech_detected = True
            else:
                self.speech_frames.append(False)
                self.silence_frames += 1
            
            return is_speech_detected
            
        except Exception as e:
            print(f"⚠️ Error en VAD: {e}")
            return False
    
    def is_silence_timeout(self, max_silence_frames: int = 30) -> bool:
        """
        Detecta si hubo suficiente silencio para terminar la captura.
        
        Args:
            max_silence_frames: Máximo de frames silenciosos antes de terminar
            
        Returns:
            True si hemos detectado suficiente silencio después de voz
        """
        if not self.speech_detected:
            return False
        
        return self.silence_frames > max_silence_frames
    
    def reset(self) -> None:
        """Reinicia el detector"""
        self.speech_frames.clear()
        self.silence_frames = 0
        self.speech_detected = False
