import asyncio
import os
import sys
import uuid
from pathlib import Path
from typing import Optional

# Configurar path para imports
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
import numpy as np

try:
    import sounddevice as sd
except ImportError:
    print("⚠️ sounddevice no instalado. Audio playback desactivado.")
    sd = None

from config.settings import Settings
from config.container import DIContainer
from app.domain.entities.conversation import Conversation
from app.domain.entities.message import Message, MessageRole
from app.ports.output.llm_port import LLMRequest
from app.ports.output.knowledge_base_port import KnowledgeBaseQuery


class HotelKioskApp:
    """
    Aplicación principal: Kiosco Interactivo del Hotel.
    
    Modos de ejecución:
    - interactive: Escucha micrófono en tiempo real
    - demo: Procesa preguntas predefinidas (sin micrófono)
    """
    
    def __init__(self, settings: Settings):
        """
        Constructor.
        
        Args:
            settings: Configuración validada
        """
        self.settings = settings
        self.container = DIContainer(settings)
        self.conversation: Optional[Conversation] = None
        self.is_running = False
    
    async def initialize(self) -> None:
        """Inicializa todos los componentes"""
        await self.container.initialize()
        
        # Crear conversación
        self.conversation = Conversation(
            session_id=str(uuid.uuid4()),
            language="es"
        )
        
        # Inyectar conversación en el servicio
        assistant_service = self.container.get_assistant_service()
        assistant_service.set_conversation(self.conversation)
        
        # Cargar base de conocimiento
        await self._load_knowledge_base()
    
    async def _load_knowledge_base(self) -> None:
        """Carga documentos en la base de conocimiento"""
        kb_port = self.container.get_kb_port()
        
        # Documentos de ejemplo del hotel
        hotel_docs = [
            "El hotel dispone de recepción 24/7. Teléfono: +34-XXX-XXXX. Email: info@hotel.com",
            "Check-in a las 15:00, check-out a las 11:00. Puedes solicitar check-in anticipado o check-out tardío.",
            "Disponemos de desayuno buffet de 6:30 a 10:30 en el restaurante principal.",
            "El hotel cuenta con gimnasio, piscina climatizada, spa y zona de negocios.",
            "WiFi gratuito en todas las habitaciones. Velocidad: 100 Mbps. Red: HOTEL-WIFI, Contraseña: disponible en recepción.",
            "Tarifas: Habitación individual €80/noche, doble €100/noche, suite €150/noche.",
            "Estacionamiento: €10/noche. Garaje cubierto con vigilancia 24/7.",
            "Ubicación: Centro histórico, a 5 minutos del metro, 10 minutos del aeropuerto.",
            "Tenemos servicio de conserjería para reservar excursiones y restaurantes.",
            "Mascotas permitidas: €15/noche adicionales. Máximo 2 mascotas por habitación.",
        ]
        
        print("📚 Cargando base de conocimiento...")
        await kb_port.add_documents(
            documents=hotel_docs,
            metadata={"source": "hotel_info", "type": "static"}
        )
    
    async def run_interactive_mode(self) -> None:
        """
        Modo interactivo: captura audio del micrófono.
        
        Flujo CORREGIDO (sin eco infinito):
        1. Usuario habla → VAD detecta voz
        2. Silencio → DETIENE micrófono
        3. STT → LLM → TTS → Reproduce respuesta
        4. REINICIA micrófono para siguiente pregunta
        """
        print("\n🎤 Modo interactivo: Habla cuando estés listo, Ctrl+C para salir")
        print("=" * 60)
        
        self.is_running = True
        assistant_service = self.container.get_assistant_service()
        audio_input = self.container.get_audio_input_port()
        
        captured_audio: Optional[bytes] = None
        silence_detected = False
        
        def on_audio_chunk(chunk: bytes) -> None:
            """Callback cuando se captura audio"""
            nonlocal captured_audio
            if captured_audio is None:
                captured_audio = chunk
            else:
                captured_audio += chunk
        
        def on_silence_detected() -> None:
            """Callback cuando se detecta silencio (fin de discurso)"""
            nonlocal silence_detected
            silence_detected = True
        
        try:
            # Iniciar escucha inicial
            audio_input.start_listening(on_audio_chunk, on_silence_detected)
            
            while self.is_running:
                try:
                    # Esperar a que el usuario hable
                    await asyncio.sleep(0.1)
                    
                    # Si detectamos silencio y hay audio capturado suficiente
                    if silence_detected and captured_audio and len(captured_audio) > 1000:
                        # ============================================================
                        # CORRECCIÓN CRÍTICA #1: DETENER MICRÓFONO (Prevenir Eco)
                        # ============================================================
                        audio_input.stop_listening()
                        print("\n🔄 Procesando...")
                        
                        try:
                            # Flujo completo: Audio → Texto → Respuesta → Audio
                            response_text, response_audio = await assistant_service.process_audio(
                                captured_audio
                            )
                            
                            # Mostrar respuesta
                            print(f"\n🤖 Asistente: {response_text}")
                            
                            # Reproducir audio (sin que el mic escuche)
                            if response_audio:
                                await self._play_audio(response_audio)
                            
                            # Mostrar contexto del historial
                            if self.conversation and len(self.conversation.messages) >= 2:
                                print(f"\n📋 Historial:")
                                for msg in self.conversation.messages[-2:]:
                                    content_preview = msg.content[:80] + "..." if len(msg.content) > 80 else msg.content
                                    print(f"  {msg.role.value.upper()}: {content_preview}")
                            
                        except Exception as e:
                            print(f"✗ Error procesando: {e}")
                        
                        finally:
                            # ========================================================
                            # CORRECCIÓN CRÍTICA #1.2: LIMPIAR Y REINICIAR
                            # ========================================================
                            captured_audio = None
                            silence_detected = False
                            
                            print("\n🎤 Escuchando de nuevo...")
                            
                            # Reiniciar micrófono para siguiente pregunta
                            audio_input.start_listening(on_audio_chunk, on_silence_detected)
                        
                except KeyboardInterrupt:
                    self.is_running = False
                    break
                    
                except Exception as e:
                    print(f"✗ Error: {e}")
                    await asyncio.sleep(1)
                    
        finally:
            audio_input.stop_listening()
            print("\n✓ Modo interactivo finalizado")
    
    async def run_demo_mode(self) -> None:
        """
        Modo demo: simula preguntas predefinidas.
        
        Útil para:
        - Testing sin micrófono
        - Demostración
        - Benchmarking
        """
        print("\n🎬 Modo demo: Procesando preguntas de ejemplo")
        print("=" * 60)
        
        questions = [
            "¿Cuál es el horario de check-in?",
            "¿Hay WiFi en las habitaciones?",
            "¿Dónde está ubicado el hotel?",
            "¿Puedo traer mi mascota?",
        ]
        
        assistant_service = self.container.get_assistant_service()
        
        for i, question in enumerate(questions, 1):
            print(f"\n📝 Pregunta {i}: {question}")
            
            try:
                # Simular que viene de STT (saltamos la captura de audio)
                
                # Añadir pregunta al historial
                if self.conversation:
                    self.conversation.add_message(
                        Message(question, MessageRole.USER)
                    )
                
                # Buscar contexto
                kb_port = self.container.get_kb_port()
                kb_results = await kb_port.search(
                    KnowledgeBaseQuery(query_text=question, top_k=3)
                )
                kb_context = "\n".join([r.content for r in kb_results])
                
                # Generar respuesta
                llm_port = self.container.get_llm_port()
                llm_request = LLMRequest(
                    user_message=question,
                    conversation_history=self.conversation.get_recent_context(3) if self.conversation else "",
                    hotel_context=kb_context,
                    language="es"
                )
                
                llm_response = await llm_port.generate(llm_request)
                response_text = llm_response.text
                
                # Guardar en historial
                if self.conversation:
                    self.conversation.add_message(
                        Message(response_text, MessageRole.ASSISTANT)
                    )
                
                print(f"🤖 Respuesta: {response_text}")
                print(f"⏱️ Latencia: {llm_response.latency_ms:.1f}ms")
                
            except Exception as e:
                print(f"✗ Error: {e}")
            
            await asyncio.sleep(1)
        
        print("\n✓ Demo finalizado")
    
    async def _play_audio(self, audio_bytes: bytes) -> None:
        """
        Reproduce audio usando sounddevice.
        Soporta WAV nativo y convierte MP3/otros usando FFmpeg.
        
        Args:
            audio_bytes: Audio en formato WAV o MP3
        """
        if sd is None:
            print("⚠️ sounddevice no disponible, saltando reproducción")
            return
        
        try:
            import io
            import wave
            import subprocess
            import tempfile
            
            # Intentar leer como WAV directo
            try:
                with wave.open(io.BytesIO(audio_bytes), 'rb') as wav_file:
                    frames = wav_file.readframes(wav_file.getnframes())
                    audio_data = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768
                    sample_rate = wav_file.getframerate()
            except wave.Error:
                # Si falla, asumir que es MP3 (ElevenLabs) y convertir con FFmpeg
                # print("ℹ️ Convirtiendo formato de audio...")
                
                with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp_mp3:
                    tmp_mp3.write(audio_bytes)
                    mp3_path = tmp_mp3.name
                
                wav_path = mp3_path.replace(".mp3", ".wav")
                
                # Convertir MP3 a WAV (16kHz, 16-bit, mono)
                subprocess.run([
                    "ffmpeg", "-y", "-i", mp3_path,
                    "-ar", "16000", "-ac", "1", "-f", "wav", wav_path
                ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
                
                # Leer el WAV convertido
                with wave.open(wav_path, 'rb') as wav_file:
                    frames = wav_file.readframes(wav_file.getnframes())
                    audio_data = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768
                    sample_rate = wav_file.getframerate()
                
                # Limpiar temporales
                try:
                    os.unlink(mp3_path)
                    os.unlink(wav_path)
                except:
                    pass
            
            # Reproducir
            print("🔊 Reproduciendo respuesta...")
            sd.play(audio_data, sample_rate)
            sd.wait()
            print("✓ Reproducción finalizada")
            
        except Exception as e:
            print(f"⚠️ No se pudo reproducir audio: {e}")


async def main():
    """Punto de entrada principal"""
    
    # Cargar variables de entorno
    load_dotenv()
    
    # Crear instancia de settings
    settings = Settings()
    
    if settings.debug:
        print("🔍 Modo DEBUG activado")
    
    # Crear aplicación
    app = HotelKioskApp(settings)
    
    try:
        # Inicializar
        await app.initialize()
        
        # Elegir modo de ejecución
        mode = sys.argv[1] if len(sys.argv) > 1 else "interactive"
        
        if mode == "demo":
            print("\n✓ Iniciando en MODO DEMO")
            await app.run_demo_mode()
        else:
            print("\n✓ Iniciando en MODO INTERACTIVO")
            await app.run_interactive_mode()
        
    except KeyboardInterrupt:
        print("\n\n👋 Interrupción del usuario")
    
    except Exception as e:
        print(f"\n✗ Error fatal: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    # Ejecutar
    asyncio.run(main())
