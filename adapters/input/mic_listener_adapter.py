import io
import wave
import threading
from typing import Optional, Callable

from app.ports.input.audio_input_port import AudioInputPort
from adapters.input.mic_listener.vad_filter import VADFilter
from adapters.input.mic_listener.pyaudio_handler import PyAudioHandler


class MicListenerAdapter(AudioInputPort):
    """
    Adaptador de micrófono con VAD mejorado.
    
    Orquesta:
    - PyAudioHandler: Captura continua en thread
    - VADFilter: Detección robusta de voz vs ruido
    - Callbacks: Notifica cuando hay audio y cuando termina el discurso
    
    Flujo:
    1. start_listening() → activa PyAudio
    2. Loop continuo:
       - Obtiene chunk del queue
       - Pasa por VAD
       - Si voz: callback on_audio_chunk()
       - Si silencio prolongado: callback on_silence_detected()
    3. stop_listening() → detiene captura
    """
    
    def __init__(self,
                 sample_rate: int = 16000,
                 silence_timeout_ms: float = 750.0):
        """
        Constructor.
        
        Args:
            sample_rate: 16000 Hz (estándar para Whisper)
            silence_timeout_ms: Cuánto silencio para terminar grabación
        """
        self.sample_rate = sample_rate
        self.chunk_size = 1024
        self.silence_timeout_ms = silence_timeout_ms
        
        # Inicializar PyAudio
        self.pyaudio_handler = PyAudioHandler(
            sample_rate=sample_rate,
            chunk_size=self.chunk_size
        )
        
        # Inicializar VAD (modo 3 = muy agresivo)
        self.vad = VADFilter(
            sample_rate=sample_rate,
            frame_duration_ms=30,
            mode=3  # Muy agresivo para ruido de Expo
        )
        
        self.is_listening = False
        self.listener_thread: Optional[threading.Thread] = None
        self.audio_buffer = bytearray()
        self.last_audio_chunk: Optional[bytes] = None
    
    def start_listening(self,
                       on_audio_chunk: Callable[[bytes], None],
                       on_silence_detected: Callable[[], None]) -> None:
        """
        Inicia captura y llama callbacks cuando detecta discurso/silencio.
        
        Args:
            on_audio_chunk: Callback cuando hay audio
            on_silence_detected: Callback cuando detecta fin de discurso
        """
        if self.is_listening:
            print("⚠️ Ya estamos escuchando")
            return
        
        self.is_listening = True
        self.audio_buffer = bytearray()
        
        # Iniciar PyAudio
        self.pyaudio_handler.start_listening()
        
        # Iniciar thread de captura con VAD
        self.listener_thread = threading.Thread(
            target=self._capture_loop,
            args=(on_audio_chunk, on_silence_detected),
            daemon=True
        )
        self.listener_thread.start()
        
        print("🎙️ Micrófono listo (VAD activado)")
    
    def stop_listening(self) -> None:
        """Detiene la captura"""
        self.is_listening = False
        self.pyaudio_handler.stop_listening()
        
        if self.listener_thread:
            self.listener_thread.join(timeout=2.0)
        
        print("✓ Captura detenida")
    
    def _capture_loop(self,
                     on_audio_chunk: Callable[[bytes], None],
                     on_silence_detected: Callable[[], None]) -> None:
        """
        Loop de captura con VAD.
        
        Args:
            on_audio_chunk: Callback para audio
            on_silence_detected: Callback para silencio
        """
        silence_frames = 0
        max_silence_frames = int(
            (self.silence_timeout_ms / 1000.0) * self.sample_rate / self.chunk_size
        )
        
        print(f"📊 Esperando audio... (silencio: {max_silence_frames} frames = {self.silence_timeout_ms}ms)")
        
        try:
            while self.is_listening:
                # Obtener chunk del queue (no bloqueante)
                chunk = self.pyaudio_handler.get_chunk(timeout_s=0.1)
                
                if chunk is None:
                    continue
                
                # Detectar si hay voz usando WebRTC VAD
                has_speech = self.vad.is_speech(chunk)
                
                if has_speech:
                    # Resetear contador de silencio
                    silence_frames = 0
                    
                    # Bufferar audio
                    self.audio_buffer.extend(chunk)
                    self.last_audio_chunk = chunk
                    
                    # Callback: audio detectado
                    on_audio_chunk(chunk)
                    
                else:
                    # Silencio
                    if self.vad.speech_detected:
                        # Solo contar silencio si ya detectamos voz antes
                        silence_frames += 1
                
                # Verificar timeout de silencio
                if silence_frames > max_silence_frames:
                    print(f"⏸️ Silencio detectado ({silence_frames}/{max_silence_frames} frames)")
                    
                    # Callback: fin de discurso
                    on_silence_detected()
                    
                    # Resetear para nueva captura
                    self.vad.reset()
                    self.audio_buffer = bytearray()
                    silence_frames = 0
                    
        except Exception as e:
            print(f"✗ Error en capture loop: {e}")
    
    def get_last_audio_chunk(self) -> Optional[bytes]:
        """Retorna el último chunk capturado"""
        return self.last_audio_chunk
    
    def get_buffered_audio_wav(self) -> bytes:
        """
        Retorna el audio buffereado en formato WAV.
        
        Returns:
            Audio en formato WAV (16-bit PCM, mono, 16kHz)
        """
        if not self.audio_buffer:
            return b""
        
        # Crear archivo WAV en memoria
        output = io.BytesIO()
        with wave.open(output, 'wb') as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(self.sample_rate)
            wav_file.writeframes(bytes(self.audio_buffer))
        
        return output.getvalue()
