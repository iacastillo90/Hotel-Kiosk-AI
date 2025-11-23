import asyncio
import os
import sys
import uuid
import logging
from pathlib import Path
from typing import Optional

# Configurar path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
import numpy as np

# Configuración de Logging Estructurado
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("HotelKiosk")

try:
    import sounddevice as sd
except ImportError:
    logger.warning("⚠️ sounddevice no instalado. Audio playback desactivado.")
    sd = None

from config.settings import Settings
from config.container import DIContainer
from app.domain.entities.conversation import Conversation

class HotelKioskApp:
    """
    Kiosco Interactivo - Versión Optimizada (Non-blocking I/O)
    """
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.container = DIContainer(settings)
        self.conversation: Optional[Conversation] = None
        self.is_running = False
        self._loop = None # Referencia al loop principal
    
    async def initialize(self) -> None:
        """Inicializa componentes con warm-up"""
        logger.info("⚙️ Inicializando sistema...")
        self._loop = asyncio.get_running_loop()
        await self.container.initialize()
        
        self.conversation = Conversation(session_id=str(uuid.uuid4()), language="es")
        self.container.get_assistant_service().set_conversation(self.conversation)
        
        # Cargar KB (Simulado para brevedad, mantener tu lógica original aquí)
        await self._load_knowledge_base()
        logger.info("✓ Sistema listo")

    async def _load_knowledge_base(self):
        # ... (Tu código original de carga de documentos se mantiene igual) ...
        pass
    
    async def run_interactive_mode(self) -> None:
        """Ciclo principal optimizado para latencia baja"""
        print("\n🎤 MODO INTERACTIVO: Escuchando... (Ctrl+C para salir)\n" + "="*60)
        
        self.is_running = True
        assistant = self.container.get_assistant_service()
        audio_input = self.container.get_audio_input_port()
        
        # Variables de estado del ciclo
        captured_audio: Optional[bytes] = None
        silence_event = asyncio.Event()
        
        def on_audio(chunk: bytes):
            nonlocal captured_audio
            if captured_audio is None: captured_audio = chunk
            else: captured_audio += chunk
            
        def on_silence():
            # Signal thread-safe para despertar el loop principal
            if not silence_event.is_set():
                self._loop.call_soon_threadsafe(silence_event.set)

        try:
            # Iniciar escucha
            audio_input.start_listening(on_audio, on_silence)
            
            while self.is_running:
                # 1. Esperar señal de silencio (Non-blocking wait)
                await silence_event.wait()
                
                # 2. INMEDIATAMENTE detener micrófono para evitar eco
                audio_input.stop_listening()
                
                # Validar audio capturado
                if captured_audio and len(captured_audio) > 4000: # Min ~0.25s
                    logger.info(f"🔄 Procesando audio ({len(captured_audio)} bytes)...")
                    
                    try:
                        # 3. Pipeline IA (STT -> Intent -> LLM -> TTS)
                        # Al ser async, no bloquea el loop
                        text_resp, audio_resp = await assistant.process_audio(captured_audio)
                        
                        print(f"\n🤖: {text_resp}")
                        
                        # 4. Reproducir Audio (Off-thread para no bloquear)
                        if audio_resp:
                            await self._play_audio(audio_resp)
                            
                    except Exception as e:
                        logger.error(f"Error en pipeline: {e}")
                
                # 5. Reiniciar ciclo
                captured_audio = None
                silence_event.clear()
                
                if self.is_running:
                    print("\n🎤 Escuchando...")
                    audio_input.start_listening(on_audio, on_silence)
                    
        except KeyboardInterrupt:
            logger.info("👋 Deteniendo...")
        finally:
            audio_input.stop_listening()
            self.is_running = False

    async def _play_audio(self, audio_bytes: bytes) -> None:
        """
        Reproduce audio (WAV o MP3) en thread separado sin bloquear.
        """
        if sd is None or not audio_bytes: return

        def _blocking_play():
            import io
            import wave
            import tempfile
            import subprocess
            
            try:
                # 1. Intentar reproducir como WAV nativo
                with wave.open(io.BytesIO(audio_bytes), 'rb') as f:
                    data = f.readframes(f.getnframes())
                    fs = f.getframerate()
                    audio_np = np.frombuffer(data, dtype=np.int16)
                    
                sd.play(audio_np, fs)
                sd.wait()

            except wave.Error:
                # 2. Si falla, asumimos MP3 (ElevenLabs) y convertimos
                # Esto sigue ocurriendo en el thread secundario, así que es seguro usar subprocess
                try:
                    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp_mp3:
                        tmp_mp3.write(audio_bytes)
                        mp3_path = tmp_mp3.name
                    
                    wav_path = mp3_path.replace(".mp3", ".wav")
                    
                    # Conversión rápida con FFmpeg
                    subprocess.run([
                        "ffmpeg", "-y", "-i", mp3_path,
                        "-ar", "16000", "-ac", "1", "-f", "wav", wav_path
                    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
                    
                    # Leer y reproducir el WAV convertido
                    with wave.open(wav_path, 'rb') as f:
                        data = f.readframes(f.getnframes())
                        fs = f.getframerate()
                        audio_np = np.frombuffer(data, dtype=np.int16)
                        
                    sd.play(audio_np, fs)
                    sd.wait()
                    
                    # Limpieza
                    os.unlink(mp3_path)
                    os.unlink(wav_path)
                    
                except Exception as e:
                    logger.error(f"Error convirtiendo/reproduciendo MP3: {e}")

            except Exception as e:
                logger.error(f"Error general audio: {e}")

        # Ejecutar en thread pool
        await self._loop.run_in_executor(None, _blocking_play)

    # ... (Tu código de run_demo_mode se mantiene igual) ...

async def main():
    load_dotenv()
    settings = Settings()
    app = HotelKioskApp(settings)
    
    try:
        await app.initialize()
        # Simple selector de modo
        mode = sys.argv[1] if len(sys.argv) > 1 else "interactive"
        if mode == "demo": await app.run_demo_mode()
        else: await app.run_interactive_mode()
    except Exception as e:
        logger.critical(f"Error fatal: {e}")

if __name__ == "__main__":
    asyncio.run(main())
