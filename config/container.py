from typing import Optional

from config.settings import Settings
from app.ports.output.llm_port import LLMPort
from app.ports.output.stt_port import STTPort
from app.ports.output.tts_port import TTSPort
from app.ports.output.tts_port import TTSPort
from app.ports.output.knowledge_base_port import KnowledgeBasePort
from app.ports.output.repository_port import RepositoryPort
from app.ports.output.affect_port import AffectPort
from app.ports.input.audio_input_port import AudioInputPort
from app.domain.services.assistant_service import AssistantService

class DIContainer:
    """
    Contenedor de Inyección de Dependencias (Singleton Pattern).
    
    Responsable de:
    1. Crear instancias de adaptadores
    2. Cablear dependencias
    3. Garantizar una sola instancia (singleton)
    
    Ventajas:
    - Desacoplamiento: Los servicios no saben qué adaptadores usan
    - Testabilidad: Fácil inyectar mocks
    - Configurabilidad: Cambiar implementaciones sin modificar código
    """
    
    def __init__(self, settings: Settings):
        """
        Constructor.
        
        Args:
            settings: Configuración validada
        """
        self.settings = settings
        
        # Instancias singleton (lazy loading)
        self._llm_port: Optional[LLMPort] = None
        self._stt_port: Optional[STTPort] = None
        self._tts_port: Optional[TTSPort] = None
        self._tts_port: Optional[TTSPort] = None
        self._kb_port: Optional[KnowledgeBasePort] = None
        self._repository_port: Optional[RepositoryPort] = None
        self._audio_input_port: Optional[AudioInputPort] = None
        self._affect_port: Optional[AffectPort] = None
        self._assistant_service: Optional[AssistantService] = None
    
    def get_affect_port(self) -> AffectPort:
        """Factory para AffectPort (singleton)"""
        if self._affect_port is None:
            from adapters.output.affect.acoustic_adapter import AcousticAdapter
            self._affect_port = AcousticAdapter()
        return self._affect_port
    
    def get_llm_port(self) -> LLMPort:
        """
        Factory para LLM (singleton).
        
        Returns:
            Implementación del contrato LLMPort
        """
        if self._llm_port is None:
            if self.settings.llm_provider == "gemini":
                from adapters.output.llm.gemini_adapter import GeminiAdapter
                self._llm_port = GeminiAdapter(self.settings.google_api_key)
            elif self.settings.llm_provider == "openai":
                from adapters.output.llm.openai_adapter import OpenAIAdapter
                self._llm_port = OpenAIAdapter(self.settings.openai_api_key)
            else:
                raise ValueError(f"LLM provider no soportado: {self.settings.llm_provider}")
        
        return self._llm_port
    
    def get_stt_port(self) -> STTPort:
        """
        Factory para STT (singleton).
        
        Returns:
            Implementación del contrato STTPort
        """
        if self._stt_port is None:
            from adapters.output.speech.whisper_local_adapter import WhisperLocalAdapter
            self._stt_port = WhisperLocalAdapter(
                model_size=self.settings.whisper_model,
                language=self.settings.stt_language
            )
        
        return self._stt_port
    
    def get_tts_port(self) -> TTSPort:
        """
        Factory para TTS (singleton) con fallback automático.
        
        Returns:
            Implementación del contrato TTSPort
        """
        if self._tts_port is None:
            try:
                if self.settings.tts_provider == "elevenlabs":
                    from adapters.output.speech.elevenlabs_adapter import ElevenLabsAdapter
                    self._tts_port = ElevenLabsAdapter(
                        api_key=self.settings.elevenlabs_api_key,
                        voice_id=self.settings.tts_voice_id
                    )
                elif self.settings.tts_provider == "pyttsx3":
                    from adapters.output.speech.pyttsx3_fallback_adapter import Pyttsx3FallbackAdapter
                    self._tts_port = Pyttsx3FallbackAdapter()
            except Exception as e:
                print(f"⚠️ Error inicializando TTS principal: {e}")
                print(f"  Usando fallback pyttsx3...")
                from adapters.output.speech.pyttsx3_fallback_adapter import Pyttsx3FallbackAdapter
                self._tts_port = Pyttsx3FallbackAdapter()
        
        return self._tts_port
    
    def get_kb_port(self) -> KnowledgeBasePort:
        """
        Factory para Knowledge Base (singleton).
        
        Returns:
            Implementación del contrato KnowledgeBasePort
        """
        if self._kb_port is None:
            from adapters.output.database.chroma_adapter import ChromaDBAdapter
            self._kb_port = ChromaDBAdapter(db_path=self.settings.chroma_db_path)
        
        return self._kb_port
    
    def get_repository_port(self) -> RepositoryPort:
        """
        Factory inteligente para Repository.
        Decide si usar MySQL real o Mock (memoria) según configuración.
        """
        if self._repository_port is None:
            # Usamos la variable del settings.py, no os.getenv directo
            # Esto mantiene la configuración centralizada.
            if self.settings.use_database:
                print("🔌 Conectando a Base de Datos MySQL...")
                from adapters.output.database.mysql_adapter import MySQLAdapter
                
                self._repository_port = MySQLAdapter(
                    host=self.settings.db_host,
                    user=self.settings.db_user,
                    password=self.settings.db_password,
                    database=self.settings.db_name,
                    port=self.settings.db_port
                )
            else:
                print("⚠️ Modo DB desactivado: Usando Mock en memoria")
                from adapters.output.database.mock_adapter import MockRepositoryAdapter
                self._repository_port = MockRepositoryAdapter()
        
        return self._repository_port
    
    def get_audio_input_port(self) -> AudioInputPort:
        """
        Factory para entrada de audio (singleton).
        
        Returns:
            Implementación del contrato AudioInputPort
        """
        if self._audio_input_port is None:
            from adapters.input.mic_listener_adapter import MicListenerAdapter
            self._audio_input_port = MicListenerAdapter(
                sample_rate=self.settings.sample_rate,
                silence_timeout_ms=self.settings.silence_timeout_ms
            )
        
        return self._audio_input_port
    
    def get_llm_chain(self) -> list[LLMPort]:
        """Devuelve cadena de LLMs (Primario -> Fallback)"""
        chain = []
        
        # 1. Primario (según config)
        chain.append(self.get_llm_port())
        
        # 2. Fallback: OpenAI (si el primario es Gemini y tenemos key)
        if self.settings.llm_provider == "gemini" and self.settings.openai_api_key:
            try:
                from adapters.output.llm.openai_adapter import OpenAIAdapter
                chain.append(OpenAIAdapter(self.settings.openai_api_key))
            except Exception as e:
                print(f"⚠️ No se pudo cargar OpenAI fallback: {e}")
                
        # 3. Fallback: Gemini (si el primario es OpenAI y tenemos key)
        elif self.settings.llm_provider == "openai" and self.settings.google_api_key:
            try:
                from adapters.output.llm.gemini_adapter import GeminiAdapter
                chain.append(GeminiAdapter(self.settings.google_api_key))
            except Exception as e:
                print(f"⚠️ No se pudo cargar Gemini fallback: {e}")
                
        return chain

    def get_tts_chain(self) -> list[TTSPort]:
        """Devuelve cadena de TTS (Primario -> Fallback)"""
        chain = []
        
        # 1. Primario
        chain.append(self.get_tts_port())
        
        # 2. Fallback (Pyttsx3) - Si el primario no es ya pyttsx3
        # Importamos Pyttsx3FallbackAdapter para verificar tipo
        from adapters.output.speech.pyttsx3_fallback_adapter import Pyttsx3FallbackAdapter
        
        if not isinstance(chain[0], Pyttsx3FallbackAdapter):
             chain.append(Pyttsx3FallbackAdapter())
             
        return chain

    def get_prompt_factory(self) -> 'PromptFactory':
        """Factory para PromptFactory (singleton)"""
        from app.domain.services.prompt_factory import PromptFactory
        if not hasattr(self, '_prompt_factory') or self._prompt_factory is None:
            self._prompt_factory = PromptFactory()
        return self._prompt_factory

    def get_command_bus(self) -> 'CommandBus':
        """Factory para CommandBus (singleton)"""
        # Importación local para evitar ciclos
        from app.domain.services.command_bus import CommandBus
        
        if not hasattr(self, '_command_bus') or self._command_bus is None:
            self._command_bus = CommandBus(
                llm_chain=self.get_llm_chain(),
                tts_chain=self.get_tts_chain(),
                kb_port=self.get_kb_port(),
                repository_port=self.get_repository_port(),
                prompt_factory=self.get_prompt_factory()
            )
        return self._command_bus

    def get_assistant_service(self) -> AssistantService:
        """
        Factory para AssistantService (singleton).
        """
        if self._assistant_service is None:
            self._assistant_service = AssistantService(
                stt_port=self.get_stt_port(),
                affect_port=self.get_affect_port(),
                command_bus=self.get_command_bus()
            )
        
        return self._assistant_service
    
    async def initialize(self) -> None:
        """
        Inicializa y valida todos los componentes.
        
        Ejecuta:
        1. Validación de configuración
        2. Carga de componentes (lazy loading)
        3. Health checks
        """
        print("\n🚀 Inicializando Hotel Kiosk AI...")
        print("=" * 60)
        
        try:
            # Validar settings
            self.settings.validate()
            
            # Cargar componentes (con lazy loading)
            print("\n📦 Cargando componentes:")
            
            print("  1. STT (Whisper local)...", end=" ")
            stt = self.get_stt_port()
            print(f"✓ ({self.settings.whisper_model})")
            
            print("  2. LLM...", end=" ")
            llm = self.get_llm_port()
            print(f"✓ ({self.settings.llm_provider})")
            
            print("  3. TTS...", end=" ")
            tts = self.get_tts_port()
            print("✓")
            
            print("  4. Knowledge Base...", end=" ")
            kb = self.get_kb_port()
            print("✓")
            
            print("  5. Database (MySQL)...", end=" ")
            repo = self.get_repository_port()
            print("✓")

            print("  6. Audio Input...", end=" ")
            audio = self.get_audio_input_port()
            print("✓")
            
            # Health checks
            print("\n🏥 Health checks:")
            
            print("  LLM...", end=" ")
            llm_ok = await llm.health_check()
            print("✓" if llm_ok else "✗ (Verificar API keys)")
            
            print("  TTS...", end=" ")
            tts_ok = await tts.health_check()
            print("✓" if tts_ok else "⚠️ (Fallback disponible)")
            
            print("\n" + "=" * 60)
            print("✓ Sistema listo\n")
            
        except Exception as e:
            print(f"\n✗ Error inicializando: {e}")
            raise
