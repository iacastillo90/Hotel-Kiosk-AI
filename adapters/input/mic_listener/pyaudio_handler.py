import pyaudio
import numpy as np
import threading
import queue
from typing import Optional
import time


class PyAudioHandler:
    """
    Captura de audio usando PyAudio con thread separado.
    
    PyAudio es un binding de Python para PortAudio, que permite
    captura de audio cross-platform (Windows, Mac, Linux).
    
    Arquitectura:
    - Thread principal: Lógica de la app
    - Thread secundario: Captura continua de audio
    - Queue: Comunicación entre threads (thread-safe)
    
    Ventajas:
    - No bloquea el event loop principal
    - Captura continua sin drops
    - Buffer automático
    """
    
    def __init__(self,
                 sample_rate: int = 16000,
                 chunk_size: int = 1024,
                 channels: int = 1,
                 device_index: Optional[int] = None):
        """
        Constructor.
        
        Args:
            sample_rate: 16000 Hz es estándar para Whisper
            chunk_size: Frames por buffer (1024 = ~64ms a 16kHz)
            channels: Mono (1) o Estéreo (2)
            device_index: Índice del dispositivo (None = default)
        """
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.channels = channels
        self.device_index = device_index
        
        self.pa = pyaudio.PyAudio()
        self.stream: Optional[pyaudio.Stream] = None
        self.is_listening = False
        
        # Queue para pasar audio entre threads
        self.audio_queue: queue.Queue = queue.Queue(maxsize=100)
        self.listener_thread: Optional[threading.Thread] = None
        
        print(f"🎤 PyAudio inicializado")
        self._list_devices()
    
    def _list_devices(self):
        """Lista dispositivos de audio disponibles"""
        print(f"  Dispositivos de audio disponibles:")
        for i in range(self.pa.get_device_count()):
            info = self.pa.get_device_info_by_index(i)
            if info['maxInputChannels'] > 0:
                print(f"    [{i}] {info['name']} (Input: {info['maxInputChannels']} ch)")
    
    def start_listening(self) -> None:
        """Inicia la captura en un thread separado"""
        if self.is_listening:
            print("⚠️ Ya estamos escuchando")
            return
        
        self.is_listening = True
        self.listener_thread = threading.Thread(
            target=self._listening_loop,
            daemon=True
        )
        self.listener_thread.start()
        print("✓ Micrófono activado")
    
    def stop_listening(self) -> None:
        """Detiene la captura"""
        self.is_listening = False
        if self.listener_thread:
            self.listener_thread.join(timeout=2.0)
        
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        
        print("✓ Micrófono desactivado")
    
    def _listening_loop(self) -> None:
        """Loop de captura en el thread secundario"""
        try:
            self.stream = self.pa.open(
                format=pyaudio.paInt16,  # 16-bit PCM
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                input_device_index=self.device_index,
                frames_per_buffer=self.chunk_size,
                stream_callback=None
            )
            
            print(f"🔴 Grabando... (sample_rate={self.sample_rate}, chunk={self.chunk_size})")
            
            while self.is_listening:
                try:
                    # Leer chunk del micrófono (bloqueante)
                    audio_chunk = self.stream.read(
                        self.chunk_size,
                        exception_on_overflow=False
                    )
                    
                    # Añadir a queue (no bloquear si está llena)
                    try:
                        self.audio_queue.put_nowait(audio_chunk)
                    except queue.Full:
                        print("⚠️ Audio queue llena, descartando frame")
                        
                except Exception as e:
                    print(f"✗ Error leyendo audio: {e}")
                    break
                    
        except Exception as e:
            print(f"✗ Error stream PyAudio: {e}")
        finally:
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()
    
    def get_chunk(self, timeout_s: float = 0.5) -> Optional[bytes]:
        """
        Obtiene un chunk de audio del queue.
        
        Args:
            timeout_s: Timeout en segundos
            
        Returns:
            Audio bytes o None si timeout
        """
        try:
            return self.audio_queue.get(timeout=timeout_s)
        except queue.Empty:
            return None
    
    def queue_size(self) -> int:
        """Retorna el tamaño actual del queue"""
        return self.audio_queue.qsize()
    
    def __del__(self):
        """Destructor: limpiar recursos"""
        try:
            if self.is_listening:
                self.stop_listening()
            self.pa.terminate()
        except:
            pass
